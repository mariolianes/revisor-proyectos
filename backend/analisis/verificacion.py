"""Lo que comprobamos nosotros antes de creernos lo que dice el motor.

Siete defensas, y ninguna delega en que el modelo se porte bien. Todas son
código de aquí, todas fallan del lado seguro, y todas se prueban contra un
motor hostil en vez de contra uno que colabora.

La primera es la que sostiene las demás: un modelo puede inventarse una frase,
pero no puede hacer que exista en el documento del alumno.
"""

import re
import unicodedata

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
