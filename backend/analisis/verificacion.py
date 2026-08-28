"""Lo que comprobamos nosotros antes de creernos lo que dice el motor.

Siete defensas, y ninguna delega en que el modelo se porte bien. Todas son
código de aquí, todas fallan del lado seguro, y todas se prueban contra un
motor hostil en vez de contra uno que colabora.

La primera es la que sostiene las demás: un modelo puede inventarse una frase,
pero no puede hacer que exista en el documento del alumno.
"""

import unicodedata

# Una cita más corta que esto no señala nada: «el» o «viable» aparecen en
# cualquier trabajo y localizarlas no demuestra que el juicio se apoye ahí.
CITA_MINIMA = 20


def normalizar_para_buscar(texto: str) -> str:
    """Minúsculas, sin tildes y con los espacios colapsados.

    Se normaliza porque el texto extraído de un PDF trae saltos de línea donde
    el original tenía un espacio, y porque un modelo puede devolver la cita sin
    acentuar. Ninguna de esas dos diferencias significa que la cita sea falsa.
    """
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def cita_localizada(cita: str, texto: str) -> bool:
    """Si la cita aparece literalmente en el texto del trabajo.

    Literalmente quiere decir literalmente: se admite que cambien los espacios
    y las tildes, y nada más. Una paráfrasis no se da por buena, porque el
    objetivo no es saber si el motor entendió el documento, sino si el docente
    puede ir a la página y leer eso mismo.
    """
    limpia = normalizar_para_buscar(cita)
    if len(limpia) < CITA_MINIMA:
        return False
    return limpia in normalizar_para_buscar(texto)
