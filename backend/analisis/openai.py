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

from backend.analisis.proveedor import ErrorDelProveedor, RespuestaNoValida

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


class ProveedorOpenAI:
    """Pide el análisis a OpenAI y devuelve el formulario ya validado."""

    def __init__(self, clave: str, modelo: str, cliente=None) -> None:
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
        self._modelo = modelo
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

    @property
    def nombre(self) -> str:
        """Queda guardado en el informe: dentro de un año importará con qué
        modelo se hizo cada análisis."""
        return f"openai:{self._modelo}"

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )

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
                temperature=0,
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

        analisis = getattr(respuesta, "output_parsed", None)
        if analisis is None:
            raise RespuestaNoValida(
                "El proveedor ha respondido, pero lo devuelto no encaja con "
                "lo que se le pidió. Se puede reintentar."
            )
        return analisis
