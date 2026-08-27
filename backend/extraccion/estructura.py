"""Índice, contenido y anexos.

El §6.2 del Maestro cuenta las páginas «excluidas portada, índice y
anexos», así que hay que saber dónde empieza y acaba el contenido. Se
localiza por lo que el propio documento declara: el encabezado del índice y
el de los anexos.

Si el índice no aparece, no se deduce nada. Se podría suponer que la
portada es la primera página y que el contenido empieza en la segunda, y
acertaría muchas veces; pero cuando fallara produciría una cuenta de
páginas equivocada con aspecto de dato medido, y sobre esa cuenta se decide
si un trabajo cumple la extensión mínima. Un hueco declarado es
recuperable; un número inventado, no.
"""

import re
import unicodedata

import pymupdf

from backend.extraccion.medidas import EntradaDeIndice, MedidasDeEstructura

# Una línea de índice: título, relleno de puntos o espacios, y la página.
# El relleno es opcional porque no todos los procesadores lo ponen.
LINEA_DE_INDICE = re.compile(r"^(.{3,120}?)[\s.·_]{2,}(\d{1,3})\s*$")

ENCABEZADOS_DE_INDICE = ("indice", "indice de contenidos", "tabla de contenidos",
                         "contenido", "contenidos", "sumario")
ENCABEZADOS_DE_ANEXOS = ("anexo", "anexos", "apendice", "apendices")

# El índice está al principio: buscarlo más allá de aquí solo produce
# falsos positivos con menciones dentro del texto.
PAGINAS_EN_QUE_BUSCAR_EL_INDICE = 6


def _plano(texto: str) -> str:
    """Sin tildes, sin mayúsculas y sin espacios de sobra, para comparar."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def _lineas_por_pagina(documento: pymupdf.Document) -> list[list[str]]:
    """Las líneas de texto de cada página, en orden."""
    return [
        [linea.strip() for linea in pagina.get_text().splitlines() if linea.strip()]
        for pagina in documento
    ]


def _buscar_indice(paginas: list[list[str]]) -> int | None:
    """Número de la página cuyo encabezado es el del índice, o None."""
    for numero, lineas in enumerate(paginas[:PAGINAS_EN_QUE_BUSCAR_EL_INDICE], start=1):
        for linea in lineas[:5]:
            if _plano(linea) in ENCABEZADOS_DE_INDICE:
                return numero
    return None


def _buscar_anexos(paginas: list[list[str]], desde: int) -> int | None:
    """Primera página cuyo encabezado anuncia los anexos, o None."""
    for numero, lineas in enumerate(paginas, start=1):
        if numero <= desde:
            continue
        for linea in lineas[:2]:
            plano = _plano(linea)
            if plano in ENCABEZADOS_DE_ANEXOS or plano.startswith("anexos "):
                return numero
    return None


def _leer_entradas(lineas: list[str]) -> list[EntradaDeIndice]:
    """Las entradas de la página del índice, sin su propio encabezado."""
    entradas = []
    for linea in lineas:
        if _plano(linea) in ENCABEZADOS_DE_INDICE:
            continue
        coincidencia = LINEA_DE_INDICE.match(linea)
        if coincidencia:
            entradas.append(EntradaDeIndice(
                titulo=coincidencia.group(1).strip(" .·_"),
                pagina_declarada=int(coincidencia.group(2)),
            ))
    return entradas


def _localizar(titulo: str, paginas: list[list[str]], desde: int) -> int | None:
    """Página donde ese título aparece como encabezado, o None.

    Se busca solo en las primeras líneas de cada página y solo desde donde
    acaba el índice: una mención del título dentro de un párrafo no es el
    apartado.
    """
    buscado = _plano(titulo)
    if not buscado:
        return None
    for numero, lineas in enumerate(paginas, start=1):
        if numero <= desde:
            continue
        for linea in lineas[:3]:
            if _plano(linea) == buscado:
                return numero
    return None


def medir_estructura(documento: pymupdf.Document) -> MedidasDeEstructura:
    """Localiza índice, contenido y anexos, y contrasta el índice declarado."""
    paginas = _lineas_por_pagina(documento)
    indice = _buscar_indice(paginas)
    if indice is None:
        return MedidasDeEstructura()

    entradas = _leer_entradas(paginas[indice - 1])
    anexos = _buscar_anexos(paginas, indice)
    contenido = indice + 1 if indice < len(paginas) else None

    no_encontrados: list[str] = []
    descuadrados: list[str] = []
    for entrada in entradas:
        if _plano(entrada.titulo) in ENCABEZADOS_DE_ANEXOS:
            continue
        entrada.pagina_encontrada = _localizar(entrada.titulo, paginas, indice)
        if entrada.pagina_encontrada is None:
            no_encontrados.append(entrada.titulo)
        elif entrada.pagina_encontrada != entrada.pagina_declarada:
            descuadrados.append(
                f"«{entrada.titulo}»: el índice dice página "
                f"{entrada.pagina_declarada} y está en la "
                f"{entrada.pagina_encontrada}."
            )

    ultima = (anexos - 1) if anexos else len(paginas)
    cuenta = max(0, ultima - contenido + 1) if contenido else None

    return MedidasDeEstructura(
        pagina_del_indice=indice,
        primera_pagina_de_contenido=contenido,
        primera_pagina_de_anexos=anexos,
        paginas_de_contenido=cuenta,
        entradas_de_indice=entradas,
        titulos_no_encontrados=no_encontrados,
        paginas_declaradas_incorrectas=descuadrados,
    )
