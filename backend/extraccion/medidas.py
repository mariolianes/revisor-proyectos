"""Lo que se mide sobre un PDF, sin juzgar si está bien o mal.

Estos modelos son hechos: cuántas páginas, qué cuerpo, qué imágenes. La
comparación con lo que exigen los criterios ocurre en backend/formato/, que
no sabe abrir un PDF, igual que este módulo no sabe qué exige el Maestro.
"""

from pydantic import BaseModel, Field


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


class Imagen(BaseModel):
    """Una imagen colocada en una página.

    `dpi_efectivo` es la resolución a la que se imprime de verdad: los
    píxeles que tiene repartidos entre el tamaño que ocupa. Es lo que
    delata una captura de pantalla estirada, que en el archivo parece
    correcta y en el papel se ve borrosa.

    `proporcion_de_pagina` no está acotada a 1: no es un porcentaje que no
    pueda pasar del 100 %, es el área del rectángulo de colocación dividida
    entre el área de la página. Una imagen puesta más grande que la propia
    página da un valor mayor que 1, y es geométricamente correcto que lo dé.
    """

    pagina: int
    ancho_px: int
    alto_px: int
    dpi_efectivo: float
    proporcion_de_pagina: float


class Medidas(BaseModel):
    """Todo lo medido sobre un archivo, sin valorar nada.

    `texto_plano` vive aquí porque lo necesita la comparación evolutiva
    (`backend/evolucion/comparacion.py`, que lo lee como atributo del
    objeto en memoria, nunca de una forma serializada). No se guarda en
    Supabase -la decisión D-001 excluye el texto del trabajo de la base de
    datos- y tampoco se serializa: `Field(exclude=True)` lo saca de
    cualquier `model_dump()` y por tanto de cualquier respuesta HTTP,
    presente o futura, sin que quien añada el próximo endpoint tenga que
    acordarse de excluirlo a mano. Es el trabajo del alumno; no tiene nada
    que hacer viajando por la red ni quedando en el registro de peticiones
    de nadie. Se usa y se descarta.
    """

    nombre_archivo: str
    huella: str
    paginas: list[Pagina]
    total_paginas: int
    paginas_en_blanco: list[int]
    escaneado: bool
    texto: MedidasDeTexto
    estructura: MedidasDeEstructura
    imagenes: list[Imagen]
    texto_plano: str = Field(exclude=True)
