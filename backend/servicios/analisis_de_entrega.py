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

Antes de que ese texto salga hacia `proveedor.analizar`, pasa por
`backend.privacidad.minimizacion.minimizar`: sustituye el nombre del alumno
-si `listado` lo conoce- y retira DNI, correos y teléfonos con las mismas
expresiones de R6. A partir de ahí, `texto` dentro de esta función YA es el
texto minimizado, no el original: se usa así tanto para pedir el análisis
como para verificar sus citas (`verificar()`, más abajo), porque el motor
nunca vio el original y sus citas se refieren a lo que sí vio. Ver el
docstring de `backend.privacidad.minimizacion` para por qué esto es
minimización de mejor esfuerzo, no una garantía de anonimización, y qué le
dice el sistema al docente cuando no puede comprobar que quedó limpio -el
`aviso_privacidad` de `Correccion`, más abajo-.

Esta función también deja constancia de lo que ha costado la ejecución -
`backend.persistencia.consumo.RegistroDeConsumo`, vía `almacen.
registrar_consumo`-, en los tres desenlaces posibles. Es telemetría, no
parte del resultado: si registrar el consumo falla, se avisa por el log
-nunca con el texto ni la instrucción, solo tipo de fallo e identificador de
entrega- y el análisis sigue su curso, porque un profesor que ya ha pagado
la llamada no debería perder el resultado por un fallo al escribir cuánto
costó.
"""

import logging
import time
from datetime import date
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, ConfigDict

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.instruccion import construir
from backend.analisis.precios import estimar_coste
from backend.analisis.proveedor import ErrorDelProveedor, ProveedorAnalisis, RespuestaNoValida
from backend.analisis.verificacion import verificar
from backend.extraccion.lectura import PdfIlegible
from backend.persistencia.consumo import RegistroDeConsumo
from backend.persistencia.modelos import Almacen, EntregaRegistrada
from backend.privacidad.listado_local import ListadoLocal
from backend.privacidad.minimizacion import minimizar
from backend.salidas.borrador import BorradorNoValido, Devolucion, componer
from backend.salidas.informe import Informe, componer_informe
from backend.servicios.lectura_objetiva import leer

_T = TypeVar("_T")

ANALIZADO = "ANALIZADO"

logger = logging.getLogger(__name__)


class Correccion(BaseModel):
    """Las dos salidas de una entrega, con la ficha que las origina."""

    model_config = ConfigDict(extra="forbid")

    entrega: EntregaRegistrada
    informe: Informe
    devolucion: Devolucion
    motor: str
    # Lo que la minimización no pudo comprobar antes de enviar el texto al
    # motor -típicamente, que el listado local no tenía nombre para este
    # código de alumno-. Cadena vacía cuando no hay nada que decir, nunca
    # `None`: así compone igual que `FichaDeLectura.aviso`
    # (`backend/servicios/lectura_objetiva.py`), sin que quien lo muestre
    # tenga que distinguir los dos casos.
    aviso_privacidad: str = ""


class InformeSinBorrador(Exception):
    """El análisis se completó y el informe es válido, pero el borrador no.

    La entrega ya ha pasado a ANALIZADO cuando esta excepción sube -el
    análisis y el informe no dependen del borrador, así que no hay motivo
    para retener ese avance-, y `informe` lleva el documento entero para que
    quien capture el fallo no tenga que rehacer el análisis para recuperar
    lo que ya era correcto. Esta función no decide qué hacer después -pedir
    la redacción otra vez, escribirla a mano-; eso es de quien la llama.
    """

    def __init__(
        self,
        mensaje: str,
        entrega: EntregaRegistrada,
        informe: Informe,
        aviso_privacidad: str = "",
    ) -> None:
        super().__init__(mensaje)
        self.entrega = entrega
        self.informe = informe
        self.aviso_privacidad = aviso_privacidad


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


class MedidorDeConsumo:
    """Lo que ha costado, en tokens y en tiempo, una ejecución de análisis
    entera -hasta dos llamadas reales al proveedor, cada una con hasta dos
    intentos-.

    `registrar_intento` se llama alrededor de cada llamada a `proveedor.
    analizar` (directa, o dentro de `salidas.borrador.componer`), tanto si
    tuvo éxito como si no: la duración y el intento cuentan siempre que se
    hizo una llamada real, y los tokens se suman solo cuando el proveedor
    deja consumo legible (`getattr(proveedor, "ultimo_consumo", None)`).

    Distinguir «se hizo una llamada que no dejó tokens legibles» de «no se
    hizo ninguna llamada» exige más que mirar `ultimo_consumo`: `componer()`
    (`backend/salidas/borrador.py`) puede devolver una `Devolucion` vacía
    sin llegar a llamar al proveedor -cuando no hay ni fortalezas ni
    prioridades de las que redactar nada-, y en ese caso `ultimo_consumo`
    seguiría teniendo el valor de la llamada ANTERIOR (la del análisis), no
    `None`. Por eso se compara `proveedor.numero_de_llamadas` antes y
    después: solo si sube de verdad hubo una llamada real que contar.
    """

    def __init__(self, paginas: int, caracteres_texto: int) -> None:
        self.paginas = paginas
        self.caracteres_texto = caracteres_texto
        self.intentos = 0
        self.duracion_ms = 0
        self.tokens_entrada = 0
        self.tokens_salida = 0
        self.tokens_entrada_cacheados = 0
        self._hay_tokens = False

    def registrar_intento(self, proveedor: ProveedorAnalisis, duracion_ms: int) -> None:
        self.intentos += 1
        self.duracion_ms += duracion_ms
        consumo = getattr(proveedor, "ultimo_consumo", None)
        if consumo is not None:
            self._hay_tokens = True
            self.tokens_entrada += consumo.tokens_entrada
            self.tokens_salida += consumo.tokens_salida
            self.tokens_entrada_cacheados += consumo.tokens_entrada_cacheados

    @property
    def hay_tokens(self) -> bool:
        return self._hay_tokens


def _medir(medidor: MedidorDeConsumo, proveedor: ProveedorAnalisis, funcion: Callable[[], _T]) -> _T:
    """Ejecuta `funcion` -una llamada directa a `proveedor.analizar`, o
    `salidas.borrador.componer`, que puede o no llamarlo por dentro- y
    cuenta, si de verdad hizo una llamada real, cuánto tardó y cuántos
    tokens dejó.

    Cuenta la llamada tanto si `funcion` termina bien como si levanta una
    excepción -un `RespuestaNoValida` también costó dinero-, por eso se mide
    en un `finally` y no solo en el camino feliz.
    """
    llamadas_antes = getattr(proveedor, "numero_de_llamadas", None)
    inicio = time.monotonic()
    try:
        return funcion()
    finally:
        duracion_ms = int((time.monotonic() - inicio) * 1000)
        llamadas_despues = getattr(proveedor, "numero_de_llamadas", None)
        hubo_llamada_real = (
            llamadas_antes is not None
            and llamadas_despues is not None
            and llamadas_despues > llamadas_antes
        )
        if hubo_llamada_real:
            medidor.registrar_intento(proveedor, duracion_ms)


def _registrar_consumo(
    raiz: Path,
    almacen: Almacen,
    medidor: MedidorDeConsumo,
    proveedor: ProveedorAnalisis,
    entrega: EntregaRegistrada,
    estado: str,
    causa_error: str | None,
) -> None:
    """Deja constancia del gasto de esta ejecución, si hubo alguno que
    contar. Nunca deja que ese registro tumbe el análisis: ver el docstring
    del módulo.
    """
    if medidor.intentos == 0:
        # `proveedor.nombre == "simulado"` no hace ninguna llamada real -y
        # tampoco tiene `numero_de_llamadas`-, así que `medidor.intentos`
        # se queda en 0: no hay nada que registrar, ni dinero que contar.
        return

    registrar = getattr(almacen, "registrar_consumo", None)
    if registrar is None:
        # Un almacén -o un doble de prueba- que no implementa esta
        # capacidad opcional. No es un `Protocol` obligatorio (ver el
        # docstring de `backend/persistencia/consumo.py`): degradar en
        # silencio aquí es preferible a que cada doble de prueba existente
        # tenga que aprender un método nuevo para poder seguir analizando.
        return

    coste_estimado_usd: float | None = None
    tarifa_aplicada: str | None = None
    if medidor.hay_tokens:
        modelo_para_tarifa = getattr(proveedor, "modelo", None) or proveedor.nombre
        coste_estimado_usd, tarifa_aplicada = estimar_coste(
            raiz, modelo_para_tarifa, medidor.tokens_entrada, medidor.tokens_salida,
            medidor.tokens_entrada_cacheados, fecha=date.today(),
        )

    registro = RegistroDeConsumo(
        entrega_id=entrega.id,
        modelo=proveedor.nombre,
        tokens_entrada=medidor.tokens_entrada if medidor.hay_tokens else None,
        tokens_salida=medidor.tokens_salida if medidor.hay_tokens else None,
        tokens_entrada_cacheados=(
            medidor.tokens_entrada_cacheados if medidor.hay_tokens else None
        ),
        coste_estimado_usd=coste_estimado_usd,
        tarifa_aplicada=tarifa_aplicada,
        duracion_ms=medidor.duracion_ms,
        estado=estado,
        intentos=medidor.intentos,
        causa_error=causa_error,
        paginas=medidor.paginas,
        caracteres_texto=medidor.caracteres_texto,
        reutilizado=False,
    )
    try:
        registrar(registro)
    except Exception:
        # A propósito, sin volver a lanzar: el análisis ya se completó (o ya
        # ha fallado por su cuenta, y esa excepción sigue su camino aparte).
        # `logger.exception` no incluye ni el texto ni la instrucción -no
        # están en el alcance de esta función, y `entrega.id` es el único
        # dato que identifica de qué se trata, el mismo código anónimo de
        # siempre-.
        logger.exception(
            "No se ha podido registrar el consumo de la entrega %s", entrega.id
        )


def analizar_entrega(
    raiz: Path,
    carpeta: Path,
    version: str,
    almacen: Almacen,
    proveedor: ProveedorAnalisis,
    entrega: EntregaRegistrada,
    listado: ListadoLocal | None = None,
) -> Correccion:
    """Lee, minimiza, analiza, verifica, compone y guarda.

    Si el archivo no se puede leer, no llega al motor: `leer` ya deja la
    entrega en BLOQUEADO con su motivo, y pedir un análisis sin texto solo
    gastaría una llamada para nada. Si el motor no llega a entregar un
    análisis útil -ni a la primera ni al reintento-, no se guarda nada y la
    entrega sigue en el estado en el que estaba: un estado que miente es
    peor que un estado atrasado.

    `listado` es la correspondencia local nombre-código
    (`backend.privacidad.listado_local.ListadoLocal`). Puede ser `None` -no
    hay carpeta de datos locales configurada, o no se ha importado ningún
    listado todavía-, y en ese caso el nombre del alumno no se puede buscar
    ni sustituir; el resto de la minimización (DNI, correo, teléfono) sigue
    aplicándose igual, porque no depende del listado.
    """
    ficha = leer(raiz, carpeta, version, almacen, entrega)
    if ficha.medidas is None:
        raise PdfIlegible(
            ficha.entrega.motivo_bloqueo or "No se ha podido leer el archivo."
        )

    nombre_conocido = (
        listado.nombre_de(entrega.codigo_alumno) if listado is not None else None
    )
    minimizacion = minimizar(ficha.medidas.texto_plano, nombre_conocido)
    texto = minimizacion.texto
    instruccion = construir(raiz, version, entrega.fase)

    # El aviso de la minimización solo importa cuando de verdad sale algo
    # hacia fuera: con el proveedor simulado no se envía nada a ningún
    # sitio (`ProveedorSimulado` no habla con ningún servicio), así que
    # avisar de que el nombre podría no haberse retirado sería ruido sobre
    # un envío que no ocurre -el mismo criterio que ya aplica
    # `proveedor.nombre != "simulado"` en la guarda de protección de datos
    # de `backend/api/analisis.py`-.
    aviso_privacidad = minimizacion.aviso if proveedor.nombre != "simulado" else ""

    medidor = MedidorDeConsumo(
        paginas=len(ficha.medidas.paginas), caracteres_texto=len(texto)
    )

    try:
        crudo = _con_un_reintento(
            lambda: _medir(
                medidor, proveedor,
                lambda: proveedor.analizar(instruccion, texto, AnalisisDelMotor),
            )
        )
    except ErrorDelProveedor as fallo:
        _registrar_consumo(
            raiz, almacen, medidor, proveedor, entrega, "ERROR", str(fallo)
        )
        raise

    analisis = verificar(raiz, version, entrega.fase, texto, crudo)
    informe = componer_informe(raiz, version, entrega, ficha, analisis, proveedor.nombre)

    try:
        devolucion = _con_un_reintento(
            lambda: _medir(
                medidor, proveedor,
                lambda: componer(raiz, version, proveedor, analisis),
            )
        )
    except (ErrorDelProveedor, BorradorNoValido) as fallo:
        actualizada = almacen.cambiar_estado(entrega.id, ANALIZADO, None) or entrega
        _registrar_consumo(
            raiz, almacen, medidor, proveedor, entrega, "PARCIAL", str(fallo)
        )
        raise InformeSinBorrador(
            f"El informe se ha generado y ha quedado guardado, pero el "
            f"borrador de devolución no se ha podido completar: {fallo}",
            entrega=actualizada,
            informe=informe,
            aviso_privacidad=aviso_privacidad,
        ) from fallo

    _registrar_consumo(raiz, almacen, medidor, proveedor, entrega, "OK", None)

    actualizada = almacen.cambiar_estado(entrega.id, ANALIZADO, None) or entrega
    return Correccion(
        entrega=actualizada,
        informe=informe,
        devolucion=devolucion,
        motor=proveedor.nombre,
        aviso_privacidad=aviso_privacidad,
    )
