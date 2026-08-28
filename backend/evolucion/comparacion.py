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

Conjunto, no multiconjunto: por qué se probó contar y se descartó
--------------------------------------------------------------------
Las firmas se comparan como conjunto: si una firma aparece en un texto, da
igual cuántas veces se repita, cuenta una sola vez. Esto tiene un coste
conocido: un bloque repetido literalmente muchas veces -una tabla de
valores casi iguales, una plantilla con huecos, una fila que se copia y se
pega- no se cuenta más de una vez, así que si un trabajo está hecho de
filas idénticas puede perder la mitad de ellas sin que se avise. Es una
limitación real, y queda documentada como tal en el ejemplo del final.

Se probó la alternativa obvia: contar las repeticiones con un
multiconjunto (``collections.Counter``) en vez de un conjunto, para que
borrar la mitad de las copias de una plantilla sí se notara. Funcionaba
para ese caso -pasar de 40 copias de una fila a 20 hacía caer la
proporción conservada a la mitad, como debía- pero rompía uno mucho más
corriente: un pie de página o un encabezado que aparece en cada página del
documento y que, al cambiar de maquetación entre una entrega y la
siguiente (más o menos páginas, un salto de columna distinto), pasa de
repetirse, por ejemplo, 150 veces a 20, sin que el alumno haya tocado ni
una palabra del cuerpo del trabajo. Con el multiconjunto, esa entrega
intacta recibía una proporción conservada por debajo del 20 % y el aviso
más grave que emite este módulo: que la entrega no parece incluir el
trabajo anterior.

Los dos casos son la misma forma -un bloque repetido N veces que pasa a
M- y esa forma no distingue, mirando solo el texto, si el bloque es
contenido (la plantilla que sí hay que proteger) o formato (el pie de
página, que no). Topar el número de repeticiones que se cuentan y
descartar las firmas muy frecuentes por considerarlas formato se probaron
también; ninguna de las dos resuelve el caso de la plantilla sin reabrir
el del pie de página.

Así que hay que elegir qué error se prefiere, y el criterio es el mismo
que en el resto del sistema: entre no ver un descuadre y acusar en falso,
se prefiere no verlo. No ver un descuadre deja trabajo al docente, que lee
la entrega de todos modos y puede notar la plantilla recortada él mismo.
Acusar en falso hace daño, porque el docente traslada el aviso al alumno
sin verificarlo primero, y aquí además el falso positivo dispara el aviso
más severo sobre un trabajo en el que no ha cambiado ni una palabra. El
conjunto se equivoca por defecto (calla ante la plantilla recortada); el
multiconjunto se equivoca por exceso (acusa al pie de página). Entre los
dos, se eligió el conjunto.

Limitación conocida: si un trabajo consiste en filas o párrafos idénticos
entre sí -no solo parecidos, literalmente iguales tras normalizar-, borrar
la mitad de esas filas no cambia ni una firma y el sistema no lo detecta.
Medido con una plantilla de una frase repetida 40 veces y recortada a 20:
como conjunto, la proporción conservada sale 100 % y no hay aviso; como
multiconjunto salía 49,6 % y sí lo había, pero ese mismo cambio hacía caer
un pie de página que pasa de 150 a 20 repeticiones -sin tocar el cuerpo-
al 15,8 %. Antes de tocar este criterio de nuevo, hay que volver a medir
los dos casos a la vez: el experimento que llevó aquí ya está hecho, y
quien lo repita sin mirar el segundo caso volverá a encontrarse con el
mismo problema.
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

    Es un conjunto, no un multiconjunto: una firma que se repite cuenta
    una sola vez. Ver el docstring del módulo para la razón -contar las
    repeticiones se probó y se descartó por un falso positivo peor.
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
