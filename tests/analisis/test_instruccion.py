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

    assert "Fundamentación y fuentes" in texto


def test_explica_los_cuatro_niveles_de_prioridad(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    for codigo in ("P1", "P2", "P3", "P4"):
        assert codigo in texto
    assert "No compensa el coste pedagógico" in texto


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
            "Fundamentación y fuentes", "Rigor de las fuentes citadas"
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


def test_el_limite_de_economia_pedagogica_aparece_y_cambia_con_el_criterio(
    criterios_de_analisis: Path,
) -> None:
    """El "como mucho N" no puede estar escrito en el código: si el YAML no
    lo trae, no debe aparecer, y si el YAML lo cambia, el número cambia con
    él. Sin esta prueba, borrar el bloque entero deja pasar los demás tests
    igual de verdes.
    """
    feedback = criterios_de_analisis / "criteria" / "v2026-2027" / "feedback.yaml"
    con_limite = construir(criterios_de_analisis, "v2026-2027", "E2")
    assert "4" in con_limite

    feedback.write_text(
        feedback.read_text(encoding="utf-8").replace(
            "prioridades_maximas: 4", "prioridades_maximas: 2"
        ),
        encoding="utf-8",
    )
    con_otro_limite = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "2" in con_otro_limite
    assert con_limite != con_otro_limite


def test_pide_priorizar_lo_que_el_criterio_marca(criterios_de_analisis: Path) -> None:
    """El 2026-08-31 el docente pidió que «objetivos claros», «desarrollo
    real» y compañía se prioricen siempre, y no de memoria: si
    `priorizar_siempre` desaparece de `feedback.yaml`, la instrucción deja
    de pedirlo."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Objetivos claros y coherentes" in texto
    assert "Cumplimiento del formato mínimo" in texto


def test_sin_priorizar_siempre_no_se_inventa_la_lista(tmp_path: Path) -> None:
    """Sin el criterio, no hay lista que pedir -no una lista escrita a mano
    aquí como red de seguridad-."""
    import shutil

    from tests.conftest import RAIZ_DEL_REPOSITORIO

    destino = tmp_path / "criteria" / "v2026-2027"
    shutil.copytree(RAIZ_DEL_REPOSITORIO / "criteria" / "v2026-2027", destino)
    feedback = destino / "feedback.yaml"
    contenido = feedback.read_text(encoding="utf-8")
    inicio = contenido.index("priorizar_siempre:")
    fin = contenido.index("\n\n", inicio)
    feedback.write_text(contenido[:inicio] + contenido[fin + 2:], encoding="utf-8")

    texto = construir(tmp_path, "v2026-2027", "E2")

    assert "Objetivos claros y coherentes" not in texto


def test_pide_no_exigir_lo_que_el_criterio_marca(criterios_de_analisis: Path) -> None:
    """El ejemplo real que motivó este bloque: un proyecto de importación
    textil al que se le pidieron indicadores de logro, flujo de caja y
    ratios financieros como si fueran requisitos generales. La instrucción
    tiene que decir explícitamente que no se exijan, no solo hablar de
    "rigor proporcional" en abstracto."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "indicadores de logro" in texto.lower()
    assert "flujo de caja" in texto.lower()
    assert "no exijas" in texto.lower()


def test_el_limite_de_prioridades_menciona_la_agrupacion_por_causa(
    criterios_de_analisis: Path,
) -> None:
    """El límite ya no se pide como "cuatro hallazgos", sino como "cuatro
    causas": si el texto vuelve a hablar solo de un número, el modelo puede
    volver a elegir cuatro observaciones aisladas."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "causa" in texto.lower()


def test_las_dimensiones_salen_en_el_orden_del_criterio(
    criterios_de_analisis: Path,
) -> None:
    """D05 va antes que D06 en dimensiones.yaml; en la instrucción, también."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert texto.index("D05") < texto.index("D06")
