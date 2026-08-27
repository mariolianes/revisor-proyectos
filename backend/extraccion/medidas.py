"""Lo que se mide sobre un PDF, sin juzgar si está bien o mal.

Estos modelos son hechos: cuántas páginas, qué cuerpo, qué imágenes. La
comparación con lo que exigen los criterios ocurre en backend/formato/, que
no sabe abrir un PDF, igual que este módulo no sabe qué exige el Maestro.
"""

from pydantic import BaseModel


class Pagina(BaseModel):
    """Una página del documento."""

    numero: int
    caracteres: int
    en_blanco: bool
    ancho_pt: float
    alto_pt: float


class MedidasDeTexto(BaseModel):
    """Tipografía, interlineado, márgenes y alineación, tal como se miden.

    Los campos opcionales son `None` cuando el documento no da material para
    medirlos —un escaneado no tiene tipografía, una sola línea no define un
    interlineado—. Nunca llevan un valor supuesto: un dato ausente que
    parece presente es peor que un hueco declarado.
    """

    familia_dominante: str
    cuerpo_dominante: float
    proporcion_cuerpo_dominante: float
    ratio_interlineado: float | None = None
    margen_izquierdo_cm: float | None = None
    margen_derecho_cm: float | None = None
    margen_superior_cm: float | None = None
    margen_inferior_cm: float | None = None
    proporcion_lineas_al_margen_derecho: float | None = None
