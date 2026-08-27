"""Inferencia literal de valores al cambiar la prosa.

Deliberadamente corta de alcance. Solo propone un valor nuevo cuando la
correspondencia con el texto es literal e inequívoca; en cualquier otro caso
devuelve el criterio marcado para que lo mire el docente.

Inferir de más aquí sería fabricar un criterio que nadie decidió, que es
exactamente lo que R1 existe para impedir.
"""

import re
from pathlib import Path

from pydantic import BaseModel

from backend.servicios.dependencias import criterios_de
from backend.servicios.repositorio import leer_seccion


class Propuesta(BaseModel):
    """Qué le pasa a un valor de un criterio cuando cambia su sección."""

    fichero: str
    identificador: str
    clave: str
    valor_actual: str
    valor_propuesto: str | None
    motivo: str


def _es_numero(valor: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", valor))


# Límite derecho de un número aislado: ni pegado a otra letra/dígito (evita
# colarse dentro de "115" al buscar "11"), ni seguido de un separador decimal
# con más dígitos detrás (evita colarse dentro de "20.5" al buscar "20"). Un
# punto o coma de fin de frase sin dígito detrás sí cuenta como límite válido:
# "Arial 11." tiene que reconocer el 11.
_LIMITE_IZQUIERDO = r"(?<![\w.,])"
_LIMITE_DERECHO = r"(?!\w)(?![.,]\d)"
_PATRON_NUMERO_AISLADO = re.compile(rf"{_LIMITE_IZQUIERDO}\d+(?:[.,]\d+)?{_LIMITE_DERECHO}")


def _apariciones(valor: str, texto: str) -> int:
    patron = rf"{_LIMITE_IZQUIERDO}{re.escape(valor)}{_LIMITE_DERECHO}"
    return len(re.findall(patron, texto))


def _numeros_aislados(texto: str) -> set[str]:
    """Todos los números que aparecen sueltos (no como parte de otro token) en el texto."""
    return set(_PATRON_NUMERO_AISLADO.findall(texto))


def _candidatos_nuevos(texto_viejo: str, texto_nuevo: str) -> list[str]:
    """Números que aparecen en el texto nuevo y no aparecían en el viejo.

    Son los que podrían ocupar el sitio que dejó libre el valor que ha
    desaparecido. Si hay más de uno, no hay forma de saber cuál es el
    correcto sin que lo diga el docente.
    """
    return sorted(_numeros_aislados(texto_nuevo) - _numeros_aislados(texto_viejo))


def proponer(raiz: Path, ancla: str, texto_nuevo: str) -> list[Propuesta]:
    """Qué se propone cambiar en los criterios que derivan de esta sección."""
    seccion = leer_seccion(raiz, ancla)
    if seccion is None:
        return []
    texto_viejo = seccion.texto

    propuestas: list[Propuesta] = []
    for criterio in criterios_de(raiz, ancla):
        for clave, valor in criterio.valores.items():
            propuestas.append(_evaluar(criterio, clave, valor, texto_viejo, texto_nuevo))
    return propuestas


def _evaluar(criterio, clave: str, valor: str, texto_viejo: str, texto_nuevo: str) -> Propuesta:
    """Decide qué proponer para un valor concreto, o por qué no proponer nada."""
    def resultado(propuesto: str | None, motivo: str) -> Propuesta:
        return Propuesta(
            fichero=criterio.fichero,
            identificador=criterio.identificador,
            clave=clave,
            valor_actual=valor,
            valor_propuesto=propuesto,
            motivo=motivo,
        )

    # Primero, si el valor ni siquiera aparece literalmente una vez en el
    # texto anterior: da igual que sea o no un número, no hay nada de lo que
    # partir. Comprobarlo antes que la numericidad importa para los valores
    # que no son números (listas, texto libre): también ellos deben salir
    # con "no aparece literalmente" cuando ese es el motivo real, no con un
    # "no es un número" que oculta el motivo verdadero.
    if _apariciones(valor, texto_viejo) != 1:
        return resultado(None, (
            "El valor no aparece literalmente una sola vez en el texto anterior, "
            "así que no se puede saber a qué parte corresponde. Revísalo a mano."
        ))

    if not _es_numero(valor):
        return resultado(None, (
            "Este valor no es un número, así que su relación con el texto no es "
            "literal. Revisa a mano si el cambio le afecta."
        ))

    if _apariciones(valor, texto_nuevo) == 1:
        return resultado(None, "El valor sigue apareciendo igual en el texto nuevo.")

    candidatos = _candidatos_nuevos(texto_viejo, texto_nuevo)
    if not candidatos:
        return resultado(None, (
            "El valor ha desaparecido del texto y no hay uno nuevo que ocupe "
            "su lugar de forma clara. Decide tú qué debe decir el criterio."
        ))
    if len(candidatos) > 1:
        return resultado(None, (
            "Hay más de un número que podría corresponder a este valor. "
            "Elige tú cuál."
        ))

    candidato = candidatos[0]
    return resultado(candidato, (
        f"El texto decía «{valor}» y ahora dice «{candidato}» en el mismo sitio."
    ))
