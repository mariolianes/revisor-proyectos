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

# El registro vive en criteria/, no dentro de una versión, porque
# '_anclas_referenciadas' recorre criteria/ entero: el alcance del fichero y
# el alcance del recorrido tienen que ser el mismo. Guardarlo dentro de una
# versión significaba escribir la union de las anclas de todas las versiones
# dentro de una sola, y en cuanto exista una segunda -que es justo lo que R4
# prescribe para cualquier cambio- sellar tocaria una carpeta congelada.
FICHERO_SINCRONIA = "criteria/.sincronia.json"
# Bug encontrado el 2026-08-31: a "calibracion" se le dio fuente propia en
# _DOCUMENTOS (más abajo) para el §14.1, pero este patrón se quedó con solo
# los tres primeros documentos. Como docs/maestro/04-calibracion.md no
# contiene NINGÚN ancla de maestro, indice o guia, `hash_de_seccion` nunca
# encontraba un límite dentro de ese fichero: el "cuerpo" de cualquier
# sección citada de la calibración se extendía siempre hasta el final del
# documento entero, nunca solo hasta la siguiente sección. El efecto no era
# silencioso -R2 no dejaba pasar un cambio real sin avisar-, pero sí un
# falso positivo permanente: añadir contenido en cualquier punto posterior
# del documento (una sección nueva al final, por ejemplo) invalidaba el
# hash de TODAS las secciones de calibración citadas anteriores a ese
# punto, aunque su prosa no hubiera cambiado ni una letra. Ver
# tests/gobernanza/test_sincronia.py::test_una_seccion_de_calibracion_no_se_ve_alterada_por_un_cambio_posterior_en_otra
# para la regresión.
# Lo encontraron dos trabajos distintos el mismo dia, por separado, cada uno
# desde su lado: la calibracion del 2026-08-31 toco el §2 y el sello del §4
# cambio sin que su texto se hubiera tocado. Ver también
# test_hash_no_se_extiende_a_la_siguiente_ancla_calibracion.
PATRON_CUALQUIER_ANCLA = re.compile(
    r"^<!-- ancla: (?:maestro|indice|guia|calibracion|decisiones)#[a-z0-9-]+ -->$", re.M
)

_DOCUMENTOS = {
    "maestro": "01-documento-maestro.md",
    "indice": "02-indice-comentado.md",
    "guia": "03-guia-desarrollo.md",
    # Nivel 5 de la jerarquía del §14.1: calibra y concreta lo que dicen los
    # tres anteriores, y nunca puede contradecirlos. Lo dice él mismo en su
    # recuadro de apertura.
    "calibracion": "04-calibracion.md",
    # Respuesta del docente del 2026-09-02 a las ocho preguntas de
    # arquitectura. Mismo nivel que el calibrador: concreta lo que los
    # tres primeros dejan abierto, y no puede contradecirlos. Donde
    # aclara una interpretación anterior -el semáforo de cuatro estados,
    # las fases del banco- manda este.
    "decisiones": "05-decisiones-arquitectura.md",
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
                f"No existe el registro de sincronía ({FICHERO_SINCRONIA}). "
                "Genéralo con 'python tools/verificar_gobernanza.py --sellar' "
                "después de comprobar que los criterios reflejan la prosa."
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
                    f"'{ancla}' se referencia desde criteria/ pero no está en el "
                    f"registro. Sella tras revisar el derivado con "
                    f"'python tools/verificar_gobernanza.py --sellar'."
                ),
            ))
        elif anterior != h:
            infracciones.append(Infraccion(
                regla="R2",
                fichero=FICHERO_SINCRONIA,
                detalle=(
                    f"La sección '{ancla}' ha cambiado en docs/maestro/ y su "
                    f"derivado en criteria/ no se ha revisado. Comprueba si el "
                    f"cambio afecta a los criterios que la citan, ajústalos si "
                    f"procede, y sella con "
                    f"'python tools/verificar_gobernanza.py --sellar'."
                ),
            ))

    for ancla in sorted(set(registrado) - set(actual)):
        infracciones.append(Infraccion(
            regla="R2",
            fichero=FICHERO_SINCRONIA,
            detalle=(
                f"'{ancla}' está en el registro pero ningún criterio la "
                f"referencia con ese nombre. O se ha retirado el criterio que "
                f"la citaba, o el ancla se ha renombrado en docs/maestro/ y el "
                f"criterio sigue citando el nombre viejo -en ese caso R1 "
                f"protesta también, y lo que hay que arreglar es la 'fuente', "
                f"no el registro-. Si era intencionado, sella para limpiarlo "
                f"con 'python tools/verificar_gobernanza.py --sellar'."
            ),
        ))

    return infracciones
