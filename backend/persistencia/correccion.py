"""El análisis, ya guardado, y los límites de longitud sobre lo que lleva
dentro.

Vive en su propio módulo y no en `modelos.py` porque necesita `Informe` y
`Devolucion` de verdad -no solo como anotación de tipo, sino para construir
instancias- y `salidas/informe.py` ya importa `EntregaRegistrada` desde
`modelos.py`. Meter el import contrario ahí crearía un ciclo; aquí no hay
ninguno, porque nada en `salidas/` importa de este módulo.
"""

from pydantic import BaseModel, ConfigDict

from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe

# D-001, el mismo límite que impone `evidencia.fragmento` en la migración:
# una cita es un fragmento que se busca literal en el documento, y sumar
# citas sin límite reconstruiría el trabajo del alumno por partes.
LIMITE_DE_CITA = 1500

# El resto de la prosa que este módulo guarda -la que compone el propio
# sistema o el motor para explicar un juicio, no una cita textual- no tiene
# equivalente en la base de datos: son columnas `jsonb`, sin ningún CHECK.
# Sin un límite aquí, el de la cita se rodea con nada más que verbosidad: un
# motor que en vez de citar dos líneas «explicando» pegara medio párrafo del
# alumno en la observación dejaría la afirmación del §19 -que el límite de
# las citas impide reconstruir el trabajo por partes- siendo falsa, aunque
# la cita misma respetara sus 1.500 caracteres. Ninguno de estos límites
# copia el de la cita: una observación necesita más aire que una cita, y un
# borrador de devolución más aún, así que cada uno es el que tiene sentido
# para lo que guarda, no un número reutilizado por comodidad.
LIMITE_DE_RESUMEN = 500
LIMITE_DE_OBSERVACION = 800
LIMITE_DE_DUDA = 500
LIMITE_DE_REPARO = 500
LIMITE_DE_APERTURA_O_CIERRE = 600
LIMITE_DE_LINEA_DE_DEVOLUCION = 400


class TextoFueraDeLimite(ValueError):
    """Un texto de la corrección supera el límite de caracteres que le toca.

    Lleva la etiqueta, la longitud y el límite como atributos propios, no
    solo dentro del mensaje: `str(self)` compone un texto completo que
    asume que lo escribió el motor -«esto indica un fallo del motor»-,
    porque ese es el origen habitual de lo que guarda este módulo. Pero no
    es el único: `revisar()` (`backend/api/analisis.py`) guarda de nuevo la
    corrección después de aplicar una edición del docente, y ahí el texto
    largo no lo escribió el motor, lo escribió él a mano. Quien capture esta
    excepción en ese canal no debe reenviar `str(self)` -acusaría al
    docente de un fallo que no es suyo-, sino componer su propio mensaje a
    partir de `etiqueta`, `longitud` y `limite`.
    """

    def __init__(self, etiqueta: str, longitud: int, limite: int) -> None:
        self.etiqueta = etiqueta
        self.longitud = longitud
        self.limite = limite
        super().__init__(
            f"{etiqueta} tiene {longitud} caracteres; el límite para "
            f"guardarlo es {limite}. Esto indica un fallo del motor, no un "
            "dato del alumno que recortar: revisa el análisis antes de "
            "guardarlo."
        )


def _validar_longitud(texto: str, limite: int, etiqueta: str) -> None:
    if len(texto) > limite:
        raise TextoFueraDeLimite(etiqueta, len(texto), limite)


def validar_textos_acotados(
    informe: Informe, devolucion: Devolucion | None = None
) -> None:
    """Ninguna cita ni ningún bloque de prosa del análisis pasa de su límite.

    Las citas (D-001, `LIMITE_DE_CITA`) llegan por cuatro canales: las
    valoraciones, las prioridades y las prioridades descartadas -en
    principio las mismas instancias que `valoraciones`, comparten objeto por
    diseño (`analisis/verificacion.py`), y `revisar()`
    (`backend/api/analisis.py`) aplica la decisión del docente una sola vez
    por dimensión y reutiliza el mismo resultado en las tres listas, así que
    hoy no deberían divergir-, las fortalezas y los indicios de autoría. Se
    comprueban los tres por separado de todos modos, y no solo
    `valoraciones`: nada en los tipos obliga a que compartan objeto, y esta
    validación es la última defensa antes de escribir, no el sitio para
    confiar en que otra capa ya mantuvo la coherencia. Los
    patrones (`PatronVerificado`) quedan fuera a propósito y no por olvido:
    `Informe` no lleva un campo `patrones` -se descartan al componer el
    informe (`salidas/informe.py`), y solo `AnalisisVerificado`, que no se
    guarda, los conserva-, así que no hay ninguna cita de patrón que este
    módulo pueda llegar a persistir.

    El resto de la prosa -el resumen, la observación de cada valoración, las
    dudas para el docente, el detalle de cada reparo, y si se guarda una
    devolución, su apertura, su cierre y cada fortaleza y acción- lleva su
    propio límite, más generoso que el de una cita porque es prosa y no una
    transcripción literal, pero acotado igual: sin límite, un motor
    verboso podría reconstruir el trabajo del alumno por un campo que no es
    la cita, y el límite de D-001 dejaría de significar lo que el §19 del
    Documento Maestro dice que significa.

    Se llama antes de escribir nada, en los dos almacenes: un análisis con
    un texto fuera de límite no debe dejar ni una fila a medias.
    """
    for v in (*informe.valoraciones, *informe.prioridades,
              *informe.prioridades_descartadas):
        _validar_longitud(
            v.evidencia.cita, LIMITE_DE_CITA, f"La cita de {v.dimension}"
        )
        _validar_longitud(
            v.observacion, LIMITE_DE_OBSERVACION,
            f"La observación de {v.dimension}",
        )
    for f in informe.fortalezas:
        _validar_longitud(
            f.evidencia.cita, LIMITE_DE_CITA, "La cita de una fortaleza"
        )
    for i in informe.indicios:
        _validar_longitud(
            i.evidencia.cita, LIMITE_DE_CITA,
            "La cita de un indicio de autoría",
        )
    _validar_longitud(informe.resumen, LIMITE_DE_RESUMEN, "El resumen del informe")
    for duda in informe.dudas:
        _validar_longitud(duda, LIMITE_DE_DUDA, "Una duda para el docente")
    for reparo in informe.reparos:
        _validar_longitud(
            reparo.detalle, LIMITE_DE_REPARO, "El detalle de un reparo"
        )

    if devolucion is not None:
        _validar_longitud(
            devolucion.apertura, LIMITE_DE_APERTURA_O_CIERRE,
            "La apertura de la devolución",
        )
        _validar_longitud(
            devolucion.cierre, LIMITE_DE_APERTURA_O_CIERRE,
            "El cierre de la devolución",
        )
        for linea in devolucion.fortalezas:
            _validar_longitud(
                linea, LIMITE_DE_LINEA_DE_DEVOLUCION,
                "Una fortaleza de la devolución",
            )
        for linea in devolucion.acciones:
            _validar_longitud(
                linea, LIMITE_DE_LINEA_DE_DEVOLUCION,
                "Una acción de la devolución",
            )


class Correccion(BaseModel):
    """El análisis tal como queda en el almacén: sus dos salidas y el motor.

    `devolucion` puede ser `None`: es el caso de `InformeSinBorrador` -el
    informe es válido y ya está guardado, y la redacción del borrador no se
    completó-. Forzar aquí una `Devolucion` vacía confundiría ese caso con el
    que ya produce una vacía a propósito -sin fortalezas ni prioridades de
    las que redactar nada-, el mismo motivo por el que `ResultadoAnalisis` de
    la API (`backend/api/analisis.py`) hace la misma distinción.

    `aviso` es el texto que vio el docente al guardar, si lo hubo. No es un
    dato del análisis: es lo que compuso la API sobre él (por ejemplo, que el
    borrador no se pudo completar). Se guarda tal cual para que una recarga
    de la ficha diga lo mismo, sin recomponerlo a partir de una causa -la
    excepción original- que ya no existe fuera de la petición que la lanzó.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    informe: Informe
    devolucion: Devolucion | None
    motor: str
    aviso: str | None = None
