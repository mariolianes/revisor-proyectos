"""Dónde están las cosas cuando el programa va empaquetado en un ejecutable.

Para la beta, el docente recibe **un solo fichero** y lo abre. No instala
Python, ni Node, ni dependencias: PyInstaller mete todo eso dentro. Eso parte
en dos lo que hasta ahora era una sola raíz:

- **Los recursos del programa** -los criterios, la prosa normativa del
  docente, la configuración, el frontend compilado- viajan dentro del
  ejecutable. PyInstaller los desempaqueta en una carpeta temporal que
  cambia en cada arranque.
- **Lo suyo** -el `.env` con sus claves y la ruta de sus entregas- vive al
  lado del ejecutable, y tiene que sobrevivir a una actualización del
  programa.

Confundir las dos es el fallo clásico de empaquetar: el `.env` acaba dentro
del temporal y se pierde cada vez que cierra el programa, o los criterios se
buscan al lado del ejecutable y no aparecen. Por eso son dos funciones con
nombres distintos y no un parámetro.

Sin empaquetar -ejecutando desde el repositorio- las dos devuelven la raíz
del repositorio, que es lo que hacía el sistema antes de que esto existiera.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[1]


def empaquetado() -> bool:
    """Si esto corre dentro de un ejecutable de PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def raiz_de_recursos() -> Path:
    """De dónde se leen los criterios, la prosa normativa y el frontend.

    Van dentro del ejecutable: son parte del programa, no del docente, y
    tienen que actualizarse con él. Nada de lo que hay aquí se escribe.
    """
    if empaquetado():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _RAIZ_DEL_REPOSITORIO


def carpeta_de_trabajo() -> Path:
    """Dónde vive el `.env` del docente, al lado del ejecutable.

    Tiene que sobrevivir a una actualización del programa: si esto
    devolviera la carpeta temporal de PyInstaller, sus claves y la ruta de
    sus entregas desaparecerían cada vez que cierra el programa, y volvería a
    configurarlo todo en cada arranque.
    """
    if empaquetado():
        return Path(sys.executable).resolve().parent
    return _RAIZ_DEL_REPOSITORIO


def config(nombre: str, raiz: Path) -> Path:
    """Un fichero de `config/`, prefiriendo el del docente al del programa.

    La mayoría de la configuración es del programa y viaja dentro: la
    estructura de carpetas, las tarifas. Pero `centros.yaml` **no**: los
    centros son suyos, cambian cuando abre uno nuevo, y no puede editarlos si
    están dentro del ejecutable.

    Empaquetado, se busca primero al lado del ejecutable y se cae al de
    dentro si no está: el programa arranca siempre -con el catálogo que
    traiga- y él puede poner el suyo encima sin esperar a una versión nueva.
    Sin empaquetar, `raiz` manda y no hay sustitución que buscar.

    Se descubrió importando un listado de verdad desde el ejecutable: las dos
    filas se rechazaron por un catálogo de centros vacío que no había forma
    de rellenar.
    """
    if empaquetado():
        suyo = carpeta_de_trabajo() / "config" / nombre
        if suyo.is_file():
            return suyo
    return raiz / "config" / nombre
