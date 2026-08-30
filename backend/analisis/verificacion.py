"""Lo que comprobamos nosotros antes de creernos lo que dice el motor.

Siete defensas, y ninguna delega en que el modelo se porte bien. Todas son
código de aquí, todas fallan del lado seguro, y todas se prueban contra un
motor hostil en vez de contra uno que colabora.

La primera es la que sostiene las demás: un modelo puede inventarse una frase,
pero no puede hacer que exista en el documento del alumno.

Esa primera defensa tiene un refinamiento, `recortar_cita`: cuando el motor
copia bien el principio de una cita y luego añade algo que no está -una
viñeta con contenido nuevo, un "..." que salta a otro punto del documento-,
recorta la cita al prefijo que sí es literal en vez de descartar la
observación entera. Sigue siendo la misma defensa: `cita_localizada` decide
si el recorte vale, no `recortar_cita`, que solo propone un candidato. Y
sigue fallando del lado seguro: una cita sin ningún tramo real -por ejemplo,
una que describe una ausencia en vez de citar algo que exista- no tiene
prefijo que recortar y se descarta igual que antes.

Los cuatro modelos que representan un juicio ya verificado -`ValoracionVerificada`,
`PatronVerificado`, `FortalezaVerificada` e `IndicioDeAutoriaVerificado`- son
inmutables (`frozen=True`). No es una preferencia defensiva: son la constancia de
un juicio ya emitido y comprobado, no un borrador que alguien deba poder retocar
después. La Task 8 (el borrador) y la Task 9 (el informe) construyen sus dos
salidas a partir del mismo `AnalisisVerificado`, compartiendo instancia -no una
copia- de cada valoración, patrón, fortaleza e indicio: si una de las dos pudiera
modificar un campo en el sitio, corrompería en silencio lo que la otra le enseña
al profesor. La inmutabilidad cierra esa vía sin tener que copiar nada.
"""

import re
import unicodedata
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.contrato import AnalisisDelMotor, Evidencia

# El §2.3 del calibrador: un máximo orientativo de tres o cuatro prioridades,
# no diez. El límite se usa al componer la devolución, no aquí: aquí solo se
# deja escrito de dónde sale.
PRIORIDADES_EN_LA_DEVOLUCION = 4

# Formas de afirmar la autoría que el §11 del Maestro y el punto 9 del anexo B
# del calibrador prohíben. «no_exigir» en criteria/v2026-2027/feedback.yaml lo
# llama por su nombre: «afirmaciones categóricas de autoría basadas solo en el
# estilo». Se buscan sobre el texto normalizado, así que van sin tildes.
#
# ESTO NO ES LA GARANTÍA. Es un realce: si el indicio suena a veredicto, lo
# señala aparte. Pero el castellano tiene demasiadas maneras de decir «esto lo
# escribió una IA» -verbos distintos, nombres de modelo distintos, la vuelta
# de negar al alumno y atribuir a la máquina- como para que una lista cerrada
# las agote nunca: quedaba demostrado con que "escrito por una inteligencia
# artificial" -la formulación literal de la prohibición del §13- no encajaba
# en la lista original de siete frases. Ampliarla ayuda, pero no cierra nada:
# la garantía real es que TODO indicio, lo diga como lo diga, lleva el aviso
# de verificar() antes de este bloque. Que esta lista no reconozca una
# formulación nueva no abre ningún hueco; solo pierde el realce.
_VERBOS_DE_ATRIBUCION_A_IA = (
    "generado", "escrito", "redactado", "creado", "producido", "elaborado",
    "confeccionado",
)

_NOMBRES_DE_IA = (
    "una ia", "una inteligencia artificial", "chatgpt", "gemini", "copilot",
    "claude", "un modelo de lenguaje", "un modelo de ia", "un llm",
)

# Sueltas, sin que detrás tenga que venir un nombre de la lista de arriba:
# "ha sido generado por un algoritmo" o "está generado por un sistema no
# identificado" no nombran ninguna IA conocida y son la misma afirmación.
# Estaban en la primera versión de esta defensa como frases sueltas; se
# recuperan aquí para no retroceder respecto a lo que ya se cazaba.
_CONSTRUCCIONES_DE_AUTORIA_SIN_NOMBRE = (
    "ha sido generado por",
    "esta generado por",
    "fue generado por",
)

_AFIRMACIONES_DE_AUTORIA = tuple(
    f"{verbo} por {nombre}"
    for verbo in _VERBOS_DE_ATRIBUCION_A_IA
    for nombre in _NOMBRES_DE_IA
) + _CONSTRUCCIONES_DE_AUTORIA_SIN_NOMBRE + (
    "es obra de una ia",
    "es obra de una inteligencia artificial",
    "es obra de chatgpt",
    "es obra de gemini",
    "producido integramente por",
    "no lo redacto el alumno",
    "no redacto esto",
    "no lo escribio el alumno",
    "proviene de un modelo de lenguaje",
    "no de una persona",
)

# Una cita más corta que esto no señala nada: «el» o «viable» aparecen en
# cualquier trabajo y localizarlas no demuestra que el juicio se apoye ahí.
# El umbral se mide siempre sobre la cita ya normalizada (ver cita_localizada):
# medirlo sobre la cita en bruto dejaría colar "el" seguido de espacios de
# relleno como si señalara algo.
CITA_MINIMA = 20

# La calibración del 2026-08-30 con los nueve casos del banco: el motor cita
# bien el principio y luego añade algo que no está -una viñeta con contenido
# nuevo, un "..." que salta a otro punto del documento, a veces una frase
# entera describiendo una ausencia-. Cuando eso pasa, `recortar_cita` (más
# abajo) busca el prefijo más largo de la cita que sí es literal en el
# documento, pero un prefijo cualquiera no basta: hace falta que siga siendo
# la mayor parte de lo que el motor dijo que sostenía la observación, no una
# esquirla que ya no lo hace. Un tercio es el punto de corte: por debajo, lo
# que sobrevive es menos que lo que se perdió, y quedarse con eso sería dar
# por buena una evidencia que ya no sostiene lo que decía sostener -el caso
# de manual: una cita de 300 caracteres de la que solo se localizan 21 no es
# una evidencia recortada, es casi ninguna evidencia, aunque 21 ya supere
# `CITA_MINIMA`-. Por encima de un tercio, lo que queda sigue siendo la
# mayor parte del testimonio original, aunque el motor haya añadido algo más
# después. El recorte exige las dos cosas a la vez: `CITA_MINIMA` como suelo
# absoluto (nunca cambia, y ya es el que impide una cita trivial) y esta
# proporción como suelo relativo al tamaño de la cita que el motor propuso.
PROPORCION_MINIMA_DE_RECORTE = 1 / 3

# Word parte una palabra al final de línea con un guion que no está en el
# texto real; al extraer el PDF ese guion queda pegado a un salto de línea.
# Se cierra esa costura, pero solo cuando el guion va seguido de un salto de
# línea: un guion de palabra compuesta como "coste-beneficio" no lleva detrás
# ningún "\n" y no se toca.
_GUION_DE_MAQUETACION = re.compile(r"-\s*\n\s*")

# Word sustituye las comillas rectas por las tipográficas al exportar a PDF.
# Para la comparación son la misma comilla.
_COMILLAS_TIPOGRAFICAS = str.maketrans({"“": '"', "”": '"'})


def normalizar_para_buscar(texto: str) -> str:
    """Minúsculas, sin tildes, sin artefactos de maquetación y con los
    espacios colapsados.

    Se normaliza porque el texto extraído de un PDF no es el texto original:
    trae saltos de línea donde había un espacio, parte palabras con un guion
    de maquetación al final de línea, cambia las comillas rectas por
    tipográficas y puede fundir "fi" en una sola ligadura. Y porque un modelo
    puede devolver la cita sin acentuar. Ninguna de esas diferencias significa
    que la cita sea falsa.
    """
    sin_guiones_de_maquetacion = _GUION_DE_MAQUETACION.sub("", texto)
    con_comillas_rectas = sin_guiones_de_maquetacion.translate(_COMILLAS_TIPOGRAFICAS)
    # NFKD y no NFD: además de separar la tilde de la letra para poder
    # quitarla, descompone ligaduras tipográficas como "ﬁ" en sus letras
    # sueltas "fi", que NFD deja intactas.
    descompuesto = unicodedata.normalize("NFKD", con_comillas_rectas)
    sin_tildes = "".join(
        caracter for caracter in descompuesto if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def cita_localizada(cita: str, texto: str) -> bool:
    """Si la cita aparece literalmente en el texto del trabajo.

    Literalmente quiere decir literalmente: se admite que cambien los espacios,
    las tildes y los artefactos de maquetación que introduce un PDF, y nada
    más. Una paráfrasis no se da por buena, porque el objetivo no es saber si
    el motor entendió el documento, sino si el docente puede ir a la página y
    leer eso mismo.

    El mínimo se comprueba sobre la cita ya normalizada, no sobre la cita en
    bruto: si se comprobara sobre el original, una cita trivial rellena de
    espacios bastaría para superarlo sin decir nada.
    """
    limpia = normalizar_para_buscar(cita)
    if len(limpia) < CITA_MINIMA:
        return False
    return limpia in normalizar_para_buscar(texto)


def recortar_cita(cita: str, texto: str) -> str | None:
    """El prefijo más largo de `cita` que sí es literal en `texto`, si llega.

    Para cuando `cita_localizada(cita, texto)` ya ha dado `False` pero la
    cita no es pura invención: a veces el motor copia bien el principio y
    luego añade algo que no está -una viñeta con una idea nueva, un "..."
    que salta a otro punto del documento-. Descartar la observación entera
    tira una evidencia real por lo que se añadió después; esta función
    busca cuánto de la cita se sostiene por sí sola.

    Busca por palabras completas, nunca a mitad de una: una cita que
    acabara en «el presupuesto asc» sería peor que ninguna, porque parece
    evidencia y no lo es. `cita.split()` parte por cualquier espacio en
    blanco -incluidos los saltos de línea de una cita con viñetas-, así que
    cada candidato que se prueba es siempre un número entero de palabras
    del motor, nunca un corte a medias.

    Cada candidato se comprueba con `cita_localizada`, la misma función que
    usa el resto del sistema: busca sobre lo mismo que ella compara
    -`normalizar_para_buscar`-, así que un recorte aguanta las mismas
    diferencias de tildes, espacios, guiones de maquetación y comillas
    tipográficas que una cita entera.

    Se recorre de más palabras a menos, y el primer candidato que se
    localiza ya es el más largo posible: si un candidato de N palabras
    aparece en el texto, todo prefijo suyo -con menos palabras- aparece
    también, en el mismo sitio. Por eso, en cuanto se encuentra el primero
    que se localiza, ya no hace falta seguir probando candidatos más
    cortos: si ese, el más largo posible, no llega a
    `PROPORCION_MINIMA_DE_RECORTE` de la cita original, ninguno de los que
    quedan por probar -todos más cortos que él- va a llegar tampoco.

    Devuelve `None` cuando no hay ningún candidato que valga: porque ni la
    primera palabra está en el documento -el caso de una cita inventada del
    todo, sin ningún tramo real-, o porque lo único que se localiza es una
    esquirla que ya no sostiene la observación. `verificar()` es quien
    decide qué hacer con ese candidato o con ese `None`: esta función solo
    lo propone, nunca lo da por bueno.
    """
    palabras = cita.split()
    original_normalizado = normalizar_para_buscar(cita)
    if not original_normalizado:
        return None

    for n in range(len(palabras) - 1, 0, -1):
        candidato = " ".join(palabras[:n])
        if not cita_localizada(candidato, texto):
            continue
        if len(normalizar_para_buscar(candidato)) < (
            len(original_normalizado) * PROPORCION_MINIMA_DE_RECORTE
        ):
            return None
        return candidato
    return None


class Reparo(BaseModel):
    """Algo que el motor devolvió y no se ha dado por bueno.

    Un reparo no borra nada: es la constancia de por qué un elemento se ha
    descartado o se ha marcado. El docente lo lee para entender la diferencia
    entre lo que dijo el motor y lo que el sistema le está dando por bueno.
    """

    model_config = ConfigDict(extra="forbid")

    regla: str
    detalle: str


class ValoracionVerificada(BaseModel):
    """Una valoración que ya ha pasado por las comprobaciones.

    Inmutable: es la constancia de un juicio ya verificado, no un borrador que
    un consumidor posterior pueda retocar en el sitio.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: str
    nivel: str
    prioridad: str | None
    evidencia: Evidencia
    observacion: str
    evidencia_localizada: bool


class PatronVerificado(BaseModel):
    """Un patrón del §5 del calibrador, ya con su cita comprobada.

    Inmutable, por la misma razón que `ValoracionVerificada`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    nombre: str
    descripcion: str
    evidencia: Evidencia
    evidencia_localizada: bool


class FortalezaVerificada(BaseModel):
    """Una fortaleza, ya con su cita comprobada.

    Llega al alumno a través del borrador de devolución, y una fortaleza
    inventada es tan falsa como una carencia inventada: por eso pasa por la
    misma comprobación que una valoración.

    Inmutable, por la misma razón que `ValoracionVerificada`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    descripcion: str
    evidencia: Evidencia
    evidencia_localizada: bool


class IndicioDeAutoriaVerificado(BaseModel):
    """Un indicio de autoría, ya con su cita comprobada.

    Que la cita se localice no dice nada sobre si el indicio es acertado:
    solo dice que el docente puede ir al documento y ver de dónde sale. La
    decisión sobre la autoría sigue siendo suya.

    Inmutable, por la misma razón que `ValoracionVerificada`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    descripcion: str
    evidencia: Evidencia
    evidencia_localizada: bool


class AnalisisVerificado(BaseModel):
    """Lo que damos por bueno, que no es lo mismo que lo que dijo el motor."""

    model_config = ConfigDict(extra="forbid")

    valoraciones: list[ValoracionVerificada]
    fortalezas: list[FortalezaVerificada]
    patrones: list[PatronVerificado]
    dudas_para_el_docente: list[str]
    indicios_de_autoria: list[IndicioDeAutoriaVerificado]
    dimensiones_ausentes: list[str]
    reparos: list[Reparo]


def _evidencia_o_recorte(
    evidencia: Evidencia, texto: str, contexto: str
) -> tuple[Evidencia, bool, Reparo | None]:
    """Localiza una evidencia y, si no se localiza entera, intenta recortarla.

    Es el punto donde `recortar_cita` entra en la verificación, usado por
    los cuatro canales que traen una cita -valoraciones, patrones,
    fortalezas e indicios de autoría- para no repetir la misma secuencia
    cuatro veces.

    `cita_localizada` sigue siendo la que manda, en los dos pasos: primero
    decide si la cita entera se localiza, y si no, decide -otra vez, no el
    candidato de `recortar_cita`- si el recorte propuesto se localiza. Esta
    función nunca da nada por bueno por su cuenta.

    Devuelve la evidencia que se debe conservar -la original si se localiza
    entera, o si ningún recorte llega; la recortada si un recorte se
    localiza y alcanza `PROPORCION_MINIMA_DE_RECORTE`-, si se ha dado por
    localizada, y el reparo que avisa del recorte cuando lo ha habido -para
    que el docente distinga una cita que el motor copió bien de una que el
    sistema ha tenido que acortar-. Cuando no hay recorte, ese reparo es
    `None`; sigue siendo tarea de quien llama añadir el reparo de
    `evidencia_localizable` si `localizada` acaba en `False`.

    `contexto` es la frase que identifica de qué evidencia se trata dentro
    del reparo -"de D07", "del patrón «Uso de IA sin declarar»", "de una
    fortaleza", "de un indicio de autoría"-, la misma idea que ya usa el
    reparo de `evidencia_localizable` en cada uno de los cuatro bucles.
    """
    if cita_localizada(evidencia.cita, texto):
        return evidencia, True, None

    candidato = recortar_cita(evidencia.cita, texto)
    if candidato is None or not cita_localizada(candidato, texto):
        return evidencia, False, None

    recortada = Evidencia(cita=candidato, apartado=evidencia.apartado)
    reparo = Reparo(
        regla="cita_recortada",
        detalle=(
            f"La evidencia {contexto} no se localizaba entera; se ha "
            "recortado a la parte que sí está literal en el documento. "
            f"Cita del motor: «{evidencia.cita}». "
            f"Cita usada tras el recorte: «{candidato}»."
        ),
    )
    return recortada, True, reparo


def _dimensiones_activas(raiz: Path, version: str, fase: str) -> list[str]:
    """Las dimensiones que corresponden a esa fase, según los criterios."""
    fichero = raiz / "criteria" / version / "dimensiones.yaml"
    if not fichero.is_file():
        return []
    catalogo = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    return [
        d["codigo"]
        for d in catalogo
        if isinstance(d, dict) and fase in (d.get("activa_en") or [])
    ]


def verificar(
    raiz: Path,
    version: str,
    fase: str,
    texto: str,
    analisis: AnalisisDelMotor,
) -> AnalisisVerificado:
    """Somete lo que dijo el motor a las comprobaciones que no dependen de él.

    Nada de esto lanza una excepción. Un juicio mal citado se marca, una
    dimensión que no toca se descarta, y el resto del análisis sigue siendo
    utilizable: un informe con una observación menos le sirve al docente, y
    uno que no existe porque el motor se equivocó en un campo, no.

    La cita se comprueba en los cuatro canales que la traen -valoraciones,
    patrones, fortalezas e indicios de autoría-, no solo en el primero: una
    fortaleza o un indicio sin evidencia localizable es tan poco fiable como
    una valoración sin ella, y dejar alguno sin comprobar reabriría el hueco
    que la primera defensa cierra.

    El aviso del §13 sobre un indicio de autoría es incondicional: se pone
    en todos, redactados como estén. No es una lista de frases prohibidas
    -esa lista solo da un realce, no la garantía- porque una lista nunca
    reconoce todas las formas de decir «esto lo escribió una IA», y la
    garantía no puede depender de que el motor elija una de las palabras
    que la lista sí conoce.
    """
    activas = _dimensiones_activas(raiz, version, fase)
    reparos: list[Reparo] = []
    verificadas: list[ValoracionVerificada] = []
    vistas: set[str] = set()

    for v in analisis.valoraciones:
        if v.dimension not in activas:
            reparos.append(Reparo(
                regla="dimension_activa",
                detalle=f"La dimensión {v.dimension} no está activa en la fase "
                        f"{fase} y se ha descartado.",
            ))
            continue
        if v.dimension in vistas:
            reparos.append(Reparo(
                regla="dimension_repetida",
                detalle=f"La dimensión {v.dimension} venía valorada dos veces; "
                        "se ha conservado la primera.",
            ))
            continue
        vistas.add(v.dimension)

        evidencia, localizada, reparo_recorte = _evidencia_o_recorte(
            v.evidencia, texto, f"de {v.dimension}"
        )
        if reparo_recorte is not None:
            reparos.append(reparo_recorte)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle=f"La evidencia de {v.dimension} no se ha localizado en "
                        "el documento. La observación se conserva para que la "
                        "revises, pero no pasará a la devolución.",
            ))
        verificadas.append(ValoracionVerificada(
            dimension=v.dimension,
            nivel=v.nivel,
            prioridad=v.prioridad,
            evidencia=evidencia,
            observacion=v.observacion,
            evidencia_localizada=localizada,
        ))

    patrones: list[PatronVerificado] = []
    for p in analisis.patrones:
        evidencia, localizada, reparo_recorte = _evidencia_o_recorte(
            p.evidencia, texto, f"del patrón «{p.nombre}»"
        )
        if reparo_recorte is not None:
            reparos.append(reparo_recorte)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle=f"La evidencia del patrón «{p.nombre}» no se ha "
                        "localizado en el documento; no pasará a la devolución.",
            ))
        patrones.append(PatronVerificado(
            nombre=p.nombre,
            descripcion=p.descripcion,
            evidencia=evidencia,
            evidencia_localizada=localizada,
        ))

    fortalezas: list[FortalezaVerificada] = []
    for f in analisis.fortalezas:
        evidencia, localizada, reparo_recorte = _evidencia_o_recorte(
            f.evidencia, texto, "de una fortaleza"
        )
        if reparo_recorte is not None:
            reparos.append(reparo_recorte)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle="La evidencia de una fortaleza no se ha localizado en "
                        "el documento; no pasará a la devolución.",
            ))
        fortalezas.append(FortalezaVerificada(
            descripcion=f.descripcion,
            evidencia=evidencia,
            evidencia_localizada=localizada,
        ))

    indicios_de_autoria: list[IndicioDeAutoriaVerificado] = []
    for indicio in analisis.indicios_de_autoria:
        evidencia, localizada, reparo_recorte = _evidencia_o_recorte(
            indicio.evidencia, texto, "de un indicio de autoría"
        )
        if reparo_recorte is not None:
            reparos.append(reparo_recorte)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle="La evidencia de un indicio de autoría no se ha "
                        "localizado en el documento.",
            ))

        # La garantía del §13, no un realce: TODO indicio lleva este aviso,
        # esté redactado como esté. No depende de qué palabras eligió el
        # motor -ni de que la lista de abajo las reconozca-, así que no hay
        # formulación que la evada.
        reparos.append(Reparo(
            regla="autoria_es_indicio",
            detalle="Esto es un indicio de autoría, no un veredicto: la "
                    "decisión es del profesor (§13).",
        ))

        # Realce, no garantía: si además el indicio suena a veredicto -«lo
        # escribió una IA» en vez de una observación-, se señala aparte. Que
        # esta comprobación no reconozca una formulación no certifica nada:
        # la garantía ya quedó puesta arriba. Se conserva el texto del motor
        # tal cual -reescribirlo sería el sistema decidiendo algo que no le
        # toca-, y de paso lo categórico que suene le dice al docente algo
        # útil sobre la fiabilidad del análisis.
        plano = normalizar_para_buscar(indicio.descripcion)
        if any(forma in plano for forma in _AFIRMACIONES_DE_AUTORIA):
            reparos.append(Reparo(
                regla="autoria_formulada_categoricamente",
                detalle="Además, el indicio está redactado en términos "
                        "categóricos, como un veredicto y no como una "
                        "observación.",
            ))
        indicios_de_autoria.append(IndicioDeAutoriaVerificado(
            descripcion=indicio.descripcion,
            evidencia=evidencia,
            evidencia_localizada=localizada,
        ))

    return AnalisisVerificado(
        valoraciones=verificadas,
        fortalezas=fortalezas,
        patrones=patrones,
        dudas_para_el_docente=analisis.dudas_para_el_docente,
        indicios_de_autoria=indicios_de_autoria,
        dimensiones_ausentes=[d for d in activas if d not in vistas],
        reparos=reparos,
    )
