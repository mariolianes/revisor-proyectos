"""Lo que se guarda de una entrega, y lo que no.

No se guarda el PDF. No se guarda el texto del trabajo. Es la decisión
D-001, y lo que hay aquí es exactamente lo que las tablas admiten: la ficha
del alumno codificado, el proyecto, y de la entrega su nombre y su huella.

Tampoco se guardan las medidas ni las comprobaciones. Se recalculan al
abrir la ficha: medir un PDF es determinista y rápido, y conservarlas
exigiría una tabla nueva para un dato que se puede volver a obtener. Si más
adelante hace falta el histórico de lo medido, será su propia migración con
su documento de cambio.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    # Solo para anotar el protocolo `Almacen`. `from __future__ import
    # annotations` (arriba) hace que estas anotaciones se guarden como
    # cadenas y no se evalúen en tiempo de ejecución, así que este import no
    # se ejecuta nunca fuera de un comprobador de tipos: si se ejecutara,
    # cerraría un ciclo, porque `salidas/informe.py` importa
    # `EntregaRegistrada` de este mismo módulo.
    from backend.persistencia.correccion import Correccion
    from backend.salidas.borrador import Devolucion
    from backend.salidas.informe import Informe

# Los siete del §16.1, en el orden en que ocurren.
ESTADOS: tuple[str, ...] = (
    "RECIBIDO",
    "BLOQUEADO",
    "ANALIZADO",
    "BORRADORES_GENERADOS",
    "EN_REVISION_DOCENTE",
    "APROBADO",
    "COMUNICADO",
)

ESTADO_INICIAL = "RECIBIDO"
BLOQUEADO = "BLOQUEADO"


def _normalizar_identidad(valor: str) -> str:
    """Quita todo carácter de espacio -no solo los de los extremos- y pasa
    a mayúsculas.

    `"".join(valor.split())` reparte por cualquier carácter de espacio
    Unicode -espacio normal, tabulador, NBSP- y los descarta todos, estén
    en los extremos o en medio. Un `strip()` solo limpia los bordes y deja
    pasar un espacio, un tabulador o un NBSP pegado en medio del código
    -justo lo que aparece al copiar desde un PDF o una web-, y un
    `replace(" ", "")` solo se lleva el espacio ASCII normal y deja el
    NBSP intacto. Ni un código de alumno, ni unas siglas de ciclo, ni el
    nombre de una fase llevan espacios legítimos, así que no hay nada que
    preservar.

    Normalizar y no rechazar es deliberado: el docente puede escribir la
    fase en minúsculas en el formulario, o pegar el código con algún
    espacio de más, y eso no debe fallarle.
    """
    return "".join(valor.split()).upper()


class EntregaNueva(BaseModel):
    """Una entrega que el docente acaba de confirmar."""

    codigo_alumno: str
    ciclo: str
    fase: str
    version: int
    nombre_archivo: str
    huella: str
    version_criterios: str

    @field_validator("codigo_alumno", "ciclo", "fase")
    @classmethod
    def _normalizar(cls, valor: str) -> str:
        return _normalizar_identidad(valor)


class EntregaRegistrada(BaseModel):
    """Una entrega ya guardada.

    Lleva la misma normalización que `EntregaNueva` en los mismos tres
    campos, y no solo por si acaso: quien construye esto no siempre parte
    de un `EntregaNueva` ya limpio. Una fila leída de Supabase puede venir
    de antes de que esta regla existiera, y sin este validador aquí
    también, un alumno guardado con un NBSP en el código volvería a quedar
    bajo una clave que `anterior_de` no reconoce.
    """

    id: str
    codigo_alumno: str
    ciclo: str
    fase: str
    version: int
    nombre_archivo: str
    huella: str
    recibida_en: datetime
    estado: str
    motivo_bloqueo: str | None
    version_criterios: str

    @field_validator("codigo_alumno", "ciclo", "fase")
    @classmethod
    def _normalizar(cls, valor: str) -> str:
        return _normalizar_identidad(valor)


class Almacen(Protocol):
    """Lo que cualquier almacén tiene que saber hacer.

    `es_duradero` no es un detalle: el frontend lo enseña. Un almacén que
    pierde lo guardado al cerrar es utilizable, pero el docente tiene que
    saber que lo es.
    """

    @property
    def es_duradero(self) -> bool: ...

    def registrar(self, entrega: EntregaNueva) -> EntregaRegistrada: ...

    def listar(self) -> list[EntregaRegistrada]: ...

    def por_id(self, identificador: str) -> EntregaRegistrada | None: ...

    def por_huella(self, huella: str) -> EntregaRegistrada | None: ...

    def anterior_de(
        self, codigo_alumno: str, fase: str, version: int = 1
    ) -> EntregaRegistrada | None: ...

    def cambiar_estado(
        self, identificador: str, estado: str, motivo: str | None
    ) -> EntregaRegistrada | None: ...

    def guardar_correccion(
        self,
        entrega_id: str,
        informe: Informe,
        devolucion: Devolucion | None,
        motor: str,
        aviso: str | None = None,
    ) -> str:
        """Guarda el análisis y sus dos salidas. Devuelve el id de la corrección.

        Una entrega tiene una corrección -lo impone `unique (entrega_id)` en
        la migración-: guardar dos veces sobre la misma entrega sustituye la
        anterior entera, no la amplía. Es lo que necesitan tanto un
        reanálisis como una revisión del docente, que en esta API son la
        misma operación: guardar de nuevo con el informe ya corregido.

        `devolucion` es `None` cuando el informe se completó pero el
        borrador no (`InformeSinBorrador`): un informe válido sin borrador es
        un resultado legítimo del análisis, no un dato a medias, y forzar
        aquí una `Devolucion` vacía lo confundiría con el caso -distinto- en
        que no hay nada que redactar.

        Guardar el análisis son varias escrituras (la corrección, y una
        valoración con su evidencia por cada dimensión valorada). Si alguna
        falla a mitad, no debe quedar una corrección sin sus valoraciones ni
        una fila huérfana: la implementación deshace lo que ya escribió y
        levanta `ErrorDeAlmacen` -de `backend/persistencia/supabase.py`-, en
        vez de dejar una corrección a medio guardar que el docente vería
        como completa.
        """
        ...

    def correccion_de(self, entrega_id: str) -> Correccion | None:
        """La corrección guardada de esta entrega, o `None` si no hay ninguna.

        No hay `motor` a la vista del que decidir un formulario aparte para
        Supabase y otro para memoria: los dos devuelven exactamente el mismo
        tipo, `backend.persistencia.correccion.Correccion`, con sus dos
        salidas ya reconstruidas.
        """
        ...


# Lo declarado se compara en estos campos para decidir si una huella
# repetida es de verdad el mismo archivo confirmado dos veces. El nombre o
# la ruta quedan fuera a propósito: es dónde está el fichero, no de quién
# es, y moverlo de subcarpeta no debe dar error.
#
# El ciclo también queda fuera, y por la misma clase de razón: el ciclo no
# es de la entrega, es del alumno -en la base de datos lo tiene la tabla
# `alumno` y la tabla `entrega` no lo tiene-, así que no forma parte de la
# identidad de una entrega. Estuvo dentro, y el efecto era este: el docente
# confirmaba declarando un ciclo distinto al que el alumno tiene, el
# sistema aceptaba la entrega y le ponía el ciclo del alumno -que es lo
# correcto-, y al volver a confirmar el MISMO archivo con los MISMOS datos
# se le acusaba de haber cambiado el dato. No lo había cambiado él: lo
# había cambiado el sistema. Y era justo el caso legítimo que este
# mecanismo existe para dejar pasar, el de un trabajo que se mueve de
# carpeta y se vuelve a confirmar.
#
# La discrepancia de ciclo no se pierde: la cuenta el aviso que compone
# `api/entregas.confirmar`, que informa sin bloquear, que es el sitio
# correcto para algo que el docente tiene que mirar y decidir.
#
# Vive aquí, con el resto de validaciones compartidas, y no en cada
# almacén. Estuvo duplicado palabra por palabra en los dos, con un
# comentario que prometía que se comportaban igual, y esa promesa no la
# sostenía nada: quitar un campo de la tupla en uno solo de los dos dejaba
# los tests en verde. Ahora hay un test de paridad permanente.
CAMPOS_DE_IDENTIDAD = ("codigo_alumno", "fase", "version")


def choca_con_lo_declarado(
    existente: EntregaRegistrada, nueva: EntregaNueva
) -> bool:
    """Si lo que ahora se declara no coincide con la ficha bajo la que ya está."""
    return any(
        getattr(existente, campo) != getattr(nueva, campo)
        for campo in CAMPOS_DE_IDENTIDAD
    )


def error_de_atribucion(
    existente: EntregaRegistrada, nueva: EntregaNueva
) -> ValueError:
    """El aviso de una huella repetida con otros datos declarados.

    También compartido: los dos almacenes tienen que decir lo mismo, y el
    docente no debería leer un texto u otro según haya credenciales.
    """
    return ValueError(
        f"El archivo «{nueva.huella}» ya está registrado como "
        f"{existente.codigo_alumno}/{existente.ciclo}/"
        f"{existente.fase} v{existente.version} (ficha "
        f"{existente.id}), pero ahora se declara como "
        f"{nueva.codigo_alumno}/{nueva.ciclo}/{nueva.fase} "
        f"v{nueva.version}. Si es el mismo trabajo, corrige el "
        "dato que no coincide antes de confirmarlo."
    )


def validar_fase(fase: str) -> None:
    """Que la fase exista, dicho en castellano.

    Separado de `validar` para que cualquier operación que necesite indexar
    `FASES` —`anterior_de`, por ejemplo— pueda comprobarlo antes de indexar
    en vez de dejar que `tuple.index` reviente con un mensaje en inglés.
    """
    from backend.vigilancia.nombres import FASES

    if fase not in FASES:
        raise ValueError(
            f"«{fase}» no es una fase. Las fases son: " + ", ".join(FASES) + "."
        )


def validar(entrega: EntregaNueva) -> None:
    """Lo que la base de datos rechazaría, rechazado antes y con mejor aviso."""
    validar_fase(entrega.fase)
    if entrega.version < 1:
        raise ValueError("La versión de una entrega empieza en 1.")
    if not entrega.codigo_alumno:
        raise ValueError("La entrega necesita el código del alumno.")


def validar_estado(estado: str, motivo: str | None) -> None:
    """El estado existe, y si es BLOQUEADO viene con su motivo."""
    if estado not in ESTADOS:
        raise ValueError(
            f"«{estado}» no es un estado del flujo. Son: " + ", ".join(ESTADOS) + "."
        )
    if estado == BLOQUEADO and not (motivo or "").strip():
        raise ValueError(
            "Bloquear una entrega exige decir el motivo: es lo que el docente "
            "leerá para saber qué pedir."
        )
