"""Qué se deduce del nombre de un archivo, y qué no."""

from datetime import date

import pytest

from backend.vigilancia.nombres import deducir


def test_nombre_completo_se_deduce_entero() -> None:
    propuesta = deducir("AF023_DAM_E2_20260115_v1.pdf")

    assert propuesta.codigo_alumno == "AF023"
    assert propuesta.ciclo == "DAM"
    assert propuesta.fase == "E2"
    assert propuesta.fecha == date(2026, 1, 15)
    assert propuesta.version == 1
    assert propuesta.completa is True
    assert propuesta.motivo == ""


@pytest.mark.parametrize("fase", ["TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA"])
def test_todas_las_fases_conocidas(fase: str) -> None:
    propuesta = deducir(f"AF023_DAM_{fase}_20260115_v1.pdf")

    assert propuesta.fase == fase


def test_la_fase_se_reconoce_en_minusculas() -> None:
    propuesta = deducir("af023_dam_e2_20260115_v1.pdf")

    assert propuesta.fase == "E2"
    assert propuesta.codigo_alumno == "AF023"


def test_una_fase_desconocida_no_se_inventa() -> None:
    propuesta = deducir("AF023_DAM_E9_20260115_v1.pdf")

    assert propuesta.fase is None
    assert propuesta.completa is False
    assert "E9" in propuesta.motivo


def test_un_nombre_que_no_sigue_la_convencion_no_deduce_nada() -> None:
    propuesta = deducir("trabajo final juan.pdf")

    assert propuesta.codigo_alumno is None
    assert propuesta.fase is None
    assert propuesta.completa is False
    assert "no sigue la convención" in propuesta.motivo


def test_una_fecha_imposible_no_se_inventa() -> None:
    propuesta = deducir("AF023_DAM_E2_20261352_v1.pdf")

    assert propuesta.fecha is None
    assert propuesta.completa is False
    assert "fecha" in propuesta.motivo


def test_sin_version_la_propuesta_sigue_incompleta() -> None:
    propuesta = deducir("AF023_DAM_E2_20260115.pdf")

    assert propuesta.codigo_alumno == "AF023"
    assert propuesta.version is None
    assert propuesta.completa is False


def test_la_version_admite_mayuscula() -> None:
    assert deducir("AF023_DAM_E2_20260115_V3.pdf").version == 3


def test_el_motivo_va_dirigido_al_docente() -> None:
    """Dice qué se esperaba, con un ejemplo, no un patrón de expresión regular."""
    propuesta = deducir("cosa.pdf")

    assert "AF023_DAM_E2_20260115_v1.pdf" in propuesta.motivo
