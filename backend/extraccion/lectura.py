"""Apertura del PDF y hechos básicos de sus páginas.

El archivo se abre en lectura y nunca se modifica, ni se mueve, ni se
renombra: lo exige el §18.1 del Documento Maestro.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pymupdf

from backend.extraccion.medidas import Pagina

# Una página con menos caracteres que esto no tiene contenido: son restos de
# numeración, encabezado o pie. Un dígito y poco más.
CARACTERES_MINIMOS = 3


class PdfIlegible(Exception):
    """El archivo no se puede leer. Es una parada del §18.2, no un fallo."""


@contextmanager
def abrir(ruta: Path) -> Iterator[pymupdf.Document]:
    """Abre el PDF en lectura y lo cierra pase lo que pase.

    Los mensajes los lee el docente: dicen qué archivo y qué le ocurre, no
    qué excepción lanzó la librería.
    """
    if not ruta.is_file():
        raise PdfIlegible(f"El archivo «{ruta.name}» no existe en la carpeta.")
    try:
        documento = pymupdf.open(ruta)
    except Exception as fallo:
        raise PdfIlegible(
            f"El archivo «{ruta.name}» no se ha podido abrir como PDF. "
            "Puede estar dañado, incompleto o no ser realmente un PDF."
        ) from fallo
    try:
        if documento.needs_pass:
            raise PdfIlegible(
                f"El archivo «{ruta.name}» está protegido con contraseña. "
                "Pide al alumno una copia sin protección."
            )
        if documento.page_count == 0:
            raise PdfIlegible(
                f"El archivo «{ruta.name}» no tiene ninguna página."
            )
        yield documento
    finally:
        documento.close()


def leer_paginas(documento: pymupdf.Document) -> list[Pagina]:
    """Una entrada por página, numeradas desde 1 como las ve el docente."""
    paginas = []
    for indice, pagina in enumerate(documento, start=1):
        texto = pagina.get_text().strip()
        paginas.append(Pagina(
            numero=indice,
            caracteres=len(texto),
            en_blanco=len(texto) < CARACTERES_MINIMOS,
            ancho_pt=pagina.rect.width,
            alto_pt=pagina.rect.height,
        ))
    return paginas


def procede_de_escaner(documento: pymupdf.Document) -> bool:
    """Si el PDF es imagen sin texto extraíble.

    Un trabajo escaneado no es corregible: no se puede medir su tipografía
    ni citar un fragmento. El §6 del Índice comentado lo excluye, y aquí se
    detecta por lo único que lo distingue de forma fiable: que no hay ni un
    carácter de texto en todo el documento.
    """
    return not any(pagina.get_text().strip() for pagina in documento)
