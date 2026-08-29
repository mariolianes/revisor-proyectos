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
servicio tarda demasiado, la cuota se agota-. Cada una se traduce a un
mensaje en castellano que dice qué ha pasado y, cuando aplica, qué hacer; el
docente no tiene por qué leer una traza de Python para saber si el problema
es suyo (revisar la clave) o del servicio (esperar y reintentar). No hay
reintento automático aquí: cuando conviene reintentar -una respuesta que no
encaja, `RespuestaNoValida`- lo señala el tipo de la excepción, y quien llama
decide si lo hace.

Ni una sola de estas rutas repite la clave en el mensaje de error. El caso
que lo exige de verdad es `AuthenticationError`: la propia API de OpenAI
devuelve, dentro de su mensaje, un fragmento de la clave que se envió -para
que el que la lee la reconozca-, y esa clave puede ser la real del profesor.
Repetirla en un `ErrorDelProveedor` la dejaría en cualquier log o pantalla
que capture ese error. Por eso ese caso, y solo ese, no incluye el texto de
la excepción original.
"""

from typing import TypeVar

from pydantic import BaseModel

from backend.analisis.proveedor import ErrorDelProveedor, RespuestaNoValida

T = TypeVar("T", bound=BaseModel)

# Tiempo máximo de espera por una respuesta, en segundos. Un análisis real es
# una llamada larga -el trabajo completo del alumno, más el formulario
# entero por devolver-, así que el valor por omisión del cliente se queda
# corto antes de que el proveedor haya tenido ocasión de responder.
ESPERA = 120.0


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

            cliente = OpenAI(api_key=clave, timeout=ESPERA)
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
            # Deliberadamente sin `fallo` en el mensaje: la API de OpenAI
            # repite un fragmento de la clave enviada dentro de su propio
            # texto de error, y esa clave puede ser la real del profesor.
            raise ErrorDelProveedor(
                "No se ha podido obtener el análisis: la clave de OpenAI no "
                "es válida o ha caducado. Revisa OPENAI_API_KEY en el "
                "fichero .env. Por seguridad, este aviso no repite la clave."
            ) from fallo
        except RateLimitError as fallo:
            raise ErrorDelProveedor(
                "No se ha podido obtener el análisis: OpenAI ha rechazado "
                "la petición por límite de uso. Puede ser que la cuota de "
                "la cuenta se haya agotado o que se estén enviando "
                "demasiadas peticiones seguidas; espera un momento o "
                "revisa el plan de la cuenta antes de reintentar."
            ) from fallo
        except APITimeoutError as fallo:
            raise ErrorDelProveedor(
                f"No se ha podido obtener el análisis: OpenAI no ha "
                f"respondido en los {ESPERA:.0f} segundos de espera "
                "configurados. Puede ser una entrega larga o el servicio "
                "estar saturado; se puede reintentar."
            ) from fallo
        except APIConnectionError as fallo:
            # APITimeoutError hereda de esta, así que va antes en el orden
            # de los except: si no, un timeout se contaría como un fallo de
            # conexión y el aviso sería menos preciso.
            raise ErrorDelProveedor(
                "No se ha podido obtener el análisis: no hay contacto con "
                "OpenAI. Revisa la conexión a internet de este equipo e "
                "inténtalo de nuevo."
            ) from fallo
        except Exception as fallo:
            raise ErrorDelProveedor(
                "No se ha podido obtener el análisis del proveedor. "
                f"Motivo: {fallo}"
            ) from fallo

        analisis = getattr(respuesta, "output_parsed", None)
        if analisis is None:
            raise RespuestaNoValida(
                "El proveedor ha respondido, pero lo devuelto no encaja con "
                "lo que se le pidió. Se puede reintentar."
            )
        return analisis
