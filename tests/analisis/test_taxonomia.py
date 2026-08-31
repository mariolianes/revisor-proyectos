"""La taxonomía de incidencias del §13 del calibrador.

`criterios_de_analisis` copia el árbol real de `criteria/`, así que estas
pruebas comprueban tanto el módulo (`backend/analisis/taxonomia.py`) como
el fichero de verdad del repositorio, no una copia inventada.
"""

from pathlib import Path

import pytest

from backend.analisis.taxonomia import (
    CategoriaDeIncidencia,
    cargar_taxonomia,
    categorias_de_dimension,
    codigos_validos,
)

LOS_DIEZ_CODIGOS = {
    "DEV-INSUF", "TEO-EXCESO", "APL-FALTA", "OBJ-DEF", "CUANT-BAS",
    "EST-INCOH", "CIERRE-FALTA", "FOR-DEF", "FUE-INSUF", "FB-NOAPL",
}


def test_carga_las_diez_categorias_del_docente(criterios_de_analisis: Path) -> None:
    categorias = cargar_taxonomia(criterios_de_analisis, "v2026-2027")

    assert {c.codigo for c in categorias} == LOS_DIEZ_CODIGOS
    assert all(isinstance(c, CategoriaDeIncidencia) for c in categorias)


def test_toda_categoria_declara_su_fuente(criterios_de_analisis: Path) -> None:
    """R1: ningún criterio sin origen. Se comprueba aquí también, no solo con
    el verificador de gobernanza, para que un fichero mal formado falle en
    la suite de pytest y no solo en un `python tools/verificar_gobernanza.py`
    que alguien podría olvidar ejecutar."""
    categorias = cargar_taxonomia(criterios_de_analisis, "v2026-2027")

    for categoria in categorias:
        assert categoria.fuente == "calibracion#13-taxonomia-de-incidencias"


def test_codigos_validos_es_el_mismo_conjunto(criterios_de_analisis: Path) -> None:
    assert codigos_validos(criterios_de_analisis, "v2026-2027") == LOS_DIEZ_CODIGOS


def test_una_version_sin_taxonomia_no_revienta(tmp_path: Path) -> None:
    """Una raíz sin `criteria/<version>/taxonomia-incidencias.yaml` -una
    versión futura que todavía no la tenga- se lee como "sin categorías",
    no como un error: la calibración debe poder seguir con el resto de
    indicadores aunque este fichero falte."""
    raiz = tmp_path / "repo"

    assert cargar_taxonomia(raiz, "v2099-2100") == []
    assert codigos_validos(raiz, "v2099-2100") == set()


# ---------------------------------------------------------------------------
# categorias_de_dimension(): de dónde sale la categoría de una observación
# ---------------------------------------------------------------------------


def test_una_dimension_con_una_sola_categoria_plausible(criterios_de_analisis: Path) -> None:
    """D11 (Redacción y presentación) solo puede ser FOR-DEF."""
    assert categorias_de_dimension(criterios_de_analisis, "v2026-2027", "D11") == ["FOR-DEF"]


def test_d07_tiene_tres_categorias_plausibles(criterios_de_analisis: Path) -> None:
    """El caso de manual del propio encargo: una insuficiencia de
    "Desarrollo aplicado" puede ser desarrollo insuficiente, exceso de
    teoría o aplicación práctica insuficiente, y el sistema no elige por el
    docente cuál de las tres es -devuelve las tres, no una media inventada."""
    codigos = categorias_de_dimension(criterios_de_analisis, "v2026-2027", "D07")

    assert set(codigos) == {"DEV-INSUF", "TEO-EXCESO", "APL-FALTA"}


@pytest.mark.parametrize("dimension", ["D01", "D02", "D06", "D12"])
def test_las_dimensiones_que_la_taxonomia_no_cubre_devuelven_vacio(
    criterios_de_analisis: Path, dimension: str
) -> None:
    """La taxonomía del docente tiene diez categorías, no doce: adecuación al
    ciclo, tema y justificación, metodología y autoría no encajan en
    ninguna, y eso se dice con una lista vacía, no con una categoría
    forzada."""
    assert categorias_de_dimension(criterios_de_analisis, "v2026-2027", dimension) == []


def test_una_dimension_que_no_existe_tambien_devuelve_vacio(
    criterios_de_analisis: Path,
) -> None:
    assert categorias_de_dimension(criterios_de_analisis, "v2026-2027", "D99") == []
