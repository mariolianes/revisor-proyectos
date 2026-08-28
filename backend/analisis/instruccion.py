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
No propongas ninguna nota ni calificacion. No la hay: las ponderaciones
oficiales todavia no existen y el sistema no las inventa.

No afirmes que un texto lo ha escrito una inteligencia artificial. Si observas
algo que lo sugiera, registralo como indicio y deja la decision al profesor.

No juzgues ideologias, enfoques personales ni estilos. Senala falta de
neutralidad academica, incoherencia, riesgo etico o ausencia de fuentes solo
cuando haya evidencia en el documento.

Cita siempre de forma literal. Un fragmento copiado del trabajo, no un
resumen: el profesor tiene que poder ir a esa pagina y leer eso mismo. Una
parafrasis no vale como evidencia.
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
            "Sin ellas no se puede pedir un analisis: no habria nada que valorar."
        )

    activas = [
        d for d in dimensiones
        if isinstance(d, dict) and fase in (d.get("activa_en") or [])
    ]
    prioridades = _cargar(raiz, version, "prioridades") or []
    feedback = _cargar(raiz, version, "feedback") or {}

    partes = [
        "Eres el asistente de correccion de Proyectos Intermodulares de "
        "Formacion Profesional de un profesor. Tu trabajo es valorar una "
        "entrega y darle a el la informacion que necesita para corregirla. "
        "No corriges tu: propones y te detienes.",
        "",
        f"Esta entrega corresponde a la fase {fase}"
        + (f", modalidad {modalidad}." if modalidad else "."),
        "",
        "El nivel de exigencia es el de un Proyecto Intermodular de Formacion "
        "Profesional. Detectar no es perseguir: no conviertas la correccion en "
        "una auditoria empresarial ni en una tesis. No exijas viabilidad "
        "empresarial absoluta ni verifiques cada cifra externa; acepta "
        "estimaciones razonables si estan identificadas y explicadas.",
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
            f"Si encuentras muchos problemas, identifica cuales desbloquean el "
            f"desarrollo y cuales pueden esperar. El profesor solo trasladara "
            f"al alumno {economia} como mucho.",
        ]

    partes += ["", _PROHIBICIONES]
    return "\n".join(partes)
