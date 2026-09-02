"""Buscar en la portada, sin adivinar nada.

El docente llama a la portada «una evidencia auxiliar»
(`decisiones#4-portada`), y esa palabra decide el diseño entero de este
módulo: **no se extrae un nombre del documento; se comprueba si alguno de los
alumnos que ya conocemos aparece en él**.

La diferencia importa. Extraer un nombre de un texto libre exige adivinar
dónde empieza y dónde acaba, y equivocarse ahí produce exactamente lo que él
quiere evitar: asignar un trabajo a la persona equivocada. Comprobar si un
nombre conocido aparece no requiere adivinar nada, y responde a la única
pregunta que la portada tiene que responder -«¿confirma a este candidato o
lo contradice?»-.

**Solo se ejecuta en el equipo del docente, y antes de minimizar.** Lo que
sale de aquí son candidatos del listado local, con nombre; lo que cruza la
frontera hacia el resto del sistema es la `Identificacion` de
`backend/identificacion/determinista.py`, que no lleva ninguno.
"""

from __future__ import annotations

from pathlib import Path

from backend.extraccion.lectura import abrir
from backend.identificacion.determinista import CandidatoLocal
from backend.identificacion.nombres import normalizar, palabras

# Cuántas páginas cuentan como «portada o primeras páginas». Tres cubre la
# portada, una contraportada o página de créditos y un índice corto, que es
# donde el nombre del autor aparece si aparece. Leer más no ayuda: a partir
# de ahí, encontrar el nombre en el cuerpo del texto dice poco sobre quién
# lo entrega.
PAGINAS_DE_PORTADA = 3


def texto_de_la_portada(ruta: Path, paginas: int = PAGINAS_DE_PORTADA) -> str:
    """El texto de las primeras páginas, tal cual.

    Lanza `PdfIlegible` si el archivo no se puede abrir, igual que el resto
    de la capa de extracción: quien llame decide si eso es una incidencia.
    """
    with abrir(ruta) as documento:
        trozos = [
            documento[i].get_text() for i in range(min(paginas, documento.page_count))
        ]
    return "\n".join(trozos)


def aparece_en(nombre: str, texto: str) -> bool:
    """Si ese nombre aparece en el texto, en cualquier orden.

    Se busca una ventana de palabras consecutivas cuyo conjunto sea
    exactamente el del nombre. Así «Ficticia Inventada, Ana» en el listado
    encuentra «Ana Ficticia Inventada» en la portada -él pide ignorar el
    orden «apellidos, nombre»- sin que por eso valga encontrar las tres
    palabras desperdigadas por la página, que no significaría nada.

    No hay umbral ni parecido: o la ventana coincide o no coincide.
    """
    del_nombre = palabras(nombre)
    if not del_nombre:
        return False

    tokens = normalizar(texto).split()
    ancho = len(del_nombre)
    for inicio in range(len(tokens) - ancho + 1):
        ventana = tokens[inicio : inicio + ancho]
        if set(ventana) == del_nombre and len(set(ventana)) == ancho:
            return True
    return False


def candidatos_nombrados_en(
    texto: str, candidatos: list[CandidatoLocal]
) -> list[CandidatoLocal]:
    """Cuáles de esos alumnos aparecen nombrados en el texto.

    Normalmente será ninguno o uno. Si son varios -dos alumnos nombrados en
    la misma portada, un trabajo en grupo, una plantilla reutilizada sin
    borrar el nombre anterior- quien llame no debe elegir: es justamente el
    caso que va a Incidencias.
    """
    return [c for c in candidatos if aparece_en(c.nombre, texto)]


def nombre_confirmado_por_la_portada(
    texto: str, candidatos: list[CandidatoLocal]
) -> str | None:
    """El nombre que la portada confirma, o `None`.

    Devuelve `None` tanto cuando no aparece nadie como cuando aparece más de
    uno: en los dos casos la portada no confirma a nadie, y decidir cuál de
    dos sería adivinar. `identificar()` trata ese `None` como «no se ha
    podido leer la portada con la que confirmarlo», que manda el caso a
    Incidencias en vez de asignarlo.
    """
    nombrados = candidatos_nombrados_en(texto, candidatos)
    return nombrados[0].nombre if len(nombrados) == 1 else None
