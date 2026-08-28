"""Lo que comprobamos nosotros antes de creernos lo que dice el motor.

Siete defensas, y ninguna delega en que el modelo se porte bien. Todas son
código de aquí, todas fallan del lado seguro, y todas se prueban contra un
motor hostil en vez de contra uno que colabora.

La primera es la que sostiene las demás: un modelo puede inventarse una frase,
pero no puede hacer que exista en el documento del alumno.
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

_AFIRMACIONES_DE_AUTORIA = tuple(
    f"{verbo} por {nombre}"
    for verbo in _VERBOS_DE_ATRIBUCION_A_IA
    for nombre in _NOMBRES_DE_IA
) + (
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
    """Una valoración que ya ha pasado por las comprobaciones."""

    model_config = ConfigDict(extra="forbid")

    dimension: str
    nivel: str
    prioridad: str | None
    evidencia: Evidencia
    observacion: str
    evidencia_localizada: bool


class PatronVerificado(BaseModel):
    """Un patrón del §5 del calibrador, ya con su cita comprobada."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    descripcion: str
    evidencia: Evidencia
    evidencia_localizada: bool


class FortalezaVerificada(BaseModel):
    """Una fortaleza, ya con su cita comprobada.

    Llega al alumno a través del borrador de devolución, y una fortaleza
    inventada es tan falsa como una carencia inventada: por eso pasa por la
    misma comprobación que una valoración.
    """

    model_config = ConfigDict(extra="forbid")

    descripcion: str
    evidencia: Evidencia
    evidencia_localizada: bool


class IndicioDeAutoriaVerificado(BaseModel):
    """Un indicio de autoría, ya con su cita comprobada.

    Que la cita se localice no dice nada sobre si el indicio es acertado:
    solo dice que el docente puede ir al documento y ver de dónde sale. La
    decisión sobre la autoría sigue siendo suya.
    """

    model_config = ConfigDict(extra="forbid")

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

        localizada = cita_localizada(v.evidencia.cita, texto)
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
            evidencia=v.evidencia,
            observacion=v.observacion,
            evidencia_localizada=localizada,
        ))

    patrones: list[PatronVerificado] = []
    for p in analisis.patrones:
        localizada = cita_localizada(p.evidencia.cita, texto)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle=f"La evidencia del patrón «{p.nombre}» no se ha "
                        "localizado en el documento; no pasará a la devolución.",
            ))
        patrones.append(PatronVerificado(
            nombre=p.nombre,
            descripcion=p.descripcion,
            evidencia=p.evidencia,
            evidencia_localizada=localizada,
        ))

    fortalezas: list[FortalezaVerificada] = []
    for f in analisis.fortalezas:
        localizada = cita_localizada(f.evidencia.cita, texto)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle="La evidencia de una fortaleza no se ha localizado en "
                        "el documento; no pasará a la devolución.",
            ))
        fortalezas.append(FortalezaVerificada(
            descripcion=f.descripcion,
            evidencia=f.evidencia,
            evidencia_localizada=localizada,
        ))

    indicios_de_autoria: list[IndicioDeAutoriaVerificado] = []
    for indicio in analisis.indicios_de_autoria:
        localizada = cita_localizada(indicio.evidencia.cita, texto)
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
            evidencia=indicio.evidencia,
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
