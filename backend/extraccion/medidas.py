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
