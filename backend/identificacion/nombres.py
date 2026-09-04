"""Comparar dos nombres de persona sin decidir por parecido.

El docente descartó expresamente la coincidencia difusa
(`decisiones#6-identificacion`): «no estableceremos un porcentaje de parecido
para asignar automáticamente un trabajo». Aquí no hay, por tanto, ninguna
distancia de edición ni ningún umbral. Lo único que se hace es **normalizar**
—quitar lo que él enumera como ignorable— y después comparar por igualdad o
por inclusión de palabras.

Lo que él autoriza a ignorar, literalmente: «mayúsculas, tildes, guiones,
comas, dobles espacios y el orden "apellidos, nombre"».

Este módulo trabaja con nombres de alumnos, así que **solo se ejecuta en el
equipo del docente**. Nada de lo que hay aquí viaja a la API ni a la base de
datos: ver `backend/privacidad/listado_local.py`, que es donde vive la
correspondencia, y `backend/privacidad/minimizacion.py`, que es lo que se
aplica *después* de identificar y *antes* de cualquier llamada externa.
"""

from __future__ import annotations

import unicodedata

# Partículas que no distinguen a una persona de otra y que aparecen o
# desaparecen sin criterio entre un listado y una portada. No se usan para
# decidir una coincidencia, pero tampoco la impiden.
PARTICULAS = frozenset({"de", "del", "la", "las", "los", "y", "i", "da", "do"})


def normalizar(nombre: str) -> str:
    """El nombre reducido a lo que sí distingue a una persona.

    Minúsculas, sin tildes, sin guiones ni comas ni puntos, sin dobles
    espacios. Es la misma normalización que `_normalizar_texto` en
    `backend/servicios/importacion_alumnos.py` -no se importa de allí para
    no atar la identificación al importador, pero si una de las dos cambia,
    la otra tiene que cambiar igual: hay un test que lo comprueba-.
    """
    descompuesto = unicodedata.normalize("NFKD", nombre)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    solo_alfanumerico = "".join(
        c if c.isalnum() else " " for c in sin_tildes.lower()
    )
    return " ".join(solo_alfanumerico.split())


def palabras(nombre: str) -> frozenset[str]:
    """Las palabras significativas del nombre, sin partículas.

    Se devuelve un conjunto y no una lista porque el orden no debe
    importar: el docente pide expresamente ignorar el orden «apellidos,
    nombre», y «García Pérez, Ana» y «Ana García Pérez» tienen que dar lo
    mismo.
    """
    return frozenset(
        p for p in normalizar(nombre).split() if p not in PARTICULAS
    )


def es_el_mismo_nombre(uno: str, otro: str) -> bool:
    """Si son el mismo nombre completo, en cualquier orden.

    Exige que coincidan **todas** las palabras significativas. No es una
    medida de parecido: o son las mismas palabras o no lo son.
    """
    del_uno, del_otro = palabras(uno), palabras(otro)
    return bool(del_uno) and del_uno == del_otro


def es_nombre_parcial_de(parcial: str, completo: str) -> bool:
    """Si `parcial` es un subconjunto propio del nombre completo.

    El caso típico: la portada dice «Ana García» y el listado «Ana García
    Pérez». Sirve para la prioridad 3 del docente -nombre más al menos un
    apellido-, nunca para asignar por su cuenta: la prioridad 3 exige,
    además, candidato único.

    Devuelve `False` cuando son idénticos: eso ya lo cubre
    `es_el_mismo_nombre`, y confundirlos haría que un nombre completo
    entrara por la puerta de la coincidencia parcial.
    """
    del_parcial, del_completo = palabras(parcial), palabras(completo)
    if not del_parcial or del_parcial == del_completo:
        return False
    return del_parcial < del_completo


def tiene_nombre_y_apellido(nombre: str) -> bool:
    """Al menos dos palabras significativas.

    La prioridad 3 del docente pide «nombre más al menos un apellido». Una
    sola palabra no identifica a nadie en un grupo de 200-250 alumnos, y
    tratarla como si lo hiciera es justo el error que él quiere evitar.
    """
    return len(palabras(nombre)) >= 2


# Lo que sigue compara un NOMBRE contra un TEXTO que lo contiene -el nombre
# de un archivo, típicamente-, no dos nombres entre sí. Es un caso distinto y
# hace falta separarlo: un archivo se llama «Ana_Ficticia_Inventada_Entrega_2»
# y eso no es un nombre de persona, es un nombre de persona con dos palabras
# más pegadas. Comparar por igualdad ahí no encuentra a nadie -se descubrió
# escribiendo la primera prueba de integración de la admisión, con un nombre
# de archivo tal como lo devuelve la plataforma-.
#
# Sigue sin haber ningún parecido difuso: se cuenta cuántas palabras del
# nombre están en el texto, y nada más.

# Cuántas palabras del nombre tienen que aparecer para considerar que el
# texto lo nombra a medias. Dos, porque el docente pide «nombre más al menos
# un apellido» para su prioridad 3: una sola palabra no distingue a nadie en
# un grupo de 200-250 alumnos.
PALABRAS_MINIMAS = 2


def nombra_a(texto: str, nombre: str) -> bool:
    """Si el texto contiene todas las palabras significativas del nombre.

    Sirve para la prioridad 2 del docente -«nombre completo normalizado y
    único»-: que el archivo traiga además la fase o la fecha no lo hace menos
    completo.
    """
    del_nombre = palabras(nombre)
    return bool(del_nombre) and del_nombre <= palabras(texto)


def nombra_parcialmente_a(texto: str, nombre: str) -> bool:
    """Si el texto contiene parte del nombre, pero no todo.

    Es la prioridad 3 -nombre más al menos un apellido-, y por eso exige
    `PALABRAS_MINIMAS` y no una. Devuelve `False` cuando están todas: ese
    caso ya lo cubre `nombra_a`, y confundirlos haría que un nombre completo
    entrara por la puerta de la coincidencia parcial, que es más débil.
    """
    del_nombre = palabras(nombre)
    if not del_nombre:
        return False
    comunes = del_nombre & palabras(texto)
    return len(comunes) >= PALABRAS_MINIMAS and comunes != del_nombre
