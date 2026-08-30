"""El adaptador real, contra un cliente simulado.

No se llama a OpenAI: se comprueba que se le pide lo que hay que pedirle y
que sus fallos se traducen a algo que el profesor entienda. Ningún test de
este fichero necesita red ni una clave real -los objetos `httpx.Request` y
`httpx.Response` que arman los fallos de OpenAI se construyen en memoria,
sin abrir ninguna conexión.
"""

import logging
import traceback

import httpx
import openai
import pydantic
import pytest

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.openai import (
    admite_temperatura,
)
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


def _fallo_de_json_cortado(marca: str = "") -> pydantic.ValidationError:
    """Un `ValidationError` real, del mismo tipo que lanza `responses.parse`
    dentro del SDK cuando el JSON que ha llegado no se puede interpretar
    como el formulario -el caso típico es una respuesta cortada porque el
    modelo agotó el límite de tokens de salida-.

    Si se pasa `marca`, se incrusta dentro del JSON truncado: pydantic
    repite un fragmento del valor recibido en el propio mensaje de
    `ValidationError` (comprobado contra la versión instalada), así que sirve
    para las mismas pruebas de fuga que un mensaje de OpenAI con un
    fragmento de clave -aquí la «clave» sería, en un caso real, un trozo del
    trabajo del alumno o del propio JSON del modelo, no menos sensible."""

    class _FormularioDePrueba(pydantic.BaseModel):
        campo: str

    try:
        _FormularioDePrueba.model_validate_json(f'{{"campo": "{marca}sin cerrar')
    except pydantic.ValidationError as fallo:
        return fallo
    raise AssertionError("se esperaba que el JSON incompleto fallara al validar")


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


def test_un_fallo_no_categorizado_llega_en_castellano_sin_repetir_el_original() -> None:
    """El manejador genérico -`except Exception`- es el que recibe cualquier
    fallo que no se haya anticipado arriba: un `PermissionDeniedError`, un
    `BadRequestError`, un `RuntimeError` a secas. Por eso no puede incluir
    `str(fallo)` en el mensaje: una rama genérica es, por definición, la que
    recibe lo que no se sabía que iba a pasar, y no hay forma de garantizar
    que ese texto no traiga un fragmento de la clave -tal y como demuestra
    `AuthenticationError` con su propio mensaje-. El mensaje tiene que ser
    comprensible y en castellano igualmente, remitiendo al log del servidor
    para el detalle, en vez de reenviar el original."""
    cliente = _ClienteFalso(error=ConnectionError("connection refused, clave=sk-secreta"))
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    mensaje = str(fallo.value)
    assert "no se ha podido" in mensaje.lower()
    assert "log" in mensaje.lower()
    assert "connection refused" not in mensaje
    assert "sk-secreta" not in mensaje


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
    """Cinturón y tirantes sobre los tests individuales de cada excepción:
    recorre las cinco que el adaptador clasifica -autenticación, límite de
    uso, tiempo de espera agotado, sin conexión y JSON truncado- con una
    marca reconocible incrustada en cada una, y comprueba que ninguna la
    deja pasar hasta el mensaje final.

    Antes esta prueba decía cubrir «las cuatro que existen hoy» y la lista
    solo tenía dos: un test que afirma cubrir más de lo que cubre es peor
    que no tenerlo, porque da una seguridad falsa a quien lo lea. Ahora
    tiene las cinco reales, no cuatro ni dos.

    `APITimeoutError` no admite un mensaje propio -el SDK lo fija siempre a
    "Request timed out."-, así que en su caso se comprueba que ese texto
    fijo tampoco sobrevive, en vez de una marca inyectada."""
    marca = "CLAVE-DE-PRUEBA-QUE-NO-DEBE-APARECER"
    casos = [
        (_fallo_con_estado(openai.AuthenticationError, 401, f"clave invalida: {marca}"), marca),
        (_fallo_con_estado(openai.RateLimitError, 429, f"limite alcanzado: {marca}"), marca),
        (openai.APITimeoutError(request=_peticion()), "Request timed out"),
        (
            openai.APIConnectionError(message=f"fallo de red: {marca}", request=_peticion()),
            marca,
        ),
        (_fallo_de_json_cortado(marca), marca),
    ]
    for fallo_programado, texto_que_no_debe_aparecer in casos:
        cliente = _ClienteFalso(error=fallo_programado)
        p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

        with pytest.raises(ErrorDelProveedor) as fallo:
            p.analizar("i", "t", AnalisisDelMotor)

        assert texto_que_no_debe_aparecer not in str(fallo.value)


def test_una_clave_falsa_no_aparece_por_ninguno_de_los_cinco_caminos(caplog) -> None:
    """El hallazgo crítico de la ronda de revisión: no basta con que la
    clave no aparezca en el mensaje. `raise ... from fallo` la dejaba
    enganchada en `__cause__`, y de ahí la recorren `repr()`,
    `traceback.format_exc()` y cualquier `logger.exception(...)` que
    capture el fallo más adelante -que es justo lo que hace FastAPI, o
    cualquier framework, ante un error que no esperaba-.

    Se prueban los cinco caminos exactos de la tabla de la revisión, con una
    clave falsa reconocible incrustada en el mensaje que devolvería la API
    real. Se comprueba también `__context__`, no solo `__cause__`: incluso
    con `from None`, un `raise` dentro de un `except` activo deja el
    `__context__` apuntando al fallo original -Python lo hace solo, sin que
    el código lo pida-, y una herramienta que lea esa referencia sin pasar
    por el formateo estándar de `traceback` la recuperaría igual. El
    adaptador evita el problema de raíz: construye la excepción de
    sustitución dentro del `except`, pero la lanza fuera de él, cuando ya no
    hay ninguna excepción en curso a la que Python pueda engancharla."""
    marca = "sk-CLAVE-FALSA-RECONOCIBLE-0000000000"
    mensaje_de_la_api = (
        f"Incorrect API key provided: {marca}. You can find your API key "
        "at https://platform.openai.com/account/api-keys."
    )
    cliente = _ClienteFalso(
        error=_fallo_con_estado(openai.AuthenticationError, 401, mensaje_de_la_api)
    )
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErrorDelProveedor) as info:
            p.analizar("i", "t", AnalisisDelMotor)
    excepcion = info.value

    # 1. str()
    assert marca not in str(excepcion)
    # 2. repr()
    assert marca not in repr(excepcion)
    # 3. traceback.format_exc() -equivalente aquí, sobre la excepción capturada-
    traza = "".join(
        traceback.format_exception(type(excepcion), excepcion, excepcion.__traceback__)
    )
    assert marca not in traza
    # 4. excepcion.__cause__ y excepcion.__context__: ninguno de los dos
    # debe conservar una referencia al fallo original.
    assert excepcion.__cause__ is None
    assert excepcion.__context__ is None
    # 5. logger.exception(...): lo que ya ha quedado escrito en el log del
    # servidor durante la llamada -incluye lo que registra
    # `_registrar_diagnostico`- tampoco puede contener la clave.
    assert marca not in caplog.text

    # Y, aparte, un logger.exception() posterior sobre esta misma excepción
    # -el caso real: algo más arriba la captura sin saber qué es y la
    # registra entera- tampoco puede recuperar la clave.
    registrador = logging.getLogger("prueba_de_fuga_openai")
    with caplog.at_level(logging.ERROR, logger="prueba_de_fuga_openai"):
        try:
            raise excepcion
        except ErrorDelProveedor:
            registrador.exception("fallo simulado al conectar con el proveedor")
    assert marca not in caplog.text


MARCA_NO_CATEGORIZADA = "sk-CLAVE-FALSA-EN-UN-FALLO-NO-CATEGORIZADO"


@pytest.mark.parametrize(
    "fallo_programado",
    [
        pytest.param(
            _fallo_con_estado(
                openai.PermissionDeniedError,
                403,
                f"You don't have access to this resource: {MARCA_NO_CATEGORIZADA}.",
            ),
            id="PermissionDeniedError-403",
        ),
        pytest.param(
            RuntimeError(f"fallo interno inesperado: {MARCA_NO_CATEGORIZADA}"),
            id="RuntimeError-generico",
        ),
    ],
)
def test_un_tipo_no_categorizado_no_aparece_por_ninguno_de_los_cinco_caminos(
    fallo_programado, caplog
) -> None:
    """El caso que importa después de cerrar el manejador genérico: un tipo
    que el adaptador NO clasifica -un `PermissionDeniedError`, con la misma
    forma que `AuthenticationError` y `RateLimitError`, que sí se protegen;
    o un `RuntimeError` a secas, sin ninguna forma reconocible- también
    tiene que superar los cinco caminos de la tabla, no solo el tipo que ya
    se protegía antes de esta ronda."""
    cliente = _ClienteFalso(error=fallo_programado)
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErrorDelProveedor) as info:
            p.analizar("i", "t", AnalisisDelMotor)
    excepcion = info.value

    # 1. str()
    assert MARCA_NO_CATEGORIZADA not in str(excepcion)
    # 2. repr()
    assert MARCA_NO_CATEGORIZADA not in repr(excepcion)
    # 3. traceback.format_exc()
    traza = "".join(
        traceback.format_exception(type(excepcion), excepcion, excepcion.__traceback__)
    )
    assert MARCA_NO_CATEGORIZADA not in traza
    # 4. __cause__ / __context__
    assert excepcion.__cause__ is None
    assert excepcion.__context__ is None
    # 5. logger.exception(...) posterior, simulando que algo más arriba
    # captura el fallo sin saber qué tipo es.
    assert MARCA_NO_CATEGORIZADA not in caplog.text
    registrador = logging.getLogger("prueba_de_fuga_openai_no_categorizado")
    with caplog.at_level(logging.ERROR, logger="prueba_de_fuga_openai_no_categorizado"):
        try:
            raise excepcion
        except ErrorDelProveedor:
            registrador.exception("fallo simulado, tipo no categorizado")
    assert MARCA_NO_CATEGORIZADA not in caplog.text


def test_el_diagnostico_registra_tipo_estado_y_peticion(caplog) -> None:
    """Prueba positiva, no solo negativa. Hasta ahora todo lo que fijaba el
    comportamiento de `_registrar_diagnostico` eran pruebas de que la clave
    NO aparece en el log: dejando esa función sin hacer nada, los dieciocho
    tests anteriores seguían en verde, y nada avisaba de que el mecanismo de
    diagnóstico se había roto. Esta prueba comprueba que el log SÍ lleva lo
    que hace falta para depurar un fallo raro -tipo de excepción, código de
    estado HTTP e identificador de petición-, con un `request_id` real en la
    respuesta simulada para comprobar que también se recoge cuando existe."""
    peticion = _peticion()
    respuesta = httpx.Response(
        429,
        request=peticion,
        headers={"x-request-id": "req_prueba_12345"},
        json={"error": {"message": "Rate limit reached"}},
    )
    fallo_programado = openai.RateLimitError(
        "Rate limit reached", response=respuesta, body=respuesta.json()
    )
    cliente = _ClienteFalso(error=fallo_programado)
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErrorDelProveedor):
            p.analizar("i", "t", AnalisisDelMotor)

    assert "RateLimitError" in caplog.text
    assert "429" in caplog.text
    assert "req_prueba_12345" in caplog.text


def test_una_respuesta_cortada_se_clasifica_como_reintentable() -> None:
    """El caso más probable con un formulario tan grande como el nuestro: el
    modelo agota el límite de tokens de salida y el JSON llega a medias. El
    SDK lo detecta dentro de la propia llamada a `.parse()`, antes de que
    exista `output_parsed`, así que la comprobación de `output_parsed is
    None` no llega a ejecutarse -hay que capturar el `ValidationError` del
    parseo interno y clasificarlo igual que esa comprobación."""
    cliente = _ClienteFalso(error=_fallo_de_json_cortado())
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(RespuestaNoValida) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "reintentar" in str(fallo.value).lower()


def test_el_cliente_real_no_reintenta_por_su_cuenta(monkeypatch) -> None:
    """El SDK trae `max_retries=2` por omisión, con espera exponencial. Cada
    reintento reenvía el trabajo íntegro del alumno al proveedor otra vez, y
    eso es una decisión de alcance que no se puede colar por la puerta de
    atrás del valor por omisión del cliente: tiene que pedirse a propósito,
    y aquí se pide que no la haya."""
    recibido = {}

    class _OpenAIFalso:
        def __init__(self, **kwargs) -> None:
            recibido.update(kwargs)

    monkeypatch.setattr("openai.OpenAI", _OpenAIFalso)

    ProveedorOpenAI("clave", "un-modelo")  # sin cliente inyectado: construye el real

    assert recibido["max_retries"] == 0


def test_pide_que_openai_no_conserve_la_llamada() -> None:
    """El profesor lo pidió expresamente: `store: false`, para que no queden
    objetos persistentes al otro lado."""
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["store"] is False


class _Detalles:
    def __init__(self, cached_tokens: int) -> None:
        self.cached_tokens = cached_tokens


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.input_tokens_details = _Detalles(cached_tokens)


def test_captura_el_consumo_de_una_llamada_con_exito() -> None:
    respuesta = _RespuestaFalsa(parsed=VACIO)
    respuesta.usage = _Usage(input_tokens=10290, output_tokens=2054, cached_tokens=128)
    cliente = _ClienteFalso(resultado=respuesta)
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    p.analizar("i", "t", AnalisisDelMotor)

    assert p.ultimo_consumo is not None
    assert p.ultimo_consumo.tokens_entrada == 10290
    assert p.ultimo_consumo.tokens_salida == 2054
    assert p.ultimo_consumo.tokens_entrada_cacheados == 128


def test_sin_usage_en_la_respuesta_no_hay_consumo_que_capturar() -> None:
    """Los dobles de prueba de este mismo fichero -`_RespuestaFalsa`- no
    simulan `usage`: el adaptador tiene que degradar sin reventar."""
    cliente = _ClienteFalso()
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    p.analizar("i", "t", AnalisisDelMotor)

    assert p.ultimo_consumo is None


def test_una_respuesta_que_no_encaja_tambien_deja_leer_su_consumo() -> None:
    """OpenAI factura los tokens generados aunque el JSON no encaje en el
    formulario -el caso de `RespuestaNoValida`-, así que el consumo se debe
    poder leer aunque `analizar` acabe levantando esa excepción."""
    respuesta = _RespuestaFalsa(parsed=None)
    respuesta.usage = _Usage(input_tokens=500, output_tokens=300)
    cliente = _ClienteFalso(resultado=respuesta)
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)

    assert p.ultimo_consumo is not None
    assert p.ultimo_consumo.tokens_entrada == 500


def test_numero_de_llamadas_sube_en_cada_intento_tenga_o_no_exito() -> None:
    cliente = _ClienteFalso()
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    assert p.numero_de_llamadas == 0
    p.analizar("i", "t", AnalisisDelMotor)
    assert p.numero_de_llamadas == 1

    cliente_que_falla = _ClienteFalso(error=ConnectionError("sin red"))
    q = ProveedorOpenAI("clave", "un-modelo", cliente=cliente_que_falla)
    with pytest.raises(ErrorDelProveedor):
        q.analizar("i", "t", AnalisisDelMotor)
    assert q.numero_de_llamadas == 1


def test_el_consumo_se_reinicia_en_cada_llamada_nueva() -> None:
    """Si una llamada no deja `usage` legible, no debe arrastrar el consumo
    de la llamada anterior: sería contar dos veces el mismo gasto."""
    respuesta_con_usage = _RespuestaFalsa(parsed=VACIO)
    respuesta_con_usage.usage = _Usage(input_tokens=100, output_tokens=50)
    cliente = _ClienteFalso(resultado=respuesta_con_usage)
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)
    p.analizar("i", "t", AnalisisDelMotor)
    assert p.ultimo_consumo is not None

    cliente._resultado = _RespuestaFalsa(parsed=VACIO)  # sin usage
    p.analizar("i", "t", AnalisisDelMotor)

    assert p.ultimo_consumo is None


def test_el_modelo_se_expone_sin_el_prefijo_de_nombre() -> None:
    p = ProveedorOpenAI("clave", "gpt-4.1", cliente=_ClienteFalso())

    assert p.modelo == "gpt-4.1"
    assert p.nombre == "openai:gpt-4.1"


@pytest.mark.parametrize("modelo", ["gpt-4.1", "gpt-4o", "gpt-5.6-sol"])
def test_a_los_modelos_que_la_admiten_se_les_pide_temperatura_cero(modelo) -> None:
    """Un juicio que cambia cada vez que se pulsa no es un juicio."""
    assert admite_temperatura(modelo)


@pytest.mark.parametrize("modelo", ["o3", "o3-mini", "o4-mini", "o1-pro"])
def test_a_los_modelos_de_razonamiento_no_se_les_manda_temperatura(modelo) -> None:
    """Responden 400 «Unsupported parameter» si se les manda: fijan la suya.

    Mandarla a ciegas ataba el sistema a una familia de modelos sin que nada
    lo dijera, en un puerto que existe justamente para poder cambiar de
    proveedor. Se descubrió probando `o3` de verdad, no leyendo código.
    """
    assert not admite_temperatura(modelo)


def test_el_modelo_sin_temperatura_no_la_recibe_en_la_llamada() -> None:
    """Lo que importa no es la función suelta, sino lo que de verdad se envía."""
    cliente = _ClienteFalso()

    ProveedorOpenAI(clave="sk-de-prueba", modelo="o3", cliente=cliente).analizar(
        "instrucción", "texto del trabajo", AnalisisDelMotor
    )

    assert "temperature" not in cliente.recibido
    assert cliente.recibido["model"] == "o3"
    assert cliente.recibido["store"] is False


def test_el_modelo_que_si_la_admite_la_recibe() -> None:
    cliente = _ClienteFalso()

    ProveedorOpenAI(clave="sk-de-prueba", modelo="gpt-4.1", cliente=cliente).analizar(
        "instrucción", "texto del trabajo", AnalisisDelMotor
    )

    assert cliente.recibido["temperature"] == 0
