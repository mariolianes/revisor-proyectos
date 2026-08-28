"""La entrega nueva frente a la anterior.

El §5.1 prohíbe tres cosas que se detectan contrastando textos: entregar
solo los capítulos nuevos, repetir la versión anterior sin progreso real, y
eliminar contenido ya validado. Ninguna necesita entender el texto, solo
compararlo, así que aquí no interviene ningún modelo de lenguaje.

Los avisos son avisos. No dicen que el alumno haya hecho algo mal: dicen
que hay algo que mirar. Quien decide es el docente.
"""

import difflib
import re
import unicodedata

from pydantic import BaseModel

# Un párrafo más corto que esto es una numeración, un encabezado suelto o
# un pie de página. Contarlo como contenido ensucia las proporciones.
CARACTERES_MINIMOS = 25

# Dos párrafos son el mismo si se parecen tanto: deja pasar el retoque de
# una palabra y no confunde dos párrafos distintos del mismo apartado.
PARECIDO_MINIMO = 0.85

# Por debajo de esto, la entrega nueva no contiene el trabajo anterior.
CONSERVADO_MINIMO = 0.30


class Evolucion(BaseModel):
    """Qué se conserva, qué se ha añadido y qué ha desaparecido."""

    proporcion_conservada: float = 0.0
    proporcion_nueva: float = 0.0
    parrafos_eliminados: int = 0
    parrafos_nuevos: int = 0
    avisos: list[str] = []


def normalizar(texto: str) -> list[str]:
    """Párrafos con contenido, en minúsculas, sin tildes ni espacios de sobra."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    parrafos = []
    for crudo in re.split(r"\n\s*\n", sin_tildes):
        limpio = " ".join(crudo.lower().split())
        if len(limpio) >= CARACTERES_MINIMOS:
            parrafos.append(limpio)
    return parrafos


def _esta_en(parrafo: str, otros: list[str]) -> bool:
    """Si el párrafo aparece en la otra lista, admitiendo retoques menores."""
    return bool(difflib.get_close_matches(parrafo, otros, n=1, cutoff=PARECIDO_MINIMO))


def comparar(texto_anterior: str, texto_nuevo: str) -> Evolucion:
    """Contrasta las dos entregas y avisa de lo que el §5.1 prohíbe."""
    anteriores = normalizar(texto_anterior)
    nuevos = normalizar(texto_nuevo)

    if not anteriores:
        # Primera entrega: no hay con qué comparar y no se finge que sí.
        return Evolucion(parrafos_nuevos=len(nuevos))

    conservados = [parrafo for parrafo in anteriores if _esta_en(parrafo, nuevos)]
    añadidos = [parrafo for parrafo in nuevos if not _esta_en(parrafo, anteriores)]

    proporcion_conservada = len(conservados) / len(anteriores)
    proporcion_nueva = len(añadidos) / len(nuevos) if nuevos else 0.0
    eliminados = len(anteriores) - len(conservados)

    avisos = []
    if proporcion_conservada < CONSERVADO_MINIMO:
        avisos.append(
            "La entrega no parece incluir el trabajo anterior: solo se "
            f"reconoce el {proporcion_conservada:.0%} de lo que había. El §5.1 "
            "pide el documento completo en cada fase, no solo lo nuevo."
        )
    elif eliminados:
        avisos.append(
            f"Han desaparecido {eliminados} párrafos que estaban en la entrega "
            "anterior. El §5.1 no admite eliminar contenido ya validado sin "
            "justificarlo."
        )

    # Identidad exacta, no parecido. Con el umbral de PARECIDO_MINIMO un
    # párrafo retocado cuenta como conservado y no cuenta como nuevo, así
    # que medir el progreso con esas proporciones marcaría como estancada
    # una entrega que sí se ha corregido.
    if anteriores == nuevos:
        avisos.append(
            "La entrega llega sin cambios respecto a la anterior: no se "
            "aprecia progreso."
        )

    return Evolucion(
        proporcion_conservada=proporcion_conservada,
        proporcion_nueva=proporcion_nueva,
        parrafos_eliminados=eliminados,
        parrafos_nuevos=len(añadidos),
        avisos=avisos,
    )
