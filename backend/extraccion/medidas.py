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


class EntradaDeIndice(BaseModel):
    """Una línea del índice y dónde está de verdad ese apartado."""

    titulo: str
    pagina_declarada: int
    pagina_encontrada: int | None = None


class MedidasDeEstructura(BaseModel):
    """Dónde empieza y acaba lo que cuenta como contenido.

    Todo opcional por el mismo motivo de siempre: sin índice localizable no
    se sabe dónde empieza el contenido, y esa cuenta se declara ausente en
    lugar de estimarse.
    """

    pagina_del_indice: int | None = None
    primera_pagina_de_contenido: int | None = None
    primera_pagina_de_anexos: int | None = None
    paginas_de_contenido: int | None = None
    entradas_de_indice: list[EntradaDeIndice] = []
    titulos_no_encontrados: list[str] = []
    paginas_declaradas_incorrectas: list[str] = []
