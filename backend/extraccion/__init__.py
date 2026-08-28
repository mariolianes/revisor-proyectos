"""Medición objetiva de un PDF. No llama a ningún modelo de lenguaje."""

import hashlib
from pathlib import Path

from backend.extraccion.medidas import Medidas

# Leer un PDF de golpe para calcular su huella cargaría en memoria un
# archivo que puede pesar decenas de megas.
TROZO = 1024 * 1024


def _huella(ruta: Path) -> str:
    """SHA-256 del archivo, para identificarlo sin conservarlo (§19.1)."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        while trozo := archivo.read(TROZO):
            resumen.update(trozo)
    return resumen.hexdigest()


def medir(ruta: Path) -> Medidas:
    """Todo lo que se puede saber del archivo sin criterio humano."""
    from backend.extraccion.estructura import medir_estructura
    from backend.extraccion.imagenes import leer_imagenes
    from backend.extraccion.lectura import abrir, leer_paginas, procede_de_escaner
    from backend.extraccion.tipografia import medir_texto

    with abrir(ruta) as documento:
        paginas = leer_paginas(documento)
        return Medidas(
            nombre_archivo=ruta.name,
            huella=_huella(ruta),
            paginas=paginas,
            total_paginas=len(paginas),
            paginas_en_blanco=[p.numero for p in paginas if p.en_blanco],
            escaneado=procede_de_escaner(documento),
            texto=medir_texto(documento),
            estructura=medir_estructura(documento),
            imagenes=leer_imagenes(documento),
            texto_plano="\n".join(pagina.get_text() for pagina in documento),
        )
