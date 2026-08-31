"""El borrador de devolución, pedido como formulario.

La decisión que sostiene el control de coherencia del §17.2: al motor no se
le pide un texto, se le piden los cuatro bloques del Anexo D por separado.
Con eso, comprobar que el borrador no contradice al informe deja de ser un
análisis del lenguaje y pasa a ser una comparación de listas.

Si se le pidiera un párrafo libre, para saber si dice «está todo bien»
habría que interpretarlo, y para interpretarlo haría falta otro modelo, que
también puede equivocarse. Así no: las acciones del borrador son -como
máximo- las observaciones que pasaron el filtro, y eso se cuenta.

Pedir un formulario no es fiarse del motor. `Devolucion` con
`extra="forbid"` impide que aparezca un campo de más -una nota como campo
nuevo se rechazaría antes de que nadie la viera-, pero eso no impide que el
motor escriba «tu nota es un 8» dentro de `cierre`, que sigue siendo texto
libre. Por eso, después de recibir la respuesta, `componer` la somete a
`_viola_una_regla_dura`: un repaso literal de las cuatro reglas que no se
negocian (nota, evidencia, autoría, informe interno) sobre el texto que de
verdad se va a entregar, no sobre la instrucción que se le dio.

Qué se hace si el motor no pasa esa comprobación: no se recorta la frase
suelta y se sigue -un borrador con una frase tachada a mitad no es un
borrador entregable, y adivinar qué se calla el resto del párrafo sería
inventar otra vez-. Se levanta `BorradorNoValido` y `componer` no devuelve
nada: el profesor no llega a ver un texto que parece limpio y no lo está. Es
la misma filosofía que el resto del sistema -se propone y se detiene-,
aplicada al único momento en que lo que se compone podría llegar a otra
persona que no es él.

Desde D-019 (`docs/decisions.md`, 2026-08-31), `componer` aplica una
comprobación hermana de `_viola_una_regla_dura`, pero de naturaleza distinta:
`_semaforo_y_acciones_incoherentes`. El docente pidió que apertura,
prioridades, cierre y semáforo «cuenten la misma historia»; un ejemplo real
-un proyecto ROJO cuyo borrador hablaba de «avance sólido» y «cuatro
retoques»- mostró que el semáforo y el texto podían contradecirse. Detectar
esa contradicción en la prosa libre de `apertura` y `cierre` exigiría un
catálogo de frases -«suena a retoques», «suena a insuficiencia»- que es
exactamente la clase de comprobación que ya falló una vez en este proyecto,
con la detección de afirmaciones de autoría por palabra clave: cualquier
lista de expresiones es un catálogo que hay que perseguir para siempre y que
un modelo esquiva sin querer con un sinónimo.

Por eso esta comprobación no lee `apertura` ni `cierre`: compara el color
que se propuso -`semaforo_por_valoraciones(analisis.valoraciones)`,
`backend/salidas/informe.py`- contra el color que sostienen, por sí solas,
las prioridades que de verdad van a generar las `acciones` del borrador
-`color_sostenido_por_prioridades(elegidas)`, en el mismo módulo-. Es
estructural, no textual: no juzga si la redacción "suena" a poco, comprueba
si lo que se le va a pedir al alumno se corresponde con la gravedad que ya
se calculó.

En el uso normal casi nunca dispara: `seleccionar_prioridades`
(`backend/salidas/seleccion.py`) ordena P1 antes que P2 y P2 antes que P3,
así que la prioridad que decide el color -la más severa presente- siempre
cae en los primeros puestos, y el límite de la economía pedagógica solo
recorta la cola. Su valor es de red de seguridad, igual que
`_con_evidencia_localizada` vuelve a filtrar por si acaso: si
`prioridades.yaml` marcara la prioridad que sostiene el color con
`llega_al_alumno: nunca` -sacándola del `orden` que decide quién puede
llegar al alumno, no del límite de cuántas caben-, o si un cambio futuro en
`seleccionar_prioridades` dejara de ordenar por severidad primero, un color
severo llegaría con un borrador sin ninguna acción que lo explique. Eso sí
se rechaza aquí, antes incluso de llamar al motor.

Esto no cierra el problema entero: el tono de `apertura` y `cierre` sigue
siendo texto libre que ningún validador estructural puede garantizar. La
mitigación de ese resto está en `instruccion_de_devolucion`, no en una
comprobación posterior: se le dice al motor, con el mismo texto `calibrado`
que ya declara `criteria/<version>/semaforo.yaml` -no uno inventado aquí-,
qué estado se ha calculado, para que redacte sobre ese nivel en vez de
inferirlo solo de cuántas acciones ve. Es una instrucción, no una garantía
-el resto del módulo ya asume que una instrucción se puede desobedecer-, pero
ataca la causa en vez de perseguir el síntoma en el texto ya escrito.
"""

import re
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.proveedor import ProveedorAnalisis
from backend.analisis.verificacion import (
    _AFIRMACIONES_DE_AUTORIA,
    _NOMBRES_DE_IA,
    AnalisisVerificado,
    FortalezaVerificada,
    ValoracionVerificada,
    normalizar_para_buscar,
)
from backend.salidas.informe import (
    SEVERIDAD_SEMAFORO,
    color_sostenido_por_prioridades,
    semaforo_por_valoraciones,
)
from backend.salidas.seleccion import seleccionar_prioridades

_T = TypeVar("_T")


class Devolucion(BaseModel):
    """Los cuatro bloques del Anexo D.

    `extra="forbid"`: si el motor añadiera un campo -una nota, una
    probabilidad de autoría- la validación del formulario lo rechaza antes
    de que llegue aquí. No cubre el texto libre dentro de cada campo; de eso
    se ocupa `_viola_una_regla_dura`, después.
    """

    model_config = ConfigDict(extra="forbid")

    apertura: str
    fortalezas: list[str]
    acciones: list[str]
    cierre: str


class BorradorNoValido(Exception):
    """El motor ha devuelto un borrador que viola una regla que no se negocia.

    No lleva el texto recortado a lo que sí pasaría: un borrador a medio
    limpiar no es un borrador entregable. La decisión de qué hacer después
    -pedir otra redacción, avisar al docente, escribirlo a mano- es de quien
    llama a `componer`, no de este módulo.
    """


def _feedback(raiz: Path, version: str) -> dict:
    fichero = raiz / "criteria" / version / "feedback.yaml"
    if not fichero.is_file():
        return {}
    return yaml.safe_load(fichero.read_text(encoding="utf-8")) or {}


def _calibrado_por_color(raiz: Path, version: str) -> dict[str, str]:
    """El texto `calibrado` de cada color, leído de `semaforo.yaml`.

    Mismo patrón que `_recomendaciones_por_color`
    (`backend/salidas/informe.py`): no se redacta un texto nuevo aquí, se
    reutiliza la columna que `semaforo.yaml` ya declara -con su propia
    `fuente` al documento de calibración- para anclar la instrucción del
    motor a la severidad ya calculada, en vez de dejar que la infiera solo de
    cuántas acciones ve.
    """
    fichero = raiz / "criteria" / version / "semaforo.yaml"
    if not fichero.is_file():
        return {}
    catalogo = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    return {
        c["codigo"]: c["calibrado"]
        for c in catalogo
        if isinstance(c, dict) and "codigo" in c and "calibrado" in c
    }


def _con_evidencia_localizada(elementos: list[_T]) -> list[_T]:
    """Filtra por `evidencia_localizada`, otra vez, en la frontera hacia el
    alumno.

    `seleccionar_prioridades` (Task 7) ya deja fuera lo que no se localizó,
    y `analisis.fortalezas` debería llegar aquí ya verificado. Pero esta
    función no se fía de que quien la llame lo haya hecho bien: filtrar de
    nuevo es barato, y es la única defensa que no depende de que el resto
    del sistema no cambie nunca. `elementos` es `ValoracionVerificada` o
    `FortalezaVerificada`; los dos tienen el campo.
    """
    return [e for e in elementos if e.evidencia_localizada]  # type: ignore[attr-defined]


# Cómo se dice cada número en la instrucción: para que "parrafos_habituales:
# 2" en feedback.yaml se lea como "dos párrafos" y no como una cifra suelta
# sin más contexto. Si el profesor pusiera un número fuera de este rango, se
# usa la cifra; no es un error, solo un texto menos elegante.
_NUMEROS_EN_LETRA = {1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco"}


def _en_letra(numero: int) -> str:
    return _NUMEROS_EN_LETRA.get(numero, str(numero))


# Traduce el código de `nunca_en_la_devolucion.conceptos` -pensado para que
# el código lo compare, no para que lo lea nadie- a una frase que el motor
# pueda entender como instrucción. Si el profesor añadiera un concepto
# nuevo que esta tabla no conoce, se usa el código con guiones bajos
# cambiados por espacios: no se pierde la prohibición, solo queda menos
# elegante hasta que alguien traduzca la frase aquí.
_CONCEPTOS_PROHIBIDOS = {
    "nota_interna": "una nota, puntuación o calificación, en cualquier forma",
    "sospecha_categorica_de_ia": (
        "cualquier mención a que el trabajo lo haya escrito una "
        "inteligencia artificial o un modelo de lenguaje"
    ),
    "deliberacion_tecnica": "razonamientos internos de la corrección",
    "hallazgos_p4": "detalles menores que no se trasladan al alumno",
    "observaciones_personales_del_docente": (
        "opiniones personales del docente sobre el alumno"
    ),
}


def instruccion_de_devolucion(
    raiz: Path,
    version: str,
    analisis: AnalisisVerificado,
    elegidas: list[ValoracionVerificada],
) -> str:
    """Lo que se le pide al motor para redactar.

    Solo se le enseñan las observaciones y fortalezas con evidencia
    localizada: lo que no puede llegar al alumno no se le muestra siquiera.
    Ningún dato del informe interno entra aquí -ni `dudas_para_el_docente`,
    ni `reparos`, ni las descartadas por el límite de la economía
    pedagógica-, y ningún indicio de autoría: `elegidas` es
    `list[ValoracionVerificada]`, no hay tipo por el que un indicio pueda
    colarse, y esta función no lee `analisis.indicios_de_autoria` en ningún
    punto.

    Los límites de extensión, el estilo y lo que no se debe exigir salen de
    `feedback.yaml`, no de una frase fija en este módulo: si el profesor
    cambia el fichero, la instrucción cambia con él sin tocar código.

    Desde D-019, también se le dice al motor qué color de semáforo se ha
    calculado y su lectura calibrada -tal cual la declara
    `criteria/<version>/semaforo.yaml`, no una frase nueva-, para que la
    apertura y el cierre partan de esa severidad en vez de que el motor la
    infiera solo de cuántas fortalezas o acciones ve. Es una instrucción, no
    una garantía: `componer` sigue sin confiar en que se obedezca (ver el
    docstring del módulo y `_semaforo_y_acciones_incoherentes`).
    """
    criterios = _feedback(raiz, version)
    extension = criterios.get("extension_devolucion") or {}
    estilo = criterios.get("estilo") or {}
    prohibido = criterios.get("nunca_en_la_devolucion") or {}
    limites = criterios.get("no_exigir") or {}

    elegidas_seguras = _con_evidencia_localizada(elegidas)
    fortalezas_seguras = _con_evidencia_localizada(analisis.fortalezas)

    parrafos = int(extension.get("parrafos_habituales") or 2)
    ampliar_solo_si = extension.get("ampliar_solo_si") or "la situación lo exige"

    partes = [
        "Redacta la devolución para el alumno a partir de lo siguiente. "
        "La escribes para que el profesor la revise antes de enviarla: él "
        "decide si se envía y con qué palabras exactas.",
        "",
        f"Extensión habitual: {_en_letra(parrafos)} párrafos. Amplía solo "
        f"si {ampliar_solo_si.lower()}, no por defecto. Cercano, directo, "
        "firme y constructivo. Sin condescendencia.",
    ]

    color = semaforo_por_valoraciones(analisis.valoraciones)
    calibrado = _calibrado_por_color(raiz, version).get(color)
    if calibrado:
        partes.append("")
        partes.append(
            f"Estado calculado del proyecto: {color}. {calibrado} La "
            "apertura y el cierre tienen que sonar acordes a este nivel: ni "
            "más alarmantes ni más tranquilizadores de lo que dice, para que "
            "todo el borrador cuente la misma historia que el semáforo."
        )

    contenido = extension.get("debe_contener") or []
    if contenido:
        partes.append("El texto debe recoger: " + "; ".join(contenido) + ".")
    partes.append("")

    if fortalezas_seguras:
        partes.append("Fortalezas reales del trabajo, con evidencia localizada:")
        partes += [f"- {f.descripcion}" for f in fortalezas_seguras]
        partes.append("")

    if elegidas_seguras:
        partes.append(
            "Acciones prioritarias para el alumno, en este orden y sin "
            "añadir ninguna más: son exactamente las observaciones que ya "
            "pasaron el filtro, no una lista para completar."
        )
        partes += [f"- ({v.dimension}) {v.observacion}" for v in elegidas_seguras]
        partes.append("")

    for conservar in estilo.get("conservar") or []:
        partes.append(f"Mantén: {conservar}.")
    for evitar in estilo.get("evitar") or []:
        partes.append(f"Evita: {evitar}.")
    for limite in limites.get("limites") or []:
        partes.append(f"No exijas: {limite}.")

    partes.append("")
    for concepto in prohibido.get("conceptos") or []:
        frase = _CONCEPTOS_PROHIBIDOS.get(concepto, concepto.replace("_", " "))
        partes.append(f"No incluyas nunca: {frase}.")

    return "\n".join(partes)


# --- La comprobación posterior: no confiar en que la instrucción se obedezca ---
#
# Lo de arriba es lo que se le pide al motor. Lo de aquí abajo es lo que se
# comprueba sobre lo que respondió, porque una instrucción no es una
# garantía: un modelo puede desobedecerla, y el filtro que importa es el que
# se aplica al texto que de verdad va a salir, no al que se le pidió que
# escribiera.
#
# Nota, calificación o puntuación, en cualquier redacción habitual.
# «notable» no coincide -\b exige que "nota" termine en límite de palabra, y
# en "notable" sigue "ble"-, ni «descalificación» -el límite de palabra
# falla justo antes de "calificación"-.
_PATRON_NOTA = re.compile(r"\b(notas?|calificacion(es)?|puntuacion(es)?)\b")

# Un porcentaje, en cifra o en palabras, y una fracción sobre diez -la forma
# habitual de dar una nota numérica sin escribir la palabra "nota".
_PATRON_PORCENTAJE = re.compile(r"\d+\s*(%|por\s*ciento)")
_PATRON_FRACCION_SOBRE_DIEZ = re.compile(r"\b\d{1,2}\s*(/|sobre)\s*10\b")

# Apto, no apto, y sus formas en femenino y plural.
_PATRON_APTO = re.compile(r"\b(no\s+)?apt[oa]s?\b")


def _viola_una_regla_dura(devolucion: Devolucion) -> str | None:
    """El nombre de la regla que se ha violado, o `None` si el texto pasa.

    Se comprueba sobre el texto que de verdad va a salir -ya recortado a lo
    que cupo-, no sobre lo que el motor devolvió antes de recortar: una
    frase inventada que se recorta fuera nunca llega a nadie, así que no
    hace falta que la rechace esta función.
    """
    texto_completo = " ".join([
        devolucion.apertura,
        devolucion.cierre,
        *devolucion.fortalezas,
        *devolucion.acciones,
    ])
    plano = normalizar_para_buscar(texto_completo)
    plano_con_bordes = f" {plano} "

    if _PATRON_NOTA.search(plano):
        return "nota_o_calificacion"
    if _PATRON_PORCENTAJE.search(plano) or _PATRON_FRACCION_SOBRE_DIEZ.search(plano):
        return "porcentaje_o_nota_numerica"
    if _PATRON_APTO.search(plano):
        return "apto_o_no_apto"
    # Los mismos catálogos que usa `verificacion.py` para realzar un indicio
    # de autoría formulado como veredicto: aquí no son un realce, son la
    # comprobación entera, porque en la devolución ninguna mención de
    # autoría es aceptable, esté redactada como esté.
    if any(nombre in plano_con_bordes for nombre in _NOMBRES_DE_IA):
        return "indicio_de_autoria"
    if any(forma in plano for forma in _AFIRMACIONES_DE_AUTORIA):
        return "indicio_de_autoria"
    return None


def _semaforo_y_acciones_incoherentes(
    valoraciones: list[ValoracionVerificada], elegidas: list[ValoracionVerificada],
) -> bool:
    """`True` si el color propuesto dice más de lo que sostienen, por sí
    solas, las prioridades que van a generar `acciones`.

    Comprobación estructural, hermana de `_viola_una_regla_dura` pero de
    naturaleza distinta: esa lee el texto que redactó el motor; esta compara
    dos colores que ya se sabían antes de pedirle nada al motor, así que
    `componer` la aplica primero y se ahorra la llamada si ya falla aquí. Ver
    el docstring del módulo para el porqué de no intentar detectar la
    incoherencia en la prosa de `apertura` o `cierre`.

    `elegidas` siempre sostiene, en la práctica, el mismo color que
    `valoraciones`: `seleccionar_prioridades` ordena por severidad primero,
    así que la prioridad que decide el color siempre cae en los primeros
    puestos y el límite de la economía pedagógica solo recorta la cola.
    Esta comprobación es una red de seguridad para cuando esa garantía se
    rompe por otra vía -`prioridades.yaml` con `llega_al_alumno: nunca` en
    la prioridad que sostiene el color, un cambio futuro en
    `seleccionar_prioridades` que deje de ordenar por severidad-, no una que
    se espere disparar en el uso normal.
    """
    color_propuesto = semaforo_por_valoraciones(valoraciones)
    color_de_las_acciones = color_sostenido_por_prioridades(elegidas)
    return SEVERIDAD_SEMAFORO[color_propuesto] > SEVERIDAD_SEMAFORO[color_de_las_acciones]


# Lo que va en el hueco del texto al pedir el borrador. **No es el trabajo del
# alumno, y esa es la clave**: la instrucción ya lleva las prioridades
# verificadas y sus citas, así que el documento no tiene que viajar una
# segunda vez al proveedor.
#
# Aquí iba una cadena vacía, y por eso el borrador no se generó nunca con el
# motor real: la API de OpenAI responde 400 -«One of "input" or
# "previous_response_id"...»- cuando el campo llega vacío. No lo cazó ningún
# test porque todos usan `ProveedorSimulado`, que acepta cualquier cosa; se
# vio ejecutando el flujo entero contra el servicio de verdad. Es el mismo
# punto ciego que dejó pasar la prioridad «P1» contra el enum de la base de
# datos: un doble más permisivo que el original no protege de lo que el
# original rechaza.
PETICION_DEL_BORRADOR = "Redacta el borrador con lo que dice la instrucción."


def componer(
    raiz: Path,
    version: str,
    proveedor: ProveedorAnalisis,
    analisis: AnalisisVerificado,
) -> Devolucion:
    """Pide la redacción y comprueba lo que el motor ha devuelto.

    Primero recorta: si el motor ha añadido acciones o fortalezas de su
    cosecha, se descartan las que sobran del final -son exactamente las que
    se le pidieron, y eso se cuenta-. Después comprueba: el texto que queda
    se somete a `_viola_una_regla_dura` antes de devolverlo. Si lo viola, no
    se devuelve un borrador a medio limpiar: se levanta `BorradorNoValido` y
    no hay `Devolucion` que entregar. Es el control de coherencia del §17.2
    aplicado donde se puede aplicar sin interpretar texto, más la comprobación
    de que el motor no ha colado, dentro de un campo de texto libre, algo que
    el tipo `Devolucion` no podía impedir por sí solo.

    Antes de llamar al motor -ni siquiera hace falta pedirle nada- se
    comprueba también que el color propuesto lo sostienen las prioridades que
    van a llegar al alumno: `_semaforo_y_acciones_incoherentes`. Se hace aquí
    y no después porque no depende de lo que redacte el motor, y porque un
    fallo aquí significaría entregar un borrador vacío o casi vacío sobre un
    color severo -el atajo de la línea siguiente, sin ninguna acción con la
    que explicarlo-, que es peor que no entregar nada.
    """
    seleccion = seleccionar_prioridades(raiz, version, analisis)
    elegidas = _con_evidencia_localizada(seleccion.elegidas)
    fortalezas = _con_evidencia_localizada(analisis.fortalezas)

    if _semaforo_y_acciones_incoherentes(analisis.valoraciones, elegidas):
        raise BorradorNoValido(
            "El semáforo propuesto no lo sostienen las prioridades que van a "
            "llegar al alumno: el color dice más de lo que el borrador podría "
            "pedirle que corrija. No se entrega. Revisa "
            "'llega_al_alumno' en prioridades.yaml para la prioridad que "
            "sostiene este color, o las prioridades de este análisis, antes "
            "de volver a intentarlo."
        )

    if not elegidas and not fortalezas:
        return Devolucion(apertura="", fortalezas=[], acciones=[], cierre="")

    borrador = proveedor.analizar(
        instruccion_de_devolucion(raiz, version, analisis, elegidas),
        PETICION_DEL_BORRADOR,
        Devolucion,
    )
    devolucion = Devolucion(
        apertura=borrador.apertura,
        fortalezas=borrador.fortalezas[: len(fortalezas)],
        acciones=borrador.acciones[: len(elegidas)],
        cierre=borrador.cierre,
    )

    regla_violada = _viola_una_regla_dura(devolucion)
    if regla_violada is not None:
        raise BorradorNoValido(
            f"El motor ha devuelto un borrador que viola la regla "
            f"«{regla_violada}»; no se entrega. Corrígelo a mano o pide "
            "de nuevo la redacción."
        )
    return devolucion
