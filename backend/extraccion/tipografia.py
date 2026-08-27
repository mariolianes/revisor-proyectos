"""Tipografía, interlineado, márgenes y alineación.

Sobre el interlineado, que es el punto delicado: un PDF no guarda «1,5
líneas». Guarda dónde cae la línea base de cada línea, y de ahí sale la
distancia real en puntos. Convertir esa distancia en el valor que el alumno
eligió en su procesador de textos depende de la fuente y de la versión del
programa —para Arial 11 a 1,5 líneas sale un ratio cercano a 1,73, no a
1,5—. Aquí se mide el ratio y se deja a la vista. Qué ratio corresponde a
1,5 lo dirá la calibración del §20, no este módulo.

Limitación conocida de los márgenes: se miden sobre todo el texto de la
página, así que un encabezado o un pie reducen el margen superior o el
inferior medidos. El izquierdo y el derecho no se ven afectados. Los cuatro
se miden además sobre el texto de todas las páginas del documento, portada
incluida: no hay forma de distinguir, solo mirando el PDF, qué página es
portada y cuál no lo es.
"""

import re
import statistics
from collections import Counter

import pymupdf

from backend.extraccion.medidas import MedidasDeTexto

PUNTOS_POR_CM = 72 / 2.54

# Las fuentes incrustadas llegan como «ABCDEF+Arial-BoldMT»: seis letras
# mayúsculas y un «+» delante, y el estilo pegado detrás.
PREFIJO_SUBCONJUNTO = re.compile(r"^[A-Z]{6}\+")
SUFIJO_ESTILO = re.compile(
    r"(MT|PS|PSMT)?[-,]"
    r"(BoldItalic|BoldOblique|BoldMT|ItalicMT|Bold|Italic|Oblique|Regular|Roman|Light|Medium)"
    r"(MT|PS)?$",
    re.I,
)
SUFIJO_SUELTO = re.compile(r"(PSMT|MT|PS)$")

# Un salto mayor que esto no es interlineado: es el hueco entre párrafos o
# entre secciones, y contarlo desplazaría la mediana.
SALTO_MAXIMO_EN_CUERPOS = 3.0

# Dos líneas terminan «en el mismo sitio» si su borde derecho no se separa
# más que esto. Un punto es la anchura de un pelo de letra.
TOLERANCIA_BORDE_PT = 1.0

# Páginas con menos líneas que esto no entran en el cálculo de la alineación.
LINEAS_MINIMAS_PARA_ALINEACION = 2


def normalizar_familia(nombre: str) -> str:
    """«ABCDEF+Arial-BoldMT» → «Arial». La familia, sin estilo ni subconjunto."""
    limpio = PREFIJO_SUBCONJUNTO.sub("", nombre)
    limpio = SUFIJO_ESTILO.sub("", limpio)
    return SUFIJO_SUELTO.sub("", limpio)


def _lineas_de(pagina: pymupdf.Page) -> list[dict]:
    """Las líneas de texto de una página, con sus spans."""
    lineas = []
    for bloque in pagina.get_text("dict")["blocks"]:
        if bloque["type"] != 0:  # 0 es texto; 1 es imagen
            continue
        lineas.extend(bloque["lines"])
    return lineas


def _ratio_de_pagina(lineas: list[dict], cuerpo: float) -> list[float]:
    """Saltos entre líneas base consecutivas, en múltiplos del cuerpo."""
    bases = sorted(
        linea["spans"][0]["origin"][1] for linea in lineas if linea["spans"]
    )
    saltos = []
    for anterior, siguiente in zip(bases, bases[1:]):
        salto = siguiente - anterior
        if 0 < salto <= cuerpo * SALTO_MAXIMO_EN_CUERPOS:
            saltos.append(salto / cuerpo)
    return saltos


def medir_texto(documento: pymupdf.Document) -> MedidasDeTexto:
    """Mide el texto del documento entero.

    Lo dominante se decide por número de caracteres, no por número de
    fragmentos: un titular corto no puede desplazar al cuerpo del trabajo.
    """
    por_estilo: Counter[tuple[str, float]] = Counter()
    ratios: list[float] = []
    margenes_izquierdos: list[float] = []
    margenes_derechos: list[float] = []
    margen_superior_cm: float | None = None
    margen_inferior_cm: float | None = None
    lineas_totales = 0
    lineas_al_borde = 0

    for pagina in documento:
        lineas = _lineas_de(pagina)
        if not lineas:
            continue

        for linea in lineas:
            for span in linea["spans"]:
                estilo = (normalizar_familia(span["font"]), round(span["size"] * 2) / 2)
                por_estilo[estilo] += len(span["text"])

        # El margen es una barrera que ninguna línea cruza: izquierdo y
        # derecho se acumulan línea a línea de todo el documento antes de
        # tomar la mediana, para que una portada corta no pese lo mismo que
        # catorce páginas de cuerpo. Superior e inferior son el mínimo
        # alcanzado en todo el documento, no una mediana por página.
        for linea in lineas:
            margenes_izquierdos.append(linea["bbox"][0] / PUNTOS_POR_CM)
            margenes_derechos.append((pagina.rect.width - linea["bbox"][2]) / PUNTOS_POR_CM)
            superior = linea["bbox"][1] / PUNTOS_POR_CM
            inferior = (pagina.rect.height - linea["bbox"][3]) / PUNTOS_POR_CM
            if margen_superior_cm is None or superior < margen_superior_cm:
                margen_superior_cm = superior
            if margen_inferior_cm is None or inferior < margen_inferior_cm:
                margen_inferior_cm = inferior

        derechas = [linea["bbox"][2] for linea in lineas]

        # Una página de una sola línea no dice nada de la alineación: esa
        # línea es a la vez el máximo y el único candidato, así que contaría
        # como alineada siempre. Una portada bastaría para que un texto
        # alineado a la izquierda pareciera justificado.
        if len(lineas) >= LINEAS_MINIMAS_PARA_ALINEACION:
            borde = max(derechas)
            lineas_totales += len(lineas)
            lineas_al_borde += sum(
                1 for derecha in derechas if borde - derecha <= TOLERANCIA_BORDE_PT
            )

    if not por_estilo:
        return MedidasDeTexto(
            familia_dominante="",
            cuerpo_dominante=0.0,
            proporcion_cuerpo_dominante=0.0,
        )

    (familia, cuerpo), caracteres = por_estilo.most_common(1)[0]
    total = sum(por_estilo.values())

    # El interlineado se calcula con el cuerpo dominante ya conocido: los
    # saltos de un titular no dicen nada del cuerpo del trabajo.
    if cuerpo > 0:
        for pagina in documento:
            ratios.extend(_ratio_de_pagina(_lineas_de(pagina), cuerpo))

    return MedidasDeTexto(
        familia_dominante=familia,
        cuerpo_dominante=cuerpo,
        proporcion_cuerpo_dominante=caracteres / total,
        ratio_interlineado=statistics.median(ratios) if ratios else None,
        margen_izquierdo_cm=(
            statistics.median(margenes_izquierdos) if margenes_izquierdos else None
        ),
        margen_derecho_cm=(
            statistics.median(margenes_derechos) if margenes_derechos else None
        ),
        margen_superior_cm=margen_superior_cm,
        margen_inferior_cm=margen_inferior_cm,
        proporcion_lineas_al_margen_derecho=(
            lineas_al_borde / lineas_totales if lineas_totales else None
        ),
    )
