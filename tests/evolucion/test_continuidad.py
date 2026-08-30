"""El bloque «Continuidad»: qué se hizo con el feedback de la fase anterior.

`clasificar_continuidad` solo tiene dos salidas posibles hoy -PENDIENTE y
NO_VERIFICABLE-, y el docstring de `backend/evolucion/continuidad.py`
explica por qué APLICADO y PARCIALMENTE_APLICADO no se emiten nunca. Esta
batería comprueba exactamente esa frontera: cuándo la certeza mecánica
basta para PENDIENTE, y cuándo el sistema se conforma con decir que no lo
sabe en vez de adivinar.
"""

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import ValoracionVerificada
from backend.evolucion.comparacion import CONSERVADO_MINIMO, Evolucion
from backend.evolucion.continuidad import (
    NO_VERIFICABLE,
    PENDIENTE,
    clasificar_continuidad,
)

CITA_D01 = "El presupuesto no incluye ninguna fuente que lo respalde"
CITA_D02 = "La arquitectura de tres capas no se justifica en ningun apartado"


def _prioridad(dimension="D01", cita=CITA_D01, prioridad="P1"):
    return ValoracionVerificada(
        dimension=dimension, nivel="INSUFICIENTE", prioridad=prioridad,
        evidencia=Evidencia(cita=cita, apartado="5"),
        observacion=f"Observación de {dimension}.", evidencia_localizada=True,
    )


def _evolucion(proporcion_conservada=0.9) -> Evolucion:
    return Evolucion(proporcion_conservada=proporcion_conservada)


def test_sin_prioridades_anteriores_no_hay_nada_que_clasificar():
    assert clasificar_continuidad([], "cualquier texto", _evolucion()) == []


def test_sin_comparacion_posible_todo_es_no_verificable():
    resultado = clasificar_continuidad([_prioridad()], "texto nuevo", None)

    assert len(resultado) == 1
    assert resultado[0].estado == NO_VERIFICABLE
    assert "no se ha podido comparar" in resultado[0].motivo.lower()


def test_divergencia_severa_hace_no_verificable_incluso_si_la_cita_aparece():
    """Si la comparación global dice que la entrega no parece incluir el
    trabajo anterior, ni siquiera encontrar la cita literal es de fiar: el
    umbral de `comparacion.py` decide antes que la búsqueda por cita."""
    evolucion = _evolucion(proporcion_conservada=CONSERVADO_MINIMO - 0.01)
    texto_nuevo = f"Un documento distinto que sí contiene: {CITA_D01}."

    resultado = clasificar_continuidad([_prioridad()], texto_nuevo, evolucion)

    assert resultado[0].estado == NO_VERIFICABLE
    assert "se reconoce tan poco" in resultado[0].motivo.lower()


def test_la_cita_que_sigue_igual_es_pendiente():
    texto_nuevo = f"Introducción. {CITA_D01}. Conclusión sin cambios."

    resultado = clasificar_continuidad([_prioridad()], texto_nuevo, _evolucion())

    assert resultado[0].estado == PENDIENTE
    assert "sigue apareciendo" in resultado[0].motivo.lower()


def test_la_cita_que_ya_no_aparece_es_no_verificable_no_aplicado():
    texto_nuevo = "El presupuesto se ha reescrito por completo con cifras nuevas."

    resultado = clasificar_continuidad([_prioridad()], texto_nuevo, _evolucion())

    assert resultado[0].estado == NO_VERIFICABLE
    assert "ya no aparece" in resultado[0].motivo.lower()


def test_cada_prioridad_se_clasifica_por_su_cuenta():
    """Una sigue igual (PENDIENTE) y la otra ha cambiado (NO_VERIFICABLE):
    la clasificación es por prioridad, no un veredicto único para todo el
    bloque."""
    texto_nuevo = f"{CITA_D01}. El resto del apartado de arquitectura es nuevo."

    resultado = clasificar_continuidad(
        [_prioridad("D01", CITA_D01), _prioridad("D02", CITA_D02, "P2")],
        texto_nuevo, _evolucion(),
    )

    por_dimension = {c.dimension: c.estado for c in resultado}
    assert por_dimension == {"D01": PENDIENTE, "D02": NO_VERIFICABLE}


def test_el_resultado_lleva_la_dimension_prioridad_y_observacion_original():
    resultado = clasificar_continuidad(
        [_prioridad("D05", CITA_D01, "P3")], "texto que no la contiene", _evolucion(),
    )

    assert resultado[0].dimension == "D05"
    assert resultado[0].prioridad == "P3"
    assert resultado[0].observacion_anterior == "Observación de D05."
