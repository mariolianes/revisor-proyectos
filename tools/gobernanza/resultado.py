"""Tipo comun de resultado de los verificadores de gobernanza."""

from dataclasses import dataclass
from collections import Counter


@dataclass(frozen=True)
class Infraccion:
    """Una infraccion concreta de una regla de gobernanza.

    regla: identificador corto, "R1" a "R7".
    fichero: ruta relativa a la raiz del repositorio.
    detalle: explicacion accionable, en castellano, sin jerga.
    """

    regla: str
    fichero: str
    detalle: str


def formatear(infracciones: list[Infraccion]) -> str:
    """Devuelve el informe legible que imprime la CLI."""
    if not infracciones:
        return "Gobernanza conforme: 0 infracciones."

    conteo = Counter(inf.regla for inf in infracciones)
    resumen = ", ".join(f"{regla} ({conteo[regla]})" for regla in sorted(conteo))
    lineas = [f"{len(infracciones)} infracciones -> {resumen}", ""]
    for inf in sorted(infracciones, key=lambda i: (i.regla, i.fichero)):
        lineas.append(f"  [{inf.regla}] {inf.fichero}")
        lineas.append(f"        {inf.detalle}")
    return "\n".join(lineas)
