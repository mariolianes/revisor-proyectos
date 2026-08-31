"""La comparación por taxonomía de incidencias (§13), no por frase literal.

El docente, 2026-08-31: «que el sistema use palabras distintas a las del
banco no es un problema [...] La comparación debería realizarse mediante
una taxonomía estable de incidencias [...] coinciden cuando detectan la
misma categoría con una severidad equivalente y evidencias compatibles».

Este fichero prueba `mapa_de_categorias`, `evaluar()` con
`incidencias_esperadas`, y que el nuevo mecanismo convive con
`debe_encontrar` sin romperlo -esa parte ya la cubre
`tests/tools/test_calibrar.py`, que sigue en verde sin haberse tocado-.
"""

from pathlib import Path

from backend.analisis.contrato import Evidencia
from backend.analisis.proveedor import ProveedorSimulado
from backend.analisis.taxonomia import codigos_validos
from backend.analisis.verificacion import ValoracionVerificada
from backend.salidas.informe import Informe
from tools.calibrar import (
    CasoDeCalibracion,
    IncidenciaEsperada,
    cargar_casos,
    ejecutar,
    evaluar,
    mapa_de_categorias,
)

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]


def _valoracion(
    dimension: str, prioridad: str | None, evidencia_localizada: bool = True
) -> ValoracionVerificada:
    return ValoracionVerificada(
        dimension=dimension,
        nivel="INSUFICIENTE" if prioridad else "SOLIDO",
        prioridad=prioridad,
        evidencia=Evidencia(cita="Cita de prueba, no de un alumno real.", apartado="5"),
        observacion="Observación de prueba.",
        evidencia_localizada=evidencia_localizada,
    )


def _informe(valoraciones: list[ValoracionVerificada]) -> Informe:
    return Informe(
        identificacion={
            "alumno": "AF999", "ciclo": "CALIBRACION", "fase": "E3",
            "version": "1", "archivo": "caso.pdf", "criterios": "v2026-2027",
        },
        control_administrativo=[],
        resumen="Resumen de prueba.",
        sintesis_provisional="Síntesis provisional de prueba.",
        valoraciones=valoraciones,
        fortalezas=[],
        prioridades=[],
        prioridades_descartadas=[],
        dudas=[],
        indicios=[],
        reparos=[],
        dimensiones_ausentes=[],
        semaforo_propuesto="AMBAR",
        semaforo_final_docente=None,
        recomendacion=None,
        nota_propuesta_sistema=None,
        estado_nota="pendiente_de_rubrica",
        version_rubrica=None,
        ponderaciones_nota=None,
        nota_final_docente=None,
        motivo_modificacion_nota=None,
        motor="simulado",
    )


def _caso(**cambios) -> CasoDeCalibracion:
    base = dict(
        codigo="X01", archivo="x01.pdf", fase="E3", semaforo_esperado="AMBAR",
        notas="Caso inventado de prueba.",
    )
    base.update(cambios)
    return CasoDeCalibracion(**base)


# ---------------------------------------------------------------------------
# mapa_de_categorias(): dimensión -> códigos posibles, para la tanda entera
# ---------------------------------------------------------------------------


def test_mapa_de_categorias_agrupa_por_dimension(criterios_de_analisis: Path) -> None:
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")

    assert mapa["D11"] == ["FOR-DEF"]
    assert set(mapa["D07"]) == {"DEV-INSUF", "TEO-EXCESO", "APL-FALTA"}
    assert "D01" not in mapa  # la taxonomía no cubre esta dimensión


def test_mapa_de_categorias_vacio_si_falta_el_fichero(tmp_path: Path) -> None:
    assert mapa_de_categorias(tmp_path, "v2099-2100") == {}


# ---------------------------------------------------------------------------
# evaluar(): coincidencia por categoría, severidad y evidencia
# ---------------------------------------------------------------------------


def test_una_incidencia_esperada_coincide_por_categoria_severidad_y_evidencia(
    criterios_de_analisis: Path,
) -> None:
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso(incidencias_esperadas=[
        IncidenciaEsperada(codigo="FOR-DEF", severidad="P2"),
    ])
    informe = _informe([_valoracion("D11", "P2", evidencia_localizada=True)])

    resultado = evaluar(caso, informe, mapa)

    assert resultado.incidencias_halladas == ["FOR-DEF"]
    assert resultado.incidencias_ausentes == []


def test_sin_evidencia_localizada_no_cuenta_como_coincidencia(
    criterios_de_analisis: Path,
) -> None:
    """"Evidencias compatibles" del criterio del docente: una categoría y
    severidad que coinciden pero cuya cita no se localizó no demuestran
    nada -es la misma cautela que ya aplica en el resto del sistema."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso(incidencias_esperadas=[
        IncidenciaEsperada(codigo="FOR-DEF", severidad="P2"),
    ])
    informe = _informe([_valoracion("D11", "P2", evidencia_localizada=False)])

    resultado = evaluar(caso, informe, mapa)

    assert resultado.incidencias_halladas == []
    assert resultado.incidencias_ausentes == ["FOR-DEF"]


def test_severidad_distinta_no_coincide(criterios_de_analisis: Path) -> None:
    """"Severidad equivalente" se interpreta aquí como igual (P1-P4): un P1
    esperado no coincide con un P3 obtenido, aunque la categoría sí."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso(incidencias_esperadas=[
        IncidenciaEsperada(codigo="FOR-DEF", severidad="P1"),
    ])
    informe = _informe([_valoracion("D11", "P3", evidencia_localizada=True)])

    resultado = evaluar(caso, informe, mapa)

    assert resultado.incidencias_ausentes == ["FOR-DEF"]


def test_una_dimension_ambigua_coincide_con_cualquiera_de_sus_categorias(
    criterios_de_analisis: Path,
) -> None:
    """D07 puede ser DEV-INSUF, TEO-EXCESO o APL-FALTA: el caso de manual del
    encargo. Esperar cualquiera de las tres coincide con la misma
    valoración -el sistema no elige por el docente cuál de las tres es-."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    informe = _informe([_valoracion("D07", "P2", evidencia_localizada=True)])

    for codigo in ("DEV-INSUF", "TEO-EXCESO", "APL-FALTA"):
        caso = _caso(incidencias_esperadas=[IncidenciaEsperada(codigo=codigo, severidad="P2")])
        resultado = evaluar(caso, informe, mapa)
        assert resultado.incidencias_halladas == [codigo], codigo


def test_una_categoria_de_otra_dimension_no_coincide(criterios_de_analisis: Path) -> None:
    """FUE-INSUF sale de D05, no de D11: una valoración sobre D11 no puede
    confirmarla, por buena que sea su evidencia."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso(incidencias_esperadas=[
        IncidenciaEsperada(codigo="FUE-INSUF", severidad="P2"),
    ])
    informe = _informe([_valoracion("D11", "P2", evidencia_localizada=True)])

    resultado = evaluar(caso, informe, mapa)

    assert resultado.incidencias_ausentes == ["FUE-INSUF"]


def test_sin_mapa_ninguna_incidencia_puede_coincidir(criterios_de_analisis: Path) -> None:
    """El valor por omisión de `mapa` es `None`: sin él, ningún código
    coincide nunca -no es un fallo silencioso, es lo único seguro que se
    puede hacer sin la taxonomía cargada-."""
    caso = _caso(incidencias_esperadas=[
        IncidenciaEsperada(codigo="FOR-DEF", severidad="P2"),
    ])
    informe = _informe([_valoracion("D11", "P2", evidencia_localizada=True)])

    resultado = evaluar(caso, informe)

    assert resultado.incidencias_ausentes == ["FOR-DEF"]


def test_una_valoracion_sin_prioridad_no_cuenta_como_incidencia(
    criterios_de_analisis: Path,
) -> None:
    """SOLIDO/ADECUADO sin prioridad es un juicio positivo, no una
    incidencia: no debe poder "confirmar" una incidencia esperada solo
    porque comparte dimensión."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso(incidencias_esperadas=[
        IncidenciaEsperada(codigo="FOR-DEF", severidad="P2"),
    ])
    informe = _informe([_valoracion("D11", None, evidencia_localizada=True)])

    resultado = evaluar(caso, informe, mapa)

    assert resultado.incidencias_ausentes == ["FOR-DEF"]


def test_un_caso_sin_incidencias_esperadas_no_se_ve_afectado(
    criterios_de_analisis: Path,
) -> None:
    """Compatibilidad con casos que aún no tienen `incidencias_esperadas`
    (el valor por omisión es una lista vacía): no hay nada que comparar, y
    eso no es un fallo."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso()
    informe = _informe([_valoracion("D11", "P2", evidencia_localizada=True)])

    resultado = evaluar(caso, informe, mapa)

    assert resultado.incidencias_halladas == []
    assert resultado.incidencias_ausentes == []


def test_debe_encontrar_sigue_funcionando_junto_a_incidencias_esperadas(
    criterios_de_analisis: Path,
) -> None:
    """Los dos mecanismos conviven en el mismo caso sin interferirse."""
    mapa = mapa_de_categorias(criterios_de_analisis, "v2026-2027")
    caso = _caso(
        debe_encontrar=["formato deficiente"],
        incidencias_esperadas=[IncidenciaEsperada(codigo="FOR-DEF", severidad="P2")],
    )
    informe = _informe([_valoracion("D11", "P2", evidencia_localizada=True)])
    informe.resumen = "El formato deficiente compromete la presentación."

    resultado = evaluar(caso, informe, mapa)

    assert resultado.debe_encontrar_hallado == ["formato deficiente"]
    assert resultado.incidencias_halladas == ["FOR-DEF"]


# ---------------------------------------------------------------------------
# ejecutar(): el mapa se calcula una vez y llega hasta evaluar() de verdad
# ---------------------------------------------------------------------------


def test_ejecutar_conecta_el_mapa_de_verdad_con_evaluar(
    criterios_de_analisis: Path, tmp_path: Path, escribir_pdf,
) -> None:
    """No basta con que `evaluar()` funcione aislada: `ejecutar()` tiene que
    calcular `mapa_de_categorias` y pasarlo por `_ejecutar_caso` hasta
    `evaluar()`. Este test pasa por el camino completo -PDF, proveedor
    simulado, `analizar_entrega`- para comprobar que el cableado, no solo la
    lógica de comparación, funciona."""
    from backend.analisis.contrato import AnalisisDelMotor, Valoracion
    from backend.salidas.borrador import Devolucion

    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto = "Contenido inventado con un problema de formato reconocible."
    escribir_pdf(carpeta / "x01.pdf", [[texto]], salto=19.0)

    caso = CasoDeCalibracion(
        codigo="X01", archivo="x01.pdf", fase="E3", semaforo_esperado="AMBAR",
        incidencias_esperadas=[IncidenciaEsperada(codigo="FOR-DEF", severidad="P2")],
    )
    analisis = AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D11", nivel="INSUFICIENTE", prioridad="P2",
            evidencia=Evidencia(cita=texto[:30], apartado="1"),
            observacion="Formato deficiente en el cuerpo del documento.",
        )],
        fortalezas=[], patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )
    devolucion = Devolucion(
        apertura="Avance correcto.", fortalezas=["Fortaleza de prueba."],
        acciones=["Corrige el formato."], cierre="Adelante.",
    )
    proveedor = ProveedorSimulado(respuestas=[analisis, devolucion])

    informe = ejecutar(criterios_de_analisis, [caso], carpeta, proveedor)

    resultado = informe.resultados[0]
    assert resultado.saltado is False
    assert resultado.incidencias_halladas == ["FOR-DEF"]
    assert "FOR-DEF" not in resultado.incidencias_ausentes
    assert "1/1 incidencias" in informe.indicadores["cobertura"].lectura


# ---------------------------------------------------------------------------
# El banco real (docs/calibracion/casos.example.yaml)
# ---------------------------------------------------------------------------


def test_el_banco_de_ejemplo_solo_usa_codigos_validos_de_la_taxonomia() -> None:
    """Cada código que declara `incidencias_esperadas` en el banco de
    ejemplo tiene que existir de verdad en
    `criteria/v2026-2027/taxonomia-incidencias.yaml`: un código mal escrito
    no debe fallar en silencio -nunca "coincide", nunca avisa- sino
    delatarse aquí."""
    fichero = RAIZ_DEL_REPOSITORIO / "docs" / "calibracion" / "casos.example.yaml"
    validos = codigos_validos(RAIZ_DEL_REPOSITORIO, "v2026-2027")

    casos = cargar_casos(fichero)

    al_menos_un_caso_con_incidencias = False
    for caso in casos:
        for incidencia in caso.incidencias_esperadas:
            al_menos_un_caso_con_incidencias = True
            assert incidencia.codigo in validos, (
                f"{caso.codigo}: «{incidencia.codigo}» no es un código de la "
                "taxonomía del §13."
            )
            assert incidencia.severidad in {"P1", "P2", "P3", "P4"}

    assert al_menos_un_caso_con_incidencias
