"""R4: los criterios se versionan y se congelan.

Una versión que ya se uso en una corrección aprobada no se toca nunca mas.
Esto es lo que permite reconstruir, un ano después, con que criterio exacto
se corrigio a un alumno concreto. Si hay que cambiar algo, se crea la
version siguiente.
"""

import hashlib
import json
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

SELLO = ".congelada"


def _hash_fichero(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _yaml_de(carpeta: Path) -> dict[str, str]:
    return {r.name: _hash_fichero(r) for r in sorted(carpeta.glob("*.yaml"))}


def congelar(raiz: Path, version: str) -> None:
    """Sella una versión de criterios por primera y unica vez.

    Si la versión no existe, lanza FileNotFoundError. Si ya esta congelada,
    no reescribe el sello: lanza RuntimeError, porque volver a sellar
    borraria sin dejar rastro la prueba de que una versión usada en
    correcciones aprobadas fue alterada. Ambos son errores de uso del
    programador, no infracciones de gobernanza.
    """
    carpeta = raiz / "criteria" / version
    if not carpeta.is_dir():
        raise FileNotFoundError(f"No existe la versión de criterios: {carpeta}")
    sello = carpeta / SELLO
    if sello.is_file():
        raise RuntimeError(
            f"La versión {version} ya está congelada. Una versión usada en "
            f"correcciones aprobadas no se vuelve a sellar. Si necesitas "
            f"cambiar algo, crea la versión siguiente."
        )
    contenido = json.dumps(_yaml_de(carpeta), indent=2, ensure_ascii=False)
    sello.write_text(contenido + "\n", encoding="utf-8")


def verificar_r4(raiz: Path) -> list[Infraccion]:
    """Comprueba que ninguna versión congelada ha sido alterada."""
    infracciones: list[Infraccion] = []
    carpeta_criterios = raiz / "criteria"
    if not carpeta_criterios.is_dir():
        return infracciones

    for carpeta in sorted(p for p in carpeta_criterios.iterdir() if p.is_dir()):
        sello = carpeta / SELLO
        if not sello.is_file():
            continue

        version = carpeta.name
        registrado: dict[str, str] = json.loads(sello.read_text(encoding="utf-8"))
        actual = _yaml_de(carpeta)

        for nombre, h in sorted(registrado.items()):
            relativa = (carpeta / nombre).relative_to(raiz).as_posix()
            if nombre not in actual:
                infracciones.append(Infraccion(
                    regla="R4",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' ha desaparecido de la versión congelada "
                        f"{version}. Una versión usada en correcciones aprobadas "
                        f"no se altera. Restaura el fichero y crea una nueva "
                        f"versión si necesitas cambiar algo."
                    ),
                ))
            elif actual[nombre] != h:
                infracciones.append(Infraccion(
                    regla="R4",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' ha cambiado, pero la versión {version} está "
                        f"congelada. Deshaz el cambio y crea una nueva versión: "
                        f"copia solo los *.yaml de criteria/{version}/ a la "
                        f"carpeta de la versión siguiente -el sello .congelada "
                        f"no se copia, o la versión nueva nacería cerrada-, "
                        f"modifica allí y registra el cambio en docs/changes/."
                    ),
                ))

        for nombre in sorted(set(actual) - set(registrado)):
            relativa = (carpeta / nombre).relative_to(raiz).as_posix()
            infracciones.append(Infraccion(
                regla="R4",
                fichero=relativa,
                detalle=(
                    f"'{nombre}' se ha añadido a la versión congelada {version}. "
                    f"Un criterio nuevo va en una versión nueva, no en una "
                    f"cerrada. Copia solo los *.yaml de criteria/{version}/ a la "
                    f"carpeta de la versión siguiente -el sello .congelada no se "
                    f"copia, o la versión nueva nacería cerrada-, añade allí el "
                    f"fichero y registra el cambio en docs/changes/."
                ),
            ))

    return infracciones
