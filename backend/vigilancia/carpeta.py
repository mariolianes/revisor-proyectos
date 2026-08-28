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
    modificado_en: datetime | None
    propuesta: PropuestaDeIdentificacion
    problema: str = ""


def mirar(carpeta: Path, rutas_ya_registradas: set[str]) -> list[ArchivoVisto]:
    """Los PDFs pendientes, el más reciente primero.

    Se compara por la ruta relativa a `carpeta`, no por el nombre suelto del
    archivo. El §15.2 organiza las entregas por alumno en subcarpetas, y dos
    alumnos distintos pueden dejar un archivo con el mismo nombre; comparar
    solo por nombre haría que registrar el de uno tapase para siempre, sin
    aviso, al del otro. Tampoco se compara por huella, porque calcular la
    huella obliga a leer el archivo entero, y esto se llama cada vez que el
    docente abre la bandeja; la huella se calcula al registrar, que es
    cuando importa.

    El recorrido no filtra con `rglob("*.pdf")` porque ese patrón no
    encuentra `.PDF` en un sistema de archivos que distingue mayúsculas de
    minúsculas —Windows no distingue, pero el backend puede acabar
    desplegado en Linux, que sí—. Se recorre todo y se filtra por la
    extensión en minúsculas.

    Un archivo que no se puede leer -permiso denegado, bloqueo del
    antivirus, un marcador de sincronización en la nube aún no descargado,
    o borrado entre el recorrido y la lectura- no debe tumbar el listado
    entero, y tampoco debe desaparecer en silencio, que sería peor: entra en
    la lista con `modificado_en=None` y `problema` explicando qué ha
    pasado, para que el docente sepa si es cosa suya o del sistema.
    """
    if not carpeta.is_dir():
        return []

    vistos = []
    for ruta in carpeta.rglob("*"):
        if ruta.suffix.lower() != EXTENSION:
            continue

        relativa = ruta.relative_to(carpeta).as_posix()
        if relativa in rutas_ya_registradas:
            continue

        try:
            if not ruta.is_file():
                continue
            modificado_en = datetime.fromtimestamp(ruta.stat().st_mtime)
            problema = ""
        except OSError as fallo:
            modificado_en = None
            problema = (
                f"No se ha podido leer «{relativa}»: {fallo}. Puede deberse "
                "a un permiso denegado, a un bloqueo del antivirus, o a que "
                "el archivo todavía no se ha descargado si la carpeta se "
                "sincroniza en la nube."
            )

        vistos.append(ArchivoVisto(
            nombre=relativa,
            ruta=ruta,
            modificado_en=modificado_en,
            propuesta=deducir(ruta.name),
            problema=problema,
        ))

    # Los que no tienen fecha (problema al leer) van al final: el primer
    # elemento de la clave vale True cuando hay fecha, y con reverse=True
    # las claves True se colocan antes que las False.
    return sorted(
        vistos,
        key=lambda visto: (
            visto.modificado_en is not None,
            visto.modificado_en or datetime.min,
        ),
        reverse=True,
    )
