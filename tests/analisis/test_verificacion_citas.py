"""La defensa de la que depende todo lo demás."""

from backend.analisis.verificacion import (
    CITA_MINIMA,
    cita_localizada,
    normalizar_para_buscar,
)

TRABAJO = """
5. Presupuesto y viabilidad

El presupuesto inicial asciende a 4.500 euros, repartidos entre licencias,
formación y difusión. La recuperación de la inversión se estima en catorce
meses, considerando un margen bruto del treinta por ciento.

6. Conclusiones

El proyecto resulta viable y sostenible a medio plazo.
"""


def test_una_cita_literal_se_localiza() -> None:
    assert cita_localizada("El presupuesto inicial asciende a 4.500 euros", TRABAJO)


def test_una_cita_inventada_no_se_localiza() -> None:
    """El caso que esta defensa existe para cazar."""
    assert not cita_localizada(
        "El presupuesto inicial asciende a 12.000 euros", TRABAJO
    )


def test_la_cita_aguanta_diferencias_de_espaciado() -> None:
    """El texto de un PDF llega con saltos de línea donde no los había."""
    assert cita_localizada(
        "formación y difusión. La recuperación de la inversión", TRABAJO
    )


def test_la_cita_aguanta_diferencias_de_tildes() -> None:
    """Un modelo puede devolver la cita sin acentuar."""
    assert cita_localizada("La recuperacion de la inversion se estima", TRABAJO)


def test_una_parafrasis_no_se_da_por_buena() -> None:
    """Resumir no es citar. Si el motor resume, no hay evidencia localizable."""
    assert not cita_localizada(
        "El trabajo dice que el presupuesto ronda los cuatro mil quinientos euros",
        TRABAJO,
    )


def test_una_cita_demasiado_corta_no_vale() -> None:
    """«el» aparece en cualquier documento y no señala nada."""
    assert not cita_localizada("el", TRABAJO)
    assert not cita_localizada("viable", TRABAJO)


def test_una_cita_vacia_no_vale() -> None:
    assert not cita_localizada("", TRABAJO)
    assert not cita_localizada("     ", TRABAJO)


def test_normalizar_colapsa_espacios_y_quita_tildes() -> None:
    assert normalizar_para_buscar("  La  recuperación\n de la inversión ") == (
        "la recuperacion de la inversion"
    )


def test_una_cita_de_veinte_caracteres_normalizados_se_acepta() -> None:
    """El umbral es un mínimo inclusivo: veinte caracteres ya valen."""
    cita = "Presupuesto y viabil"
    assert len(normalizar_para_buscar(cita)) == CITA_MINIMA
    assert cita_localizada(cita, TRABAJO)


def test_una_cita_de_diecinueve_caracteres_normalizados_se_rechaza() -> None:
    """Un carácter por debajo del mínimo, y dejar de valer aunque esté en el texto."""
    cita = "Presupuesto y viabi"
    assert len(normalizar_para_buscar(cita)) == CITA_MINIMA - 1
    assert not cita_localizada(cita, TRABAJO)


def test_una_cita_rellenada_de_espacios_no_burla_el_minimo() -> None:
    """El mínimo se mide sobre la cita normalizada, no sobre la cita en bruto.

    Si se midiera sobre el original, rellenar "el" con espacios hasta superar
    veinte caracteres en bruto bastaría para colarlo como si señalara algo,
    porque "el" aparece como subcadena en casi cualquier texto.
    """
    relleno = "el" + " " * 30
    assert len(relleno) >= CITA_MINIMA
    assert len(normalizar_para_buscar(relleno)) < CITA_MINIMA
    assert not cita_localizada(relleno, TRABAJO)


def test_la_normalizacion_reune_una_palabra_partida_por_guion_de_maquetacion() -> None:
    """Al exportar a PDF, Word puede partir una palabra al final de línea."""
    texto_con_guion_de_maquetacion = (
        "La recuperación de la inver-\nsión se estima en catorce meses."
    )
    assert cita_localizada(
        "La recuperación de la inversión se estima", texto_con_guion_de_maquetacion
    )


def test_un_guion_de_palabra_compuesta_no_se_toca() -> None:
    """"coste-beneficio" es una palabra legítima: no lleva un salto de línea detrás."""
    assert normalizar_para_buscar("un análisis coste-beneficio detallado") == (
        "un analisis coste-beneficio detallado"
    )


def test_las_comillas_tipograficas_de_word_se_igualan_a_las_rectas() -> None:
    """Word sustituye las comillas rectas por unas tipográficas al exportar."""
    texto = "En sus conclusiones escribe: “el proyecto es viable” y lo argumenta bien"
    assert cita_localizada('"el proyecto es viable"', texto)


def test_una_ligadura_tipografica_no_impide_encontrar_la_cita() -> None:
    """"ﬁ" es un único carácter Unicode; el modelo la transcribe como "fi"."""
    texto = "la eﬁciencia energética del proceso productivo mejora notablemente"
    assert cita_localizada(
        "la eficiencia energetica del proceso productivo", texto
    )
