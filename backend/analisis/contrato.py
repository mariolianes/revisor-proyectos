"""El formulario que el motor rellena.

El motor no redacta un informe: rellena esta estructura, y el proveedor la
valida antes de devolverla. Eso convierte «el modelo dijo algo» en «el modelo
rellenó estos campos», que es lo único que se puede comprobar.

Sobre el modo estricto del proveedor: exige que TODOS los campos sean
obligatorios y que ningún objeto admita propiedades de más. Un campo opcional
se traduce a «obligatorio que admite nulo», así que el motor no puede callarse
la prioridad de un hallazgo: tiene que decidirla, aunque sea para decir que no
tiene. Nos conviene, y por eso los opcionales se declaran de esta forma.

Que no se admitan propiedades de más tiene una consecuencia que importa: si el
motor decidiera devolver una nota, la validación la rechaza aquí, antes de que
nadie la vea. La regla R3 se cumple en el tipo, no en una comprobación que
alguien pueda olvidar.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Escala del §8.1 del Documento Maestro.
NIVELES: tuple[str, ...] = (
    "SOLIDO",
    "ADECUADO",
    "EN_DESARROLLO",
    "INSUFICIENTE",
    "NO_APLICABLE",
    "NO_VERIFICABLE",
)

# Niveles de prioridad del §7 del documento de calibración.
PRIORIDADES: tuple[str, ...] = ("P1", "P2", "P3", "P4")

# Las doce dimensiones del §8. El catálogo vive en criteria/dimensiones.yaml;
# aquí se enumeran para que el proveedor pueda validarlas, y la comprobación
# de cuáles están activas en cada fase la hace backend/analisis/verificacion.py
# leyendo los criterios.
_CODIGOS = Literal[
    "D01", "D02", "D03", "D04", "D05", "D06",
    "D07", "D08", "D09", "D10", "D11", "D12",
]


class Evidencia(BaseModel):
    """Dónde se apoya un juicio.

    `cita` es un fragmento literal del trabajo. Literal de verdad: la
    verificación lo busca en el texto, y una paráfrasis no se da por buena.

    El mínimo de longitud sale de la calibración del 2026-08-29 con los nueve
    casos del banco: el motor devolvía a veces la cita vacía, y una cadena
    vacía no es una evidencia corta, es la ausencia de evidencia. Rechazarla
    aquí -donde el formulario se valida, antes de que nadie la mire- ahorra
    tener que distinguirla después de una cita que simplemente no se localizó.
    El valor coincide con `CITA_MINIMA` de la verificación y se repite en vez
    de importarse para no acoplar el contrato a las defensas: si algún día
    dejaran de coincidir, la verificación seguiría mandando.
    """

    model_config = ConfigDict(extra="forbid")

    cita: str = Field(min_length=20)
    apartado: str


class Valoracion(BaseModel):
    """Una dimensión valorada, con su evidencia.

    No hay valoración sin evidencia: el campo es obligatorio y el §7 del
    Maestro lo exige. Un juicio que no se puede señalar en el documento no es
    un juicio, es una opinión.
    """

    model_config = ConfigDict(extra="forbid")

    dimension: _CODIGOS
    nivel: Literal[
        "SOLIDO", "ADECUADO", "EN_DESARROLLO",
        "INSUFICIENTE", "NO_APLICABLE", "NO_VERIFICABLE",
    ]
    prioridad: Literal["P1", "P2", "P3", "P4"] | None
    evidencia: Evidencia
    observacion: str


class Patron(BaseModel):
    """Uno de los patrones del §5 del calibrador, si se observa."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    descripcion: str
    evidencia: Evidencia


class Fortaleza(BaseModel):
    """Un punto fuerte del trabajo, con la evidencia que lo sostiene.

    Llega al alumno a través del borrador de devolución, y una fortaleza
    inventada es tan falsa como una carencia inventada.
    """

    model_config = ConfigDict(extra="forbid")

    descripcion: str
    evidencia: Evidencia


class IndicioDeAutoria(BaseModel):
    """Un indicio de autoría, con la evidencia que lo sostiene.

    El §13 reserva al docente la decisión sobre autoría; este campo solo
    registra el indicio. Pero un indicio sin cita es una sospecha que el
    docente no puede comprobar, y este sistema entero se sostiene sobre que
    nada llegue sin evidencia localizable en el PDF. La dimensión D12 ya
    valora la autoría por el canal que exige cita; este campo era la puerta
    de atrás.
    """

    model_config = ConfigDict(extra="forbid")

    descripcion: str
    evidencia: Evidencia


class AnalisisDelMotor(BaseModel):
    """Todo lo que el motor devuelve, antes de comprobarlo.

    Se llama «del motor» a propósito: esto es lo que dijo, no lo que damos por
    bueno. Lo segundo sale de backend/analisis/verificacion.py.

    No hay campo para la nota, y no es un olvido: `extra="forbid"` hace que
    una nota devuelta por el motor sea un error de validación.

    `dudas_para_el_docente` sigue siendo texto libre: una duda suele ser sobre
    algo que no está en el trabajo, y de una ausencia no hay cita que aportar.
    Tampoco llega al alumno. `fortalezas` e `indicios_de_autoria` sí exigen
    evidencia, por la misma razón que `valoraciones` y `patrones`.
    """

    model_config = ConfigDict(extra="forbid")

    valoraciones: list[Valoracion]
    fortalezas: list[Fortaleza]
    patrones: list[Patron]
    dudas_para_el_docente: list[str]
    indicios_de_autoria: list[IndicioDeAutoria]


def esquema_estricto() -> dict:
    """El JSON Schema que se le pasa al proveedor.

    Se usa la utilidad del propio cliente para que el esquema sea exactamente
    el que su modo estricto acepta, en vez de construirlo a mano y descubrir
    la diferencia en producción.
    """
    from openai.lib._pydantic import to_strict_json_schema

    return to_strict_json_schema(AnalisisDelMotor)
