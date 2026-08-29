"""El puerto y el proveedor simulado."""

import pytest
from pydantic import BaseModel

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.proveedor import (
    LONGITUD_MINIMA_DE_TEXTO,
    ErrorDelProveedor,
    ProveedorSimulado,
    RespuestaNoValida,
    analisis_de_ejemplo,
)
from backend.analisis.verificacion import cita_localizada

VACIO = AnalisisDelMotor(
    valoraciones=[], fortalezas=[], patrones=[],
    dudas_para_el_docente=[], indicios_de_autoria=[],
)

# Un texto de trabajo ficticio, sin dato real de ningún alumno, con longitud
# suficiente para que los fragmentos que toma `analisis_de_ejemplo` en
# distintos puntos de su extensión quepan todos dentro del texto.
TEXTO_DE_EJEMPLO = """
El proyecto AF023 plantea la puesta en marcha de un taller mecánico de
proximidad orientado a vehículos eléctricos e híbridos, con un plan de
negocio a tres años y una previsión de personal de cuatro técnicos.

En el apartado de análisis de mercado se estudia la competencia existente
en la zona y se identifica un hueco en el mantenimiento especializado de
baterías, apoyándose en fuentes del sector citadas al final del documento.

El plan económico financiero desarrolla la inversión inicial necesaria, el
punto de equilibrio estimado y las fuentes de financiación previstas,
incluyendo una línea de préstamo bancario y aportación propia de los
promotores del proyecto.

Las conclusiones del trabajo recogen las principales dificultades
encontradas durante su desarrollo y proponen líneas de mejora para una
futura implantación real del negocio descrito en los apartados anteriores.
""".strip()


def test_devuelve_la_respuesta_que_se_le_dio() -> None:
    p = ProveedorSimulado(respuestas=[VACIO])

    assert p.analizar("instrucción", "texto", AnalisisDelMotor) is VACIO


def test_registra_lo_que_se_le_pidio() -> None:
    """Los tests de la instrucción necesitan ver que llegó al proveedor."""
    p = ProveedorSimulado(respuestas=[VACIO])
    p.analizar("la instrucción", "el texto del trabajo", AnalisisDelMotor)

    assert p.llamadas == [("la instrucción", "el texto del trabajo")]


def test_se_puede_programar_un_fallo() -> None:
    p = ProveedorSimulado(fallos=[RespuestaNoValida("no encaja en el formulario")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)


def test_una_llamada_que_falla_tambien_se_registra() -> None:
    """El registro de llamadas tiene que servir para depurar un fallo real
    del proveedor, no solo el camino feliz: si se registrara después de
    comprobar los fallos programados, una llamada que termina en error
    desaparecería de `llamadas` justo cuando más falta hace verla."""
    p = ProveedorSimulado(fallos=[RespuestaNoValida("mal")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("la instrucción", "el texto", AnalisisDelMotor)

    assert p.llamadas == [("la instrucción", "el texto")]


def test_un_fallo_y_luego_una_respuesta() -> None:
    """Es el caso del reintento: falla una vez y a la segunda va."""
    p = ProveedorSimulado(respuestas=[VACIO], fallos=[RespuestaNoValida("mal")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)
    assert p.analizar("i", "t", AnalisisDelMotor) is VACIO


def test_quedarse_sin_respuestas_es_un_error_del_test() -> None:
    """Si un test pide más análisis de los que programó, que se note."""
    p = ProveedorSimulado(respuestas=[])

    with pytest.raises(AssertionError, match="sin respuestas"):
        p.analizar("i", "t", AnalisisDelMotor)


def test_el_simulado_dice_que_lo_es() -> None:
    """El frontend lo enseña: un análisis simulado no es un análisis."""
    assert ProveedorSimulado(respuestas=[VACIO]).nombre == "simulado"


def test_respuesta_no_valida_es_un_error_del_proveedor() -> None:
    assert issubclass(RespuestaNoValida, ErrorDelProveedor)


def test_el_mensaje_para_el_profesor_es_el_de_la_excepcion_por_omision() -> None:
    """El contrato explícito de `ErrorDelProveedor`: por omisión, el texto
    que ve el docente es el mismo con el que se construyó la excepción.

    Esto es justo lo que ya hacían las dos capas que consumen esta
    excepción -`servicios/analisis_de_entrega.py` y `api/analisis.py`-
    cuando hacían `str(fallo)` directamente; declarar la propiedad no
    cambia ningún mensaje existente, solo deja de ser una convención
    implícita que dependía de que cada proveedor la respetara sin que
    nada se lo recordara.
    """
    fallo = ErrorDelProveedor("sin conexión con el proveedor")

    assert fallo.mensaje_para_el_profesor == "sin conexión con el proveedor"
    assert fallo.mensaje_para_el_profesor == str(fallo)


def test_una_subclase_puede_dar_un_mensaje_distinto_al_de_str() -> None:
    """El contrato admite que un proveedor futuro necesite un texto
    distinto del que lleva la excepción -compuesto a partir de varios
    datos internos, por ejemplo-, sobrescribiendo la propiedad en su
    propia subclase sin tocar `__str__`.
    """
    class _FalloConMensajePropio(ErrorDelProveedor):
        @property
        def mensaje_para_el_profesor(self) -> str:
            return "texto pensado para el docente"

    fallo = _FalloConMensajePropio("detalle interno, no para el docente")

    assert fallo.mensaje_para_el_profesor == "texto pensado para el docente"
    assert str(fallo) == "detalle interno, no para el docente"


def test_el_puerto_es_generico_en_el_formulario_pedido() -> None:
    """El mismo proveedor sirve para pedir cualquier formulario, no solo el
    análisis: es el punto de diseño que permite reutilizarlo para el
    borrador de devolución en una tarea posterior."""

    class OtroFormulario(BaseModel):
        campo: str

    otro = OtroFormulario(campo="valor")
    p = ProveedorSimulado(respuestas=[otro])

    assert p.analizar("i", "t", OtroFormulario) is otro


def test_las_respuestas_se_devuelven_en_el_orden_en_que_se_programaron() -> None:
    """FIFO, no LIFO: es el orden que documenta el reintento -falla una vez,
    la siguiente respuesta programada es la que le toca-. Con una sola
    respuesta programada, como en el resto de los tests, ese orden nunca se
    llegaría a comprobar."""

    class OtroFormulario(BaseModel):
        campo: str

    primera = OtroFormulario(campo="primera")
    segunda = OtroFormulario(campo="segunda")
    p = ProveedorSimulado(respuestas=[primera, segunda])

    assert p.analizar("i", "t", OtroFormulario) is primera
    assert p.analizar("i", "t", OtroFormulario) is segunda


def test_los_fallos_se_lanzan_en_el_orden_en_que_se_programaron() -> None:
    """Hermano del test anterior, para `_fallos`: mismo FIFO, mismo motivo.
    Un reintento que programa dos fallos distintos -uno para el primer
    intento, otro para el segundo, por ejemplo para probar que cada uno se
    trata de forma distinta- necesita que salgan en ese orden. Con un solo
    fallo programado, como en el resto de los tests, ese orden nunca se
    llegaría a comprobar."""
    primero = RespuestaNoValida("primero")
    segundo = RespuestaNoValida("segundo")
    p = ProveedorSimulado(fallos=[primero, segundo])

    with pytest.raises(RespuestaNoValida) as info_primero:
        p.analizar("i", "t", AnalisisDelMotor)
    assert info_primero.value is primero

    with pytest.raises(RespuestaNoValida) as info_segundo:
        p.analizar("i", "t", AnalisisDelMotor)
    assert info_segundo.value is segundo


def test_analisis_de_ejemplo_tiene_citas_localizables_en_el_texto() -> None:
    """El simulado no puede probar el camino feliz con citas inventadas: las
    defensas de verificación las rechazarían. Esta prueba ata el generador
    de ejemplos a la defensa real (`cita_localizada`), no a la idea de lo
    que esa defensa hace."""
    analisis = analisis_de_ejemplo(TEXTO_DE_EJEMPLO)

    citas = (
        [v.evidencia.cita for v in analisis.valoraciones]
        + [f.evidencia.cita for f in analisis.fortalezas]
        + [pat.evidencia.cita for pat in analisis.patrones]
        + [i.evidencia.cita for i in analisis.indicios_de_autoria]
    )

    assert citas, "El análisis de ejemplo debería traer al menos una cita"
    for cita in citas:
        assert cita_localizada(cita, TEXTO_DE_EJEMPLO), (
            f"La cita {cita!r} no se localiza en el texto de origen"
        )


def test_analisis_de_ejemplo_es_determinista() -> None:
    """Si variara entre llamadas, los tests de las tareas siguientes que se
    apoyen en él serían intermitentes."""
    assert analisis_de_ejemplo(TEXTO_DE_EJEMPLO) == analisis_de_ejemplo(TEXTO_DE_EJEMPLO)


def test_desde_texto_programa_un_proveedor_simulado_con_citas_reales() -> None:
    """La forma en que las tareas siguientes usarán el simulado: construido
    directamente a partir del texto del trabajo."""
    p = ProveedorSimulado.desde_texto(TEXTO_DE_EJEMPLO)

    analisis = p.analizar("instrucción", TEXTO_DE_EJEMPLO, AnalisisDelMotor)

    assert isinstance(analisis, AnalisisDelMotor)
    assert analisis.valoraciones
    assert cita_localizada(
        analisis.valoraciones[0].evidencia.cita, TEXTO_DE_EJEMPLO
    )


def test_un_texto_por_debajo_del_minimo_falla_a_la_cara() -> None:
    """Sin esta guarda temprana, el análisis se construiría igual, con
    apariencia correcta, y sus citas las rechazaría cita_localizada más
    adelante: quien lo use en una tarea siguiente perseguiría el fallo en
    el sitio equivocado."""
    texto_corto = "x" * (LONGITUD_MINIMA_DE_TEXTO - 1)

    with pytest.raises(ValueError, match=str(LONGITUD_MINIMA_DE_TEXTO)):
        analisis_de_ejemplo(texto_corto)


def test_un_texto_justo_en_el_limite_sin_artefactos_funciona() -> None:
    """Fija la frontera del caso limpio: un off-by-one en el cálculo de
    LONGITUD_MINIMA_DE_TEXTO no se notaría solo con el test del texto
    corto."""
    texto_en_el_limite = "x" * LONGITUD_MINIMA_DE_TEXTO

    analisis = analisis_de_ejemplo(texto_en_el_limite)

    citas = (
        [v.evidencia.cita for v in analisis.valoraciones]
        + [f.evidencia.cita for f in analisis.fortalezas]
        + [pat.evidencia.cita for pat in analisis.patrones]
        + [i.evidencia.cita for i in analisis.indicios_de_autoria]
    )
    for cita in citas:
        assert cita_localizada(cita, texto_en_el_limite)


def test_un_texto_en_el_limite_con_artefactos_de_pdf_falla_con_error_claro() -> None:
    """El caso incómodo: alcanzar LONGITUD_MINIMA_DE_TEXTO no basta cuando
    el texto trae los artefactos que introduce un PDF real -aquí, espacios
    dobles pegados justo donde se recorta el último fragmento-, porque
    colapsan al normalizar y la cita se queda por debajo de CITA_MINIMA.

    Antes de verificar cada cita contra `cita_localizada`, esto pasaba en
    silencio: el análisis se construía igual, con una cita que la
    verificación real rechazaría más adelante. Ahora tiene que fallar aquí,
    con un error que señale cuál cita es y por qué."""
    texto = "b" * 113 + "a  aa  aa  aa  aa  aa"
    assert len(texto) == LONGITUD_MINIMA_DE_TEXTO

    with pytest.raises(ValueError, match="no se localiza"):
        analisis_de_ejemplo(texto)


def test_un_texto_en_el_limite_con_guion_de_maquetacion_falla_con_error_claro() -> None:
    """La misma incomodidad que el test anterior, con el otro artefacto que
    `normalizar_para_buscar` existe para tratar: un guion de maquetación al
    final de línea, que desaparece por completo al normalizar y también
    puede dejar la cita por debajo de CITA_MINIMA."""
    texto = "b" * 132 + "-\n"
    assert len(texto) == LONGITUD_MINIMA_DE_TEXTO

    with pytest.raises(ValueError, match="no se localiza"):
        analisis_de_ejemplo(texto)
