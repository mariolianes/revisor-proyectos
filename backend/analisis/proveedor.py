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
from backend.analisis.verificacion import CITA_MINIMA, cita_localizada

T = TypeVar("T", bound=BaseModel)


class ErrorDelProveedor(Exception):
    """No se ha podido obtener un análisis.

    `mensaje_para_el_profesor` es el contrato explícito de lo que esta
    excepción puede enseñarle a un docente: por omisión es el mensaje con
    el que se construyó -que es justo lo que ya hacían las dos capas que
    la consumen (`servicios/analisis_de_entrega.py`, al componer el aviso
    de `InformeSinBorrador`, y `api/analisis.py`, al traducirla a un 503)-,
    así que declarar la propiedad no cambia ningún mensaje existente.

    Lo que sí cambia es que deja de ser una convención implícita que solo
    cumple el adaptador de OpenAI porque su docstring lo explica: el
    puerto `ProveedorAnalisis` existe para que se puedan escribir otros
    proveedores, y un proveedor nuevo que herede de esta clase sin pensar
    en su mensaje también hereda esta propiedad -no hay que acordarse de
    nada extra para que siga siendo segura-. Si algún día un proveedor
    necesita un texto distinto del que lleva la excepción -compuesto a
    partir de varios datos internos, por ejemplo, sin volcarlos todos en
    el mensaje-, sobrescribe esta propiedad en su propia subclase; eso no
    afecta a `str()` ni a nada que ya dependa de él.
    """

    @property
    def mensaje_para_el_profesor(self) -> str:
        return str(self)


class ConsumoDeLlamada(BaseModel):
    """Lo que ha costado, en tokens, la última llamada real de un proveedor.

    Solo lo rellena un proveedor que de verdad habla con un servicio de
    pago -`ProveedorOpenAI`-: no es parte del `Protocol` de abajo, y
    `ProveedorSimulado` no lo tiene, a propósito, porque no cuesta nada. Lo
    que lo lee (`backend/servicios/analisis_de_entrega.py`) lo comprueba con
    `getattr(proveedor, "ultimo_consumo", None)` y no cuenta nada cuando no
    está: la ausencia del atributo ES el dato -«esta llamada no ha costado
    dinero real»-, no un fallo que ocultar.

    Los tokens cacheados son un subconjunto de los de entrada, no una
    cantidad aparte: `tokens_entrada` es el total que cuenta la API, y
    `tokens_entrada_cacheados` la parte de ese total que se facturó a precio
    reducido por reutilizar contexto ya visto. `backend/analisis/precios.py`
    calcula el coste con esa relación.
    """

    tokens_entrada: int
    tokens_salida: int
    tokens_entrada_cacheados: int = 0


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

# Una guarda barata y temprana para el caso obvio -un texto de una frase-,
# calculada desde `CITA_MINIMA` en vez de fijada a mano: si el mínimo de
# `cita_localizada` sube en `verificacion.py`, este número sube con él.
#
# No es la garantía: se mide sobre la longitud en bruto del fragmento, y
# normalizar puede acortarlo más de lo que esta cuenta prevé -espacios
# dobles que colapsan a uno, un guion de maquetación que desaparece- porque
# esos son exactamente los artefactos que introduce un PDF real. Un texto
# que supera esta guarda puede seguir produciendo una cita que
# `cita_localizada` rechace; la garantía real es la verificación que hace
# `analisis_de_ejemplo` después de construir cada fragmento.
LONGITUD_MINIMA_DE_TEXTO = math.ceil(CITA_MINIMA / (1 - _PROPORCION_MAS_EXIGENTE))


def _citas_con_etiqueta(analisis: AnalisisDelMotor) -> list[tuple[str, str]]:
    """Todas las citas del análisis, con una etiqueta que dice de dónde sale
    cada una.

    Sirve para poder señalar, si `cita_localizada` rechaza alguna, cuál es y
    no solo que "una de las citas" ha fallado.
    """
    citas: list[tuple[str, str]] = []
    for valoracion in analisis.valoraciones:
        citas.append((f"la valoración de {valoracion.dimension}", valoracion.evidencia.cita))
    for fortaleza in analisis.fortalezas:
        citas.append(("la fortaleza", fortaleza.evidencia.cita))
    for patron in analisis.patrones:
        citas.append((f"el patrón «{patron.nombre}»", patron.evidencia.cita))
    for indicio in analisis.indicios_de_autoria:
        citas.append(("el indicio de autoría", indicio.evidencia.cita))
    return citas


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
    más corto que `LONGITUD_MINIMA_DE_TEXTO`, se falla aquí, a la cara, sin
    llegar a construir nada.

    Pero esa longitud es solo una guarda barata para el caso obvio, no la
    garantía: alcanzarla no basta si el texto tiene artefactos de PDF
    -espacios dobles, un guion de maquetación- que colapsan justo donde se
    recorta un fragmento, porque entonces la cita puede quedar por debajo de
    `CITA_MINIMA` una vez normalizada aunque el texto en bruto pareciera de
    sobra. Por eso, después de construir el análisis, cada cita se
    comprueba de verdad con `cita_localizada` contra `texto`; si alguna no
    se localiza, se falla también aquí, con un error que dice cuál es, en
    vez de devolver un análisis con apariencia correcta y una cita que la
    verificación real rechazaría más adelante.
    """
    if len(texto) < LONGITUD_MINIMA_DE_TEXTO:
        raise ValueError(
            f"analisis_de_ejemplo necesita un texto de al menos "
            f"{LONGITUD_MINIMA_DE_TEXTO} caracteres para que sus citas "
            f"superen el mínimo de {CITA_MINIMA} caracteres que exige "
            f"cita_localizada una vez normalizadas; se han recibido "
            f"{len(texto)}."
        )
    analisis = AnalisisDelMotor(
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

    for etiqueta, cita in _citas_con_etiqueta(analisis):
        if not cita_localizada(cita, texto):
            raise ValueError(
                f"El fragmento de ejemplo para {etiqueta} no se localiza en "
                f"`texto` una vez normalizado (cita: {cita!r}). El texto "
                f"recibido probablemente tiene artefactos -espacios dobles, "
                f"un guion de maquetación- que colapsan justo donde se "
                f"recorta este fragmento; prueba con un texto más largo o "
                f"sin esos artefactos en ese tramo."
            )

    return analisis
