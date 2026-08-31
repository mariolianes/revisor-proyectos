"""El informe técnico interno, según el Anexo C del Documento Maestro.

Es la salida donde SI aparece todo: los P4, las observaciones cuya evidencia
no se pudo localizar, los reparos de la verificación, las dudas que el motor
reserva al docente y los indicios de autoría. Al alumno le llega un resumen
(Task 8); al docente, el trabajo entero. Esa es la diferencia entre las dos
salidas, y no es de formato: este documento no llega jamás al alumno, y por
eso puede ser franco donde el borrador tiene que ser prudente.

Sobre la nota, la decisión del docente del 2026-08-30 (D-015 en
`docs/decisions.md`) distingue dos verbos que antes se trataban como uno
solo: el §13 reserva al profesor *aprobar o modificar* una calificación
(`maestro#13-reservas-del-profesor`), no *calcularla*. El motor sigue sin
poder proponer nada -`backend/analisis/contrato.py` sigue con
`extra="forbid"` y sin ningún campo de nota; un motor que la devolviera
sigue siendo un error de validación, no una nota que alguien tenga que
descartar a mano-. Lo que cambia es que el propio sistema, no el motor,
calcula una *estimación interna* a partir de una rúbrica oficial cargada y
versionada (§10.1: «la nota propuesta por el sistema es interna y
provisional hasta aprobación docente»), y solo cuando esa rúbrica existe:
mientras `rubrica` y `ponderaciones` sigan `PENDIENTE_OFICIAL`
(`docs/PENDIENTE_OFICIAL.md`), `estado_nota` no puede valer otra cosa que
`pendiente_de_rubrica` -o `no_aplicable`, en las fases que nunca llevan nota
de corrección- y `nota_propuesta_sistema` se queda en `None`: R3 impide
inventar la rúbrica, así que el sistema informa de la ausencia y no la
rellena con un valor razonable. Ver `calcular_nota_interna` y
`rubrica_pendiente`.

Esa nota interna no sale nunca de este documento. `nota_final_docente` es lo
que el profesor decide en `revisar()` (`backend/api/analisis.py`), y sigue
siendo un campo del informe interno, jamás de `Devolucion`
(`backend/salidas/borrador.py`), que ya la rechaza si el motor la escribe
por su cuenta dentro de un campo de texto libre. R7 sigue cumpliéndose igual
que antes: la reserva del §13 no depende de que la operación no exista, sino
de que solo el profesor pueda escribirla, y de que nunca llegue al alumno.

El semáforo y la recomendación proponen -un estado provisional y una acción
sugerida, calibrados en `criteria/<version>/semaforo.yaml`-, y ninguno de
los dos califica. Desde D-016, el semáforo vive en dos campos:
`semaforo_propuesto`, el que calcula `_semaforo` al analizar y que no vuelve
a tocarse -es la prueba de auditoría de lo que el sistema propuso antes de
que nadie revisara nada-, y `semaforo_final_docente`, que el profesor fija
al cerrar la revisión y que `revisar()` no deja fijar con un color más
benévolo del que las observaciones que siguen aprobadas sostienen. Ver
`semaforo_por_valoraciones` y el docstring de `revisar()`.

Ningún indicio de autoría se presenta como un veredicto. `verificar()` ya le
pone a cada uno el aviso del §13 (un `Reparo` con `regla:
"autoria_es_indicio"`, incondicional, en `analisis.reparos`); este módulo no
repite ni suaviza ese aviso, se limita a no esconderlo: `indicios` y
`reparos` viajan juntos en el mismo informe.
"""

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from backend.analisis.verificacion import (
    CODIGOS_SEMAFORO,
    SEVERIDAD_SEMAFORO,
    AnalisisVerificado,
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    Reparo,
    ValoracionVerificada,
    semaforo_por_valoraciones,
)
from backend.evolucion.continuidad import ContinuidadFeedback, clasificar_continuidad
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.seleccion import SeleccionDePrioridades, seleccionar_prioridades
from backend.servicios.lectura_objetiva import FichaDeLectura

# Si `semaforo.yaml` no existiera. Los mismos textos que ese fichero declara
# hoy bajo `accion`, para que la ausencia del fichero degrade sin romper y no
# para inventar un texto que el criterio no ha fijado.
_RECOMENDACION_POR_OMISION = {
    "VERDE": "Mantener fortalezas y aplicar ajustes menores",
    "AMBAR": "Aplicar cambios antes de cerrar la siguiente fase",
    "ROJO": "Revisión docente y plan de corrección",
    "GRIS": "Resolver incidencia; no emitir juicio académico automático",
}

# `CODIGOS_SEMAFORO` y `SEVERIDAD_SEMAFORO` viven ahora en
# `backend/analisis/verificacion.py`, junto con `semaforo_por_valoraciones`
# -de ahí las importa este módulo, arriba-, porque `seleccion.py` también
# los necesita y no puede importarlos de aquí sin crear un ciclo (`informe.py`
# ya importa de `seleccion.py`). Siguen expuestos con el mismo nombre desde
# aquí -reexportados, no duplicados- para que nada que ya los importara de
# este módulo se rompa. `revisar()` (`backend/api/analisis.py`) sigue
# usando `CODIGOS_SEMAFORO` para validar `semaforo_final_docente` antes de
# aceptarlo, y `SEVERIDAD_SEMAFORO` para no dejarlo más benévolo que las
# observaciones aprobadas -GRIS queda por debajo de VERDE a propósito, ver
# D-016 en `docs/decisions.md`-.

# Los cinco estados de `Informe.estado_nota`, en el orden en que una nota los
# recorre: nace `pendiente_de_rubrica` -o `no_aplicable`, si la fase nunca
# lleva nota de corrección-, pasa a `propuesta` en cuanto hay una rúbrica de
# la que calcular un número, y termina en `aprobada` o `modificada` cuando el
# docente fija `nota_final_docente` en `revisar()`. Ningún estado se salta:
# no hay forma de llegar a `aprobada` sin pasar por `propuesta`, porque
# `revisar()` exige que exista `nota_propuesta_sistema` antes de aceptar
# cualquier decisión sobre ella. Ver D-015 en `docs/decisions.md`.
EstadoNota = Literal[
    "pendiente_de_rubrica", "propuesta", "modificada", "aprobada", "no_aplicable",
]

# Fases del §5 que nunca llevan una nota calculada por este informe. TEMA no
# puntúa como entrega (comentario de la migración inicial, tabla
# `correccion`); DEFENSA se valora a mano, en la tabla `defensa`, por el §6.5
# -«el sistema no evalúa una defensa en directo»-, así que tampoco pasa por
# aquí. Las dos siguen con `estado_nota = "no_aplicable"` aunque algún día
# exista una rúbrica: no es una ausencia de dato, es que este cálculo no les
# corresponde.
_FASES_SIN_NOTA_DE_INFORME = ("TEMA", "DEFENSA")


def rubrica_pendiente(raiz: Path) -> bool:
    """Si `rubrica` o `ponderaciones` siguen constando en
    `docs/PENDIENTE_OFICIAL.md`.

    Mismo patrón que `tools.calibrar.proteccion_datos_pendiente`: sin el
    fichero no hay forma de comprobar que se haya resuelto, así que se trata
    igual que si siguiera pendiente -la duda no se resuelve a favor de
    inventar una nota-.

    Se comprueban las dos entradas, no solo `rubrica`, porque
    `criteria/v2026-2027/ponderaciones.yaml` ya declara, con sus propias
    palabras, que bloquea `nota_final` y `nota_propuesta`
    (`bloquea: [nota_final, nota_propuesta]`): la rúbrica pone los niveles y
    los mínimos, las ponderaciones dicen cuánto pesa cada dimensión en el
    número final, y sin las dos a la vez no hay con qué calcular nada.
    """
    fichero = raiz / "docs" / "PENDIENTE_OFICIAL.md"
    if not fichero.is_file():
        return True
    texto = fichero.read_text(encoding="utf-8")
    return "**rubrica**" in texto or "**ponderaciones**" in texto


def _cargar_rubrica(raiz: Path, version: str) -> dict | None:
    """`criteria/<version>/rubrica.yaml`, si ya existe.

    Hoy no existe -está `PENDIENTE_OFICIAL`, y `rubrica_pendiente` ya lo
    comprueba antes de que esta función se llegue a invocar en
    `calcular_nota_interna`-, así que esto es la vía de entrada, no un
    fichero que este cambio cree. La forma que se espera, para cuando
    alguien complete el paso 2 de «Qué hacer cuando llegue uno»
    (`docs/PENDIENTE_OFICIAL.md`), es:

        version: v2026-2027
        ponderaciones: {D01: 0.08, D02: 0.08, ...}   # suman 1 entre las 12
        escala: {SOLIDO: 10.0, ADECUADO: 7.5, EN_DESARROLLO: 5.0, INSUFICIENTE: 2.5}
        fuente: maestro#<ancla-real>

    Ninguno de esos valores se escribe aquí ni en ningún otro fichero de este
    cambio: son ejemplos de forma, no de contenido, y anotarlos como valores
    reales sería exactamente lo que R3 prohíbe.
    """
    fichero = raiz / "criteria" / version / "rubrica.yaml"
    if not fichero.is_file():
        return None
    return yaml.safe_load(fichero.read_text(encoding="utf-8")) or None


def calcular_nota_interna(
    raiz: Path, version: str, fase: str, valoraciones: list[ValoracionVerificada],
) -> tuple[float | None, EstadoNota, str | None, dict[str, float] | None]:
    """La estimación interna de la nota, o por qué todavía no hay ninguna.

    Devuelve `(nota_propuesta_sistema, estado_nota, version_rubrica,
    ponderaciones_nota)`. Los tres últimos no son un adorno del primero: sin
    `estado_nota` un `None` no dice si es porque no hay rúbrica, porque la
    fase no lleva nota, o porque el docente todavía no ha decidido nada -y
    esas tres situaciones no se tratan igual en `revisar()`-, y sin
    `version_rubrica` ni `ponderaciones_nota` un número solo no se podría
    auditar dentro de un año: de qué rúbrica salió y con qué peso por
    dimensión.

    Solo cuenta lo que ya pasó el filtro de `evidencia_localizada` -mismo
    criterio que `_semaforo`-: una valoración cuya cita no se localizó no
    tiene detrás nada que un docente pueda comprobar, y dejarla pesar en el
    cálculo inventaría precisión donde no la hay.

    Reutilizable a propósito: `componer_informe` la llama sobre el análisis
    recién verificado, y `revisar()` (`backend/api/analisis.py`) la vuelve a
    llamar sobre las valoraciones ya resueltas por el docente -mismo patrón
    que `componer_resumen`-, para que la estimación no se quede hablando de
    observaciones que el docente acaba de descartar.
    """
    if fase in _FASES_SIN_NOTA_DE_INFORME:
        return None, "no_aplicable", None, None
    if rubrica_pendiente(raiz):
        return None, "pendiente_de_rubrica", None, None
    rubrica = _cargar_rubrica(raiz, version)
    if rubrica is None:
        return None, "pendiente_de_rubrica", None, None

    ponderaciones = rubrica.get("ponderaciones") or {}
    escala = rubrica.get("escala") or {}
    version_rubrica = rubrica.get("version") or version

    numerador = 0.0
    denominador = 0.0
    ponderaciones_usadas: dict[str, float] = {}
    for v in valoraciones:
        if not v.evidencia_localizada:
            continue
        peso = ponderaciones.get(v.dimension)
        valor = escala.get(v.nivel)
        if peso is None or valor is None:
            continue
        numerador += peso * valor
        denominador += peso
        ponderaciones_usadas[v.dimension] = peso

    if denominador <= 0:
        # La rúbrica existe, pero ninguna dimensión valorada y fiable tiene
        # peso y nivel a la vez: no hay de qué partir, así que se informa de
        # la ausencia -"pendiente_de_rubrica" en el sentido de "sin base
        # para calcular todavía"-, no se devuelve un 0 que parecería un
        # juicio sobre el trabajo.
        return None, "pendiente_de_rubrica", version_rubrica, None

    nota = round(numerador / denominador, 2)
    nota = max(0.0, min(10.0, nota))
    return nota, "propuesta", version_rubrica, ponderaciones_usadas


class Informe(BaseModel):
    """Los bloques del Anexo C que este módulo sabe componer.

    Queda fuera un bloque de la plantilla del Maestro, y no se inventa aquí.

    "Revisión del profesor" -aceptar, editar o descartar, con su nota final
    interna- ya no queda fuera del todo: `revisar()`
    (`backend/api/analisis.py`) es quien la calcula, no este módulo -de ahí
    que `nota_final_docente`, `semaforo_final_docente` y
    `motivo_modificacion_nota` empiecen siempre en `None` al componer un
    informe recién analizado-, pero el tipo sí necesita el hueco: sin él,
    `revisar()` no tendría dónde guardar la decisión del docente sobre la
    misma instancia de `Informe` que ya existe. Ver D-015 y D-016 en
    `docs/decisions.md`.

    "Continuidad" sí se compone aquí, con una salvedad importante: se
    construye desde la segunda entrega de cada alumno y fase, contra el
    último análisis guardado de la entrega anterior -no contra una
    devolución que el docente haya aprobado formalmente, porque ese estado
    no existe todavía en el flujo implementado; ver D-012 en
    `docs/decisions.md`-. Y se clasifica con lo que el sistema ya puede
    comprobar mecánicamente, no con un juicio del motor: ver
    `backend/evolucion/continuidad.py` para el porqué completo y D-012 para
    la decisión, todavía provisional, de haberlo resuelto así.
    """

    model_config = ConfigDict(extra="forbid")

    identificacion: dict[str, str]
    control_administrativo: list[str]
    # Un recuento de lo ya verificado -semáforo, prioridades, dimensiones
    # ausentes y reparos-, no la síntesis interpretativa que el §17.1 y el
    # §11.1 describen. Ver `componer_resumen` para por qué. D-011
    # (`docs/decisions.md`) explicaba el hueco que eso dejaba; D-017 lo
    # resuelve con `sintesis_provisional`, más abajo, sin tocar este campo.
    resumen: str
    # La síntesis provisional editable que pide D-017: cinco o seis líneas,
    # compuestas -no interpretadas- a partir de las mismas piezas
    # verificadas que `resumen`, para que el docente las reescriba en la
    # lectura del conjunto que el §17.1 y el §11.1 describen. Ver
    # `componer_sintesis_provisional`.
    sintesis_provisional: str
    valoraciones: list[ValoracionVerificada]
    fortalezas: list[FortalezaVerificada]
    prioridades: list[ValoracionVerificada]
    prioridades_descartadas: list[ValoracionVerificada]
    dudas: list[str]
    indicios: list[IndicioDeAutoriaVerificado]
    reparos: list[Reparo]
    dimensiones_ausentes: list[str]
    # El feedback de la entrega anterior, clasificado. Vacía en la primera
    # entrega de un alumno y fase -no hay antecedente-, y también cuando sí
    # hay antecedente pero no hay nada que clasificar (ver `continuidad_nota`
    # para cuál de los dos es). Con valor por omisión -a diferencia del
    # resto de listas de este modelo- porque no todo lo que construye un
    # `Informe` pasa por `componer_informe`: `tools/calibrar.py` y varias
    # pruebas de otras tareas montan uno directamente para lo que cada una
    # necesita comprobar, y ninguna de ellas tiene por qué conocer todavía
    # este bloque. Quien sí lo conoce -`componer_informe`- lo rellena
    # siempre, sin apoyarse en la omisión.
    continuidad: list[ContinuidadFeedback] = []
    # Por qué `continuidad` está vacía, cuando lo está: primera entrega, la
    # anterior sin análisis guardado, o la anterior sin prioridades que
    # trasladar. `None` cuando `continuidad` sí trae algo -los elementos ya
    # se explican solos- o cuando no aplica ninguno de esos tres motivos.
    continuidad_nota: str | None = None
    # El propuesto por el sistema al analizar. D-016: inalterable después de
    # ese momento -ni siquiera `revisar()` lo recalcula-, para que quede
    # como prueba de auditoría de lo que se propuso antes de que nadie
    # revisara ninguna observación.
    semaforo_propuesto: str
    # El que el docente confirma al cerrar la revisión, o `None` mientras no
    # lo haya hecho -«borrador» de cierre, no una decisión tomada-.
    # `revisar()` no permite guardar aquí un color menos severo del que
    # sostienen las observaciones que siguen aprobadas. Ver
    # `semaforo_por_valoraciones`.
    semaforo_final_docente: str | None
    recomendacion: str | None
    # La estimación interna del sistema. `None` mientras `estado_nota` sea
    # `pendiente_de_rubrica` o `no_aplicable`: no hay número que enseñar
    # cuando no hay de qué calcularlo. Ver `calcular_nota_interna`.
    nota_propuesta_sistema: float | None = Field(default=None, ge=0, le=10)
    estado_nota: EstadoNota
    # De qué rúbrica salió `nota_propuesta_sistema`, y con qué peso por
    # dimensión -`None` los dos mientras no haya rúbrica-, para que un
    # número, si llega a haberlo, se pueda auditar sin adivinar de dónde
    # salió.
    version_rubrica: str | None = None
    ponderaciones_nota: dict[str, float] | None = None
    # Lo que el docente decide en `revisar()`. `None` mientras no haya
    # fijado nada -ni aprobado la propuesta del sistema tal cual, ni
    # escrito una distinta-. Nunca lo escribe el motor: no hay ninguna vía
    # por la que un valor del motor llegue a este campo.
    nota_final_docente: float | None = Field(default=None, ge=0, le=10)
    # Opcional, y deliberadamente acotado a "qué criterio de corrección
    # pesó": ver el docstring de este mismo campo en `Revision`
    # (`backend/api/analisis.py`) para por qué no se le pide más que eso.
    motivo_modificacion_nota: str | None = None
    motor: str


def _semaforo(analisis: AnalisisVerificado) -> str:
    """El peor de los estados que se desprenden de las valoraciones fiables,
    o GRIS si no hay ninguna de la que partir.

    Solo cuentan las valoraciones cuya evidencia se localizó en el
    documento. No es un matiz menor: si el motor devolviera diez P1 y
    ninguna de sus citas existiera en el texto -las diez inventadas-, un
    semáforo calculado sobre la prioridad en bruto diría ROJO con la misma
    confianza que si las diez estuvieran bien fundadas. Aquí no se computa
    sobre lo que el motor afirmó, sino sobre lo que la verificación ya dio
    por localizable; el resto se queda en `valoraciones` -entero, para que
    el docente lo vea- pero no decide el color.

    Y si no queda ninguna valoración fiable -porque no hubo ninguna, o
    porque las que hubo no se localizaron- el resultado es GRIS, no un
    hueco. Un semáforo vacío no dice nada y obliga al docente a interpretar
    el silencio; GRIS, calibrado en `criteria/<version>/semaforo.yaml` como
    "no evaluable [...] o criterio bloqueado por falta de información", dice
    dos cosas a la vez: que el trabajo no es evaluable con lo que hay, y qué
    hacer -"resolver incidencia; no emitir juicio académico automático"-.
    Que el motor no consiguiera valorar nada verificable es exactamente esa
    incidencia. GRIS no es VERDE: uno dice "revisado y correcto", el otro
    dice "no se ha podido revisar", y confundirlos sería peor que el
    silencio que sustituyen. `dimensiones_ausentes` y `reparos` siguen ahí,
    de todos modos, para que el docente vea por qué.
    """
    return semaforo_por_valoraciones(analisis.valoraciones)


def componer_resumen(
    color: str,
    seleccion: SeleccionDePrioridades,
    dimensiones_ausentes: list[str],
    reparos: list[Reparo],
) -> str:
    """El «Resumen» del §17.1, compuesto solo con lo que ya está verificado.

    Público -sin guion bajo- a propósito: no es solo lo que
    `componer_informe` llama al analizar por primera vez.
    `backend/api/analisis.py` la reutiliza en `revisar()`, para recomponer
    este mismo campo después de que el docente acepte, edite o descarte
    observaciones -ver el docstring de `revisar()`-, sobre las piezas ya
    actualizadas de esa petición. Es una función pura -sin caché, sin
    estado, sin llamar al motor-, así que no hay ningún motivo para que
    solo exista una vía hacia ella.

    El §17.1 pide «estado general en cinco o seis líneas» y el §11.1 un
    «resumen ejecutivo del estado del proyecto»: los dos piden una síntesis
    interpretativa. Antes esta función no existía y el campo se rellenaba
    con `analisis.fortalezas[0].descripcion` -la primera fortaleza que
    hubiera, o "Sin resumen del motor." si no había ninguna-, sin pasar por
    el filtro de evidencia localizada que sí aplica `_semaforo`. Una
    fortaleza con la cita inventada podía así titular el informe entero,
    sin cita y sin la tinta de señal que sí llevan las dudas, los indicios
    y las observaciones no localizadas: el único texto de la pantalla que
    afirmaba algo sobre el trabajo del alumno sin ninguna forma de
    comprobarlo.

    Esta función no le pide al motor un resumen nuevo -eso volvería a
    dejar un campo de texto libre sin cita, que es justo el problema que se
    cierra aquí-. Compone el resumen a partir de piezas que este módulo ya
    tiene verificadas: el semáforo (que ya filtra por
    `evidencia_localizada`, ver `_semaforo`), cuántas prioridades llegan al
    alumno y de qué gravedad, cuántas quedaron fuera solo por el límite de
    la economía pedagógica, si alguna dimensión activa se quedó sin
    valorar, y si la verificación dejó reparos. Son hechos comprobables
    -cada uno se puede contrastar con otro bloque del mismo informe-, no
    una interpretación nueva.

    Y por eso mismo NO es la síntesis interpretativa que el Maestro
    describe: es un recuento, no una lectura del conjunto. Interpretar el
    «estado general» de un proyecto -no solo enumerar lo verificado, sino
    decir qué significa en su conjunto- es del tipo de juicio que el §13
    reserva al profesor. Un sistema que se detiene antes de interpretar no
    puede dar esas cinco o seis líneas sin, o bien inventar una lectura que
    nadie ha verificado, o bien pedírsela de nuevo al motor y reabrir el
    hueco de origen. Ese hueco entre lo que pide la plantilla del Anexo C y
    lo que da esta función consta en D-011 de `docs/decisions.md`, no se
    rellena aquí con una frase que sonara a síntesis sin serlo.
    """
    partes: list[str] = [f"Semáforo propuesto: {color}."]

    elegidas = seleccion.elegidas
    if elegidas:
        conteo: dict[str, int] = {}
        for v in elegidas:
            conteo[v.prioridad] = conteo.get(v.prioridad, 0) + 1
        desglose = ", ".join(
            f"{cantidad} {codigo}" for codigo, cantidad in sorted(conteo.items())
        )
        etiqueta = "prioridad verificada" if len(elegidas) == 1 else "prioridades verificadas"
        partes.append(f"{len(elegidas)} {etiqueta} para la devolución ({desglose}).")
    else:
        partes.append("Ninguna prioridad verificada para la devolución.")

    if seleccion.descartadas:
        n = len(seleccion.descartadas)
        verbo = "quedó" if n == 1 else "quedaron"
        partes.append(
            f"{n} más {verbo} fuera solo por el límite de la devolución."
        )

    if dimensiones_ausentes:
        n = len(dimensiones_ausentes)
        etiqueta = "dimensión" if n == 1 else "dimensiones"
        partes.append(
            f"{n} {etiqueta} de la fase sin valorar: "
            + ", ".join(dimensiones_ausentes) + "."
        )

    if reparos:
        n = len(reparos)
        etiqueta = "reparo" if n == 1 else "reparos"
        participio = "registrado" if n == 1 else "registrados"
        partes.append(f"{n} {etiqueta} de verificación {participio}.")

    return " ".join(partes)


def componer_sintesis_provisional(
    color: str,
    seleccion: SeleccionDePrioridades,
    fortalezas: list[FortalezaVerificada],
    dimensiones_ausentes: list[str],
    reparos: list[Reparo],
) -> str:
    """La síntesis provisional de D-017: cinco o seis líneas, rotuladas en
    pantalla como «síntesis provisional para revisión docente», que el
    docente reescribe antes de darla por buena.

    D-011 (`docs/decisions.md`) explicaba por qué `resumen` no podía ser la
    síntesis interpretativa que piden el §17.1 y el §11.1: interpretar el
    estado de un proyecto en su conjunto -no solo enumerar lo verificado,
    sino decir qué significa- es un juicio que el §13 reserva al profesor, y
    pedírselo al motor como texto libre reabriría el problema de la cita
    inventada que `resumen` cerró. D-017 no cambia esa conclusión: sigue
    sin haber ningún texto de este módulo que interprete. Lo que cambia es
    que el docente ha pedido explícitamente un borrador -provisional,
    editable, nunca cerrado en automático- sobre el que escribir esa
    lectura él mismo, en vez de partir de una pantalla en blanco. Esta
    función entrega justo eso: una línea por bloque verificado -semáforo,
    prioridades con su código y su gravedad, lo descartado por el límite,
    las fortalezas fiables, las dimensiones sin valorar y los reparos-,
    nunca una frase que el sistema no pueda sostener con otro bloque del
    mismo informe.

    Comparte piezas con `componer_resumen` a propósito -las dos parten de
    las mismas fuentes verificadas-, pero no es un duplicado: nombra las
    dimensiones y prioridades concretas, y añade las fortalezas, que
    `resumen` no cuenta. Es más material para reescribir, no una segunda
    frase que diga lo mismo con más palabras. `Informe.resumen` sigue
    existiendo, sin tocar: es el recuento fijo que permite comprobar esta
    síntesis de un vistazo, tal como pidió el docente al aceptar D-017.

    Pública, igual que `componer_resumen`: `revisar()`
    (`backend/api/analisis.py`) NO la vuelve a llamar -a diferencia de
    `resumen`, esta síntesis es del docente en cuanto se compone, y
    `revisar()` guarda tal cual el texto que él envía, editado o no-, pero
    queda pública porque es la misma clase de función pura sobre piezas ya
    verificadas, y no hay motivo para que solo `componer_informe` pueda
    llamarla.
    """
    lineas: list[str] = [f"Semáforo propuesto: {color}."]

    elegidas = seleccion.elegidas
    if elegidas:
        dims = ", ".join(f"{v.dimension} ({v.prioridad})" for v in elegidas)
        etiqueta = "prioridad verificada" if len(elegidas) == 1 else "prioridades verificadas"
        lineas.append(f"{len(elegidas)} {etiqueta} para la devolución: {dims}.")
    else:
        lineas.append("Ninguna prioridad verificada para la devolución.")

    if seleccion.descartadas:
        n = len(seleccion.descartadas)
        verbo = "quedó" if n == 1 else "quedaron"
        lineas.append(f"{n} más {verbo} fuera solo por el límite de la devolución.")

    fortalezas_fiables = [f for f in fortalezas if f.evidencia_localizada]
    if fortalezas_fiables:
        etiqueta = "fortaleza verificada" if len(fortalezas_fiables) == 1 else "fortalezas verificadas"
        lineas.append(
            f"{len(fortalezas_fiables)} {etiqueta}: "
            + "; ".join(f.descripcion for f in fortalezas_fiables) + "."
        )
    else:
        lineas.append("Ninguna fortaleza verificada.")

    if dimensiones_ausentes:
        n = len(dimensiones_ausentes)
        etiqueta = "dimensión" if n == 1 else "dimensiones"
        lineas.append(
            f"{n} {etiqueta} de la fase sin valorar: "
            + ", ".join(dimensiones_ausentes) + "."
        )

    if reparos:
        n = len(reparos)
        etiqueta = "reparo" if n == 1 else "reparos"
        participio = "registrado" if n == 1 else "registrados"
        lineas.append(f"{n} {etiqueta} de verificación {participio}.")

    return "\n".join(lineas)


def _recomendaciones_por_color(raiz: Path, version: str) -> dict[str, str]:
    """La acción calibrada de cada color, leída de `semaforo.yaml`.

    No se escribe un texto nuevo aquí: se reutiliza la columna `accion` que
    ese fichero ya declara para cada código, con su propia `fuente` al
    Documento Maestro. Inventar una redacción distinta en este módulo
    duplicaría una decisión que ya vive, versionada, en `criteria/`.
    """
    fichero = raiz / "criteria" / version / "semaforo.yaml"
    if not fichero.is_file():
        return dict(_RECOMENDACION_POR_OMISION)
    catalogo = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    return {
        c["codigo"]: c["accion"]
        for c in catalogo
        if isinstance(c, dict) and "codigo" in c and "accion" in c
    }


# Los tres motivos por los que `continuidad` puede llegar vacía sin que
# haya nada que clasificar. No son un error: son la constancia de por qué
# no hay nada que enseñar, para que el docente no lo confunda con «se
# comprobó y no había nada pendiente».
_NOTA_SIN_ENTREGA_ANTERIOR = (
    "Primera entrega de este alumno en esta fase: no hay antecedente con "
    "el que comparar."
)
_NOTA_SIN_CORRECCION_ANTERIOR = (
    "La entrega anterior no tiene un análisis guardado: no hay feedback "
    "que recuperar."
)
_NOTA_SIN_PRIORIDADES_ANTERIORES = (
    "La entrega anterior no tenía prioridades para el alumno: no hay "
    "continuidad que valorar."
)


def _continuidad(
    ficha: FichaDeLectura | None,
    hay_entrega_anterior: bool,
    prioridades_anteriores: list[ValoracionVerificada] | None,
) -> tuple[list[ContinuidadFeedback], str | None]:
    """El bloque «Continuidad» del §17.1, y por qué está vacío si lo está.

    Tres estados de entrada que `componer_informe` no puede confundir entre
    sí, y que esta función traduce cada uno a su propia nota:

    - No hay entrega anterior (`hay_entrega_anterior` falso): primera
      entrega del alumno en esta fase, tal como la instrucción del docente
      la nombra -«primera entrega: sin antecedente»-.
    - Hay entrega anterior, pero sin corrección guardada
      (`prioridades_anteriores` es `None`): nunca se analizó, o el
      análisis no llegó a completarse.
    - Hay entrega y corrección anteriores, pero sin ninguna prioridad que
      llegara a la devolución (`prioridades_anteriores` es una lista
      vacía): la fase anterior no dejó nada que continuar.

    Solo en el resto de casos hay algo que clasificar, y eso lo hace
    `clasificar_continuidad` (`backend/evolucion/continuidad.py`) a partir
    de la comparación de texto que ya trae `ficha.evolucion` y del texto de
    esta entrega -`ficha.medidas.texto_plano`-, sin volver a llamar al
    motor. Si `ficha` o `ficha.medidas` faltan -no debería ocurrir cuando
    se llega aquí desde `analizar_entrega`, pero `componer_informe` acepta
    `ficha=None` para poder probarse sin ella-, no hay texto nuevo con el
    que comparar y cada prioridad anterior queda NO_VERIFICABLE, con el
    mismo motivo que si la comparación de texto no se hubiera podido hacer.
    """
    if not hay_entrega_anterior:
        return [], _NOTA_SIN_ENTREGA_ANTERIOR
    if prioridades_anteriores is None:
        return [], _NOTA_SIN_CORRECCION_ANTERIOR
    if not prioridades_anteriores:
        return [], _NOTA_SIN_PRIORIDADES_ANTERIORES

    texto_nuevo = (
        ficha.medidas.texto_plano
        if ficha is not None and ficha.medidas is not None else ""
    )
    evolucion = ficha.evolucion if ficha is not None else None
    return clasificar_continuidad(prioridades_anteriores, texto_nuevo, evolucion), None


def componer_informe(
    raiz: Path,
    version: str,
    entrega: EntregaRegistrada,
    ficha: FichaDeLectura | None,
    analisis: AnalisisVerificado,
    motor: str,
    *,
    hay_entrega_anterior: bool = False,
    prioridades_anteriores: list[ValoracionVerificada] | None = None,
    fecha: date | None = None,
) -> Informe:
    """Compone el Anexo C. `ficha` es la lectura objetiva, o `None` si no la hay.

    Llama a `seleccionar_prioridades` una sola vez: es una función pura que
    no deja marca en `analisis`, y sus dos listas -`elegidas` y
    `descartadas`- son justo `prioridades` y `prioridades_descartadas` de
    este informe. Volver a llamarla no cambiaría el resultado, pero
    duplicaría el trabajo sin motivo.

    `hay_entrega_anterior` y `prioridades_anteriores` los resuelve quien
    llama -`analizar_entrega`, en `backend/servicios/analisis_de_entrega.py`-
    porque consultar `Almacen.anterior_de` y `Almacen.correccion_de` es
    trabajo del almacén, no de este módulo de composición. Los dos son
    palabra por omisión -sin entrega anterior, sin prioridades- para no
    romper ninguna llamada existente: la primera entrega de cualquier
    prueba que no las declare sigue componiendo un informe válido, con
    `continuidad` vacía y su nota puesta.

    `fecha` es la fecha de esta ejecución, para la cabecera del §17.1 -no la
    de recepción del archivo, que ya lleva `entrega.recibida_en` con otro
    propósito-. Por omisión, hoy: cada ejecución real imprime su propia
    fecha sin que quien llama tenga que pasarla, y las pruebas pueden fijar
    una para que la comparación no dependa del reloj.
    """
    control: list[str] = []
    if ficha is not None and ficha.medidas is not None:
        control.append(f"{ficha.medidas.total_paginas} páginas en total.")
        contadas = ficha.medidas.estructura.paginas_de_contenido
        control.append(
            f"{contadas} páginas de contenido." if contadas is not None
            else "No se ha podido contar el contenido: no se localizó el índice."
        )
        for c in ficha.comprobaciones:
            if c.veredicto == "NO_CUMPLE":
                control.append(f"{c.criterio}: {c.medido}")

    seleccion = seleccionar_prioridades(raiz, version, analisis)
    color = _semaforo(analisis)
    continuidad, continuidad_nota = _continuidad(
        ficha, hay_entrega_anterior, prioridades_anteriores
    )
    nota_propuesta, estado_nota, version_rubrica, ponderaciones_nota = (
        calcular_nota_interna(raiz, version, entrega.fase, analisis.valoraciones)
    )

    return Informe(
        identificacion={
            "alumno": entrega.codigo_alumno,
            "ciclo": entrega.ciclo,
            # Del proyecto, no de la entrega -igual que `ciclo` es del
            # alumno-, y todavía puede faltar: no existe hoy una pantalla
            # de validación de tema (§3.2) que la fije antes de la primera
            # entrega. Que falte no es un error del informe, es un dato que
            # el docente aún no ha declarado, y se dice así en vez de
            # dejar la clave ausente -una clave que falta obliga a quien
            # lee el informe a adivinar si no se pidió o si se perdió por
            # el camino-.
            "modalidad": entrega.modalidad or "No registrada",
            "fase": entrega.fase,
            "version": str(entrega.version),
            "archivo": entrega.nombre_archivo,
            "criterios": entrega.version_criterios,
            # La fecha de esta ejecución -§17.1 e instrucción del docente
            # («imprimir ciclo, modalidad, fase, fecha y versión de
            # criterios en todas las ejecuciones»)-, no una fecha del
            # trabajo del alumno.
            "fecha": (fecha or date.today()).isoformat(),
        },
        control_administrativo=control,
        resumen=componer_resumen(
            color, seleccion, analisis.dimensiones_ausentes, analisis.reparos
        ),
        sintesis_provisional=componer_sintesis_provisional(
            color, seleccion, analisis.fortalezas,
            analisis.dimensiones_ausentes, analisis.reparos,
        ),
        valoraciones=analisis.valoraciones,
        fortalezas=analisis.fortalezas,
        prioridades=seleccion.elegidas,
        prioridades_descartadas=seleccion.descartadas,
        dudas=analisis.dudas_para_el_docente,
        indicios=analisis.indicios_de_autoria,
        reparos=analisis.reparos,
        dimensiones_ausentes=analisis.dimensiones_ausentes,
        continuidad=continuidad,
        continuidad_nota=continuidad_nota,
        semaforo_propuesto=color,
        semaforo_final_docente=None,
        # `.get()` y no indexado: si `semaforo.yaml` no declarara `accion`
        # para este color -un criterio alterado a mano, por ejemplo- el
        # informe pierde la recomendación, no revienta.
        recomendacion=_recomendaciones_por_color(raiz, version).get(color),
        nota_propuesta_sistema=nota_propuesta,
        estado_nota=estado_nota,
        version_rubrica=version_rubrica,
        ponderaciones_nota=ponderaciones_nota,
        nota_final_docente=None,
        motivo_modificacion_nota=None,
        motor=motor,
    )
