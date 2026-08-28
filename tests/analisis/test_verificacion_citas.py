"""La defensa de la que depende todo lo demás."""

from backend.analisis.verificacion import cita_localizada, normalizar_para_buscar

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
