"""R5: un fichero por cambio.

Todo cambio de criterio deja constancia de que cambia, por que, con que
respaldo y a que afecta. No es burocracia: es lo que permite defender una
nota meses despues de haberla puesto.
"""

import re
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

CARPETA = "docs/changes"
PLANTILLA = "PLANTILLA.md"
PATRON_NOMBRE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")

SECCIONES_OBLIGATORIAS = (
    "Que cambia",
    "Por que",
    "Fuente que lo respalda",
    "Que arrastra",
    "Correcciones cerradas afectadas",
)

# Tocar cualquiera de estos exige documentar el cambio.
PREFIJOS_VIGILADOS = ("criteria/", "docs/maestro/")


def verificar_formato_cambios(raiz: Path) -> list[Infraccion]:
    """Comprueba nombre y secciones de cada documento de cambio."""
    infracciones: list[Infraccion] = []
    carpeta = raiz / CARPETA
    if not carpeta.is_dir():
        return infracciones

    for ruta in sorted(carpeta.glob("*.md")):
        if ruta.name == PLANTILLA:
            continue
        relativa = ruta.relative_to(raiz).as_posix()

        if not PATRON_NOMBRE.match(ruta.name):
            infracciones.append(Infraccion(
                regla="R5",
                fichero=relativa,
                detalle=(
                    f"'{ruta.name}' no sigue el formato AAAA-MM-DD-asunto.md. "
                    f"La fecha en el nombre permite ordenar los cambios sin "
                    f"abrirlos."
                ),
            ))
            continue

        texto = ruta.read_text(encoding="utf-8")
        for seccion in SECCIONES_OBLIGATORIAS:
            if f"## {seccion}" not in texto:
                infracciones.append(Infraccion(
                    regla="R5",
                    fichero=relativa,
                    detalle=(
                        f"Falta la seccion '## {seccion}'. Copia "
                        f"{CARPETA}/{PLANTILLA} y rellenala entera."
                    ),
                ))

    return infracciones


def verificar_cambio_acompanado(raiz: Path, ficheros_tocados: list[str]) -> list[Infraccion]:
    """Si el commit toca criterios o prosa maestra, exige documento de cambio."""
    tocados = [f.replace("\\", "/") for f in ficheros_tocados]

    vigilados = [f for f in tocados if f.startswith(PREFIJOS_VIGILADOS)]
    if not vigilados:
        return []

    hay_documento = any(
        f.startswith(f"{CARPETA}/") and not f.endswith(PLANTILLA) for f in tocados
    )
    if hay_documento:
        return []

    return [Infraccion(
        regla="R5",
        fichero=vigilados[0],
        detalle=(
            f"Este commit toca {len(vigilados)} fichero(s) de criterios o de "
            f"prosa maestra sin documentar el cambio. Crea "
            f"{CARPETA}/AAAA-MM-DD-asunto.md a partir de la plantilla."
        ),
    )]
