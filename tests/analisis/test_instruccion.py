"""Lo que se le pide al motor sale de los criterios, no del código."""

from pathlib import Path

from backend.analisis.instruccion import construir


def test_pide_solo_las_dimensiones_de_esa_fase(criterios_de_analisis: Path) -> None:
    """D08 no está activa en E2 y no debe aparecer en lo que se le pide."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "D05" in texto
    assert "D08" not in texto


def test_en_una_fase_posterior_pide_mas(criterios_de_analisis: Path) -> None:
    en_e2 = construir(criterios_de_analisis, "v2026-2027", "E2")
    en_final = construir(criterios_de_analisis, "v2026-2027", "FINAL")

    assert "D08" in en_final
    assert len(en_final) > len(en_e2)


def test_lleva_el_nombre_de_cada_dimension(criterios_de_analisis: Path) -> None:
    """El código D05 no le dice nada a nadie; el nombre sí."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Fundamentacion y fuentes" in texto


def test_explica_los_cuatro_niveles_de_prioridad(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    for codigo in ("P1", "P2", "P3", "P4"):
        assert codigo in texto
    assert "No compensa el coste pedagogico" in texto


def test_exige_evidencia_literal(criterios_de_analisis: Path) -> None:
    """Es la instrucción que sostiene la primera defensa."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "literal" in texto.lower()


def test_prohibe_la_nota(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "no propongas" in texto.lower() or "no asignes" in texto.lower()
    assert "nota" in texto.lower()


def test_prohibe_afirmar_la_autoria(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "no afirmes" in texto.lower()


def test_traslada_el_rigor_proporcional(criterios_de_analisis: Path) -> None:
    """El §2 del calibrador: rigor de FP, no auditoría."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Formacion Profesional" in texto or "Formación Profesional" in texto


def test_cambiar_un_criterio_cambia_la_instruccion(
    criterios_de_analisis: Path,
) -> None:
    """La prueba de que la instrucción se lee y no se escribe a mano."""
    dimensiones = criterios_de_analisis / "criteria" / "v2026-2027" / "dimensiones.yaml"
    antes = construir(criterios_de_analisis, "v2026-2027", "E2")

    dimensiones.write_text(
        dimensiones.read_text(encoding="utf-8").replace(
            "Fundamentacion y fuentes", "Rigor de las fuentes citadas"
        ),
        encoding="utf-8",
    )
    despues = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Rigor de las fuentes citadas" in despues
    assert antes != despues


def test_sin_criterios_no_se_inventa_una_instruccion(tmp_path: Path) -> None:
    """Sin dimensiones no hay nada que pedir, y se dice en vez de improvisar."""
    import pytest

    with pytest.raises(ValueError, match="dimensiones"):
        construir(tmp_path, "v2026-2027", "E2")
