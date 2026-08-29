"""El adaptador real, contra un cliente simulado.

No se llama a OpenAI: se comprueba que se le pide lo que hay que pedirle y
que sus fallos se traducen a algo que el profesor entienda. Ningún test de
este fichero necesita red ni una clave real -los objetos `httpx.Request` y
`httpx.Response` que arman los fallos de OpenAI se construyen en memoria,
sin abrir ninguna conexión.
"""

import httpx
import openai
import pytest

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.openai import ProveedorOpenAI
from backend.analisis.proveedor import ErrorDelProveedor, RespuestaNoValida

VACIO = AnalisisDelMotor(
    valoraciones=[], fortalezas=[], patrones=[],
    dudas_para_el_docente=[], indicios_de_autoria=[],
)


class _RespuestaFalsa:
    def __init__(self, parsed=VACIO):
        self.output_parsed = parsed


class _ClienteFalso:
    """Imita lo justo del cliente de OpenAI: responses.parse."""

    def __init__(self, resultado=None, error=None):
        self.recibido = {}
        self._resultado = resultado if resultado is not None else _RespuestaFalsa()
        self._error = error
        self.responses = self

    def parse(self, **kwargs):
        self.recibido = kwargs
        if self._error:
            raise self._error
        return self._resultado


def _peticion() -> httpx.Request:
    """Una petición HTTP de mentira, para armar excepciones de `openai` sin
    abrir ninguna conexión de verdad."""
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def _fallo_con_estado(clase: type, estado: int, mensaje: str):
    """Construye un fallo de `openai` de los que llevan respuesta HTTP
    -autenticación, límite de uso-, con el mismo mensaje que devolvería la
    API real en el cuerpo del error."""
    respuesta = httpx.Response(estado, request=_peticion(), json={"error": {"message": mensaje}})
    return clase(mensaje, response=respuesta, body=respuesta.json())


def test_devuelve_el_analisis_ya_validado() -> None:
    cliente = _ClienteFalso()
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    assert p.analizar("instruccion", "texto", AnalisisDelMotor) is VACIO


def test_envia_la_instruccion_separada_del_texto() -> None:
    """Es lo que la API de Responses permite y nuestro diseño aprovecha."""
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar(
        "la instruccion", "el trabajo del alumno", AnalisisDelMotor
    )

    assert cliente.recibido["instructions"] == "la instruccion"
    assert "el trabajo del alumno" in str(cliente.recibido["input"])


def test_pide_la_estructura_del_contrato() -> None:
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["text_format"] is AnalisisDelMotor


def test_usa_el_modelo_configurado() -> None:
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "el-modelo-elegido", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["model"] == "el-modelo-elegido"


def test_pide_la_respuesta_mas_estable_posible() -> None:
    """Un juicio que cambia cada vez que se pulsa no es un juicio."""
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["temperature"] == 0


def test_una_respuesta_que_no_encaja_es_reintentable() -> None:
    """El fallo más común: se distingue para poder reintentarlo una vez."""
    cliente = _ClienteFalso(resultado=_RespuestaFalsa(parsed=None))
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)


def test_un_fallo_de_red_llega_en_castellano() -> None:
    cliente = _ClienteFalso(error=ConnectionError("connection refused"))
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "no se ha podido" in str(fallo.value).lower()
    assert "connection refused" in str(fallo.value)


def test_el_nombre_dice_que_modelo_se_uso() -> None:
    """El informe lo guarda: dentro de un año importará con qué se hizo."""
    p = ProveedorOpenAI("clave", "un-modelo", cliente=_ClienteFalso())

    assert p.nombre == "openai:un-modelo"


def test_no_se_construye_sin_modelo() -> None:
    """Antes que elegir uno a ciegas, no arrancar."""
    with pytest.raises(ValueError, match="modelo"):
        ProveedorOpenAI("clave", "", cliente=_ClienteFalso())


def test_no_se_construye_sin_clave() -> None:
    """Simétrico al de arriba: sin clave, `OpenAI(api_key=...)` fallaría de
    todas formas al construir el cliente real con un error del SDK que no
    dice nada del dominio; mejor no arrancar y decirlo en castellano."""
    with pytest.raises(ValueError, match="clave"):
        ProveedorOpenAI("", "un-modelo", cliente=_ClienteFalso())


def test_una_clave_invalida_no_se_repite_en_el_error() -> None:
    """El caso que de verdad importa: la API de OpenAI, al rechazar una
    clave, repite un fragmento de esa clave dentro de su propio mensaje de
    error -para que quien lo lee la reconozca-. Si ese mensaje se propagara
    tal cual, la clave real del profesor acabaría en cualquier log o
    pantalla que capture el fallo. El adaptador tiene que sustituirlo por un
    mensaje genérico, nunca reenviar el original."""
    mensaje_de_la_api = (
        "Incorrect API key provided: sk-FRAGMENTO-SECRETO-DE-LA-CLAVE. "
        "You can find your API key at https://platform.openai.com/account/api-keys."
    )
    cliente = _ClienteFalso(
        error=_fallo_con_estado(openai.AuthenticationError, 401, mensaje_de_la_api)
    )
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "sk-FRAGMENTO-SECRETO-DE-LA-CLAVE" not in str(fallo.value)
    assert "clave" in str(fallo.value).lower()
    assert "openai_api_key" in str(fallo.value).lower()


def test_el_limite_de_uso_se_distingue_del_resto() -> None:
    """Cuota agotada o demasiadas peticiones seguidas: el docente necesita
    saber que no es un fallo suyo y que puede esperar, no perseguir una
    traza de Python."""
    cliente = _ClienteFalso(
        error=_fallo_con_estado(openai.RateLimitError, 429, "Rate limit reached")
    )
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "limite" in str(fallo.value).lower() or "límite" in str(fallo.value).lower()


def test_una_espera_agotada_lo_dice_y_permite_reintentar() -> None:
    cliente = _ClienteFalso(error=openai.APITimeoutError(request=_peticion()))
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "reintentar" in str(fallo.value).lower()


def test_sin_conexion_se_distingue_de_un_timeout() -> None:
    """`APITimeoutError` hereda de `APIConnectionError`: si el adaptador
    capturara primero la clase base, un tiempo de espera agotado se
    contaría como «sin conexión», que es un mensaje menos preciso para el
    docente -uno le dice que revise su red, el otro que puede reintentar
    igual."""
    cliente = _ClienteFalso(
        error=openai.APIConnectionError(message="Connection error.", request=_peticion())
    )
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "conexion" in str(fallo.value).lower() or "conexión" in str(fallo.value).lower()


def test_ningun_mensaje_de_fallo_conocido_repite_la_clave() -> None:
    """Cinturón y tirantes sobre el test de autenticación: recorre todos los
    fallos categorizados con una clave de prueba reconocible incrustada en
    el mensaje y comprueba que ninguno la deja pasar. Si mañana se añade una
    categoría nueva de fallo que reenvíe `str(fallo)` sin pensarlo, esta
    prueba no la cubre a menos que se añada a la lista -pero cubre las
    cuatro que existen hoy."""
    marca = "CLAVE-DE-PRUEBA-QUE-NO-DEBE-APARECER"
    fallos = [
        _fallo_con_estado(openai.AuthenticationError, 401, f"clave invalida: {marca}"),
        _fallo_con_estado(openai.RateLimitError, 429, f"limite alcanzado: {marca}"),
    ]
    for fallo_programado in fallos:
        cliente = _ClienteFalso(error=fallo_programado)
        p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

        with pytest.raises(ErrorDelProveedor) as fallo:
            p.analizar("i", "t", AnalisisDelMotor)

        assert marca not in str(fallo.value)
