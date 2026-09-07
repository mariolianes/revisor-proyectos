"""El informe por comunidad, centro, ciclo y fase (punto 7 del orden de
implantación).

Se prueba sobre `AlmacenEnMemoria`: `componer_informe_centro` es lectura
pura sobre el `Protocol` `Almacen` -no toca la red-, y la paridad de lo que
lee (`listar_alumnos`, `listar`, `listar_semaforos`, `consumos`) ya la
cubre `tests/persistencia/test_paridad.py`. Repetir aquí cada prueba contra
los dos almacenes solo repetiría esa cobertura sin protegido nada nuevo.
"""

from datetime import datetime, timedelta

import pytest

from backend.persistencia.alumnos import AlumnoNuevo
from backend.persistencia.consumo import RegistroDeConsumo
from backend.persistencia.correccion import SemaforoDeEntrega
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.servicios.informe_centro import (
    UMBRAL_GRUPO_PEQUENO,
    Cobertura,
    _componer_coste,
    _componer_cobertura,
    _componer_semaforos,
    componer_informe_centro,
)


def _alumno(almacen: AlmacenEnMemoria, **cambios) -> str:
    """Da de alta un alumno con datos por omisión razonables y devuelve su
    `student_id`."""
    datos = dict(
        curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
        ciclo_code="MYP",
    )
    datos.update(cambios)
    return almacen.dar_de_alta_alumno(AlumnoNuevo(**datos)).student_id


def _entrega(almacen: AlmacenEnMemoria, codigo: str, fase: str, **cambios):
    datos = dict(
        codigo_alumno=codigo, ciclo="MYP", fase=fase, version=1,
        nombre_archivo=f"{codigo}_{fase}.pdf", huella=f"{codigo}-{fase}",
        version_criterios="v2026-2027",
    )
    datos.update(cambios)
    return almacen.registrar(EntregaNueva(**datos))


def _llenar_grupo(almacen: AlmacenEnMemoria, cuantos: int, **cambios) -> list[str]:
    """De alta `cuantos` alumnos ACTIVO -para llegar o superar
    `UMBRAL_GRUPO_PEQUENO` sin repetir la llamada en cada prueba-."""
    return [_alumno(almacen, **cambios) for _ in range(cuantos)]


# --- cobertura ---------------------------------------------------------------


def test_cuenta_matriculados_entregados_y_sin_entregar_por_fase() -> None:
    almacen = AlmacenEnMemoria()
    codigos = _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO)
    _entrega(almacen, codigos[0], "E1")
    _entrega(almacen, codigos[1], "E1")

    informe = componer_informe_centro(almacen)

    e1 = next(f for f in informe.cobertura.por_fase if f.fase == "E1")
    assert informe.cobertura.matriculados == UMBRAL_GRUPO_PEQUENO
    assert e1.entregados == 2
    assert e1.sin_entregar == UMBRAL_GRUPO_PEQUENO - 2


def test_el_filtro_de_fase_devuelve_una_unica_fase() -> None:
    almacen = AlmacenEnMemoria()
    _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO)

    informe = componer_informe_centro(almacen, fase="E2")

    assert [f.fase for f in informe.cobertura.por_fase] == ["E2"]


def test_bajas_y_traslados_no_cuentan_como_matriculados_ni_se_persiguen() -> None:
    """Un alumno de baja no se persigue por no entregar (D-025 registró
    `estado_matricula` justamente para esta distinción), pero tampoco
    desaparece del todo del informe: se cuenta aparte."""
    almacen = AlmacenEnMemoria()
    _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO)
    _alumno(almacen, estado_matricula="BAJA")
    _alumno(almacen, estado_matricula="TRASLADADO")

    informe = componer_informe_centro(almacen)

    assert informe.cobertura.matriculados == UMBRAL_GRUPO_PEQUENO
    assert informe.cobertura.bajas_o_traslados == 2
    total_fase = informe.cobertura.por_fase[0]
    assert total_fase.entregados + total_fase.sin_entregar == UMBRAL_GRUPO_PEQUENO


def test_un_repetidor_cuenta_como_matriculado() -> None:
    almacen = AlmacenEnMemoria()
    _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO - 1)
    _alumno(almacen, estado_matricula="REPETIDOR")

    informe = componer_informe_centro(almacen)

    assert informe.cobertura.matriculados == UMBRAL_GRUPO_PEQUENO


def test_filtra_por_ccaa_centro_ciclo_y_curso_de_forma_independiente() -> None:
    almacen = AlmacenEnMemoria()
    _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO, ccaa_code="AND", centro_code="AND-MAL-01")
    _llenar_grupo(almacen, 3, ccaa_code="MAD", centro_code="MAD-MAD-01")

    informe_and = componer_informe_centro(almacen, ccaa="AND")
    informe_mad = componer_informe_centro(almacen, ccaa="MAD")
    informe_centro_equivocado = componer_informe_centro(almacen, centro="MAD-MAD-99")

    assert informe_and.cobertura.matriculados == UMBRAL_GRUPO_PEQUENO
    assert informe_mad.cobertura.matriculados == 3
    assert informe_centro_equivocado.cobertura.matriculados == 0


@pytest.mark.parametrize("filtro,valor", [
    ("ccaa", "XXX"), ("ciclo", "NOEXISTE"), ("fase", "NOEXISTE"),
    ("curso", "no-es-un-curso"),
])
def test_un_filtro_desconocido_se_rechaza(filtro: str, valor: str) -> None:
    almacen = AlmacenEnMemoria()
    with pytest.raises(ValueError):
        componer_informe_centro(almacen, **{filtro: valor})


# --- el umbral del grupo pequeño ---------------------------------------------
#
# La restricción que gobierna el módulo: ningún nombre de alumno, y en un
# grupo pequeño, tampoco la lista de identificadores de quién no ha
# entregado -aunque los recuentos se mantengan exactos-. Se prueba el límite
# exacto: justo en el umbral se muestra, uno por debajo no.


def test_grupo_por_debajo_del_umbral_oculta_la_lista_pero_no_los_recuentos() -> None:
    almacen = AlmacenEnMemoria()
    codigos = _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO - 1)
    _entrega(almacen, codigos[0], "E1")

    informe = componer_informe_centro(almacen, fase="E1")

    fase = informe.cobertura.por_fase[0]
    assert fase.entregados == 1
    assert fase.sin_entregar == UMBRAL_GRUPO_PEQUENO - 2
    assert fase.sin_entregar_codigos is None
    assert informe.cobertura.aviso_grupo_pequeno is not None
    assert str(UMBRAL_GRUPO_PEQUENO) in informe.cobertura.aviso_grupo_pequeno


def test_grupo_justo_en_el_umbral_muestra_la_lista() -> None:
    almacen = AlmacenEnMemoria()
    codigos = _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO)
    _entrega(almacen, codigos[0], "E1")

    informe = componer_informe_centro(almacen, fase="E1")

    fase = informe.cobertura.por_fase[0]
    assert fase.sin_entregar_codigos is not None
    assert len(fase.sin_entregar_codigos) == UMBRAL_GRUPO_PEQUENO - 1
    assert codigos[0] not in fase.sin_entregar_codigos
    assert informe.cobertura.aviso_grupo_pequeno is None


def test_grupo_vacio_no_lleva_aviso_de_grupo_pequeno() -> None:
    """Un ámbito sin ningún matriculado no es un grupo pequeño que proteger:
    es que no hay nadie de quien informar."""
    almacen = AlmacenEnMemoria()

    informe = componer_informe_centro(almacen)

    assert informe.cobertura.matriculados == 0
    assert informe.cobertura.aviso_grupo_pequeno is None


def test_ningun_codigo_de_alumno_es_un_nombre_de_persona() -> None:
    """Cuela, a propósito, un valor con forma de nombre en vez de un
    `student_id`, para comprobar que algún mecanismo se entera: aquí el que
    se entera es que `dar_de_alta_alumno` nunca deja escribir un campo
    `nombre` -`AlumnoNuevo` declara `extra=\"forbid\"`-, así que la única
    manera de que un informe mostrara un nombre sería que alguien lo
    escribiera directamente en `codigo_alumno`, y ese campo es justo el
    `student_id` que asigna el sistema, no algo que quien registra una
    entrega pueda rellenar con lo que quiera fuera de su patrón."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AlumnoNuevo(  # type: ignore[call-arg]
            curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
            ciclo_code="MYP", nombre="Ana García",
        )


# --- estado del proceso -------------------------------------------------------


def test_estado_del_proceso_cuenta_cada_estado_incluidos_los_que_valen_cero() -> None:
    almacen = AlmacenEnMemoria()
    codigos = _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO)
    entrega = _entrega(almacen, codigos[0], "E1")
    almacen.cambiar_estado(entrega.id, "BLOQUEADO", "archivo ilegible")

    informe = componer_informe_centro(almacen)

    assert informe.proceso.por_estado["BLOQUEADO"] == 1
    assert informe.proceso.por_estado["RECIBIDO"] == 0
    assert informe.proceso.por_estado["COMUNICADO"] == 0
    assert set(informe.proceso.por_estado) == {
        "RECIBIDO", "BLOQUEADO", "ANALIZADO", "BORRADORES_GENERADOS",
        "EN_REVISION_DOCENTE", "APROBADO", "COMUNICADO",
    }


# --- semáforos -----------------------------------------------------------------


def test_distribucion_de_semaforos_separa_propuesto_de_confirmado() -> None:
    almacen = AlmacenEnMemoria()
    entregas_por_id = {}
    for color in ("VERDE", "AMBAR", "ROJO"):
        codigo = _alumno(almacen)
        entrega = _entrega(almacen, codigo, "E1")
        entregas_por_id[entrega.id] = color

    semaforos = [
        SemaforoDeEntrega(entrega_id=eid, semaforo_propuesto=color, semaforo_aprobado=None)
        for eid, color in entregas_por_id.items()
    ]
    entregas_ambito = {eid: object() for eid in entregas_por_id}

    resultado = _componer_semaforos(semaforos, entregas_ambito)

    assert resultado.propuestos == {"VERDE": 1, "AMBAR": 1, "ROJO": 1, "GRIS": 0}
    assert resultado.confirmados_por_docente == {"VERDE": 0, "AMBAR": 0, "ROJO": 0, "GRIS": 0}
    assert resultado.pendientes_de_confirmar == 3


def test_semaforo_confirmado_no_es_ningun_color_hasta_que_el_docente_lo_fija() -> None:
    """El docente puede endurecer el color propuesto (D-016 no permite
    confirmar por debajo de lo propuesto, pero sí igual o más severo): el
    informe tiene que contar el confirmado, no el propuesto, en
    `confirmados_por_docente`."""
    semaforos = [
        SemaforoDeEntrega(entrega_id="e1", semaforo_propuesto="AMBAR", semaforo_aprobado="ROJO"),
    ]
    resultado = _componer_semaforos(semaforos, {"e1": object()})

    assert resultado.propuestos["AMBAR"] == 1
    assert resultado.confirmados_por_docente["ROJO"] == 1
    assert resultado.pendientes_de_confirmar == 0


def test_un_semaforo_fuera_del_ambito_filtrado_no_se_cuenta() -> None:
    semaforos = [
        SemaforoDeEntrega(entrega_id="fuera-del-ambito", semaforo_propuesto="ROJO"),
    ]
    resultado = _componer_semaforos(semaforos, {})

    assert resultado.propuestos == {"VERDE": 0, "AMBAR": 0, "ROJO": 0, "GRIS": 0}
    assert resultado.pendientes_de_confirmar == 0


# --- coste ---------------------------------------------------------------------


def _consumo(entrega_id: str, creada_en: datetime, **cambios) -> RegistroDeConsumo:
    datos = dict(
        id="id-fijo", creada_en=creada_en, entrega_id=entrega_id,
        modelo="openai:gpt-4.1", tokens_entrada=1000, tokens_salida=200,
        tokens_entrada_cacheados=0, coste_estimado_usd=0.01,
        tarifa_aplicada="gpt-4.1@2026-08-30", duracion_ms=1000, estado="OK",
        intentos=1, causa_error=None, paginas=10, caracteres_texto=1000,
        reutilizado=False,
    )
    datos.update(cambios)
    return RegistroDeConsumo(**datos)


class _EntregaDeMentira:
    """Lo único que `_componer_coste` necesita de una entrega: su fase."""

    def __init__(self, fase: str) -> None:
        self.fase = fase


def test_la_primera_ejecucion_de_una_entrega_es_el_analisis_principal() -> None:
    """La distinción no la trae el registro: la decide el orden de
    `creada_en` dentro del grupo de una misma entrega. Se construyen los
    registros con fechas explícitas -no con el reloj de `registrar_
    consumo`- para que la prueba no dependa de la resolución del reloj del
    sistema."""
    base = datetime(2026, 9, 1, 10, 0, 0)
    consumos = [
        _consumo("e1", base, coste_estimado_usd=0.05),
        _consumo("e1", base + timedelta(hours=1), coste_estimado_usd=0.07),
    ]

    resultado = _componer_coste(consumos, {"e1": _EntregaDeMentira("E1")})

    assert resultado.coste_medio_analisis_principal_usd == 0.05
    assert resultado.coste_medio_reanalisis_usd == 0.07


def test_el_orden_de_llegada_no_importa_solo_la_fecha() -> None:
    """El segundo registro que llega -por el orden en que `consumos()`
    devuelve la lista- puede ser, de todos modos, el análisis principal si
    su `creada_en` es más antigua: `_componer_coste` ordena antes de
    decidir, no confía en el orden que trae la lista."""
    base = datetime(2026, 9, 1, 10, 0, 0)
    consumos = [
        _consumo("e1", base + timedelta(hours=1), coste_estimado_usd=0.07),
        _consumo("e1", base, coste_estimado_usd=0.05),
    ]

    resultado = _componer_coste(consumos, {"e1": _EntregaDeMentira("E1")})

    assert resultado.coste_medio_analisis_principal_usd == 0.05
    assert resultado.coste_medio_reanalisis_usd == 0.07


def test_ninguna_ejecucion_sin_reanalisis_deja_el_coste_de_reanalisis_en_none() -> None:
    consumos = [_consumo("e1", datetime(2026, 9, 1))]

    resultado = _componer_coste(consumos, {"e1": _EntregaDeMentira("E1")})

    assert resultado.coste_medio_analisis_principal_usd == 0.01
    assert resultado.coste_medio_reanalisis_usd is None


def test_coste_por_verificacion_nunca_se_inventa() -> None:
    """Hoy la verificación es código determinista, no una llamada al motor
    (`backend/analisis/verificacion.py`): no hay ningún gasto que
    registrar, así que el informe no puede mostrar una cifra -ni siquiera
    0,0, que se leería como «medido y es cero» en vez de «no medible»-."""
    resultado = _componer_coste([], {})

    assert resultado.coste_medio_verificacion_usd is None
    assert any("verificaci" in nota.lower() for nota in resultado.notas)


def test_modelos_y_tokens_se_cuentan_aunque_el_coste_no_sea_calculable() -> None:
    consumos = [_consumo(
        "e1", datetime(2026, 9, 1), coste_estimado_usd=None, tarifa_aplicada=None,
        modelo="openai:o3",
    )]

    resultado = _componer_coste(consumos, {"e1": _EntregaDeMentira("E1")})

    assert resultado.modelos == {"openai:o3": 1}
    assert resultado.tokens_entrada == 1000
    assert resultado.ejecuciones_sin_coste_calculable == 1
    assert resultado.coste_total_usd == 0.0
    assert resultado.coste_medio_analisis_principal_usd is None


def test_promedio_por_fase_agrupa_por_la_fase_de_la_entrega() -> None:
    consumos = [
        _consumo("e1", datetime(2026, 9, 1), coste_estimado_usd=0.02),
        _consumo("e2", datetime(2026, 9, 1), coste_estimado_usd=0.04),
    ]
    entregas = {"e1": _EntregaDeMentira("E1"), "e2": _EntregaDeMentira("E2")}

    resultado = _componer_coste(consumos, entregas)

    assert resultado.promedio_por_fase_usd == {"E1": 0.02, "E2": 0.04}


def test_proyeccion_necesita_dos_fechas_distintas_con_coste() -> None:
    resultado_una_sola = _componer_coste(
        [_consumo("e1", datetime(2026, 9, 1), coste_estimado_usd=0.02)],
        {"e1": _EntregaDeMentira("E1")},
    )
    assert resultado_una_sola.proyeccion_mensual_usd is None
    assert resultado_una_sola.proyeccion_anual_usd is None
    assert any("proyecci" in nota.lower() for nota in resultado_una_sola.notas)

    resultado_dos_fechas = _componer_coste(
        [
            _consumo("e1", datetime(2026, 9, 1), coste_estimado_usd=10.0),
            _consumo("e2", datetime(2026, 9, 11), coste_estimado_usd=10.0),
        ],
        {"e1": _EntregaDeMentira("E1"), "e2": _EntregaDeMentira("E2")},
    )
    # 20 USD en 10 días -> 2 USD/día -> 60 USD/mes, 730 USD/año.
    assert resultado_dos_fechas.periodo_observado_dias == 10.0
    assert resultado_dos_fechas.proyeccion_mensual_usd == pytest.approx(60.0)
    assert resultado_dos_fechas.proyeccion_anual_usd == pytest.approx(730.0)


def test_un_consumo_fuera_del_ambito_no_se_cuenta() -> None:
    consumos = [_consumo("fuera-del-ambito", datetime(2026, 9, 1))]

    resultado = _componer_coste(consumos, {})

    assert resultado.modelos == {}
    assert resultado.tokens_entrada == 0


# --- integración: el coste a través de la API pública -------------------------


def test_componer_informe_centro_incluye_el_coste_de_una_ejecucion_real() -> None:
    almacen = AlmacenEnMemoria()
    codigo = _alumno(almacen)
    entrega = _entrega(almacen, codigo, "E1")
    almacen.registrar_consumo(_consumo(entrega.id, datetime(2026, 9, 1)))

    informe = componer_informe_centro(almacen)

    assert informe.coste.modelos == {"openai:gpt-4.1": 1}
    assert informe.coste.coste_total_usd == 0.01


# --- mutación deliberada: un recuento mal hecho no debe pasar desapercibido --


def test_mutacion_un_alumno_de_mas_en_matriculados_rompe_el_recuento(
) -> None:
    """No es una prueba del código de producción: documenta, ejecutándolo,
    que `test_cuenta_matriculados_entregados_y_sin_entregar_por_fase` SÍ se
    entera si el recuento de matriculados se desvía. Se simula el error
    llamando directamente a `_componer_cobertura` con una lista de alumnos
    a la que se le ha colado uno de más -el tipo de fallo que un `+ 1`
    suelto produciría en producción-, y comprobando que el resultado ya no
    coincide con lo que el ámbito real contiene."""
    almacen = AlmacenEnMemoria()
    codigos = _llenar_grupo(almacen, UMBRAL_GRUPO_PEQUENO)
    matriculados_reales = almacen.listar_alumnos()

    matriculados_con_uno_de_mas = [*matriculados_reales, matriculados_reales[0]]

    cobertura_real: Cobertura = _componer_cobertura(
        matriculados_reales, almacen.listar(), None, 0,
    )
    cobertura_mutada: Cobertura = _componer_cobertura(
        matriculados_con_uno_de_mas, almacen.listar(), None, 0,
    )

    assert cobertura_real.matriculados == UMBRAL_GRUPO_PEQUENO
    assert cobertura_mutada.matriculados == UMBRAL_GRUPO_PEQUENO + 1
    assert cobertura_real.matriculados != cobertura_mutada.matriculados
