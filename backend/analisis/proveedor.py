"""De dónde sale el juicio. El puerto y el proveedor simulado.

Mismo patrón que el almacén de la Parte A: el sistema no depende de quién
responde. Y por el mismo motivo, el simulado no es un doble de pruebas: es lo
que corre mientras no haya clave configurada, para que el flujo se pueda
recorrer entero sin gastar dinero ni enviar el trabajo de nadie a ninguna
parte.

`nombre` existe porque el frontend lo enseña. Un análisis hecho con el
proveedor simulado no es un análisis, y el docente tiene que saberlo antes de
apoyarse en él.

El puerto es genérico en el formulario que se pide (`formato: type[T]`), no
solo en la respuesta de análisis: la misma conversación con el mismo
proveedor sirve para pedir el análisis de las dimensiones y, más adelante,
para pedir la redacción del borrador de devolución, que es otro formulario
distinto. Partir el puerto en un método por formulario habría obligado a cada
implementación futura -el adaptador de OpenAI- a repetir la misma lógica de
llamada y de reintento dos veces.
"""

import math
from typing import Protocol, TypeVar

from pydantic import BaseModel

from backend.analisis.contrato import (
    AnalisisDelMotor,
    Evidencia,
    Fortaleza,
    IndicioDeAutoria,
    Patron,
    Valoracion,
)
from backend.analisis.verificacion import CITA_MINIMA

T = TypeVar("T", bound=BaseModel)


class ErrorDelProveedor(Exception):
    """No se ha podido obtener un análisis."""


class RespuestaNoValida(ErrorDelProveedor):
    """El proveedor respondió, pero lo devuelto no encaja en el formulario.

    Se distingue del resto porque es el único fallo que merece un reintento:
    es el más común y el más barato de resolver.
    """


class ProveedorAnalisis(Protocol):
    """Lo que cualquier proveedor tiene que saber hacer.

    `formato` es el modelo que se espera de vuelta. El puerto es genérico
    porque a lo largo del flujo se le piden formularios distintos: el
    análisis de las dimensiones y, en una tarea posterior, la redacción de la
    devolución. Es la misma conversación con el mismo proveedor.
    """

    @property
    def nombre(self) -> str: ...

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T: ...


class ProveedorSimulado:
    """Devuelve lo que se le haya programado, en orden.

    Guarda lo que se le pidió en `llamadas`, que es como los tests de la
    instrucción comprueban que lo enviado era lo correcto sin tener que
    inspeccionar la construcción del mensaje por dentro.
    """

    def __init__(
        self,
        respuestas: list[BaseModel] | None = None,
        fallos: list[Exception] | None = None,
    ) -> None:
        self._respuestas = list(respuestas or [])
        self._fallos = list(fallos or [])
        self.llamadas: list[tuple[str, str]] = []

    @property
    def nombre(self) -> str:
        return "simulado"

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T:
        self.llamadas.append((instruccion, texto))
        if self._fallos:
            raise self._fallos.pop(0)
        assert self._respuestas, (
            "El proveedor simulado se ha quedado sin respuestas programadas. "
            "Si esperabas otra llamada, añádela al construirlo."
        )
        return self._respuestas.pop(0)

    @classmethod
    def desde_texto(cls, texto: str) -> "ProveedorSimulado":
        """Un proveedor simulado programado con un análisis de ejemplo sobre
        `texto`.

        Existe para las tareas siguientes -salidas, persistencia, pantalla de
        revisión-, que necesitan poder recorrer el camino feliz entero sin
        escribir a mano un `AnalisisDelMotor` cada vez y sin arriesgarse a que
        sus citas sean inventadas: al construirse a partir del texto real, un
        análisis de ejemplo supera `cita_localizada` sin trampa.
        """
        return cls(respuestas=[analisis_de_ejemplo(texto)])


def _fragmento_literal(texto: str, proporcion: float, longitud: int = 80) -> str:
    """Un fragmento literal de `texto`, tomado desde la posición relativa
    `proporcion` (entre 0 y 1) y recortado a `longitud` caracteres.

    Determinista: la misma entrada produce siempre el mismo fragmento, porque
    los tests de las tareas siguientes no pueden depender de un dato que
    cambie entre ejecuciones. Y literal: no se toca ni una letra, porque es
    lo único que garantiza que `cita_localizada` lo encuentre después en el
    mismo `texto` del que salió.
    """
    inicio = int(len(texto) * proporcion)
    return texto[inicio : inicio + longitud]


# La proporción más alta que usa `analisis_de_ejemplo` (ver la última llamada
# a `_fragmento_literal` dentro de la función): es la que menos texto deja
# detrás del punto de corte, así que es la que fija cuánto tiene que medir
# `texto` como mínimo.
_PROPORCION_MAS_EXIGENTE = 0.85

# La longitud mínima de `texto` que garantiza que ese fragmento más exigente
# supere `CITA_MINIMA`. Se calcula, no se fija a mano: si `CITA_MINIMA` sube
# en `verificacion.py`, este número tiene que subir con él y no quedarse
# mintiendo. La cota es conservadora a propósito -se mide sobre la longitud
# en bruto del fragmento, no sobre su versión normalizada-, porque normalizar
# solo puede acortarlo (colapsa espacios, quita tildes) o dejarlo igual.
LONGITUD_MINIMA_DE_TEXTO = math.ceil(CITA_MINIMA / (1 - _PROPORCION_MAS_EXIGENTE))


def analisis_de_ejemplo(texto: str) -> AnalisisDelMotor:
    """Un `AnalisisDelMotor` completo cuyas citas existen literalmente en
    `texto`.

    No es un análisis de verdad: es un análisis con forma de análisis, para
    que las tareas siguientes puedan probarse contra un caso de éxito sin
    depender de una llamada real a ningún proveedor. Las citas son
    fragmentos tomados directamente de `texto`, así que no hace falta
    inventar nada para que superen `cita_localizada`: se recortan, no se
    redactan.

    `texto` debe tener una longitud razonable -la de un documento real, no la
    de una frase suelta-, porque los fragmentos se toman en distintos puntos
    de su extensión para simular evidencia repartida por el trabajo. Si es
    más corto que `LONGITUD_MINIMA_DE_TEXTO`, se falla aquí, a la cara: sin
    esta comprobación, quien escriba un texto de prueba corto en una tarea
    posterior obtendría un análisis con apariencia correcta cuyas citas
    `cita_localizada` rechazaría más adelante, y perseguiría el fallo en la
    defensa en vez de en el texto de prueba que lo origina.
    """
    if len(texto) < LONGITUD_MINIMA_DE_TEXTO:
        raise ValueError(
            f"analisis_de_ejemplo necesita un texto de al menos "
            f"{LONGITUD_MINIMA_DE_TEXTO} caracteres para que sus citas "
            f"superen el mínimo de {CITA_MINIMA} caracteres que exige "
            f"cita_localizada una vez normalizadas; se han recibido "
            f"{len(texto)}."
        )
    return AnalisisDelMotor(
        valoraciones=[
            Valoracion(
                dimension="D01",
                nivel="ADECUADO",
                prioridad=None,
                evidencia=Evidencia(
                    cita=_fragmento_literal(texto, 0.0),
                    apartado="Introducción",
                ),
                observacion=(
                    "Ejemplo simulado: la introducción sitúa el proyecto con "
                    "claridad."
                ),
            ),
            Valoracion(
                dimension="D05",
                nivel="EN_DESARROLLO",
                prioridad="P3",
                evidencia=Evidencia(
                    cita=_fragmento_literal(texto, 0.3),
                    apartado="Desarrollo",
                ),
                observacion=(
                    "Ejemplo simulado: el desarrollo podría precisar mejor "
                    "este punto."
                ),
            ),
        ],
        fortalezas=[
            Fortaleza(
                descripcion=(
                    "Ejemplo simulado: el trabajo mantiene un hilo "
                    "argumental claro entre apartados."
                ),
                evidencia=Evidencia(
                    cita=_fragmento_literal(texto, 0.5),
                    apartado="Desarrollo",
                ),
            ),
        ],
        patrones=[
            Patron(
                nombre="Patrón de ejemplo",
                descripcion=(
                    "Patrón simulado para probar el flujo sin motor real."
                ),
                evidencia=Evidencia(
                    cita=_fragmento_literal(texto, 0.65),
                    apartado="Desarrollo",
                ),
            ),
        ],
        dudas_para_el_docente=[
            "Ejemplo simulado: conviene confirmar con el alumno el alcance "
            "real del proyecto.",
        ],
        indicios_de_autoria=[
            IndicioDeAutoria(
                descripcion=(
                    "Ejemplo simulado: el registro del texto cambia entre "
                    "apartados."
                ),
                evidencia=Evidencia(
                    cita=_fragmento_literal(texto, 0.85),
                    apartado="Conclusión",
                ),
            ),
        ],
    )
