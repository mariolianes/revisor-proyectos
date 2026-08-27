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

Limitaciones conocidas y aceptadas:

- Si los anexos empiezan a media página, compartiendo página con el final
  del contenido, la heurística de encabezado (que solo mira las dos
  primeras líneas de cada página) no los ve, y el conteo de páginas de
  contenido sale ligeramente inflado. No se amplía esa ventana a propósito:
  ampliarla agravaría los falsos positivos de un encabezado de anexo
  mencionado a mitad de párrafo, y el caso realista ya queda cubierto
  porque un trabajo con anexos casi siempre los declara en el índice, que
  es lo primero que se consulta.
- Un índice cuya continuación empiece por un encabezado repetido, del tipo
  «Índice (cont.)», se corta ahí en vez de seguir: se exige que la primera
  línea de la página ya sea una entrada, precisamente para no confundir la
  continuación con un «Índice de figuras» o una tabla de presupuesto que
  tienen la misma forma. El precio es que el contenido se calcularía
  empezando una página antes de lo debido. No se relaja la condición
  porque el caso que sí resuelve —un índice de figuras o una tabla detrás
  del índice— es más frecuente que un encabezado de continuación repetido.
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

# Un índice puede repartirse en varias páginas cuando hay muchos
# subapartados. Solo la primera lleva el encabezado; las siguientes se
# reconocen por la forma de sus líneas: cuántas casan con LINEA_DE_INDICE,
# como mínimo...
MINIMO_LINEAS_DE_INDICE_EN_PAGINA = 2
# ...y qué proporción de las líneas de la página deben ser esas
# coincidencias. Medido sobre casos reales: las páginas de índice dan 0,67
# y 1,00; las de contenido dan 0,00.
PROPORCION_MINIMA_DE_LINEAS_DE_INDICE = 0.60


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


def _parece_pagina_de_indice(lineas: list[str]) -> bool:
    """Si una página, más allá de la primera, sigue siendo del índice.

    Solo la primera página lleva el encabezado «Índice»; las siguientes se
    reconocen por la forma de sus líneas: si la mayoría son entradas con
    pinta de "título ... número", es una continuación de la tabla, no
    contenido.

    Pero esa forma no es exclusiva del índice: un «Índice de figuras» o una
    tabla de presupuesto detrás del índice tienen la misma proporción de
    líneas con puntos y un número al final. Lo que los distingue es cómo
    empiezan: la continuación de un índice arranca directamente con la
    siguiente entrada, mientras que un índice de figuras o una tabla
    arrancan con su propio título o su propia cabecera. Por eso se exige
    además que la primera línea de la página sea ya una entrada.
    """
    if not lineas:
        return False
    if not LINEA_DE_INDICE.match(lineas[0]):
        return False
    coincidencias = sum(1 for linea in lineas if LINEA_DE_INDICE.match(linea))
    return (
        coincidencias >= MINIMO_LINEAS_DE_INDICE_EN_PAGINA
        and coincidencias / len(lineas) >= PROPORCION_MINIMA_DE_LINEAS_DE_INDICE
    )


def _ultima_pagina_del_indice(paginas: list[list[str]], primera: int) -> int:
    """Hasta dónde llega el índice, mirando a partir de su primera página."""
    ultima = primera
    for numero in range(primera + 1, len(paginas) + 1):
        if not _parece_pagina_de_indice(paginas[numero - 1]):
            break
        ultima = numero
    return ultima


def _buscar_anexos_por_encabezado(paginas: list[list[str]], desde: int) -> int | None:
    """Última página, tras el índice, cuyo encabezado anuncia los anexos.

    Se toma la última aparición y no la primera: los anexos van al final, y
    un apartado que solo menciona "anexo" a mitad del trabajo (p. ej.
    "Anexo de cálculos" dentro del desarrollo) no debe llevarse por delante
    el contenido real.
    """
    encontrada = None
    for numero, lineas in enumerate(paginas, start=1):
        if numero <= desde:
            continue
        for linea in lineas[:2]:
            plano = _plano(linea)
            if plano in ENCABEZADOS_DE_ANEXOS or plano.startswith("anexos "):
                encontrada = numero
                break
    return encontrada


def _anexos_declarados_en_indice(
    entradas: list[EntradaDeIndice], total_paginas: int
) -> int | None:
    """La página de anexos que el propio índice declara, si la hay.

    Lo que el autor escribió en su índice es un dato deliberado, no una
    adivinanza: si el índice trae una entrada de anexos, esa página manda
    sobre cualquier heurística de encabezado.
    """
    for entrada in entradas:
        if _plano(entrada.titulo) in ENCABEZADOS_DE_ANEXOS:
            if 1 <= entrada.pagina_declarada <= total_paginas:
                return entrada.pagina_declarada
    return None


def _leer_entradas(lineas: list[str]) -> list[EntradaDeIndice]:
    """Las entradas de una página del índice, sin su propio encabezado."""
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

    Se busca en todas las líneas de la página y solo desde donde acaba el
    índice. Una mención del título dentro de un párrafo no se confunde con
    el encabezado del apartado porque la comparación exige que la línea
    entera sea idéntica al título, no que lo contenga; por eso no hace
    falta limitarse a las primeras líneas de cada página, y limitarse
    dejaba sin encontrar cualquier apartado que no empezara al principio de
    la página.
    """
    buscado = _plano(titulo)
    if not buscado:
        return None
    for numero, lineas in enumerate(paginas, start=1):
        if numero <= desde:
            continue
        for linea in lineas:
            if _plano(linea) == buscado:
                return numero
    return None


def medir_estructura(documento: pymupdf.Document) -> MedidasDeEstructura:
    """Localiza índice, contenido y anexos, y contrasta el índice declarado."""
    paginas = _lineas_por_pagina(documento)
    indice = _buscar_indice(paginas)
    if indice is None:
        return MedidasDeEstructura()

    ultima_pagina_indice = _ultima_pagina_del_indice(paginas, indice)

    entradas: list[EntradaDeIndice] = []
    for numero in range(indice, ultima_pagina_indice + 1):
        entradas += _leer_entradas(paginas[numero - 1])

    anexos = _anexos_declarados_en_indice(entradas, len(paginas))
    if anexos is None:
        anexos = _buscar_anexos_por_encabezado(paginas, ultima_pagina_indice)

    contenido = (
        ultima_pagina_indice + 1 if ultima_pagina_indice < len(paginas) else None
    )

    no_encontrados: list[str] = []
    descuadrados: list[str] = []
    for entrada in entradas:
        if _plano(entrada.titulo) in ENCABEZADOS_DE_ANEXOS:
            continue
        entrada.pagina_encontrada = _localizar(entrada.titulo, paginas, ultima_pagina_indice)
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
