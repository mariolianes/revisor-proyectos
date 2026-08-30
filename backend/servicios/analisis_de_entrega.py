"""Del archivo al par de salidas.

Aquí se juntan las piezas de las tareas anteriores: se lee la entrega, se le
pide el juicio al motor, se verifica lo que devuelve, y salen las dos
salidas -el informe interno y el borrador de devolución-. Aquí viven las
reglas del §5.2 del diseño.

Un reintento, no más. Una respuesta que no encaja en el formulario -en
cualquiera de los dos formularios que se piden, el del análisis o el de la
devolución- es el fallo más común y el más barato de resolver, así que se
pide otra vez. Si vuelve a fallar, no es un tropiezo: es que algo no va
bien, y insistir solo gasta dinero.

El estado no miente, y no se inventa uno nuevo para decirlo. Si el motor no
ha llegado a entregar un análisis -sin red, sin clave, cuota agotada, una
respuesta que no encaja ni a la segunda- no se guarda nada y la entrega
sigue en RECIBIDO. La constancia de ese intento fallido no es un estado
nuevo en el flujo: es la excepción que sube, con el motivo que trae el
proveedor, a quien ya tenía la ficha de la entrega entre las manos y sabe
a cuál se refería.

El informe no depende del borrador. Son dos salidas distintas para dos
lectores distintos, y una vez que el análisis está verificado, el informe se
compone sin volver a llamar al motor: no hay forma de que la redacción del
borrador -que sí depende del motor, otra vez, y puede fallar por su cuenta o
levantar `BorradorNoValido`- invalide un informe que ya es correcto. Si eso
ocurre, la entrega pasa a ANALIZADO -el análisis se completó y es lo que hoy
deja tomar una decisión al profesor- y se levanta `InformeSinBorrador`, que
lleva el informe y la entrega ya actualizada: quien reciba el fallo no
pierde lo que sí es válido, y decide él mismo si pide la redacción otra vez
o la escribe a mano.

El texto del trabajo no queda en nada de lo que aquí se construye. Pasa por
esta función como variable local -hace falta para pedir el análisis y para
verificar sus citas- y no entra en `Correccion`, ni en `Informe` ni en
`Devolucion`, ni en las excepciones que este módulo levanta: ninguno de esos
tipos tiene un campo para él, siguiendo el mismo criterio que ya cerró esto
en la Parte A -`Medidas.texto_plano` va con `exclude=True`, no es el
endpoint el que lo esconde.
"""

from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, ConfigDict

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.instruccion import construir
from backend.analisis.proveedor import ErrorDelProveedor, ProveedorAnalisis, RespuestaNoValida
from backend.analisis.verificacion import verificar
from backend.extraccion.lectura import PdfIlegible
from backend.persistencia.modelos import Almacen, EntregaRegistrada
from backend.salidas.borrador import BorradorNoValido, Devolucion, componer
from backend.salidas.informe import Informe, componer_informe
from backend.servicios.lectura_objetiva import leer

_T = TypeVar("_T")

ANALIZADO = "ANALIZADO"


class Correccion(BaseModel):
    """Las dos salidas de una entrega, con la ficha que las origina."""

    model_config = ConfigDict(extra="forbid")

    entrega: EntregaRegistrada
    informe: Informe
    devolucion: Devolucion
    motor: str


class InformeSinBorrador(Exception):
    """El análisis se completó y el informe es válido, pero el borrador no.

    La entrega ya ha pasado a ANALIZADO cuando esta excepción sube -el
    análisis y el informe no dependen del borrador, así que no hay motivo
    para retener ese avance-, y `informe` lleva el documento entero para que
    quien capture el fallo no tenga que rehacer el análisis para recuperar
    lo que ya era correcto. Esta función no decide qué hacer después -pedir
    la redacción otra vez, escribirla a mano-; eso es de quien la llama.
    """

    def __init__(self, mensaje: str, entrega: EntregaRegistrada, informe: Informe) -> None:
        super().__init__(mensaje)
        self.entrega = entrega
        self.informe = informe


def _con_un_reintento(accion: Callable[[], _T]) -> _T:
    """Ejecuta `accion`; si el motor responde con un formulario que no
    encaja, la repite una sola vez.

    Es el único fallo que merece reintento -el más común y el más barato de
    resolver-. Cualquier otro (`ErrorDelProveedor` que no sea
    `RespuestaNoValida`: sin red, sin clave, cuota agotada) se deja subir a
    la primera, y una segunda `RespuestaNoValida` también: dos formularios
    mal rellenados seguidos ya no es un tropiezo.
    """
    try:
        return accion()
    except RespuestaNoValida:
        return accion()


def analizar_entrega(
    raiz: Path,
    carpeta: Path,
    version: str,
    almacen: Almacen,
    proveedor: ProveedorAnalisis,
    entrega: EntregaRegistrada,
) -> Correccion:
    """Lee, analiza, verifica, compone y guarda.

    Si el archivo no se puede leer, no llega al motor: `leer` ya deja la
    entrega en BLOQUEADO con su motivo, y pedir un análisis sin texto solo
    gastaría una llamada para nada. Si el motor no llega a entregar un
    análisis útil -ni a la primera ni al reintento-, no se guarda nada y la
    entrega sigue en el estado en el que estaba: un estado que miente es
    peor que un estado atrasado.
    """
    ficha = leer(raiz, carpeta, version, almacen, entrega)
    if ficha.medidas is None:
        raise PdfIlegible(
            ficha.entrega.motivo_bloqueo or "No se ha podido leer el archivo."
        )

    texto = ficha.medidas.texto_plano
    instruccion = construir(raiz, version, entrega.fase)

    # Para el bloque «Continuidad» del informe (§17.1, D-012 en
    # `docs/decisions.md`). `leer()` ya consulta `anterior_de` por su cuenta
    # -para la comparación de texto que deja en `ficha.evolucion`-, pero no
    # devuelve la entrega anterior en sí, así que se vuelve a pedir aquí: es
    # una segunda consulta al almacén, no una llamada al motor, y mantiene
    # `componer_informe` sin depender de `Almacen` para nada más que lo que
    # ya recibe. Sin corrección anterior guardada, `prioridades_anteriores`
    # queda en `None` -no en una lista vacía-, para que el informe pueda
    # distinguir «no hay análisis anterior» de «lo había y no dejó
    # prioridades».
    anterior = almacen.anterior_de(entrega.codigo_alumno, entrega.fase, entrega.version)
    correccion_anterior = almacen.correccion_de(anterior.id) if anterior is not None else None
    prioridades_anteriores = (
        correccion_anterior.informe.prioridades if correccion_anterior is not None else None
    )

    crudo = _con_un_reintento(
        lambda: proveedor.analizar(instruccion, texto, AnalisisDelMotor)
    )
    analisis = verificar(raiz, version, entrega.fase, texto, crudo)
    informe = componer_informe(
        raiz, version, entrega, ficha, analisis, proveedor.nombre,
        hay_entrega_anterior=anterior is not None,
        prioridades_anteriores=prioridades_anteriores,
    )

    try:
        devolucion = _con_un_reintento(
            lambda: componer(raiz, version, proveedor, analisis)
        )
    except (ErrorDelProveedor, BorradorNoValido) as fallo:
        actualizada = almacen.cambiar_estado(entrega.id, ANALIZADO, None) or entrega
        raise InformeSinBorrador(
            f"El informe se ha generado y ha quedado guardado, pero el "
            f"borrador de devolución no se ha podido completar: {fallo}",
            entrega=actualizada,
            informe=informe,
        ) from fallo

    actualizada = almacen.cambiar_estado(entrega.id, ANALIZADO, None) or entrega
    return Correccion(
        entrega=actualizada,
        informe=informe,
        devolucion=devolucion,
        motor=proveedor.nombre,
    )
