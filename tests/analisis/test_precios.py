"""La tarifa de OpenAI: fechada, configurable, nunca inventada."""

from datetime import date
from pathlib import Path

from backend.analisis.precios import (
    Tarifa,
    calcular_coste,
    cargar_tarifas,
    estimar_coste,
    tarifa_vigente,
)


def _tarifa(**kwargs) -> Tarifa:
    base = dict(
        modelo="gpt-4.1", vigente_desde=date(2026, 8, 30),
        entrada_por_millon=2.00, entrada_cacheada_por_millon=0.50,
        salida_por_millon=8.00,
    )
    base.update(kwargs)
    return Tarifa(**base)


def test_el_dato_medido_por_el_docente_cuadra() -> None:
    """5.456 palabras dieron 10.290 tokens de entrada y 2.054 de salida con
    gpt-4.1: es el dato que el docente pidió comprobar."""
    tarifa = _tarifa()

    coste = calcular_coste(tarifa, tokens_entrada=10290, tokens_salida=2054)

    # 10290/1e6*2.00 + 2054/1e6*8.00 = 0.02058 + 0.016432 = 0.037012
    assert coste == 0.037012


def test_los_tokens_cacheados_se_facturan_a_su_propio_precio() -> None:
    tarifa = _tarifa()

    coste = calcular_coste(
        tarifa, tokens_entrada=1000, tokens_salida=0, tokens_entrada_cacheados=1000
    )

    # Los 1000 son todos cacheados: 1000/1e6*0.50, no 1000/1e6*2.00.
    assert coste == 0.0005


def test_sin_precio_cacheado_los_cacheados_van_al_precio_normal() -> None:
    tarifa = _tarifa(entrada_cacheada_por_millon=None)

    coste = calcular_coste(
        tarifa, tokens_entrada=1000, tokens_salida=0, tokens_entrada_cacheados=1000
    )

    assert coste == 0.002


def test_tarifa_vigente_elige_la_mas_reciente_que_no_es_posterior_a_la_fecha() -> None:
    antigua = _tarifa(vigente_desde=date(2026, 1, 1), entrada_por_millon=1.0)
    nueva = _tarifa(vigente_desde=date(2026, 6, 1), entrada_por_millon=3.0)

    elegida = tarifa_vigente([antigua, nueva], "gpt-4.1", date(2026, 8, 30))

    assert elegida is nueva


def test_tarifa_vigente_no_usa_una_fila_del_futuro() -> None:
    """El coste de un análisis hecho hoy no debe calcularse con una tarifa
    que todavía no regía -sería una fecha inventada en el pasado-."""
    futura = _tarifa(vigente_desde=date(2030, 1, 1))

    elegida = tarifa_vigente([futura], "gpt-4.1", date(2026, 8, 30))

    assert elegida is None


def test_un_modelo_sin_tarifa_no_inventa_un_precio() -> None:
    elegida = tarifa_vigente([_tarifa(modelo="gpt-4.1")], "modelo-desconocido", date(2026, 8, 30))

    assert elegida is None


def test_estimar_coste_sin_tabla_no_calcula_nada(tmp_path: Path) -> None:
    coste, tarifa_aplicada = estimar_coste(
        tmp_path, "gpt-4.1", tokens_entrada=100, tokens_salida=50,
    )

    assert coste is None
    assert tarifa_aplicada is None


def test_cargar_tarifas_lee_la_tabla_real_del_repositorio() -> None:
    """El fichero que de verdad usa el sistema en producción, no una copia
    de pruebas: si alguien lo borra o lo corrompe, este test cae."""
    raiz = Path(__file__).resolve().parents[2]

    tarifas = cargar_tarifas(raiz)

    assert any(t.modelo == "gpt-4.1" for t in tarifas)


def test_estimar_coste_con_la_tabla_real_y_el_dato_medido() -> None:
    raiz = Path(__file__).resolve().parents[2]

    coste, tarifa_aplicada = estimar_coste(
        raiz, "gpt-4.1", tokens_entrada=10290, tokens_salida=2054,
        fecha=date(2026, 8, 30),
    )

    assert coste is not None
    assert coste > 0
    assert tarifa_aplicada == "gpt-4.1@2026-08-30"
