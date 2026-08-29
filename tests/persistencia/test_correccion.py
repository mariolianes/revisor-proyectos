"""`validar_citas_acotadas`: D-001 aplicado en código, no solo en la base de
datos.

Valoraciones, fortalezas e indicios de autoría llevan cada uno su propia
evidencia, y solo la de las valoraciones tiene una fila con CHECK en la
migración (`evidencia.fragmento_acotado`). Esta batería comprueba que la
guarda de código cubre los tres canales por igual: una regresión que solo
mirara `informe.valoraciones` -y no `fortalezas` ni `indicios`- dejaría
pasar una fortaleza o un indicio con una cita de cualquier longitud dentro
de la columna `jsonb`, que no lleva ningún límite propio.
"""

import pytest

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import (
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    ValoracionVerificada,
)
from backend.persistencia.correccion import LIMITE_DE_CITA, validar_citas_acotadas
from backend.salidas.informe import Informe

_IDENTIFICACION = {
    "alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": "1",
    "archivo": "AF023_DAM_E2_20260115_v1.pdf", "criterios": "v2026-2027",
}


def _informe(**cambios) -> Informe:
    datos = dict(
        identificacion=_IDENTIFICACION, control_administrativo=[],
        resumen="Resumen.", valoraciones=[], fortalezas=[], prioridades=[],
        prioridades_descartadas=[], dudas=[], indicios=[], reparos=[],
        dimensiones_ausentes=[], semaforo="GRIS", recomendacion=None,
        motor="simulado",
    )
    datos.update(cambios)
    return Informe(**datos)


def test_una_cita_dentro_del_limite_no_hace_nada() -> None:
    informe = _informe(valoraciones=[ValoracionVerificada(
        dimension="D05", nivel="ADECUADO", prioridad=None,
        evidencia=Evidencia(cita="x" * LIMITE_DE_CITA, apartado="5"),
        observacion="obs", evidencia_localizada=True,
    )])

    validar_citas_acotadas(informe)  # no levanta


@pytest.mark.parametrize("canal", ["valoraciones", "fortalezas", "indicios"])
def test_una_cita_larga_se_rechaza_en_los_tres_canales(canal: str) -> None:
    """Los tres tipos que llevan `Evidencia`: valoraciones, fortalezas e
    indicios de autoría. `dudas` y `reparos` quedan fuera a propósito -son
    texto libre sin evidencia, no citan el documento-.
    """
    cita_larga = "x" * (LIMITE_DE_CITA + 1)
    evidencia = Evidencia(cita=cita_larga, apartado="5")

    if canal == "valoraciones":
        informe = _informe(valoraciones=[ValoracionVerificada(
            dimension="D05", nivel="ADECUADO", prioridad=None,
            evidencia=evidencia, observacion="obs", evidencia_localizada=True,
        )])
    elif canal == "fortalezas":
        informe = _informe(fortalezas=[FortalezaVerificada(
            descripcion="Fortaleza", evidencia=evidencia,
            evidencia_localizada=True,
        )])
    else:
        informe = _informe(indicios=[IndicioDeAutoriaVerificado(
            descripcion="Indicio", evidencia=evidencia,
            evidencia_localizada=True,
        )])

    with pytest.raises(ValueError, match="1501"):
        validar_citas_acotadas(informe)


def test_el_mensaje_no_culpa_al_alumno() -> None:
    """El límite es del sistema (D-001); si se supera es un fallo del motor,
    no un dato del alumno que recortar. El mensaje lo dice así, no como si
    hubiera que editar el trabajo del alumno.
    """
    informe = _informe(valoraciones=[ValoracionVerificada(
        dimension="D05", nivel="ADECUADO", prioridad=None,
        evidencia=Evidencia(cita="x" * (LIMITE_DE_CITA + 1), apartado="5"),
        observacion="obs", evidencia_localizada=True,
    )])

    with pytest.raises(ValueError) as info:
        validar_citas_acotadas(informe)

    assert "fallo del motor" in str(info.value)
