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

    Cuenta cuántos números ha traído la sección, sin importar dónde: una
    numeración de subapartado, un margen, cualquier cifra nueva de la
    prosa cuenta igual. Por eso esta función NUNCA decide, por sí sola, qué
    proponer -- solo sirve para elegir el motivo cuando el localizador de
    `_candidato` (que sí mira el sitio exacto) no ha encontrado nada:
    si no hay ningún número nuevo, el valor sencillamente desapareció; si
    hay alguno, puede que sea el sustituto pero no se puede dar por hecho
    sin verlo en su sitio.
    """
    return sorted(_numeros_aislados(texto_nuevo) - _numeros_aislados(texto_viejo))


def _contexto(valor: str, texto: str) -> tuple[str, str] | None:
    """Las tres palabras antes y después de la única aparición del valor."""
    patron = rf"{_LIMITE_IZQUIERDO}{re.escape(valor)}{_LIMITE_DERECHO}"
    encontrado = re.search(patron, texto)
    if encontrado is None:
        return None
    antes = texto[:encontrado.start()].split()[-3:]
    despues = texto[encontrado.end():].split()[:3]
    return " ".join(antes), " ".join(despues)


def _candidato(valor_viejo: str, texto_viejo: str, texto_nuevo: str) -> str | None:
    """El número que ocupa en el texto nuevo el mismo sitio que ocupaba el viejo.

    Esta es la ÚNICA vía por la que `proponer` puede devolver un valor: se
    localiza el sitio exacto del valor viejo por las tres palabras que lo
    precedían, y solo si ese mismo sitio tiene en el texto nuevo un único
    número se propone. Un número nuevo que ha aparecido en cualquier OTRA
    parte de la sección (una numeración de subapartado, un margen, la cifra
    de otro criterio) no cuenta como candidato: no está en el sitio.
    """
    contexto = _contexto(valor_viejo, texto_viejo)
    if contexto is None:
        return None
    antes, despues = contexto
    if not antes:
        return None

    patron = rf"{re.escape(antes)}\s+(\d+(?:[.,]\d+)?)"
    hallados = re.findall(patron, texto_nuevo)
    if len(hallados) == 1:
        return hallados[0]
    return None


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

    # "Sigue apareciendo" cubre tanto el caso normal (una vez) como el caso
    # en que ahora aparece dos o más veces: en ambos, el valor sigue en el
    # texto, así que no ha "desaparecido" y no hay que proponer nada.
    if _apariciones(valor, texto_nuevo) >= 1:
        return resultado(None, "El valor sigue apareciendo igual en el texto nuevo.")

    # El localizador por contexto es la única vía para proponer: es lo que
    # da derecho a decir "en el mismo sitio". Si no encuentra un candidato
    # único ahí, no se propone nada -- da igual qué números nuevos haya
    # sueltos por el resto de la sección.
    candidato = _candidato(valor, texto_viejo, texto_nuevo)
    if candidato is not None:
        return resultado(candidato, (
            f"El texto decía «{valor}» y ahora dice «{candidato}» en el mismo sitio."
        ))

    # El localizador no encontró nada: _candidatos_nuevos solo se usa aquí,
    # para elegir QUÉ motivo dar, nunca para proponer un valor.
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
    return resultado(None, (
        "Ha aparecido un número nuevo en el texto, pero no ocupa el mismo "
        "sitio que tenía este valor, así que no se puede dar por sentado que "
        "sea su sustituto. Revísalo a mano."
    ))
