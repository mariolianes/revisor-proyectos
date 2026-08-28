"""Lo que hay en la carpeta de entregas y no se ha registrado todavía.

Mirar es mirar: se recorre el árbol, se leen los nombres y se devuelve una
lista. Ningún archivo se abre, se mueve, se renombra ni se copia. El §18.1
lo exige y aquí se cumple por construcción, porque este módulo no tiene
ninguna llamada que escriba.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from backend.vigilancia.nombres import PropuestaDeIdentificacion, deducir

EXTENSION = ".pdf"


class ArchivoVisto(BaseModel):
    """Un archivo de la carpeta que aún no está registrado."""

    nombre: str
    ruta: Path
    modificado_en: datetime
    propuesta: PropuestaDeIdentificacion


def mirar(carpeta: Path, nombres_ya_registrados: set[str]) -> list[ArchivoVisto]:
    """Los PDFs pendientes, el más reciente primero.

    Se compara por nombre y no por huella porque calcular la huella obliga a
    leer el archivo entero, y esto se llama cada vez que el docente abre la
    bandeja. La huella se calcula al registrar, que es cuando importa.
    """
    if not carpeta.is_dir():
        return []

    vistos = []
    for ruta in carpeta.rglob(f"*{EXTENSION}"):
        if not ruta.is_file() or ruta.name in nombres_ya_registrados:
            continue
        vistos.append(ArchivoVisto(
            nombre=ruta.name,
            ruta=ruta,
            modificado_en=datetime.fromtimestamp(ruta.stat().st_mtime),
            propuesta=deducir(ruta.name),
        ))
    return sorted(vistos, key=lambda visto: visto.modificado_en, reverse=True)
