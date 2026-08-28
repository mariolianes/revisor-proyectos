"""El puerto y el proveedor simulado."""

import pytest
from pydantic import BaseModel

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.proveedor import (
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

    assert p.analizar("instruccion", "texto", AnalisisDelMotor) is VACIO


def test_registra_lo_que_se_le_pidio() -> None:
    """Los tests de la instruccion necesitan ver que llego al proveedor."""
    p = ProveedorSimulado(respuestas=[VACIO])
    p.analizar("la instruccion", "el texto del trabajo", AnalisisDelMotor)

    assert p.llamadas == [("la instruccion", "el texto del trabajo")]


def test_se_puede_programar_un_fallo() -> None:
    p = ProveedorSimulado(fallos=[RespuestaNoValida("no encaja en el formulario")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)


def test_un_fallo_y_luego_una_respuesta() -> None:
    """Es el caso del reintento: falla una vez y a la segunda va."""
    p = ProveedorSimulado(respuestas=[VACIO], fallos=[RespuestaNoValida("mal")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)
    assert p.analizar("i", "t", AnalisisDelMotor) is VACIO


def test_quedarse_sin_respuestas_es_un_error_del_test() -> None:
    """Si un test pide mas analisis de los que programo, que se note."""
    p = ProveedorSimulado(respuestas=[])

    with pytest.raises(AssertionError, match="sin respuestas"):
        p.analizar("i", "t", AnalisisDelMotor)


def test_el_simulado_dice_que_lo_es() -> None:
    """El frontend lo ensena: un analisis simulado no es un analisis."""
    assert ProveedorSimulado(respuestas=[VACIO]).nombre == "simulado"


def test_respuesta_no_valida_es_un_error_del_proveedor() -> None:
    assert issubclass(RespuestaNoValida, ErrorDelProveedor)


def test_el_puerto_es_generico_en_el_formulario_pedido() -> None:
    """El mismo proveedor sirve para pedir cualquier formulario, no solo el
    analisis: es el punto de diseno que permite reutilizarlo para el
    borrador de devolucion en una tarea posterior."""

    class OtroFormulario(BaseModel):
        campo: str

    otro = OtroFormulario(campo="valor")
    p = ProveedorSimulado(respuestas=[otro])

    assert p.analizar("i", "t", OtroFormulario) is otro


def test_analisis_de_ejemplo_tiene_citas_localizables_en_el_texto() -> None:
    """El simulado no puede probar el camino feliz con citas inventadas: las
    defensas de verificacion las rechazarian. Esta prueba ata el generador
    de ejemplos a la defensa real (`cita_localizada`), no a la idea de lo
    que esa defensa hace."""
    analisis = analisis_de_ejemplo(TEXTO_DE_EJEMPLO)

    citas = (
        [v.evidencia.cita for v in analisis.valoraciones]
        + [f.evidencia.cita for f in analisis.fortalezas]
        + [pat.evidencia.cita for pat in analisis.patrones]
        + [i.evidencia.cita for i in analisis.indicios_de_autoria]
    )

    assert citas, "El analisis de ejemplo deberia traer al menos una cita"
    for cita in citas:
        assert cita_localizada(cita, TEXTO_DE_EJEMPLO), (
            f"La cita {cita!r} no se localiza en el texto de origen"
        )


def test_analisis_de_ejemplo_es_determinista() -> None:
    """Si variara entre llamadas, los tests de las tareas siguientes que se
    apoyen en el serian intermitentes."""
    assert analisis_de_ejemplo(TEXTO_DE_EJEMPLO) == analisis_de_ejemplo(TEXTO_DE_EJEMPLO)


def test_desde_texto_programa_un_proveedor_simulado_con_citas_reales() -> None:
    """La forma en que las tareas siguientes usaran el simulado: construido
    directamente a partir del texto del trabajo."""
    p = ProveedorSimulado.desde_texto(TEXTO_DE_EJEMPLO)

    analisis = p.analizar("instruccion", TEXTO_DE_EJEMPLO, AnalisisDelMotor)

    assert isinstance(analisis, AnalisisDelMotor)
    assert analisis.valoraciones
    assert cita_localizada(
        analisis.valoraciones[0].evidencia.cita, TEXTO_DE_EJEMPLO
    )
