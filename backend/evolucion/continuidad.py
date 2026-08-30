"""El Anexo C, bloque «Continuidad»: qué se le dijo al alumno en la fase
anterior, y qué se puede comprobar que ha hecho con ello.

El §17.1 lo pide en cuatro estados -«aplicado, parcialmente aplicado,
pendiente o no verificable», en las palabras del docente-, uno por cada
prioridad que llegó a la devolución de la entrega anterior. Clasificar eso
de verdad -¿el alumno corrigió el presupuesto que le señalamos, o solo lo
tocó por encima?- exige comparar lo que se le dijo con lo que ha hecho, y
eso es un juicio.

Había dos caminos, y ninguno era gratis:

1. Pedírselo al motor. Le entregas la observación anterior y el texto
   nuevo y le pides que diga si se aplicó. Pero eso es exactamente el tipo
   de afirmación que el resto de este sistema no se cree sin comprobar
   -`backend/analisis/verificacion.py` existe entero porque un motor puede
   inventar que algo está ahí cuando no lo está-, y aquí el motor tendría
   que juzgar un cambio entre dos documentos, no solo citar uno. No hay
   forma de verificar esa clase de afirmación con lo que ya tiene este
   sistema: sería volver a fiarse de texto libre, con menos red debajo que
   en ningún otro sitio del informe.
2. Derivarlo de lo que el sistema ya mide. `comparar()`
   (`backend/evolucion/comparacion.py`) ya calcula cuánto ha cambiado una
   entrega frente a la anterior, a base de n-gramas, sin ningún juicio
   semántico. Y `cita_localizada()`
   (`backend/analisis/verificacion.py`) ya decide, con el mismo criterio
   con el que se verifica cada cita del motor, si un fragmento exacto sigue
   estando en un texto. Ninguno de los dos entiende el trabajo; los dos
   dicen algo comprobable.

Se eligió el segundo camino. Lo que sale de él es más conservador de lo que
el docente pidió, y es importante decir exactamente por qué:

- Si el fragmento que motivó una prioridad anterior -la cita exacta,
  literal, la misma que ya pasó por `cita_localizada` al verificar aquel
  análisis- SIGUE apareciendo tal cual en la entrega nueva, hay una
  certeza mecánica: lo que se señaló no se ha tocado. Eso es PENDIENTE, y
  se puede sostener con la misma cita que ya sostenía la observación.
- Si el fragmento YA NO aparece, algo ha cambiado en ese punto exacto: se
  reescribió para corregirlo, se reescribió sin corregirlo, se movió, o se
  borró junto con otra cosa. Distinguir esos cuatro casos es exactamente el
  tipo de lectura que exige entender el contenido, no solo su presencia, y
  eso es un juicio que este módulo no tiene con qué sostener. La respuesta
  aquí es NO_VERIFICABLE, con el fragmento que ya no se encuentra a la
  vista del docente para que sea él quien lea el resto.
- Si la comparación global dice que la entrega nueva «no parece incluir el
  trabajo anterior» (`CONSERVADO_MINIMO` de `comparacion.py`), ni siquiera
  la certeza mecánica del primer punto es de fiar: con tan poco texto
  reconocible, un fragmento que no aparece puede deberse a un cambio de
  maquetación o de extracción, no a que el alumno lo haya tocado. Todo el
  bloque pasa a NO_VERIFICABLE de una vez, con el motivo global en vez de
  uno por observación.
- Si no hay nada con qué comparar -no hay entrega anterior, la anterior no
  tiene análisis guardado, la anterior no tenía prioridades, o la
  comparación de texto no se pudo hacer (ver `ficha.aviso`,
  `backend/servicios/lectura_objetiva.py`)- no hay continuidad que
  construir, y se dice cuál de esos motivos es.

APLICADO y PARCIALMENTE_APLICADO existen en el vocabulario -es el que fija
el §17.1, y el que tiene que hablar el informe- pero esta función nunca los
emite: no hay ninguna medida en este sistema, hoy, capaz de distinguir «se
corrigió» de «se rehízo sin corregirlo» sin leer y entender el trabajo. Es
una limitación deliberada, no un olvido: el docstring de
`salidas/informe.py` ya explica, para GRIS, por qué una categoría honesta
vale más que una inventada, y aquí aplica el mismo criterio. Si el sistema
llega a tener una forma verificable de afirmar que algo se aplicó -por
ejemplo, una localización por apartado que hoy no existe-, esas dos
categorías se activan sin tocar el vocabulario del informe, que ya las
declara.
"""

from pydantic import BaseModel, ConfigDict

from backend.analisis.verificacion import ValoracionVerificada, cita_localizada
from backend.evolucion.comparacion import CONSERVADO_MINIMO, Evolucion

APLICADO = "APLICADO"
PARCIALMENTE_APLICADO = "PARCIALMENTE_APLICADO"
PENDIENTE = "PENDIENTE"
NO_VERIFICABLE = "NO_VERIFICABLE"

# El vocabulario completo del §17.1, en el orden en que lo enuncia el
# docente. Las dos primeras categorías nunca las produce `clasificar`, por
# la razón que explica el docstring del módulo; se declaran aquí de todos
# modos porque son parte del contrato del bloque «Continuidad», no una
# posibilidad futura sin nombre.
ESTADOS_DE_CONTINUIDAD: tuple[str, ...] = (
    APLICADO, PARCIALMENTE_APLICADO, PENDIENTE, NO_VERIFICABLE,
)

_MOTIVO_SIN_COMPARACION = (
    "No se ha podido comparar el texto con la entrega anterior, así que no "
    "se puede saber si esto se ha corregido. Revisa el aviso de la ficha "
    "para ver por qué."
)

_MOTIVO_DEMASIADO_DISTINTA = (
    "La entrega nueva se reconoce tan poco frente a la anterior que "
    "comparar fragmento a fragmento no es de fiar: un cambio de "
    "maquetación o de extracción puede parecer, aquí, lo mismo que un "
    "cambio de contenido. No se puede saber si esto se ha corregido."
)

_MOTIVO_SIGUE_IGUAL = (
    "El fragmento que motivó esta observación sigue apareciendo igual, "
    "literal, en la entrega nueva: no se ha tocado."
)

_MOTIVO_YA_NO_APARECE = (
    "El fragmento que motivó esta observación ya no aparece igual en la "
    "entrega nueva. Algo ha cambiado en ese punto, pero el sistema no "
    "puede saber si el cambio corrige lo señalado, lo corrige solo en "
    "parte, o simplemente lo desplaza sin resolverlo: esa lectura le "
    "corresponde al docente."
)


class ContinuidadFeedback(BaseModel):
    """Una prioridad de la entrega anterior, y lo que se puede comprobar de
    ella en la entrega nueva.

    Inmutable, como los demás juicios ya verificados de este sistema
    (`ValoracionVerificada` y compañía, en `backend/analisis/verificacion.py`):
    es la constancia de una comprobación ya hecha, no un borrador que
    alguien deba poder retocar después.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: str
    prioridad: str | None
    observacion_anterior: str
    estado: str
    motivo: str


def clasificar_continuidad(
    prioridades_anteriores: list[ValoracionVerificada],
    texto_nuevo: str,
    evolucion: Evolucion | None,
) -> list[ContinuidadFeedback]:
    """Clasifica cada prioridad de la entrega anterior contra el texto de la
    entrega nueva. Ver el docstring del módulo para el criterio completo.

    `prioridades_anteriores` son las que de verdad llegaron -o habrían
    llegado- a la devolución del alumno: `Informe.prioridades` de la
    corrección anterior, ya filtradas por `seleccionar_prioridades`
    (`backend/salidas/seleccion.py`), así que ninguna de ellas tiene la
    evidencia sin localizar. Clasificar la continuidad de una observación
    que ni siquiera se pudo verificar la primera vez construiría una
    comprobación sobre una base que ya era dudosa.
    """
    if not prioridades_anteriores:
        return []

    if evolucion is None:
        return [
            ContinuidadFeedback(
                dimension=v.dimension, prioridad=v.prioridad,
                observacion_anterior=v.observacion,
                estado=NO_VERIFICABLE, motivo=_MOTIVO_SIN_COMPARACION,
            )
            for v in prioridades_anteriores
        ]

    if evolucion.proporcion_conservada < CONSERVADO_MINIMO:
        return [
            ContinuidadFeedback(
                dimension=v.dimension, prioridad=v.prioridad,
                observacion_anterior=v.observacion,
                estado=NO_VERIFICABLE, motivo=_MOTIVO_DEMASIADO_DISTINTA,
            )
            for v in prioridades_anteriores
        ]

    resultado = []
    for v in prioridades_anteriores:
        if cita_localizada(v.evidencia.cita, texto_nuevo):
            estado, motivo = PENDIENTE, _MOTIVO_SIGUE_IGUAL
        else:
            estado, motivo = NO_VERIFICABLE, _MOTIVO_YA_NO_APARECE
        resultado.append(ContinuidadFeedback(
            dimension=v.dimension, prioridad=v.prioridad,
            observacion_anterior=v.observacion, estado=estado, motivo=motivo,
        ))
    return resultado
