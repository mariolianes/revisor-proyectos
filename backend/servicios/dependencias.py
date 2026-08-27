"""Qué criterio deriva de qué sección de la prosa.

Es la información que el editor enseña al lado del texto: antes de tocar
una sección, saber qué depende de ella.
"""

from pathlib import Path

from pydantic import BaseModel

from tools.gobernanza.criterios import cargar_anclas, entradas_de

# Claves que no son valores del criterio sino metadatos de la propia entrada.
CLAVES_INTERNAS = {"fuente", "_clave", "codigo"}


class CriterioDerivado(BaseModel):
    """Un criterio ejecutable que cita una sección concreta como fuente."""

    fichero: str
    identificador: str
    valores: dict[str, str]
    fuente: str


def _identificador(entrada: dict) -> str:
    return str(entrada.get("codigo") or entrada.get("_clave") or "sin identificador")


def _valores(entrada: dict) -> dict[str, str]:
    """Los valores del criterio, en texto, sin sus metadatos."""
    return {
        clave: str(valor)
        for clave, valor in entrada.items()
        if clave not in CLAVES_INTERNAS
    }


def criterios_de(raiz: Path, ancla: str) -> list[CriterioDerivado]:
    """Criterios que declaran esa ancla como su fuente."""
    derivados: list[CriterioDerivado] = []
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return derivados

    for ruta in sorted(carpeta.rglob("*.yaml")):
        relativa = ruta.relative_to(raiz).as_posix()
        for entrada in entradas_de(ruta):
            if entrada.get("fuente") != ancla:
                continue
            derivados.append(CriterioDerivado(
                fichero=relativa,
                identificador=_identificador(entrada),
                valores=_valores(entrada),
                fuente=ancla,
            ))
    return derivados


def contar_por_ancla(raiz: Path) -> dict[str, int]:
    """Cuántos criterios cita cada ancla del repositorio, incluidas las que nadie cita."""
    conteo = {ancla: 0 for ancla in cargar_anclas(raiz)}
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return conteo

    for ruta in sorted(carpeta.rglob("*.yaml")):
        for entrada in entradas_de(ruta):
            fuente = entrada.get("fuente")
            if isinstance(fuente, str) and fuente in conteo:
                conteo[fuente] += 1
    return conteo
