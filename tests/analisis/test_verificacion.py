"""Las seis defensas que quedan, probadas contra un motor hostil."""

from pathlib import Path

from backend.analisis.contrato import (
    AnalisisDelMotor,
    Evidencia,
    Fortaleza,
    IndicioDeAutoria,
    Patron,
    Valoracion,
)
from backend.analisis.verificacion import verificar

TRABAJO = """
1. Introducción

El presente proyecto describe la implantación de un sistema de reservas para
un taller mecánico de tamaño medio situado en la provincia de Sevilla.

5. Presupuesto y viabilidad

El presupuesto inicial asciende a 4.500 euros, repartidos entre licencias,
formación y difusión. La recuperación de la inversión se estima en catorce
meses, considerando un margen bruto del treinta por ciento.
"""


def _val(dimension="D05", nivel="ADECUADO", prioridad="P2", cita=None, obs="Observación."):
    return Valoracion(
        dimension=dimension,
        nivel=nivel,
        prioridad=prioridad,
        evidencia=Evidencia(
            cita=cita or "El presupuesto inicial asciende a 4.500 euros",
            apartado="5. Presupuesto y viabilidad",
        ),
        observacion=obs,
    )


def _fortaleza(descripcion="La estructura del documento es clara.", cita=None):
    return Fortaleza(
        descripcion=descripcion,
        evidencia=Evidencia(
            cita=cita or "El presupuesto inicial asciende a 4.500 euros",
            apartado="5. Presupuesto y viabilidad",
        ),
    )


def _patron(nombre="Patrón detectado", descripcion="Descripción del patrón.", cita=None):
    return Patron(
        nombre=nombre,
        descripcion=descripcion,
        evidencia=Evidencia(
            cita=cita or "El presupuesto inicial asciende a 4.500 euros",
            apartado="5. Presupuesto y viabilidad",
        ),
    )


def _indicio(descripcion="Registro uniforme en todo el texto.", cita=None):
    return IndicioDeAutoria(
        descripcion=descripcion,
        evidencia=Evidencia(
            cita=cita or "El presupuesto inicial asciende a 4.500 euros",
            apartado="5. Presupuesto y viabilidad",
        ),
    )


def _analisis(valoraciones, **cambios):
    datos = dict(
        valoraciones=valoraciones,
        fortalezas=[_fortaleza()],
        patrones=[],
        dudas_para_el_docente=[],
        indicios_de_autoria=[],
    )
    datos.update(cambios)
    return AnalisisDelMotor(**datos)


# --- Defensa 1, integrada: la cita, en los cuatro canales que la traen ---

def test_una_evidencia_inventada_marca_el_juicio(criterios_de_analisis: Path) -> None:
    """El juicio no se borra: se marca. El docente ve que no se pudo localizar."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(cita="El presupuesto asciende a 99.000 euros de inversión")]),
    )

    assert v.valoraciones[0].evidencia_localizada is False
    assert any("no se ha localizado" in r.detalle for r in v.reparos)


def test_una_evidencia_real_se_da_por_localizada(criterios_de_analisis: Path) -> None:
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([_val()]))

    assert v.valoraciones[0].evidencia_localizada is True
    assert v.reparos == []


def test_un_patron_con_evidencia_inventada_se_marca(criterios_de_analisis: Path) -> None:
    """El canal de patrones no queda sin comprobar."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val()], patrones=[_patron(cita="Una cita que no existe en el trabajo")]),
    )

    assert v.patrones[0].evidencia_localizada is False
    assert any("patrón" in r.detalle for r in v.reparos)


def test_un_patron_con_evidencia_real_se_da_por_localizado(criterios_de_analisis: Path) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val()], patrones=[_patron()]),
    )

    assert v.patrones[0].evidencia_localizada is True


def test_una_fortaleza_con_evidencia_inventada_se_marca(criterios_de_analisis: Path) -> None:
    """El canal de fortalezas no queda sin comprobar: llega al alumno."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val()], fortalezas=[_fortaleza(cita="Una cita que no existe en el trabajo")]),
    )

    assert v.fortalezas[0].evidencia_localizada is False
    assert any(
        "fortaleza" in r.detalle and "no se ha localizado" in r.detalle
        for r in v.reparos
    )


def test_una_fortaleza_con_evidencia_real_se_da_por_localizada(criterios_de_analisis: Path) -> None:
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([_val()]))

    assert v.fortalezas[0].evidencia_localizada is True


def test_un_indicio_con_evidencia_inventada_se_marca(criterios_de_analisis: Path) -> None:
    """El canal de indicios de autoría no queda sin comprobar."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis(
            [_val()],
            indicios_de_autoria=[_indicio(cita="Una cita que no existe en el trabajo")],
        ),
    )

    assert v.indicios_de_autoria[0].evidencia_localizada is False
    assert any(
        "indicio de autoría" in r.detalle and "no se ha localizado" in r.detalle
        for r in v.reparos
    )


# --- Defensa 2: ni una dimensión de más ni de menos ---

def test_una_dimension_que_no_toca_en_esa_fase_se_descarta(criterios_de_analisis: Path) -> None:
    """D08 no está activa en E2 (activa_en: [E3, FINAL]). Aunque el motor la
    devuelva, no cuenta."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(dimension="D05"), _val(dimension="D08")]),
    )

    assert [x.dimension for x in v.valoraciones] == ["D05"]
    assert any("D08" in r.detalle and "no está activa" in r.detalle for r in v.reparos)


def test_las_dimensiones_que_faltan_se_declaran(criterios_de_analisis: Path) -> None:
    """No se dan por buenas: se dicen."""
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([_val()]))

    assert "D01" in v.dimensiones_ausentes
    assert "D05" not in v.dimensiones_ausentes


def test_una_dimension_repetida_se_queda_con_la_primera(criterios_de_analisis: Path) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(obs="La primera."), _val(obs="La segunda.")]),
    )

    assert len(v.valoraciones) == 1
    assert v.valoraciones[0].observacion == "La primera."
    assert any("dos veces" in r.detalle for r in v.reparos)


def test_una_dimension_con_cita_inventada_no_aparece_tambien_como_ausente(
    criterios_de_analisis: Path,
) -> None:
    """Una dimensión con evidencia inventada sigue contando como vista: se
    marca `evidencia_localizada=False`, pero no se declara además ausente.
    Que apareciera en las dos listas a la vez sería la contradicción entre
    dos defensas que este test existe para impedir: `vistas.add` tiene que
    ocurrir antes de comprobar la cita, no después ni solo si la cita
    resulta válida."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(dimension="D05", cita="Una cita que no existe en el trabajo")]),
    )

    assert v.valoraciones[0].evidencia_localizada is False
    assert "D05" not in v.dimensiones_ausentes


# --- Defensa: ninguna nota, venga como venga ---

def test_una_nota_en_una_observacion_no_convierte_nada_en_nota(criterios_de_analisis: Path) -> None:
    """El contrato ya impide un campo de nota; esto comprueba que tampoco se
    fabrica una a partir del texto."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(obs="Yo le pondría un 7 sobre 10.")]),
    )

    assert not hasattr(v, "nota")
    assert not hasattr(v.valoraciones[0], "nota")


# --- Defensa: el aviso del §13 es estructural, no depende de la redacción ---

def test_los_indicios_de_autoria_se_conservan_como_indicios(criterios_de_analisis: Path) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val()], indicios_de_autoria=[_indicio()]),
    )

    assert v.indicios_de_autoria[0].descripcion == "Registro uniforme en todo el texto."
    assert v.indicios_de_autoria[0].evidencia_localizada is True
    # El aviso del §13 acompaña a todo indicio, aunque su redacción sea
    # neutra y no dispare el realce de frases categóricas.
    assert any(r.regla == "autoria_es_indicio" for r in v.reparos)
    assert not any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos)


def test_un_indicio_redactado_de_la_forma_mas_neutra_posible_tambien_lleva_el_aviso(
    criterios_de_analisis: Path,
) -> None:
    """Esta es la prueba que fija la garantía nueva: no depende de que el
    indicio suene a veredicto. Un indicio redactado con la máxima cautela
    -sin verbo de atribución, sin nombrar ninguna IA- lleva el aviso igual
    que uno redactado como titular."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis(
            [_val()],
            indicios_de_autoria=[_indicio(
                descripcion="El vocabulario del apartado 4 difiere del resto del trabajo."
            )],
        ),
    )

    assert any(r.regla == "autoria_es_indicio" for r in v.reparos)
    assert not any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos)


def test_un_indicio_con_cita_inventada_sigue_llevando_el_aviso_del_13(
    criterios_de_analisis: Path,
) -> None:
    """El cruce peligroso: un indicio de autoría cuya cita el motor se ha
    inventado es el menos fiable de todos los que produce el sistema, y por
    eso mismo es el que más necesita el aviso de que la decisión es del
    profesor. Si el aviso se pusiera solo cuando la cita se localiza -por
    ejemplo, si alguien lo metiera dentro de un `if localizada:`-, justo este
    indicio, el que el motor se ha sacado de la manga, llegaría al profesor
    sin la advertencia, que es el escenario de mayor riesgo de toda la
    defensa. Este test comprueba las dos condiciones a la vez y a propósito:
    ni una por separado basta para fijar la garantía."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis(
            [_val()],
            indicios_de_autoria=[_indicio(cita="Una cita que no existe en el trabajo")],
        ),
    )

    assert v.indicios_de_autoria[0].evidencia_localizada is False
    assert any(r.regla == "autoria_es_indicio" for r in v.reparos)


def test_un_indicio_redactado_como_afirmacion_se_marca(criterios_de_analisis: Path) -> None:
    """«Este texto ha sido generado por IA» no es un indicio: es un veredicto.

    El realce lo señala aparte, pero el aviso del §13 ya estaba puesto antes
    de mirar la redacción: por eso las dos reglas conviven en la lista.
    """
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis(
            [_val()],
            indicios_de_autoria=[_indicio(descripcion="Este texto ha sido generado por una IA.")],
        ),
    )

    assert any(r.regla == "autoria_es_indicio" for r in v.reparos)
    assert any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos)
    # No se destruye: el docente lo sigue viendo, con el aviso al lado.
    assert v.indicios_de_autoria[0].descripcion == "Este texto ha sido generado por una IA."


def test_una_afirmacion_de_autoria_sin_tildes_tambien_se_marca(criterios_de_analisis: Path) -> None:
    """El motor puede devolver el texto sin acentuar; la comprobación no
    depende de que lo acentúe bien."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis(
            [_val()],
            indicios_de_autoria=[_indicio(descripcion="Este texto esta generado por una IA.")],
        ),
    )

    assert any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos)


def test_un_indicio_prudente_no_dispara_el_realce(criterios_de_analisis: Path) -> None:
    """Sugerir no es afirmar: no todo indicio dispara el realce. El aviso del
    §13 sí lo lleva -esa es la garantía-, pero el realce, no."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis(
            [_val()],
            indicios_de_autoria=[_indicio(descripcion="El registro cambia bruscamente entre apartados.")],
        ),
    )

    assert not any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos)
    assert any(r.regla == "autoria_es_indicio" for r in v.reparos)


# Las diez formulaciones que la revisión coló contra la lista cerrada
# original (solo se documentaron seis explícitamente). Ninguna es necesaria
# para que la garantía se sostenga -el test de arriba con redacción neutra ya
# la fija-, pero la lista ampliada las reconoce igualmente como realce.
_FORMULACIONES_CATEGORICAS_DE_LA_REVISION = [
    "Este texto ha sido escrito por una inteligencia artificial.",
    "El presente trabajo fue redactado por una inteligencia artificial.",
    "Se trata de un texto producido íntegramente por ChatGPT.",
    "El texto ha sido creado por Gemini.",
    "El alumno no redactó esto; lo redactó una IA.",
    "Este texto proviene de un modelo de lenguaje, no de una persona.",
]


def test_el_realce_ampliado_reconoce_las_formulaciones_de_la_revision(
    criterios_de_analisis: Path,
) -> None:
    """No es la garantía -el aviso del §13 ya cubre estas frases igual que
    cualquier otra-, pero conviene que el realce ampliado las detecte."""
    for descripcion in _FORMULACIONES_CATEGORICAS_DE_LA_REVISION:
        v = verificar(
            criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
            _analisis([_val()], indicios_de_autoria=[_indicio(descripcion=descripcion)]),
        )
        assert any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos), (
            f"El realce no reconoció: {descripcion!r}"
        )


# La versión cerrada de siete frases de la primera ronda sí reconocía "ha
# sido generado por" y "está generado por" como construcciones sueltas, sin
# nombre detrás. Al reescribir la lista con combinaciones verbo+nombre esas
# dos se perdieron: "ha sido generado por un algoritmo" o "está generado por
# un sistema no identificado" no nombran ninguna IA de la lista y dejaron de
# dispararla. Este test fija que no se vuelva a perder.
def test_el_realce_no_retrocede_en_las_construcciones_sin_nombre_de_ia(
    criterios_de_analisis: Path,
) -> None:
    for descripcion in (
        "Este texto ha sido generado por un algoritmo.",
        "El documento está generado por un sistema no identificado.",
    ):
        v = verificar(
            criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
            _analisis([_val()], indicios_de_autoria=[_indicio(descripcion=descripcion)]),
        )
        assert any(r.regla == "autoria_formulada_categoricamente" for r in v.reparos), (
            f"El realce no reconoció: {descripcion!r}"
        )


# --- Un motor que devuelve basura entera ---

def test_un_analisis_vacio_no_revienta(criterios_de_analisis: Path) -> None:
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([]))

    assert v.valoraciones == []
    assert len(v.dimensiones_ausentes) > 0


def test_todas_las_dimensiones_inventadas(criterios_de_analisis: Path) -> None:
    """Ni una sobrevive, y el análisis sigue siendo utilizable."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(dimension="D08", cita="inventada del todo y bien larga")]),
    )

    assert v.valoraciones == []
    assert len(v.reparos) >= 1
