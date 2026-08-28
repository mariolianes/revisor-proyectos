"""El formulario que el motor debe rellenar."""

import pytest
from pydantic import ValidationError

from backend.analisis.contrato import (
    NIVELES,
    PRIORIDADES,
    AnalisisDelMotor,
    Evidencia,
    Valoracion,
    esquema_estricto,
)


def _valoracion(**cambios) -> dict:
    datos = dict(
        dimension="D05",
        nivel="ADECUADO",
        prioridad="P2",
        evidencia={"cita": "El presupuesto asciende a 4.500 euros.",
                   "apartado": "5. Presupuesto"},
        observacion="Las cifras se presentan sin justificar su origen.",
    )
    datos.update(cambios)
    return datos


def test_una_valoracion_completa_se_acepta() -> None:
    v = Valoracion(**_valoracion())

    assert v.dimension == "D05"
    assert v.evidencia.cita.startswith("El presupuesto")


def test_un_nivel_inventado_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Valoracion(**_valoracion(nivel="REGULAR"))


def test_una_prioridad_inventada_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Valoracion(**_valoracion(prioridad="P9"))


def test_la_prioridad_puede_ser_nula() -> None:
    """Un hallazgo puede no tener prioridad, pero el motor ha de decirlo."""
    assert Valoracion(**_valoracion(prioridad=None)).prioridad is None


def test_una_dimension_fuera_del_catalogo_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Valoracion(**_valoracion(dimension="D99"))


def test_una_valoracion_sin_evidencia_se_rechaza() -> None:
    """Ningún juicio sin evidencia. Es la regla, no una preferencia."""
    datos = _valoracion()
    del datos["evidencia"]

    with pytest.raises(ValidationError):
        Valoracion(**datos)


def test_los_niveles_son_los_del_maestro() -> None:
    assert NIVELES == (
        "SOLIDO", "ADECUADO", "EN_DESARROLLO",
        "INSUFICIENTE", "NO_APLICABLE", "NO_VERIFICABLE",
    )


def test_las_prioridades_son_las_del_calibrador() -> None:
    assert PRIORIDADES == ("P1", "P2", "P3", "P4")


def test_un_analisis_completo_se_acepta() -> None:
    a = AnalisisDelMotor(
        valoraciones=[Valoracion(**_valoracion())],
        fortalezas=["La estructura del documento es clara."],
        patrones=[],
        dudas_para_el_docente=[],
        indicios_de_autoria=[],
    )

    assert len(a.valoraciones) == 1


def test_el_analisis_no_admite_campos_de_mas() -> None:
    """Si el motor devuelve una nota, la validación la rechaza aquí mismo."""
    with pytest.raises(ValidationError):
        AnalisisDelMotor(
            valoraciones=[], fortalezas=[], patrones=[],
            dudas_para_el_docente=[], indicios_de_autoria=[],
            nota_propuesta=7.5,
        )


def test_el_esquema_estricto_lo_acepta_el_proveedor() -> None:
    """Comprueba lo que exige el modo estricto: nada opcional, nada de más."""
    esquema = esquema_estricto()

    assert esquema["additionalProperties"] is False
    assert set(esquema["required"]) == {
        "valoraciones", "fortalezas", "patrones",
        "dudas_para_el_docente", "indicios_de_autoria",
    }


def test_el_esquema_obliga_a_decidir_la_prioridad() -> None:
    """En modo estricto un opcional es «obligatorio que admite nulo».

    El motor no puede callarse el campo: tiene que decir P1..P4 o null.
    """
    esquema = esquema_estricto()
    valoracion = esquema["$defs"]["Valoracion"]

    assert "prioridad" in valoracion["required"]
    tipos = valoracion["properties"]["prioridad"]["anyOf"]
    assert {"type": "null"} in tipos
