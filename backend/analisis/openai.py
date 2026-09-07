"""El proveedor real, por la API de Responses de OpenAI.

Se usa `responses.parse` y no `chat.completions.parse` por una razón que
encaja con el diseño: permite separar la instrucción -lo que se le pide, que
sale de los criterios- del contenido -el trabajo del alumno-. Además valida
la estructura contra el contrato antes de devolverla, así que una respuesta
que no encaje no llega ni a nuestro código.

El modelo no está escrito aquí. Se configura, y sin él no se construye este
proveedor: elegir uno a ciegas produciría un fallo en la primera llamada real
con un mensaje que no ayudaría a nadie.

Los imports del paquete `openai` son locales a cada función, no de módulo:
es el mismo criterio que ya sigue `contrato.esquema_estricto`, para que nada
que solo lea el puerto o el simulado tenga que cargar el SDK.

Sobre los fallos: este proveedor habla con un servicio de red, así que falla
de maneras que el simulado no tiene -clave inválida, sin conexión, el
servicio tarda demasiado, la cuota se agota, la respuesta llega cortada-.
Cada una se traduce a un mensaje en castellano que dice qué ha pasado y,
cuando aplica, qué hacer; el docente no tiene por qué leer una traza de
Python para saber si el problema es suyo (revisar la clave) o del servicio
(esperar y reintentar). No hay reintento automático propio -por eso
`max_retries=0` al construir el cliente: el SDK trae dos reintentos con
espera exponencial por omisión, y cada uno reenvía el trabajo íntegro del
alumno al proveedor otra vez, una exposición que no se multiplica sin
decidirlo-. Cuando conviene reintentar -una respuesta que no encaja,
`RespuestaNoValida`- lo señala el tipo de la excepción, y quien llama decide
si lo hace.

Ni una sola de estas rutas repite la clave en el mensaje de error, y ninguna
la deja alcanzable por ningún otro camino tampoco. La primera versión de este
módulo hacía `raise ErrorDelProveedor(mensaje) from fallo`: el mensaje salía
limpio, pero `fallo` -con el fragmento de clave que `AuthenticationError`
repite en su propio texto, para que quien lo lee la reconozca- quedaba
enganchado en `__cause__`. De ahí no lo lee `str()` ni `repr()`, pero sí
`traceback.format_exc()` y cualquier `logger.exception(...)` que capture el
error más adelante -que es justo lo que hará FastAPI, o el propio servicio,
ante un fallo que no esperaba-.

`raise ... from None` habría bastado para que `traceback` y `logging`
dejaran de imprimirlo -ambos respetan `__suppress_context__`-, pero la
referencia a `fallo` seguía viva en `excepcion.__context__`: cualquier
herramienta que la lea directamente, sin pasar por el formateo estándar
-un agregador de errores de terceros, por ejemplo-, la recuperaría igual.
Por eso este módulo no lanza la excepción de sustitución dentro del propio
`except`: la construye ahí -es donde se puede inspeccionar `fallo`- y la
lanza después, fuera de todo manejador activo, cuando ya no hay ninguna
excepción en curso a la que Python pueda engancharla. Con eso,
`__context__` sale `None` sin necesidad de suprimir nada: no hay nada que
suprimir, porque no llegó a fijarse.

Lo único que sobrevive de `fallo` es lo que registra `_registrar_diagnostico`
en el log del servidor -tipo de excepción, código de estado, identificador
de petición-, nunca el mensaje ni el cuerpo del error.

Esa misma regla protege también al `except Exception` genérico, que es el
que más importa: ahí cae todo lo que no se ha categorizado arriba -un
`BadRequestError`, un `PermissionDeniedError`, un `NotFoundError`, un
`InternalServerError`, cualquier fallo nuevo que traiga una versión futura
del SDK-, y esas excepciones tienen la misma forma que las que sí se
protegen. Una versión anterior de este módulo metía `str(fallo)` dentro del
propio mensaje de ese `except`, así que la clave podía viajar por ahí sin
necesidad de tocar `__cause__` ni `__context__` para nada: bastaba con leer
el mensaje. El genérico ya no incluye el texto original por la misma razón
que ninguno de los otros lo incluye: una rama que recibe lo que no se
anticipó no puede garantizar que ese texto esté limpio.
"""

import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.analisis.proveedor import ConsumoDeLlamada, ErrorDelProveedor, RespuestaNoValida

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

# Tiempo máximo de espera por una respuesta, en segundos. Un análisis real es
# una llamada larga -el trabajo completo del alumno, más el formulario
# entero por devolver-, así que el valor por omisión del cliente se queda
# corto antes de que el proveedor haya tenido ocasión de responder.
ESPERA = 120.0


def _registrar_diagnostico(fallo: Exception) -> None:
    """Deja en el log del servidor lo justo para perseguir un fallo raro:
    el tipo de excepción, el código de estado HTTP y el identificador de
    petición, cuando el fallo los trae -solo los de estado los traen; una
    caída de conexión o un tiempo de espera agotado no tienen respuesta que
    los contenga, y quedan como `None`-.

    Nunca el mensaje ni el cuerpo del error: ahí es exactamente donde puede
    venir un fragmento de la clave, como demuestra `AuthenticationError`.
    Ninguno de los tres datos que se registran aquí es un secreto.
    """
    logger.error(
        "ProveedorOpenAI: fallo %s (status=%s, request_id=%s)",
        type(fallo).__name__,
        getattr(fallo, "status_code", None),
        getattr(fallo, "request_id", None),
    )


def _construir_fallo(clase: type[Exception], mensaje: str, fallo: Exception) -> Exception:
    """Registra el diagnóstico y devuelve `clase(mensaje)` sin lanzarla.

    Deliberadamente no lanza: se llama desde dentro de un `except`, y una
    excepción lanzada ahí hereda `__context__` de `fallo` aunque no se
    encadene con `from fallo`. Construirla aquí y dejar que quien llama la
    lance fuera del manejador -ver `analizar`- es lo que consigue que no
    quede ninguna referencia a `fallo` colgando de la excepción resultante,
    sin depender de que algo respete `__suppress_context__`.
    """
    _registrar_diagnostico(fallo)
    return clase(mensaje)


def _consumo_de(uso) -> ConsumoDeLlamada | None:
    """El consumo de tokens de una respuesta de OpenAI, o `None` si la
    respuesta no trae `usage` -pasa con los dobles de prueba que no lo
    simulan, y en teoría con cualquier respuesta que el SDK no rellene-.

    Los tokens cacheados viven en `usage.input_tokens_details.cached_tokens`
    -la API los separa porque se facturan a otra tarifa-, y ese campo anidado
    no siempre está: se lee con `getattr` en cada nivel, sin asumir la forma
    exacta del objeto, porque este módulo no controla qué versión del SDK
    hay instalada ni cómo cambia esa forma entre versiones.
    """
    if uso is None:
        return None
    detalles = getattr(uso, "input_tokens_details", None)
    return ConsumoDeLlamada(
        tokens_entrada=getattr(uso, "input_tokens", 0) or 0,
        tokens_salida=getattr(uso, "output_tokens", 0) or 0,
        tokens_entrada_cacheados=getattr(detalles, "cached_tokens", 0) or 0,
    )


# Familias de modelos que fijan su propia temperatura y rechazan el
# parámetro. Se enumeran por prefijo y no por nombre exacto porque salen
# versiones nuevas -`o3-2025-04-16`, `o4-mini-...`- que se comportan igual.
# Si aparece una familia nueva que tampoco lo admita, se añade aquí: es
# preferible a descubrirlo con un 400 en mitad de una corrección.
#
# La lista no se deduce del nombre: se mide contra la API antes de
# escribirla. La familia `gpt-5` está partida por la mitad y no hay forma de
# adivinar por dónde -`gpt-5.2` y `gpt-5.4` aceptan `temperature`; `gpt-5.5`
# y los tres `gpt-5.6` la rechazan-, así que se enumeran los prefijos que
# fallaron de verdad y no el «gpt-5» que parecería razonable.
_SIN_TEMPERATURA = ("o1", "o3", "o4", "gpt-5.5", "gpt-5.6")

# Modelos que admiten `reasoning.effort`. Mismo criterio: medido, no
# supuesto. `gpt-4.1` responde 400 «Unsupported parameter:
# 'reasoning.effort'», así que mandarlo a todo el mundo rompería el modelo
# que el sistema usaba hasta ahora.
_CON_ESFUERZO = ("o1", "o3", "o4", "gpt-5.5", "gpt-5.6")

ESFUERZOS = ("minimal", "low", "medium", "high")


def admite_esfuerzo(modelo: str) -> bool:
    """Si a este modelo se le puede pedir cuánto quiere razonar.

    Un modelo de razonamiento decide por su cuenta cuánto piensa antes de
    contestar, y `reasoning.effort` es la única palanca para pedirle que
    piense más. Cuesta más y tarda más; a cambio, en un juicio con doce
    dimensiones y una cita por cada una, la diferencia se nota. Los modelos
    que no razonan rechazan el parámetro con un 400.
    """
    return modelo.startswith(_CON_ESFUERZO)


def admite_temperatura(modelo: str) -> bool:
    """Si a este modelo se le puede pedir `temperature=0`.

    Importa más de lo que parece. El sistema pide temperatura cero para que
    el mismo trabajo no reciba dos juicios distintos; con un modelo que no
    la admite, esa garantía desaparece y dos ejecuciones pueden dar
    resultados diferentes. No es motivo para no usarlo -un modelo de
    razonamiento puede juzgar mejor- pero sí para saberlo y comprobarlo.
    """
    return not modelo.startswith(_SIN_TEMPERATURA)


class ProveedorOpenAI:
    """Pide el análisis a OpenAI y devuelve el formulario ya validado."""

    def __init__(
        self, clave: str, modelo: str, esfuerzo: str | None = None, cliente=None
    ) -> None:
        if not clave:
            raise ValueError(
                "No hay clave de OpenAI configurada. Indícala en "
                "OPENAI_API_KEY, dentro del fichero .env; no se versiona ni "
                "sale de este equipo."
            )
        if not modelo:
            raise ValueError(
                "No hay modelo de análisis configurado. Indica cuál usar en "
                "REVISOR_MODELO_ANALISIS, dentro del fichero .env."
            )
        if esfuerzo is not None and esfuerzo not in ESFUERZOS:
            raise ValueError(
                f"«{esfuerzo}» no es un esfuerzo de razonamiento válido. "
                f"Los que admite OpenAI son: {', '.join(ESFUERZOS)}. "
                "Se indica en REVISOR_ESFUERZO_ANALISIS, dentro del .env."
            )
        if esfuerzo is not None and not admite_esfuerzo(modelo):
            raise ValueError(
                f"El modelo «{modelo}» no admite que se le pida un esfuerzo "
                "de razonamiento: responde con un error si se le manda. "
                "Quita REVISOR_ESFUERZO_ANALISIS del .env, o elige un modelo "
                "de razonamiento."
            )
        self._modelo = modelo
        self._esfuerzo = esfuerzo
        if cliente is None:
            from openai import OpenAI

            # max_retries=0: sin esto, el SDK reintenta hasta dos veces por
            # su cuenta, con espera exponencial, y cada reintento reenvía el
            # trabajo íntegro del alumno al proveedor otra vez. Es una
            # decisión de alcance -cuánto se expone y cuántas veces-, no un
            # detalle de transporte, así que no se deja en manos del valor
            # por omisión del cliente.
            cliente = OpenAI(api_key=clave, timeout=ESPERA, max_retries=0)
        self._cliente = cliente
        # El registro de consumo (`backend/servicios/analisis_de_entrega.py`)
        # necesita distinguir «se hizo una llamada real que no dejó usage
        # legible» de «no se ha hecho ninguna llamada desde que se miró por
        # última vez». `ultimo_consumo` sola no basta para eso: si se dejara
        # tal cual estaba tras un intento sin usage, un intento posterior
        # que tampoco lo trajera parecería que reutiliza el de antes.
        # `numero_de_llamadas` sube en cada intento, tenga o no éxito, así
        # que comparar su valor antes y después de una operación dice con
        # certeza cuántas llamadas reales hizo, sin depender de que
        # `ultimo_consumo` cambie.
        self.numero_de_llamadas = 0
        self.ultimo_consumo: "ConsumoDeLlamada | None" = None

    @property
    def nombre(self) -> str:
        """Queda guardado en el informe: dentro de un año importará con qué
        modelo se hizo cada análisis."""
        return f"openai:{self._modelo}"

    @property
    def modelo(self) -> str:
        """El identificador de modelo tal como lo configuró el docente, sin
        el prefijo `openai:` de `nombre`. Es la clave con la que
        `backend/analisis/precios.py` busca la tarifa vigente: la tabla de
        precios habla en el vocabulario del proveedor (`gpt-4.1`), no en el
        de este sistema (`openai:gpt-4.1`).
        """
        return self._modelo

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )

        self.numero_de_llamadas += 1
        self.ultimo_consumo = None

        # Se construye aquí dentro, si hace falta, y se lanza más abajo,
        # fuera de todo `except`: ver el porqué en el docstring del módulo
        # y en `_construir_fallo`.
        fallo_a_propagar: Exception | None = None
        respuesta = None
        try:
            respuesta = self._cliente.responses.parse(
                model=self._modelo,
                instructions=instruccion,
                input=texto,
                text_format=formato,
                # Un juicio que cambia cada vez que se pulsa no es un juicio.
                # No todos los modelos lo admiten: los de razonamiento -o3,
                # o4-mini- responden 400 «Unsupported parameter» si se les
                # manda, porque fijan su propia temperatura. Mandarlo a
                # ciegas ataba el sistema a una familia de modelos sin que
                # nada lo dijera, en un puerto que existe justamente para
                # poder cambiar de proveedor. Con esos modelos no hay forma
                # de pedir determinismo, y eso es una diferencia que el
                # docente debe conocer antes de elegir uno: ver
                # `admite_temperatura`.
                **({"temperature": 0} if admite_temperatura(self._modelo) else {}),
                # Cuánto se le pide que piense antes de contestar. Solo se
                # manda si el docente lo ha configurado: sin esto, el modelo
                # usa su valor por omisión, que no es el mismo en todos.
                **(
                    {"reasoning": {"effort": self._esfuerzo}}
                    if self._esfuerzo
                    else {}
                ),
                # El profesor lo pidió expresamente: que OpenAI no conserve
                # un objeto persistente de esta llamada en su lado. Sin
                # `store=False`, la API de Responses guarda la conversación
                # por omisión -pensada para poder encadenar turnos con
                # `previous_response_id`, algo que este sistema no hace
                # nunca-, y eso dejaría el trabajo del alumno, ya minimizado
                # o no, retenido en un servicio externo más tiempo del que
                # dura esta petición.
                store=False,
            )
        except AuthenticationError as fallo:
            fallo_a_propagar = _construir_fallo(
                ErrorDelProveedor,
                "No se ha podido obtener el análisis: la clave de OpenAI no "
                "es válida o ha caducado. Revisa OPENAI_API_KEY en el "
                "fichero .env. Por seguridad, este aviso no repite la clave.",
                fallo,
            )
        except RateLimitError as fallo:
            fallo_a_propagar = _construir_fallo(
                ErrorDelProveedor,
                "No se ha podido obtener el análisis: OpenAI ha rechazado "
                "la petición por límite de uso. Puede ser que la cuota de "
                "la cuenta se haya agotado o que se estén enviando "
                "demasiadas peticiones seguidas; espera un momento o "
                "revisa el plan de la cuenta antes de reintentar.",
                fallo,
            )
        except APITimeoutError as fallo:
            fallo_a_propagar = _construir_fallo(
                ErrorDelProveedor,
                f"No se ha podido obtener el análisis: OpenAI no ha "
                f"respondido en los {ESPERA:.0f} segundos de espera "
                "configurados. Puede ser una entrega larga o el servicio "
                "estar saturado; se puede reintentar.",
                fallo,
            )
        except APIConnectionError as fallo:
            # APITimeoutError hereda de esta, así que va antes en el orden
            # de los except: si no, un timeout se contaría como un fallo de
            # conexión y el aviso sería menos preciso.
            fallo_a_propagar = _construir_fallo(
                ErrorDelProveedor,
                "No se ha podido obtener el análisis: no hay contacto con "
                "OpenAI. Revisa la conexión a internet de este equipo e "
                "inténtalo de nuevo.",
                fallo,
            )
        except ValidationError as fallo:
            # El SDK valida el JSON que llega contra `formato` dentro de la
            # propia llamada a `.parse()`, antes de que exista
            # `output_parsed`. El caso típico es una respuesta cortada -por
            # ejemplo al agotar el límite de tokens de salida con un
            # formulario tan grande como el nuestro-: llega JSON a medias, y
            # eso no es un fallo del formulario, es el mismo caso que
            # `output_parsed is None` de más abajo. Se clasifica igual,
            # como reintentable.
            fallo_a_propagar = _construir_fallo(
                RespuestaNoValida,
                "El proveedor ha respondido, pero el contenido no se pudo "
                "interpretar como el formulario esperado -puede haberse "
                "cortado antes de completarse-. Se puede reintentar.",
                fallo,
            )
        except Exception as fallo:
            # Genérico a propósito: aquí cae todo lo que no se ha
            # categorizado arriba -un BadRequestError, un
            # PermissionDeniedError, un NotFoundError, un InternalServerError,
            # cualquier fallo nuevo del SDK-, y esas excepciones tienen la
            # misma forma que las que sí se protegen. Por eso el mensaje NO
            # incluye `str(fallo)`: una rama genérica es, por definición, la
            # que recibe lo que no se anticipó, y no hay forma de garantizar
            # que ese texto esté libre de un fragmento de la clave. El
            # detalle se queda en el log, vía `_registrar_diagnostico`, nunca
            # en lo que ve el profesor.
            fallo_a_propagar = _construir_fallo(
                ErrorDelProveedor,
                "No se ha podido obtener el análisis: ha fallado algo no "
                "previsto al hablar con OpenAI. Revisa el log del servidor "
                "para más detalle.",
                fallo,
            )

        if fallo_a_propagar is not None:
            raise fallo_a_propagar

        # El consumo se lee de la respuesta cruda, antes de mirar si
        # `output_parsed` encajó: OpenAI factura los tokens generados aunque
        # el JSON no encaje en el formulario -es justo el caso de
        # `RespuestaNoValida`, dos líneas más abajo-, así que no leer el
        # consumo aquí perdería el coste real de un intento que sí costó
        # dinero, no solo de los que tuvieron éxito.
        self.ultimo_consumo = _consumo_de(getattr(respuesta, "usage", None))

        analisis = getattr(respuesta, "output_parsed", None)
        if analisis is None:
            raise RespuestaNoValida(
                "El proveedor ha respondido, pero lo devuelto no encaja con "
                "lo que se le pidió. Se puede reintentar."
            )
        return analisis
