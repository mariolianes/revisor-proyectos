"""El arnés de calibración: se prueba a él mismo, no al motor.

Ningún PDF real de alumno entra aquí. Los «casos» de estas pruebas son
inventados -códigos, archivos y frases que no existen en ningún proyecto
real-, y los PDF que necesitan se construyen con `escribir_pdf` (ver
`tests/conftest.py`), igual que el resto de la suite. El banco de verdad,
`docs/calibracion/casos.example.yaml`, solo se usa aquí para comprobar que
se puede leer: nunca se ejecuta contra él, porque no hay ningún PDF
`P0N.pdf` en ningún sitio de este repositorio ni de esta máquina de pruebas.
"""

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
    cargar_casos,
    ejecutar,
    evaluar,
    main,
    proteccion_datos_pendiente,
)

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]


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
        valoraciones=valoraciones or [],
        fortalezas=fortalezas or [],
        prioridades=[],
        prioridades_descartadas=[],
        dudas=dudas or [],
        indicios=indicios or [],
        reparos=[],
        dimensiones_ausentes=[],
        semaforo=semaforo,
        recomendacion=None,
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
