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

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, field_validator

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
        """Quita espacios de los extremos y pasa a mayúsculas.

        Normalizar y no rechazar es deliberado: el docente puede escribir la
        fase en minúsculas en el formulario, o el código con un espacio de
        más, y eso no debe fallarle. La alternativa —guardar el valor tal
        cual y confiar en que cada llamador lo normalice antes de comparar—
        es lo que dejaba a un mismo alumno registrado bajo dos claves
        distintas ("AF023" y "  AF023  ") y rompía `anterior_de` en
        silencio.
        """
        return valor.strip().upper()


class EntregaRegistrada(BaseModel):
    """Una entrega ya guardada."""

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
