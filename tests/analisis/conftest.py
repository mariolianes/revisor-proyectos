"""Una copia de trabajo de los criterios reales de v2026-2027.

Los textos que las pruebas comprueban -el nombre de D05, el efecto de P4, el
limite de la economia pedagogica- son los reales de `criteria/v2026-2027/`.
Si aqui se inventara una copia con otros valores, la prueba estaria
comprobando esa copia y no lo que `construir` compone de verdad a partir de
los criterios del repositorio.

Es una copia, no la carpeta original, porque una de las pruebas modifica un
fichero para comprobar que cambiarlo cambia la instruccion: hacerlo sobre
`criteria/` mutaria el repositorio real.
"""

import shutil
from pathlib import Path

import pytest

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]


@pytest.fixture
def criterios_de_analisis(tmp_path: Path) -> Path:
    """Una raiz con una copia de `criteria/`, lista para leer o alterar."""
    destino = tmp_path / "repo"
    shutil.copytree(RAIZ_DEL_REPOSITORIO / "criteria", destino / "criteria")
    return destino
