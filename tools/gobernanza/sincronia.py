"""R2: la prosa manda. Detecta que una seccion cambio sin revisar su derivado.

El mecanismo es deliberadamente tosco: se guarda el hash del texto de cada
seccion referenciada por algun criterio. Si la prosa cambia, el hash deja de
coincidir y el verificador obliga a mirar el YAML derivado antes de seguir.
No decide si el YAML esta bien: obliga a que alguien lo mire.
"""

import hashlib
import json
import re
from pathlib import Path

from tools.gobernanza.criterios import entradas_de
from tools.gobernanza.resultado import Infraccion

FICHERO_SINCRONIA = "criteria/v2026-2027/.sincronia.json"
PATRON_CUALQUIER_ANCLA = re.compile(r"^<!-- ancla: (?:maestro|indice|guia)#[a-z0-9-]+ -->$", re.M)

_DOCUMENTOS = {
    "maestro": "01-documento-maestro.md",
    "indice": "02-indice-comentado.md",
    "guia": "03-guia-desarrollo.md",
}


def _normalizar(texto: str) -> str:
    """Colapsa espacios para que reformatear no cuente como cambio de criterio."""
    return " ".join(texto.split())


def hash_de_seccion(raiz: Path, ancla: str) -> str | None:
    """SHA-256 abreviado del texto de una seccion, de su ancla a la siguiente."""
    documento, _, _ = ancla.partition("#")
    nombre = _DOCUMENTOS.get(documento)
    if nombre is None:
        return None
    ruta = raiz / "docs" / "maestro" / nombre
    if not ruta.is_file():
        return None

    texto = ruta.read_text(encoding="utf-8")
    marca = f"<!-- ancla: {ancla} -->"
    inicio = texto.find(marca)
    if inicio == -1:
        return None

    resto = texto[inicio + len(marca):]
    siguiente = PATRON_CUALQUIER_ANCLA.search(resto)
    cuerpo = resto[:siguiente.start()] if siguiente else resto

    return hashlib.sha256(_normalizar(cuerpo).encode("utf-8")).hexdigest()[:16]


def _anclas_referenciadas(raiz: Path) -> set[str]:
    """Anclas que algun criterio usa como fuente."""
    referenciadas: set[str] = set()
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return referenciadas
    for ruta in sorted(carpeta.rglob("*.yaml")):
        for entrada in entradas_de(ruta):
            fuente = entrada.get("fuente")
            if isinstance(fuente, str):
                referenciadas.add(fuente)
    return referenciadas


def calcular_sincronia(raiz: Path) -> dict[str, str]:
    """Hash actual de cada ancla referenciada por algun criterio."""
    resultado: dict[str, str] = {}
    for ancla in sorted(_anclas_referenciadas(raiz)):
        h = hash_de_seccion(raiz, ancla)
        if h is not None:
            resultado[ancla] = h
    return resultado


def escribir_sincronia(raiz: Path) -> None:
    """Regenera el registro. Ejecutar solo tras revisar el YAML derivado."""
    ruta = raiz / FICHERO_SINCRONIA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(calcular_sincronia(raiz), indent=2, ensure_ascii=False)
    ruta.write_text(contenido + "\n", encoding="utf-8")


def verificar_r2(raiz: Path) -> list[Infraccion]:
    """Comprueba que ninguna seccion cambio sin revisarse su derivado."""
    ruta = raiz / FICHERO_SINCRONIA
    actual = calcular_sincronia(raiz)

    if not ruta.is_file():
        if not actual:
            return []
        return [Infraccion(
            regla="R2",
            fichero=FICHERO_SINCRONIA,
            detalle=(
                f"No existe el registro de sincronia ({FICHERO_SINCRONIA}). "
                "Generalo con 'python tools/verificar_gobernanza.py --sellar' "
                "despues de comprobar que los criterios reflejan la prosa."
            ),
        )]

    registrado = json.loads(ruta.read_text(encoding="utf-8"))
    infracciones: list[Infraccion] = []

    for ancla, h in sorted(actual.items()):
        anterior = registrado.get(ancla)
        if anterior is None:
            infracciones.append(Infraccion(
                regla="R2",
                fichero=FICHERO_SINCRONIA,
                detalle=(
                    f"'{ancla}' se referencia desde criteria/ pero no esta en el "
                    f"registro. Sella tras revisar el derivado con "
                    f"'python tools/verificar_gobernanza.py --sellar'."
                ),
            ))
        elif anterior != h:
            infracciones.append(Infraccion(
                regla="R2",
                fichero=FICHERO_SINCRONIA,
                detalle=(
                    f"La seccion '{ancla}' ha cambiado en docs/maestro/ y su "
                    f"derivado en criteria/ no se ha revisado. Comprueba si el "
                    f"cambio afecta a los criterios que la citan, ajustalos si "
                    f"procede, y sella con "
                    f"'python tools/verificar_gobernanza.py --sellar'."
                ),
            ))

    for ancla in sorted(set(registrado) - set(actual)):
        infracciones.append(Infraccion(
            regla="R2",
            fichero=FICHERO_SINCRONIA,
            detalle=(
                f"'{ancla}' esta en el registro pero ya no la referencia ningun "
                f"criterio. Si era intencionado, sella para limpiarlo con "
                f"'python tools/verificar_gobernanza.py --sellar'."
            ),
        ))

    return infracciones
