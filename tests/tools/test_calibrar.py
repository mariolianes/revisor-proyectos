"""El arnés de calibración: se prueba a él mismo, no al motor.

Ningún PDF real de alumno entra aquí. Los «casos» de estas pruebas son
inventados -códigos, archivos y frases que no existen en ningún proyecto
real-, y los PDF que necesitan se construyen con `escribir_pdf` (ver
`tests/conftest.py`), igual que el resto de la suite. El banco de verdad,
`docs/calibracion/casos.example.yaml`, solo se usa aquí para comprobar que
se puede leer: nunca se ejecuta contra él, porque no hay ningún PDF
`P0N.pdf` en ningún sitio de este repositorio ni de esta máquina de pruebas.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.analisis.contrato import Evidencia
from backend.analisis.proveedor import ErrorDelProveedor, ProveedorSimulado
from backend.analisis.verificacion import (
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    ValoracionVerificada,
)
from backend.persistencia.modelos import EntregaNueva
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe
from tools.calibrar import (
    CasoDeCalibracion,
    ResultadoDeCaso,
    _componer_informe,
    _dentro_del_repositorio,
    _problema_de_ruta_de_salida,
    _registrar_progreso,
    cargar_casos,
    ejecutar,
    evaluar,
    main,
    proteccion_datos_pendiente,
)

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]

# Estas cuatro funciones llevan guion bajo -no forman parte de la interfaz
# pública del módulo-, pero se importan igual en este fichero porque son,
# cada una, un mecanismo crítico sin red propia: el guardián que impide
# escribir dentro del repositorio (`_dentro_del_repositorio`,
# `_problema_de_ruta_de_salida`), el conteo de sesgo al componer el informe
# (`_componer_informe`) y la persistencia incremental del progreso
# (`_registrar_progreso`). Probarlos solo a través de `main()` dejaría sin
# cazar una mutación que rompiera uno de ellos si otra parte del camino la
# compensara por casualidad; probarlos directamente es la única manera de
# señalar, cuando fallan, cuál de los tres es.


# ---------------------------------------------------------------------------
# Ayudas: un `Informe` a medida, sin pasar por el motor
# ---------------------------------------------------------------------------


def _valoracion(observacion: str, evidencia_localizada: bool = True) -> ValoracionVerificada:
    return ValoracionVerificada(
        dimension="D05",
        nivel="EN_DESARROLLO",
        prioridad="P2",
        evidencia=Evidencia(cita="cita de prueba, no de un alumno real", apartado="5"),
        observacion=observacion,
        evidencia_localizada=evidencia_localizada,
    )


def _informe(
    *,
    resumen: str = "Resumen de prueba.",
    valoraciones: list[ValoracionVerificada] | None = None,
    fortalezas: list[FortalezaVerificada] | None = None,
    indicios: list[IndicioDeAutoriaVerificado] | None = None,
    dudas: list[str] | None = None,
    semaforo: str = "VERDE",
) -> Informe:
    return Informe(
        identificacion={
            "alumno": "AF999", "ciclo": "CALIBRACION", "fase": "E3",
            "version": "1", "archivo": "caso.pdf", "criterios": "v2026-2027",
        },
        control_administrativo=[],
        resumen=resumen,
        sintesis_provisional="Síntesis provisional de prueba.",
        valoraciones=valoraciones or [],
        fortalezas=fortalezas or [],
        prioridades=[],
        prioridades_descartadas=[],
        dudas=dudas or [],
        indicios=indicios or [],
        reparos=[],
        dimensiones_ausentes=[],
        semaforo_propuesto=semaforo,
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
        codigo="X01", archivo="x01.pdf", fase="E3", semaforo_esperado="ROJO",
        debe_encontrar=[], no_debe=[], notas="Caso inventado de prueba.",
    )
    base.update(cambios)
    return CasoDeCalibracion(**base)


# ---------------------------------------------------------------------------
# cargar_casos
# ---------------------------------------------------------------------------


def test_cargar_casos_lee_una_lista_de_casos(tmp_path: Path) -> None:
    fichero = tmp_path / "casos.yaml"
    fichero.write_text(
        "- codigo: X01\n"
        "  archivo: x01.pdf\n"
        "  fase: E3\n"
        "  semaforo_esperado: ROJO\n"
        "  debe_encontrar: [desarrollo superficial]\n"
        "  no_debe: [enumerar cada defecto menor]\n"
        "  notas: Caso inventado.\n"
        "- codigo: X02\n"
        "  archivo: x02.pdf\n"
        "  fase: FINAL\n"
        "  semaforo_esperado: VERDE\n",
        encoding="utf-8",
    )

    casos = cargar_casos(fichero)

    assert [c.codigo for c in casos] == ["X01", "X02"]
    assert casos[0].debe_encontrar == ["desarrollo superficial"]
    # Sin declarar no_debe ni notas, los valores por omisión son vacíos.
    assert casos[1].no_debe == []
    assert casos[1].notas == ""


def test_cargar_casos_carga_el_banco_de_ejemplo() -> None:
    """El fichero real del repositorio, solo para comprobar que se lee.

    No se ejecuta contra estos casos en ningún test: no hay ningún P0N.pdf
    en ningún sitio de esta máquina, y no debe haberlo.
    """
    fichero = RAIZ_DEL_REPOSITORIO / "docs" / "calibracion" / "casos.example.yaml"

    casos = cargar_casos(fichero)

    assert [c.codigo for c in casos] == [f"P0{n}" for n in range(1, 10)]
    for caso in casos:
        assert caso.semaforo_esperado in {"VERDE", "AMBAR", "ROJO", "GRIS"}
        assert caso.archivo.endswith(".pdf")


def test_un_fichero_de_casos_que_no_es_una_lista_falla_con_claridad(tmp_path: Path) -> None:
    fichero = tmp_path / "casos.yaml"
    fichero.write_text("codigo: X01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="lista"):
        cargar_casos(fichero)


# ---------------------------------------------------------------------------
# evaluar(): el semáforo
# ---------------------------------------------------------------------------


def test_semaforo_que_coincide_se_marca_acertado() -> None:
    caso = _caso(semaforo_esperado="ROJO")
    informe = _informe(semaforo="ROJO")

    resultado = evaluar(caso, informe)

    assert resultado.acierta_semaforo is True
    assert resultado.direccion == "COINCIDE"


def test_semaforo_que_no_coincide_no_se_marca_acertado() -> None:
    caso = _caso(semaforo_esperado="ROJO")
    informe = _informe(semaforo="AMBAR")

    resultado = evaluar(caso, informe)

    assert resultado.acierta_semaforo is False


def test_direccion_mas_duro_cuando_el_sistema_agrava() -> None:
    """El docente dijo VERDE; el sistema dice ROJO: más duro que él."""
    caso = _caso(semaforo_esperado="VERDE")
    informe = _informe(semaforo="ROJO")

    resultado = evaluar(caso, informe)

    assert resultado.direccion == "MAS_DURO"


def test_direccion_mas_blando_cuando_el_sistema_suaviza() -> None:
    """El docente dijo ROJO; el sistema dice AMBAR: más blando que él."""
    caso = _caso(semaforo_esperado="ROJO")
    informe = _informe(semaforo="AMBAR")

    resultado = evaluar(caso, informe)

    assert resultado.direccion == "MAS_BLANDO"


def test_direccion_no_comparable_cuando_interviene_gris() -> None:
    """GRIS no es "más duro" ni "más blando": es no evaluable."""
    caso = _caso(semaforo_esperado="VERDE")
    informe = _informe(semaforo="GRIS")

    resultado = evaluar(caso, informe)

    assert resultado.direccion == "NO_COMPARABLE"


def test_gris_contra_gris_si_coincide() -> None:
    caso = _caso(semaforo_esperado="GRIS")
    informe = _informe(semaforo="GRIS")

    resultado = evaluar(caso, informe)

    assert resultado.direccion == "COINCIDE"


# ---------------------------------------------------------------------------
# evaluar(): debe_encontrar y no_debe, solo sobre el informe
# ---------------------------------------------------------------------------


def test_debe_encontrar_se_busca_en_las_observaciones_del_informe() -> None:
    caso = _caso(debe_encontrar=["desarrollo superficial", "bibliografia ausente"])
    informe = _informe(valoraciones=[
        _valoracion("Preocupa el desarrollo superficial en varios apartados."),
    ])

    resultado = evaluar(caso, informe)

    assert resultado.debe_encontrar_hallado == ["desarrollo superficial"]
    assert resultado.debe_encontrar_ausente == ["bibliografia ausente"]


def test_debe_encontrar_ignora_tildes_y_mayusculas() -> None:
    """La búsqueda normaliza igual que una cita: no es sensible a la tilde."""
    caso = _caso(debe_encontrar=["bibliografia ausente"])
    informe = _informe(valoraciones=[
        _valoracion("Preocupa la BIBLIOGRAFÍA AUSENTE de fuentes primarias."),
    ])

    resultado = evaluar(caso, informe)

    assert resultado.debe_encontrar_hallado == ["bibliografia ausente"]


def test_debe_encontrar_no_mira_un_borrador_que_no_se_le_pasa() -> None:
    """Aunque el borrador dijera la frase, `evaluar` no la ve: no la recibe.

    `evaluar` no acepta una `Devolucion` en su firma -no hay parámetro para
    ella-, así que no hay manera de que el texto del borrador contamine esta
    búsqueda. Este test lo demuestra de punta a punta: se construye un
    borrador con la frase y un informe sin ella, y solo el informe se pasa.
    """
    frase = "conviene revisar el presupuesto final"
    devolucion_con_la_frase = Devolucion(
        apertura=f"Aviso: {frase}.", fortalezas=["Buen planteamiento."],
        acciones=["Revisa el presupuesto."], cierre="Sigue así.",
    )
    assert frase in devolucion_con_la_frase.apertura  # el borrador sí la lleva

    caso = _caso(debe_encontrar=[frase])
    informe = _informe(resumen="Resumen sin esa frase en ningún sitio.")

    resultado = evaluar(caso, informe)

    assert resultado.debe_encontrar_ausente == [frase]
    assert resultado.debe_encontrar_hallado == []


def test_no_debe_marca_lo_que_aparece_y_no_deberia() -> None:
    caso = _caso(no_debe=["enumerar cada defecto menor"])
    informe = _informe(resumen="El texto enumerar cada defecto menor no debería aparecer, y aparece.")

    resultado = evaluar(caso, informe)

    assert resultado.no_debe_hallado == ["enumerar cada defecto menor"]


def test_no_debe_vacio_cuando_no_aparece() -> None:
    caso = _caso(no_debe=["enumerar cada defecto menor"])
    informe = _informe(resumen="Feedback breve, centrado en cerrar el proyecto.")

    resultado = evaluar(caso, informe)

    assert resultado.no_debe_hallado == []


def test_evidencia_localizada_se_cuenta_para_el_indicador_de_exactitud() -> None:
    caso = _caso()
    informe = _informe(valoraciones=[
        _valoracion("Con evidencia.", evidencia_localizada=True),
        _valoracion("Sin evidencia.", evidencia_localizada=False),
    ])

    resultado = evaluar(caso, informe)

    assert resultado.valoraciones_totales == 2
    assert resultado.valoraciones_con_evidencia == 1


# ---------------------------------------------------------------------------
# ejecutar(): un caso sin PDF se salta, no revienta
# ---------------------------------------------------------------------------


def test_un_caso_sin_pdf_se_salta_con_su_motivo(criterios_de_analisis, tmp_path: Path) -> None:
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    caso = _caso(archivo="no-esta-aqui.pdf")
    proveedor = ProveedorSimulado(respuestas=[])

    informe = ejecutar(criterios_de_analisis, [caso], carpeta, proveedor)

    assert informe.total_casos == 1
    assert informe.saltados == 1
    assert informe.evaluados == 0
    resultado = informe.resultados[0]
    assert resultado.saltado is True
    assert "no-esta-aqui.pdf" in resultado.motivo_salto
    # Sin archivo no hay nada que enviar: no se gasta ninguna llamada.
    assert proveedor.llamadas == []


# ---------------------------------------------------------------------------
# ejecutar(): un fallo del proveedor no tira a los demás casos
# ---------------------------------------------------------------------------


def _pdf_de_caso(carpeta: Path, escribir_pdf, nombre: str, texto: str) -> Path:
    return escribir_pdf(carpeta / nombre, [[texto]], salto=19.0)


def _analisis_simulado(cita: str):
    from backend.analisis.contrato import AnalisisDelMotor, Fortaleza, Valoracion

    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita=cita, apartado="5"),
            observacion="Observacion de prueba con evidencia localizable.",
        )],
        fortalezas=[Fortaleza(
            descripcion="Fortaleza de prueba.",
            evidencia=Evidencia(cita=cita, apartado="5"),
        )],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )


def _devolucion_simulada() -> Devolucion:
    return Devolucion(
        apertura="Avance correcto.", fortalezas=["Fortaleza de prueba."],
        acciones=["Accion de prueba."], cierre="Adelante.",
    )


def _analisis_con_prioridad(cita: str, prioridad: str | None):
    """Como `_analisis_simulado`, pero con la prioridad -y por tanto el
    semáforo resultante- a elegir en vez de fija en P2.
    """
    from backend.analisis.contrato import AnalisisDelMotor, Fortaleza, Valoracion

    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad=prioridad,
            evidencia=Evidencia(cita=cita, apartado="5"),
            observacion="Observacion de prueba con evidencia localizable.",
        )],
        fortalezas=[Fortaleza(
            descripcion="Fortaleza de prueba.",
            evidencia=Evidencia(cita=cita, apartado="5"),
        )],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )


def _analisis_sin_valoraciones_fiables(cita: str):
    """Ningún juicio verificable: sin ninguna valoración, `_semaforo()`
    (Task 9) no tiene de qué partir y el resultado es GRIS.
    """
    from backend.analisis.contrato import AnalisisDelMotor, Fortaleza

    return AnalisisDelMotor(
        valoraciones=[],
        fortalezas=[Fortaleza(
            descripcion="Fortaleza de prueba.",
            evidencia=Evidencia(cita=cita, apartado="5"),
        )],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )


def test_un_caso_que_falla_no_impide_evaluar_el_siguiente(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto_uno = "Contenido inventado del primer caso de calibracion de prueba."
    texto_dos = "Contenido inventado del segundo caso de calibracion de prueba."
    _pdf_de_caso(carpeta, escribir_pdf, "x01.pdf", texto_uno)
    _pdf_de_caso(carpeta, escribir_pdf, "x02.pdf", texto_dos)

    casos = [
        _caso(codigo="X01", archivo="x01.pdf", semaforo_esperado="ROJO"),
        _caso(codigo="X02", archivo="x02.pdf", semaforo_esperado="AMBAR"),
    ]
    proveedor = ProveedorSimulado(
        fallos=[ErrorDelProveedor("sin red, se agoto la cuota")],
        respuestas=[
            _analisis_simulado("Contenido inventado del segundo caso"),
            _devolucion_simulada(),
        ],
    )

    informe = ejecutar(criterios_de_analisis, casos, carpeta, proveedor)

    assert informe.total_casos == 2
    assert informe.saltados == 1
    assert informe.evaluados == 1
    primero, segundo = informe.resultados
    assert primero.codigo == "X01"
    assert primero.saltado is True
    assert "proveedor de análisis ha fallado" in primero.motivo_salto
    assert segundo.codigo == "X02"
    assert segundo.saltado is False
    assert segundo.semaforo_obtenido is not None


def test_una_devolucion_invalida_no_impide_evaluar_el_semaforo(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    """`InformeSinBorrador` no es un fallo del caso: el informe ya es válido.

    `componer()` (Task 8) rechaza un borrador que menciona una nota
    numérica, y `analizar_entrega` lo convierte en `InformeSinBorrador` con
    el informe ya construido dentro. El arnés no compara el borrador -no lo
    necesita-, así que este caso se evalúa igual, no se salta.
    """
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto = "Contenido inventado con una cita reconocible para el análisis."
    _pdf_de_caso(carpeta, escribir_pdf, "x01.pdf", texto)
    caso = _caso(codigo="X01", archivo="x01.pdf", semaforo_esperado="AMBAR")

    devolucion_con_nota = Devolucion(
        apertura="Tu nota final es un 8 sobre 10.",
        fortalezas=["Fortaleza de prueba."],
        acciones=["Accion de prueba."], cierre="Adelante.",
    )
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_simulado("Contenido inventado con una cita reconocible"),
        devolucion_con_nota,
    ])

    informe = ejecutar(criterios_de_analisis, [caso], carpeta, proveedor)

    assert informe.saltados == 0
    assert informe.evaluados == 1
    assert informe.resultados[0].semaforo_obtenido is not None


# ---------------------------------------------------------------------------
# ejecutar(): el informe final cuenta los siete indicadores del §11.1
# ---------------------------------------------------------------------------


def test_el_informe_cuenta_los_siete_indicadores(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto = "Contenido inventado para comprobar los indicadores del banco."
    _pdf_de_caso(carpeta, escribir_pdf, "x01.pdf", texto)
    caso = _caso(
        codigo="X01", archivo="x01.pdf", semaforo_esperado="AMBAR",
        debe_encontrar=["observacion de prueba"],
    )
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_simulado("Contenido inventado para comprobar"),
        _devolucion_simulada(),
    ])

    informe = ejecutar(criterios_de_analisis, [caso], carpeta, proveedor)

    assert set(informe.indicadores) == {
        "cobertura", "exactitud", "prioridad",
        "proporcionalidad", "tono", "prudencia", "ahorro",
    }
    automaticos = {
        clave for clave, indicador in informe.indicadores.items()
        if indicador.medible_automaticamente
    }
    assert automaticos == {"cobertura", "exactitud", "prioridad"}
    for indicador in informe.indicadores.values():
        assert indicador.pregunta
        assert indicador.lectura


def test_los_indicadores_no_medibles_no_fingen_una_cifra_cuando_no_hay_casos() -> None:
    informe = ejecutar(RAIZ_DEL_REPOSITORIO, [], Path("."), ProveedorSimulado())

    assert informe.evaluados == 0
    for indicador in informe.indicadores.values():
        assert indicador.medible_automaticamente is False
        assert "ningun" in indicador.lectura.lower() or "ningún" in indicador.lectura


# ---------------------------------------------------------------------------
# El conteo de sesgo: un lote con direcciones mixtas
# ---------------------------------------------------------------------------
#
# Es la parte útil del arnés, y la que puede engañar al docente sin que nada
# chille si se equivoca: si el informe le dijera "el sistema es indulgente"
# cuando en realidad es severo, el docente ajustaría el listón en la
# dirección contraria. Un solo caso por dirección no basta -no distingue un
# conteo bien hecho de uno que, por casualidad, da el mismo número con un
# solo dato-, así que este lote junta las cuatro direcciones (COINCIDE,
# MAS_DURO, MAS_BLANDO, NO_COMPARABLE) más un caso saltado, en una sola
# tanda, y comprueba los contadores del informe compuesto, no solo la
# dirección de cada resultado por separado -eso ya lo cubren los tests de
# `evaluar()` de más arriba-.


def test_el_lote_con_direcciones_mixtas_cuenta_bien_el_sesgo(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()

    textos = {
        "coincide": "Texto inventado del caso donde el sistema coincide con el docente.",
        "duro": "Texto inventado del caso donde el sistema resulta mas severo.",
        "blando": "Texto inventado del caso donde el sistema resulta mas indulgente.",
        "gris": "Texto inventado del caso que el sistema no logra evaluar del todo.",
    }
    for clave, texto in textos.items():
        _pdf_de_caso(carpeta, escribir_pdf, f"{clave}.pdf", texto)

    casos = [
        _caso(codigo="COINCIDE", archivo="coincide.pdf", semaforo_esperado="VERDE"),
        _caso(codigo="DURO", archivo="duro.pdf", semaforo_esperado="VERDE"),
        _caso(codigo="BLANDO", archivo="blando.pdf", semaforo_esperado="ROJO"),
        _caso(codigo="GRIS", archivo="gris.pdf", semaforo_esperado="VERDE"),
        _caso(codigo="SALTADO", archivo="no-existe.pdf", semaforo_esperado="ROJO"),
    ]
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_con_prioridad("Texto inventado del caso donde el sistema coincide", None),
        _devolucion_simulada(),
        _analisis_con_prioridad("Texto inventado del caso donde el sistema resulta mas severo", "P1"),
        _devolucion_simulada(),
        _analisis_con_prioridad(
            "Texto inventado del caso donde el sistema resulta mas indulgente", "P2"
        ),
        _devolucion_simulada(),
        _analisis_sin_valoraciones_fiables(
            "Texto inventado del caso que el sistema no logra evaluar del todo"
        ),
        _devolucion_simulada(),
    ])

    informe = ejecutar(criterios_de_analisis, casos, carpeta, proveedor)

    assert informe.total_casos == 5
    assert informe.saltados == 1
    assert informe.evaluados == 4
    assert informe.aciertos_semaforo == 1
    assert informe.mas_duro == 1
    assert informe.mas_blando == 1
    assert informe.no_comparable == 1

    direcciones = {r.codigo: r.direccion for r in informe.resultados if not r.saltado}
    assert direcciones == {
        "COINCIDE": "COINCIDE", "DURO": "MAS_DURO",
        "BLANDO": "MAS_BLANDO", "GRIS": "NO_COMPARABLE",
    }

    lectura = informe.lectura_de_sesgo
    assert "1 el sistema fue más duro" in lectura
    assert "1 más blando" in lectura
    assert "1 no comparables por GRIS" in lectura
    assert "sin un lado dominante" in lectura
    # ninguna cifra se traduce en un veredicto de "calibracion superada".
    assert "calibración superada" in lectura


def test_intercambiar_mas_duro_y_mas_blando_al_componer_lo_cazaria_este_test() -> None:
    """No es un test contra el motor: es la garantía de que
    `_componer_informe` no puede confundir un lado por el otro sin que
    algo falle aquí, aunque quien lo mire no tenga PDF ni proveedor a mano.

    Se construye la lista de `ResultadoDeCaso` a mano -sin pasar por
    `ejecutar`- para aislar exactamente la función que agrega los tres
    contadores, la misma que compone `informe.lectura_de_sesgo`.
    """
    resultados = [
        ResultadoDeCaso(
            codigo="A", semaforo_esperado="VERDE", semaforo_obtenido="VERDE",
            acierta_semaforo=True, direccion="COINCIDE",
        ),
        ResultadoDeCaso(
            codigo="B", semaforo_esperado="VERDE", semaforo_obtenido="ROJO",
            acierta_semaforo=False, direccion="MAS_DURO",
        ),
        ResultadoDeCaso(
            codigo="C", semaforo_esperado="VERDE", semaforo_obtenido="ROJO",
            acierta_semaforo=False, direccion="MAS_DURO",
        ),
        ResultadoDeCaso(
            codigo="D", semaforo_esperado="ROJO", semaforo_obtenido="AMBAR",
            acierta_semaforo=False, direccion="MAS_BLANDO",
        ),
    ]

    informe = _componer_informe(resultados)

    assert informe.mas_duro == 2
    assert informe.mas_blando == 1
    assert "2 el sistema fue más duro" in informe.lectura_de_sesgo
    assert "1 más blando" in informe.lectura_de_sesgo
    assert "hacia la dureza" in informe.lectura_de_sesgo


# ---------------------------------------------------------------------------
# proteccion_datos_pendiente
# ---------------------------------------------------------------------------


def test_proteccion_datos_pendiente_si_el_fichero_no_existe(tmp_path: Path) -> None:
    assert proteccion_datos_pendiente(tmp_path) is True


def test_proteccion_datos_pendiente_si_la_entrada_sigue_en_el_fichero(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "- **proteccion_datos** - condiciones de tratamiento aplicables.\n",
        encoding="utf-8",
    )

    assert proteccion_datos_pendiente(tmp_path) is True


def test_proteccion_datos_resuelta_si_ya_no_consta(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente\n\nYa no queda nada pendiente de este apartado.\n",
        encoding="utf-8",
    )

    assert proteccion_datos_pendiente(tmp_path) is False


# ---------------------------------------------------------------------------
# main(): la guarda de proteccion_datos, y la carpeta fuera del repositorio
# ---------------------------------------------------------------------------


def test_main_avisa_y_no_ejecuta_si_proteccion_datos_sigue_pendiente(
    tmp_path: Path, capsys
) -> None:
    raiz = tmp_path / "repo"
    docs = raiz / "docs"
    docs.mkdir(parents=True)
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "- **proteccion_datos** - pendiente.\n", encoding="utf-8"
    )
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()

    codigo = main(["--carpeta", str(carpeta)], raiz=raiz)

    assert codigo == 1
    salida = capsys.readouterr().out
    assert "PENDIENTE_OFICIAL" in salida
    assert "--confirmo" in salida
    # No se ha escrito ningun informe: el arnes no ha llegado a ejecutarse.
    assert list(carpeta.iterdir()) == []


def test_main_rechaza_una_carpeta_dentro_del_repositorio(tmp_path: Path, capsys) -> None:
    raiz = tmp_path / "repo"
    docs = raiz / "docs"
    docs.mkdir(parents=True)
    (docs / "PENDIENTE_OFICIAL.md").write_text("# Pendiente\n", encoding="utf-8")
    carpeta_interior = raiz / "01_CALIBRACION"
    carpeta_interior.mkdir()

    codigo = main(["--carpeta", str(carpeta_interior), "--confirmo"], raiz=raiz)

    assert codigo == 1
    assert "dentro del repositorio" in capsys.readouterr().out


def test_main_completa_una_pasada_sin_proveedor_configurado(
    criterios_de_analisis, tmp_path: Path, escribir_pdf, capsys, monkeypatch
) -> None:
    """Sin OPENAI_API_KEY el proveedor es el simulado y sin respuestas
    programadas: el caso falla al llamarlo, pero el arnes no revienta.

    Se limpia el entorno real de quien ejecuta la prueba -no solo el
    `.env`, que aquí no existe- porque `cargar()` fusiona el entorno del
    proceso: sin esto, una máquina con OPENAI_API_KEY puesta en su perfil
    de shell haría que esta prueba intentara hablar de verdad con la red,
    justo lo que ningún test de este proyecto puede hacer.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REVISOR_MODELO_ANALISIS", raising=False)
    raiz = criterios_de_analisis
    docs = raiz / "docs"
    docs.mkdir(parents=True)
    (docs / "PENDIENTE_OFICIAL.md").write_text("# Pendiente\n", encoding="utf-8")

    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto = "Contenido inventado para la prueba de la linea de ordenes."
    _pdf_de_caso(carpeta, escribir_pdf, "x01.pdf", texto)
    fichero_de_casos = tmp_path / "casos.yaml"
    fichero_de_casos.write_text(
        "- codigo: X01\n  archivo: x01.pdf\n  fase: E3\n"
        "  semaforo_esperado: AMBAR\n",
        encoding="utf-8",
    )

    codigo = main([
        "--carpeta", str(carpeta), "--casos", str(fichero_de_casos), "--confirmo",
    ], raiz=raiz)

    assert codigo == 0
    salida = capsys.readouterr().out
    assert "proveedor es el simulado" in salida
    assert "ADVERTENCIA: esto no es un test" in salida
    informes_escritos = list(carpeta.glob("informe-calibracion-*.md"))
    assert len(informes_escritos) == 1


# ---------------------------------------------------------------------------
# El guardián que impide escribir dentro del repositorio
# ---------------------------------------------------------------------------
#
# Es el mecanismo más delicado de esta tarea: que un informe con códigos de
# alumno y observaciones sobre su trabajo no acabe en un commit. Vive sin
# ninguna red que lo respalde si falla -R6 solo mira lo que ya está en el
# árbol versionado, no lo que un comando intenta escribir-, así que se
# prueba aquí directamente, con las rutas que produciría un descuido de
# verdad: una que sale de la carpeta permitida con `..` y vuelve a caer
# dentro del repositorio, y una carpeta hermana cuyo nombre empieza igual
# que el de la raíz, que una comparación de texto -en vez de una
# comparación de rutas- confundiría con estar dentro.


def test_dentro_del_repositorio_detecta_una_ruta_directa(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()

    assert _dentro_del_repositorio(raiz, raiz / "sub" / "informe.md") is True


def test_dentro_del_repositorio_es_cierto_para_la_propia_raiz(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()

    assert _dentro_del_repositorio(raiz, raiz) is True


def test_dentro_del_repositorio_permite_una_carpeta_hermana(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    hermana = tmp_path / "calibracion"
    hermana.mkdir()

    assert _dentro_del_repositorio(raiz, hermana / "informe.md") is False


def test_dentro_del_repositorio_no_se_deja_enganar_por_un_nombre_parecido(
    tmp_path: Path,
) -> None:
    """Una comparación de texto -`str(ruta).startswith(str(raiz))`- caería
    aquí: "repo-otro" empieza igual que "repo", letra por letra, pero no es
    la misma carpeta ni está dentro de ella. La comprobación real compara
    componentes de ruta, no cadenas, y no debe rechazar esta carpeta hermana.
    """
    raiz = tmp_path / "repo"
    raiz.mkdir()
    parecida = tmp_path / "repo-otro"
    parecida.mkdir()

    assert _dentro_del_repositorio(raiz, parecida / "informe.md") is False


def test_dentro_del_repositorio_detecta_un_recorrido_que_sale_y_vuelve(
    tmp_path: Path,
) -> None:
    """El caso que produciría un descuido de verdad: una ruta escrita desde
    la carpeta de calibración, con `..`, que en apariencia se queda fuera y
    en realidad vuelve a caer dentro del repositorio.
    """
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()

    ruta_que_vuelve = carpeta / ".." / "repo" / "informe.md"

    assert _dentro_del_repositorio(raiz, ruta_que_vuelve) is True


def test_dentro_del_repositorio_permite_un_recorrido_que_sale_y_no_vuelve(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    otra = tmp_path / "otra-carpeta"
    otra.mkdir()

    ruta = carpeta / ".." / "otra-carpeta" / "informe.md"

    assert _dentro_del_repositorio(raiz, ruta) is False


@pytest.mark.skipif(
    sys.platform != "win32", reason="el enlace de unión es específico de NTFS"
)
def test_dentro_del_repositorio_sigue_un_enlace_de_ntfs_hacia_dentro(
    tmp_path: Path,
) -> None:
    """Un enlace de unión (`mklink /J`, sin privilegios de administrador)
    que, desde fuera, apunta dentro del repositorio: `Path.resolve()` lo
    sigue hasta el destino real, y la comprobación tiene que mirar ese
    destino, no la ruta superficial del enlace.
    """
    raiz = tmp_path / "repo"
    raiz.mkdir()
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    enlace = fuera / "enlace-hacia-el-repositorio"

    resultado = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(enlace), str(raiz)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        pytest.skip(f"No se ha podido crear el enlace de prueba: {resultado.stderr}")

    assert _dentro_del_repositorio(raiz, enlace / "informe.md") is True


def test_problema_de_ruta_de_salida_es_none_cuando_esta_fuera(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    salida = tmp_path / "calibracion" / "informe.md"

    assert _problema_de_ruta_de_salida(raiz, salida) is None


def test_problema_de_ruta_de_salida_avisa_si_cae_dentro(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()

    problema = _problema_de_ruta_de_salida(raiz, raiz / "docs" / "informe.md")

    assert problema is not None
    assert "dentro del repositorio" in problema


def test_main_no_escribe_el_informe_si_la_salida_cae_dentro_del_repositorio(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REVISOR_MODELO_ANALISIS", raising=False)
    raiz = tmp_path / "repo"
    (raiz / "docs").mkdir(parents=True)
    (raiz / "docs" / "PENDIENTE_OFICIAL.md").write_text("# Pendiente\n", encoding="utf-8")
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    fichero_de_casos = tmp_path / "casos-vacios.yaml"
    fichero_de_casos.write_text("[]\n", encoding="utf-8")
    salida_maliciosa = raiz / "docs" / "informe-colado.md"

    codigo = main([
        "--carpeta", str(carpeta), "--casos", str(fichero_de_casos),
        "--salida", str(salida_maliciosa), "--confirmo",
    ], raiz=raiz)

    assert codigo == 0
    assert not salida_maliciosa.exists()
    salida_texto = capsys.readouterr().out
    assert "está dentro del repositorio" in salida_texto
    assert "no se ha escrito en disco" in salida_texto.lower()
    # Nada ha quedado escrito en ningún sitio del árbol del repositorio.
    assert set(raiz.rglob("*.md")) == {raiz / "docs" / "PENDIENTE_OFICIAL.md"}


def test_main_no_escribe_si_la_salida_recorre_con_puntos_hacia_el_repositorio(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    """El ataque que señala el propio encargo de esta tarea: una ruta de
    salida que sale de la carpeta de calibración con `..` y vuelve a caer
    dentro del repositorio.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REVISOR_MODELO_ANALISIS", raising=False)
    raiz = tmp_path / "repo"
    (raiz / "docs").mkdir(parents=True)
    (raiz / "docs" / "PENDIENTE_OFICIAL.md").write_text("# Pendiente\n", encoding="utf-8")
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    fichero_de_casos = tmp_path / "casos-vacios.yaml"
    fichero_de_casos.write_text("[]\n", encoding="utf-8")
    salida_que_vuelve = carpeta / ".." / "repo" / "informe-colado.md"

    codigo = main([
        "--carpeta", str(carpeta), "--casos", str(fichero_de_casos),
        "--salida", str(salida_que_vuelve), "--confirmo",
    ], raiz=raiz)

    assert codigo == 0
    assert not (raiz / "informe-colado.md").exists()
    assert "está dentro del repositorio" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Progreso: cada resultado se guarda en cuanto se obtiene
# ---------------------------------------------------------------------------
#
# Cada caso es una llamada de pago. Si el proceso entero muere a mitad de
# una tanda -un Ctrl+C, un corte-, los casos que ya se completaron no deben
# perderse solo porque vivían en una lista en memoria que desaparece con el
# proceso. Esto no es una reanudación automática -queda fuera de esta tarea
# a propósito-: es que el trabajo ya pagado quede en disco.


def test_registrar_progreso_anade_una_linea_json_por_llamada(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    fichero = tmp_path / "calibracion" / "progreso.jsonl"
    fichero.parent.mkdir()
    primero = ResultadoDeCaso(
        codigo="A", semaforo_esperado="VERDE", semaforo_obtenido="VERDE",
        acierta_semaforo=True, direccion="COINCIDE",
    )
    segundo = ResultadoDeCaso(codigo="B", saltado=True, motivo_salto="no está el archivo")

    _registrar_progreso(raiz, fichero, primero)
    _registrar_progreso(raiz, fichero, segundo)

    lineas = fichero.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 2
    assert json.loads(lineas[0])["codigo"] == "A"
    assert json.loads(lineas[1])["codigo"] == "B"
    assert json.loads(lineas[1])["saltado"] is True


def test_registrar_progreso_respeta_la_guarda_de_ruta(tmp_path: Path) -> None:
    """La misma comprobación que la salida final: si el fichero de progreso
    cayera dentro del repositorio, no se escribe.
    """
    raiz = tmp_path / "repo"
    raiz.mkdir()
    fichero_interior = raiz / "progreso.jsonl"
    resultado = ResultadoDeCaso(codigo="A", saltado=True, motivo_salto="motivo de prueba")

    _registrar_progreso(raiz, fichero_interior, resultado)

    assert not fichero_interior.exists()


def test_ejecutar_escribe_un_fichero_de_progreso_junto_al_informe(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto = "Contenido inventado para comprobar el fichero de progreso."
    _pdf_de_caso(carpeta, escribir_pdf, "x01.pdf", texto)
    casos = [_caso(codigo="X01", archivo="x01.pdf", semaforo_esperado="AMBAR")]
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_simulado("Contenido inventado para comprobar"), _devolucion_simulada(),
    ])

    ejecutar(criterios_de_analisis, casos, carpeta, proveedor)

    ficheros = list(carpeta.glob("progreso-calibracion-*.jsonl"))
    assert len(ficheros) == 1
    lineas = ficheros[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 1
    assert json.loads(lineas[0])["codigo"] == "X01"


class _ProveedorQueSeInterrumpe:
    """Se comporta bien hasta la llamada indicada, y ahí finge un Ctrl+C de
    verdad -`KeyboardInterrupt`, no un fallo del proveedor-, para probar que
    interrumpir el proceso entero no borra lo que ya se había completado.
    """

    def __init__(self, respuestas: list, en_la_llamada: int) -> None:
        self._respuestas = list(respuestas)
        self._en_la_llamada = en_la_llamada
        self.llamadas = 0

    @property
    def nombre(self) -> str:
        return "simulado"

    def analizar(self, instruccion, texto, formato):
        self.llamadas += 1
        if self.llamadas == self._en_la_llamada:
            raise KeyboardInterrupt()
        return self._respuestas.pop(0)


def test_un_ctrl_c_a_mitad_de_la_tanda_no_borra_lo_ya_completado(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto_uno = "Contenido inventado del primer caso, que termina antes del corte."
    texto_dos = "Contenido inventado del segundo caso, que nunca llega a terminar."
    _pdf_de_caso(carpeta, escribir_pdf, "uno.pdf", texto_uno)
    _pdf_de_caso(carpeta, escribir_pdf, "dos.pdf", texto_dos)
    casos = [
        _caso(codigo="UNO", archivo="uno.pdf", semaforo_esperado="AMBAR"),
        _caso(codigo="DOS", archivo="dos.pdf", semaforo_esperado="AMBAR"),
    ]
    # Dos llamadas completan el primer caso -análisis y devolución-; la
    # tercera es el análisis del segundo caso, y ahí se interrumpe.
    proveedor = _ProveedorQueSeInterrumpe(
        respuestas=[
            _analisis_con_prioridad(
                "Contenido inventado del primer caso, que termina", "P2"
            ),
            _devolucion_simulada(),
        ],
        en_la_llamada=3,
    )

    with pytest.raises(KeyboardInterrupt):
        ejecutar(criterios_de_analisis, casos, carpeta, proveedor)

    ficheros = list(carpeta.glob("progreso-calibracion-*.jsonl"))
    assert len(ficheros) == 1
    lineas = ficheros[0].read_text(encoding="utf-8").strip().splitlines()
    # Solo el primer caso llegó a completarse antes del "Ctrl+C": es lo
    # único que debe sobrevivir en disco a la interrupción.
    assert len(lineas) == 1
    registrado = json.loads(lineas[0])
    assert registrado["codigo"] == "UNO"
    assert registrado["saltado"] is False
    assert registrado["semaforo_obtenido"] is not None


def test_la_espera_entre_casos_se_respeta(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    """Un proyecto largo puede acercarse solo al límite de tokens por minuto
    de la cuenta, y dos seguidos lo superan: en la primera calibración real
    -límite de 30.000 por minuto- fallaron justo los dos trabajos más largos,
    de 19.418 y 13.116 tokens. `--espera` existe para eso, y no para el saldo.

    El temporizador se inyecta en vez de esperar de verdad: un test que
    duerme siete segundos para comprobar que duerme siete segundos no prueba
    nada mejor y hace la suite inservible.
    """
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    casos = []
    respuestas = []
    for numero in (1, 2, 3):
        texto = f"Contenido inventado del caso {numero} de calibracion."
        _pdf_de_caso(carpeta, escribir_pdf, f"x0{numero}.pdf", texto)
        casos.append(_caso(codigo=f"X0{numero}", archivo=f"x0{numero}.pdf"))
        respuestas += [_analisis_simulado(texto[:40]), _devolucion_simulada()]

    esperas: list[float] = []
    ejecutar(
        criterios_de_analisis, casos, carpeta,
        ProveedorSimulado(respuestas=respuestas),
        espera=7.5, dormir=esperas.append,
    )

    # Tres casos, dos pausas: el primero no espera a nadie.
    assert esperas == [7.5, 7.5]


def test_sin_espera_no_se_duerme(
    criterios_de_analisis, tmp_path: Path, escribir_pdf
) -> None:
    """Por omisión no espera: quien no tenga el problema no paga el precio de
    una pasada más lenta."""
    carpeta = tmp_path / "calibracion"
    carpeta.mkdir()
    texto = "Contenido inventado de un único caso de calibración."
    _pdf_de_caso(carpeta, escribir_pdf, "x01.pdf", texto)

    esperas: list[float] = []
    ejecutar(
        criterios_de_analisis, [_caso(codigo="X01", archivo="x01.pdf")], carpeta,
        ProveedorSimulado(
            respuestas=[_analisis_simulado(texto[:40]), _devolucion_simulada()]
        ),
        dormir=esperas.append,
    )

    assert esperas == []


def test_una_entrada_archivada_como_resuelta_ya_no_bloquea(tmp_path: Path) -> None:
    """`docs/PENDIENTE_OFICIAL.md` conserva lo resuelto en su propia sección,
    porque saber que algo estuvo pendiente y por qué dejó de estarlo es parte
    de poder reconstruir con qué criterio se corrigió a un alumno.

    Si la comprobación buscara el nombre en el fichero entero, esa constancia
    bloquearía para siempre, y la única forma de desbloquear sería borrar la
    historia. Solo cuenta lo que sigue en «Pendientes».
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "## Pendientes\n\n"
        "- **rubrica** — criterios oficiales. Se espera de la programación.\n\n"
        "## Resueltas\n\n"
        "- **proteccion_datos** — *Resuelta el 2026-08-30.* Ya no bloquea.\n",
        encoding="utf-8",
    )

    assert proteccion_datos_pendiente(tmp_path) is False


def test_lo_que_sigue_en_pendientes_bloquea_aunque_haya_resueltas(
    tmp_path: Path,
) -> None:
    """La sección de resueltas no puede tapar lo que de verdad sigue abierto."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "## Pendientes\n\n"
        "- **proteccion_datos** — condiciones de tratamiento. Bloquea.\n\n"
        "## Resueltas\n\n"
        "- **otra_cosa** — *Resuelta.* Ya no bloquea.\n",
        encoding="utf-8",
    )

    assert proteccion_datos_pendiente(tmp_path) is True
