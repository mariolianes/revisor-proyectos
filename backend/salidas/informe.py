"""El informe técnico interno, según el Anexo C del Documento Maestro.

Es la salida donde SI aparece todo: los P4, las observaciones cuya evidencia
no se pudo localizar, los reparos de la verificación, las dudas que el motor
reserva al docente y los indicios de autoría. Al alumno le llega un resumen
(Task 8); al docente, el trabajo entero. Esa es la diferencia entre las dos
salidas, y no es de formato: este documento no llega jamás al alumno, y por
eso puede ser franco donde el borrador tiene que ser prudente.

No hay campo para la nota. El Anexo C la menciona -"Semáforo, nota y
recomendación"- porque el Maestro la prevé para cuando exista la rúbrica
oficial con sus ponderaciones; mientras esas ponderaciones sigan
PENDIENTE_OFICIAL, R3 impide inventarlas y aquí no existe ni el hueco. El
semáforo y la recomendación sí tienen hueco: los dos proponen -un estado
provisional y una acción sugerida, calibrados en
`criteria/<version>/semaforo.yaml`-, y ninguno de los dos califica.

Ningún indicio de autoría se presenta como un veredicto. `verificar()` ya le
pone a cada uno el aviso del §13 (un `Reparo` con `regla:
"autoria_es_indicio"`, incondicional, en `analisis.reparos`); este módulo no
repite ni suaviza ese aviso, se limita a no esconderlo: `indicios` y
`reparos` viajan juntos en el mismo informe.
"""

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.verificacion import (
    AnalisisVerificado,
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    Reparo,
    ValoracionVerificada,
)
from backend.evolucion.continuidad import ContinuidadFeedback, clasificar_continuidad
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.seleccion import SeleccionDePrioridades, seleccionar_prioridades
from backend.servicios.lectura_objetiva import FichaDeLectura

# El §9 del calibrador, calibrado en `criteria/<version>/semaforo.yaml`: un
# P1 es carencia crítica (ROJO); un P2 o P3, mejora pendiente (AMBAR); sin
# ninguno de los tres, correcto para la fase (VERDE). GRIS -"no evaluable"-
# no sale de esta tabla: lo devuelve `_semaforo` directamente cuando no hay
# ninguna valoración fiable de la que partir. Archivo ausente, fuera de
# plazo o ilegible siguen decidiéndose en la Parte A, antes de que exista un
# `AnalisisVerificado` sobre el que razonar; este módulo solo cubre la
# incidencia que puede ver por sí mismo, que el motor no consiguió valorar
# nada verificable, y la nombra con el mismo código GRIS.
_SEMAFORO_POR_PRIORIDAD = {"P1": "ROJO", "P2": "AMBAR", "P3": "AMBAR"}

# Si `semaforo.yaml` no existiera. Los mismos textos que ese fichero declara
# hoy bajo `accion`, para que la ausencia del fichero degrade sin romper y no
# para inventar un texto que el criterio no ha fijado.
_RECOMENDACION_POR_OMISION = {
    "VERDE": "Mantener fortalezas y aplicar ajustes menores",
    "AMBAR": "Aplicar cambios antes de cerrar la siguiente fase",
    "ROJO": "Revisión docente y plan de corrección",
    "GRIS": "Resolver incidencia; no emitir juicio académico automático",
}


class Informe(BaseModel):
    """Los bloques del Anexo C que este módulo sabe componer.

    Queda fuera un bloque de la plantilla del Maestro, y no se inventa aquí.

    "Revisión del profesor" -aceptar, editar o descartar, con su nota final
    interna- no es un dato que preceda al informe, es el resultado de que
    el docente lo use. No hay ningún valor de ese bloque que este módulo
    pudiera calcular por sí mismo, ni ahora ni con más datos.

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
    # §11.1 describen. Ver `componer_resumen` para por qué, y D-011 en
    # `docs/decisions.md` para el hueco que eso deja.
    resumen: str
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
    semaforo: str
    recomendacion: str | None
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
    fiables = [v for v in analisis.valoraciones if v.evidencia_localizada]
    if not fiables:
        return "GRIS"
    for codigo in ("P1", "P2", "P3"):
        if any(v.prioridad == codigo for v in fiables):
            return _SEMAFORO_POR_PRIORIDAD[codigo]
    return "VERDE"


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
        semaforo=color,
        # `.get()` y no indexado: si `semaforo.yaml` no declarara `accion`
        # para este color -un criterio alterado a mano, por ejemplo- el
        # informe pierde la recomendación, no revienta.
        recomendacion=_recomendaciones_por_color(raiz, version).get(color),
        motor=motor,
    )
