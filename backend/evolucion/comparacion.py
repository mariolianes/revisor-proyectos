"""La entrega nueva frente a la anterior.

El §5.1 prohíbe tres cosas que se detectan contrastando textos: entregar
solo los capítulos nuevos, repetir la versión anterior sin progreso real, y
eliminar contenido ya validado. Ninguna necesita entender el texto, solo
compararlo, así que aquí no interviene ningún modelo de lenguaje.

Los avisos son avisos. No dicen que el alumno haya hecho algo mal: dicen
que hay algo que mirar. Quien decide es el docente.

Por qué n-gramas y no párrafos
-------------------------------
La primera versión de este módulo comparaba párrafo contra párrafo con
``difflib``. Una revisión encontró tres problemas de raíz común -esa
comparación es frágil ante la estructura del documento y cuadrática en
coste-, y obligó a rehacerlo:

1. Partir o fusionar un párrafo -una edición normalísima al corregir- deja
   cada mitad sin pareja exacta en la otra entrega, y la proporción
   conservada se hundía aunque el contenido siguiera intacto. Un aviso
   falso que el profesor trasladaría al alumno sin motivo.
2. Está enlazado con nuestra propia extracción: ``texto_plano`` (Task 6)
   une las páginas con un solo salto de línea, y PyMuPDF con frecuencia no
   deja líneas en blanco entre párrafos. El texto llegaba como un único
   «párrafo» gigante y la comparación por párrafos colapsaba a una
   proporción de longitudes, no de contenido.
3. Comparar cada párrafo contra todos los del otro lado es cuadrático:
   inviable en un documento de varios cientos de párrafos mientras el
   profesor espera delante de la pantalla.

La solución: reducir cada texto a su lista de palabras normalizadas y
comparar los conjuntos de n-gramas de PALABRAS_POR_FIRMA palabras
consecutivas. Un n-grama no sabe nada de párrafos, así que partirlos,
fusionarlos, reordenarlos o perder las líneas en blanco deja de importar.
Y comparar dos conjuntos por tabla hash es lineal, no cuadrático como
comparar cada elemento de una lista contra todos los de la otra.

Limitación conocida: un texto muy repetitivo -una tabla de valores casi
iguales, una plantilla con huecos- comparte n-gramas entre partes
distintas del documento, así que la proporción conservada puede salir algo
más alta de lo que un lector humano diría. El rediseño resuelve el
emparejamiento frágil de párrafos, pero no cierra del todo ese caso.
"""

import re
import unicodedata

from pydantic import BaseModel

# Cuántas palabras consecutivas forman la firma que se compara.
PALABRAS_POR_FIRMA = 8

# Por debajo de esto, la entrega nueva no parece incluir el trabajo
# anterior.
CONSERVADO_MINIMO = 0.30

# Por encima de esto el contenido anterior se da por reconocido sin
# reservas. Entre los dos umbrales se avisa de que una parte no se
# reconoce, sin decidir si es porque se reescribió o porque se suprimió.
RECONOCIDO_MINIMO = 0.80

# Ya no decide ningún aviso -eso lo hacen las proporciones de n-gramas-,
# solo filtra ruido (numeraciones, encabezados sueltos) al contar párrafos
# para los dos campos informativos.
CARACTERES_MINIMOS = 25


class Evolucion(BaseModel):
    """Qué se conserva, qué se ha añadido, y el tamaño a cada lado."""

    proporcion_conservada: float = 0.0
    proporcion_nueva: float = 0.0
    parrafos_antes: int = 0
    parrafos_despues: int = 0
    avisos: list[str] = []


def normalizar(texto: str) -> list[str]:
    """Lista de palabras en minúsculas, sin tildes ni puntuación."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    return re.findall(r"[a-z0-9]+", sin_tildes.lower())


def _firmas(palabras: list[str]) -> set[tuple[str, ...]]:
    """Conjunto de n-gramas de PALABRAS_POR_FIRMA palabras consecutivas.

    Un texto más corto que la firma se recoge entero en una única firma,
    para que un párrafo suelto de pocas palabras no quede fuera de la
    comparación.
    """
    if not palabras:
        return set()
    if len(palabras) < PALABRAS_POR_FIRMA:
        return {tuple(palabras)}
    return {
        tuple(palabras[indice : indice + PALABRAS_POR_FIRMA])
        for indice in range(len(palabras) - PALABRAS_POR_FIRMA + 1)
    }


def _contar_parrafos(texto: str) -> int:
    """Párrafos con contenido, partiendo por líneas en blanco.

    Es un conteo informativo -da al docente una idea del tamaño- y no
    decide ningún aviso, así que su fragilidad frente a la estructura del
    documento (líneas en blanco que faltan, encabezados sueltos) no tiene
    consecuencias sobre lo que se avisa.
    """
    total = 0
    for crudo in re.split(r"\n\s*\n", texto):
        limpio = " ".join(crudo.split())
        if len(limpio) >= CARACTERES_MINIMOS:
            total += 1
    return total


def comparar(texto_anterior: str, texto_nuevo: str) -> Evolucion:
    """Contrasta las dos entregas y avisa de lo que el §5.1 prohíbe."""
    palabras_anteriores = normalizar(texto_anterior)
    palabras_nuevas = normalizar(texto_nuevo)

    if not palabras_anteriores:
        # Primera entrega: no hay con qué comparar y no se finge que sí.
        return Evolucion(parrafos_despues=_contar_parrafos(texto_nuevo))

    firmas_anteriores = _firmas(palabras_anteriores)
    firmas_nuevas = _firmas(palabras_nuevas)

    conservadas = firmas_anteriores & firmas_nuevas
    proporcion_conservada = len(conservadas) / len(firmas_anteriores)
    proporcion_nueva = (
        len(firmas_nuevas - firmas_anteriores) / len(firmas_nuevas)
        if firmas_nuevas
        else 0.0
    )

    avisos = []
    if proporcion_conservada < CONSERVADO_MINIMO:
        avisos.append(
            "La entrega no parece incluir el trabajo anterior: solo se "
            f"reconoce el {proporcion_conservada:.0%} de lo que había. El "
            "§5.1 pide el documento completo en cada fase, no solo lo "
            "nuevo."
        )
    elif proporcion_conservada < RECONOCIDO_MINIMO:
        avisos.append(
            "Hay contenido de la entrega anterior que no se reconoce: un "
            f"{1 - proporcion_conservada:.0%}. Puede deberse a que se ha "
            "reescrito o a que se ha suprimido; el §5.1 no admite eliminar "
            "contenido ya validado sin justificarlo."
        )

    # Identidad exacta, no parecido. El progreso se mide comparando las
    # palabras letra a letra, no las proporciones de arriba: con el umbral
    # de reconocimiento, un párrafo retocado sigue contando como
    # reconocido, así que juzgar el progreso con esas proporciones
    # marcaría como estancada una entrega que sí se ha corregido.
    if palabras_anteriores == palabras_nuevas:
        avisos.append(
            "La entrega llega sin cambios respecto a la anterior: no se "
            "aprecia progreso."
        )

    return Evolucion(
        proporcion_conservada=proporcion_conservada,
        proporcion_nueva=proporcion_nueva,
        parrafos_antes=_contar_parrafos(texto_anterior),
        parrafos_despues=_contar_parrafos(texto_nuevo),
        avisos=avisos,
    )
