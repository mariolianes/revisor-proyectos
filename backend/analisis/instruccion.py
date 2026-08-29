"""Lo que se le pide al motor, compuesto desde los criterios.

Nada de lo que aquí se pide está escrito en este fichero como criterio: las
dimensiones, sus nombres, los niveles de prioridad y los límites del feedback
se leen de `criteria/`. Cambiar un criterio cambia lo que se le pide sin tocar
Python, igual que cambiar `formato.yaml` cambia lo que se comprueba de un PDF.

Lo que sí está aquí es la forma de pedirlo: el tono, el orden y las
prohibiciones. Eso no es criterio académico, es cómo se le habla a un modelo.
"""

from pathlib import Path

import yaml

# Las prohibiciones que no salen de un fichero de criterios porque no son
# criterio de corrección: son límites del sistema, fijados por el §13 del
# Maestro y el anexo B del calibrador.
_PROHIBICIONES = """
No propongas ninguna nota ni calificación. No la hay: las ponderaciones
oficiales todavía no existen y el sistema no las inventa.

No afirmes que un texto lo ha escrito una inteligencia artificial. Si observas
algo que lo sugiera, regístralo como indicio y deja la decisión al profesor.

No juzgues ideologías, enfoques personales ni estilos. Señala falta de
neutralidad académica, incoherencia, riesgo ético o ausencia de fuentes solo
cuando haya evidencia en el documento.

Cita siempre de forma literal. Un fragmento copiado del trabajo, no un
resumen: el profesor tiene que poder ir a esa página y leer eso mismo. Una
paráfrasis no vale como evidencia.

Copia un tramo seguido, tal cual está escrito. No unas dos partes distintas
con puntos suspensivos, no recortes por el medio y no arregles la redacción
del alumno al copiarla: el sistema busca esa cadena exacta en el documento y
descarta como no verificada cualquier cita que no encuentre entera.

Si de verdad no hay ningún fragmento que sostenga una observación, no la
hagas. Una cita vacía o inventada no es una observación con poca evidencia:
es una observación que el profesor no puede comprobar, y vale menos que el
silencio.

Eso vale también para una dimensión entera. Si no puedes valorar una porque
el trabajo no contiene nada que citar al respecto, déjala fuera en lugar de
describir su ausencia dentro de la cita: el sistema registra por su cuenta
qué dimensiones se quedaron sin valorar y se lo dice al profesor. Escribir
«no se localizan referencias a...» en el hueco de la cita convierte un dato
útil -esto no está- en una evidencia falsa.
""".strip()


def _cargar(raiz: Path, version: str, nombre: str):
    fichero = raiz / "criteria" / version / f"{nombre}.yaml"
    if not fichero.is_file():
        return None
    return yaml.safe_load(fichero.read_text(encoding="utf-8"))


def construir(
    raiz: Path, version: str, fase: str, modalidad: str | None = None
) -> str:
    """Compone la instrucción para una fase concreta.

    Sin dimensiones no se improvisa nada: si no se pueden leer, se dice. Pedir
    un juicio sin saber qué se está evaluando produciría una respuesta con
    forma de análisis y ningún criterio detrás, que es peor que no tener nada.
    """
    dimensiones = _cargar(raiz, version, "dimensiones")
    if not dimensiones:
        raise ValueError(
            f"No se han podido leer las dimensiones de criteria/{version}/. "
            "Sin ellas no se puede pedir un análisis: no habría nada que valorar."
        )

    activas = [
        d for d in dimensiones
        if isinstance(d, dict) and fase in (d.get("activa_en") or [])
    ]
    prioridades = _cargar(raiz, version, "prioridades") or []
    feedback = _cargar(raiz, version, "feedback") or {}

    partes = [
        "Eres el asistente de corrección de Proyectos Intermodulares de "
        "Formación Profesional de un profesor. Tu trabajo es valorar una "
        "entrega y darle a él la información que necesita para corregirla. "
        "No corriges tú: propones y te detienes.",
        "",
        f"Esta entrega corresponde a la fase {fase}"
        + (f", modalidad {modalidad}." if modalidad else "."),
        "",
        "El nivel de exigencia es el de un Proyecto Intermodular de Formación "
        "Profesional. Detectar no es perseguir: no conviertas la corrección en "
        "una auditoría empresarial ni en una tesis. No exijas viabilidad "
        "empresarial absoluta ni verifiques cada cifra externa; acepta "
        "estimaciones razonables si están identificadas y explicadas.",
        "",
        "Valora estas dimensiones, y solo estas:",
    ]
    for d in activas:
        linea = f"- {d['codigo']}: {d.get('nombre', '')}"
        if d.get("observa"):
            linea += f". {d['observa']}"
        partes.append(linea)

    partes += ["", "Clasifica cada hallazgo con uno de estos niveles de prioridad:"]
    for p in prioridades:
        if isinstance(p, dict):
            partes.append(f"- {p['codigo']} ({p.get('nombre','')}): {p.get('efecto','')}")

    economia = (feedback.get("economia_pedagogica") or {}).get("prioridades_maximas")
    if economia:
        partes += [
            "",
            f"Si encuentras muchos problemas, identifica cuáles desbloquean el "
            f"desarrollo y cuáles pueden esperar. El profesor solo trasladará "
            f"al alumno {economia} como mucho.",
        ]

    partes += ["", _PROHIBICIONES]
    return "\n".join(partes)
