"""`afirmacion_de_ausencia`: distinguir una cita inventada de una que
describe que algo falta.

El docente, 2026-08-31: «comprobar no solo que la frase existe, sino que
sostiene realmente la afirmación [...] Una afirmación de ausencia debe
comprobarse en todo el apartado o en todo el documento, no mediante una
única cita». Antes de este cambio, una observación como «No se localizan
referencias a la incorporación de feedback o evolución entre versiones»
-escrita en el hueco de la cita, sin citar nada- recibía el mismo reparo
genérico (`evidencia_localizable`) que una cita inventada del todo. Este
fichero prueba que ahora recibe un reparo distinto (`afirmacion_de_ausencia`)
que se lo dice al docente, sin fingir que el sistema ha comprobado la
ausencia -no lo hace; ver el docstring de `_MARCADORES_DE_AUSENCIA` en
`backend/analisis/verificacion.py` para por qué no-.
"""

from pathlib import Path

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Fortaleza, IndicioDeAutoria, Patron, Valoracion
from backend.analisis.verificacion import es_afirmacion_de_ausencia, verificar

TRABAJO = """
1. Introducción

El presente proyecto describe la implantación de un sistema de reservas para
un taller mecánico de tamaño medio situado en la provincia de Sevilla.

5. Presupuesto y viabilidad

El presupuesto inicial asciende a 4.500 euros, repartidos entre licencias,
formación y difusión.
"""


def _val(cita: str) -> Valoracion:
    return Valoracion(
        dimension="D05", nivel="INSUFICIENTE", prioridad="P2",
        evidencia=Evidencia(cita=cita, apartado="10. Evolución y feedback"),
        observacion="Observación de prueba.",
    )


def _analisis(**cambios) -> AnalisisDelMotor:
    datos = dict(
        valoraciones=[_val("El presupuesto inicial asciende a 4.500 euros")],
        fortalezas=[], patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )
    datos.update(cambios)
    return AnalisisDelMotor(**datos)


# ---------------------------------------------------------------------------
# es_afirmacion_de_ausencia(): la función de reconocimiento, aislada
# ---------------------------------------------------------------------------


def test_reconoce_la_frase_del_caso_real() -> None:
    """El caso que motivó el cambio, tal cual lo escribía el motor."""
    assert es_afirmacion_de_ausencia(
        "No se localizan referencias a la incorporación de feedback o "
        "evolución entre versiones."
    ) is True


def test_reconoce_variantes_en_mayusculas_y_sin_tildes() -> None:
    # sin-tilde: la propia prueba comprueba que la falta de tilde no importa.
    assert es_afirmacion_de_ausencia("NO SE MENCIONA la metodologia empleada") is True
    assert es_afirmacion_de_ausencia("no se menciona la metodología empleada") is True


def test_reconoce_ausencia_de_como_marcador() -> None:
    assert es_afirmacion_de_ausencia("Ausencia de bibliografía en el cierre.") is True


def test_una_cita_real_no_se_confunde_con_una_ausencia() -> None:
    assert es_afirmacion_de_ausencia("El presupuesto inicial asciende a 4.500 euros") is False


def test_una_cita_inventada_generica_no_se_confunde_con_una_ausencia() -> None:
    """"Una cita que no existe en el trabajo" es la frase que usan las
    pruebas de `test_verificacion.py` para una cita fabricada del todo, no
    para una afirmación de ausencia. No debe activar el marcador: "no
    existe" a secas no es uno de ellos, a propósito, porque encajaría con
    frases así."""
    assert es_afirmacion_de_ausencia("Una cita que no existe en el trabajo") is False


# ---------------------------------------------------------------------------
# verificar(): el reparo distinto, en los cuatro canales
# ---------------------------------------------------------------------------


def test_una_valoracion_con_afirmacion_de_ausencia_recibe_el_reparo_especifico(
    criterios_de_analisis: Path,
) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E3", TRABAJO,
        _analisis(valoraciones=[_val(
            "No se localizan referencias a la incorporación de feedback o "
            "evolución entre versiones."
        )]),
    )

    assert v.valoraciones[0].evidencia_localizada is False
    reparo = next(r for r in v.reparos if r.regla == "afirmacion_de_ausencia")
    assert "D05" in reparo.detalle
    assert "no se puede comprobar con una única cita" in reparo.detalle
    assert not any(r.regla == "evidencia_localizable" for r in v.reparos)


def test_un_patron_con_afirmacion_de_ausencia_recibe_el_reparo_especifico(
    criterios_de_analisis: Path,
) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E3", TRABAJO,
        _analisis(patrones=[Patron(
            nombre="Fuentes nominales",
            descripcion="Descripción de prueba.",
            evidencia=Evidencia(
                cita="No se aprecia ninguna cita integrada en el desarrollo.",
                apartado="5",
            ),
        )]),
    )

    assert v.patrones[0].evidencia_localizada is False
    reparo = next(r for r in v.reparos if r.regla == "afirmacion_de_ausencia")
    assert "patrón" in reparo.detalle


def test_una_fortaleza_con_afirmacion_de_ausencia_recibe_el_reparo_especifico(
    criterios_de_analisis: Path,
) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E3", TRABAJO,
        _analisis(fortalezas=[Fortaleza(
            descripcion="Fortaleza de prueba.",
            evidencia=Evidencia(cita="No consta ningún error en el cálculo.", apartado="5"),
        )]),
    )

    assert v.fortalezas[0].evidencia_localizada is False
    assert any(r.regla == "afirmacion_de_ausencia" and "fortaleza" in r.detalle for r in v.reparos)


def test_un_indicio_con_afirmacion_de_ausencia_recibe_el_reparo_especifico(
    criterios_de_analisis: Path,
) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E3", TRABAJO,
        _analisis(indicios_de_autoria=[IndicioDeAutoria(
            descripcion="Indicio de prueba.",
            evidencia=Evidencia(cita="No se observan variaciones de estilo.", apartado="5"),
        )]),
    )

    assert v.indicios_de_autoria[0].evidencia_localizada is False
    assert any(
        r.regla == "afirmacion_de_ausencia" and "indicio de autoría" in r.detalle
        for r in v.reparos
    )
    # El aviso incondicional del §13 se mantiene, sea cual sea el otro reparo.
    assert any(r.regla == "autoria_es_indicio" for r in v.reparos)


def test_una_cita_inventada_de_verdad_sigue_recibiendo_el_reparo_generico(
    criterios_de_analisis: Path,
) -> None:
    """El cambio no pierde precisión sobre lo que ya funcionaba: una cita que
    no describe una ausencia -simplemente no existe- sigue con
    `evidencia_localizable`, como siempre."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E3", TRABAJO,
        _analisis(valoraciones=[_val("El proyecto factura 3 millones de euros al año")]),
    )

    assert v.valoraciones[0].evidencia_localizada is False
    assert any(r.regla == "evidencia_localizable" for r in v.reparos)
    assert not any(r.regla == "afirmacion_de_ausencia" for r in v.reparos)


def test_no_llega_a_la_devolucion_ni_como_afirmacion_de_ausencia(
    criterios_de_analisis: Path,
) -> None:
    """El reparo cambia lo que lee el docente, no lo que decide si algo llega
    al alumno: `evidencia_localizada` sigue en `False`, el único campo que
    consulta `backend/salidas/borrador.py`."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E3", TRABAJO,
        _analisis(valoraciones=[_val(
            "No se localizan referencias a la incorporación de feedback."
        )]),
    )

    assert v.valoraciones[0].evidencia_localizada is False
