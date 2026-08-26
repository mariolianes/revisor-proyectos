"""Verificador de gobernanza del repositorio.

    python tools/verificar_gobernanza.py              todo el arbol
    python tools/verificar_gobernanza.py --staged     solo lo que se va a commitear
    python tools/verificar_gobernanza.py --sellar     regenera el registro de R2

Codigos de salida: 0 conforme, 1 hay infracciones.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Este fichero se invoca como script ("python tools/verificar_gobernanza.py"),
# y en ese caso Python solo pone tools/ en la ruta de busqueda, no la raiz del
# repositorio: sin esta linea no encontraria el paquete tools.gobernanza.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.gobernanza.cambios import (  # noqa: E402
    verificar_cambio_acompanado,
    verificar_formato_cambios,
)
from tools.gobernanza.criterios import verificar_r1, verificar_r3  # noqa: E402
from tools.gobernanza.privacidad import verificar_r6  # noqa: E402
from tools.gobernanza.resultado import Infraccion, formatear  # noqa: E402
from tools.gobernanza.sincronia import escribir_sincronia, verificar_r2  # noqa: E402
from tools.gobernanza.versiones import verificar_r4  # noqa: E402


def ficheros_en_staging(raiz: Path) -> list[str]:
    """Ficheros que el proximo commit incluira."""
    salida = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=True,
    )
    return [linea for linea in salida.stdout.splitlines() if linea.strip()]


def ejecutar(raiz: Path, ficheros: list[str], solo_staged: bool) -> list[Infraccion]:
    """Ejecuta las seis reglas mecanizables y devuelve todas las infracciones."""
    objetivos = ficheros_en_staging(raiz) if solo_staged else list(ficheros)

    infracciones: list[Infraccion] = []
    infracciones += verificar_r1(raiz)
    infracciones += verificar_r2(raiz)
    infracciones += verificar_r3(raiz)
    infracciones += verificar_r4(raiz)
    infracciones += verificar_formato_cambios(raiz)
    infracciones += verificar_r6(raiz, objetivos)

    # R5 solo tiene sentido sobre un conjunto concreto de ficheros: sin saber
    # que se esta commiteando, no se puede exigir que lo acompane un cambio.
    if objetivos:
        infracciones += verificar_cambio_acompanado(raiz, objetivos)

    return infracciones


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de gobernanza.")
    parser.add_argument("--staged", action="store_true",
                        help="verificar solo los ficheros en staging")
    parser.add_argument("--sellar", action="store_true",
                        help="regenerar el registro de sincronia de R2")
    args = parser.parse_args()

    raiz = Path(__file__).resolve().parents[1]

    if args.sellar:
        escribir_sincronia(raiz)
        print("Registro de sincronia regenerado.")
        print("Hazlo solo despues de comprobar que los criterios reflejan la prosa.")
        return 0

    infracciones = ejecutar(raiz, ficheros=[], solo_staged=args.staged)
    print(formatear(infracciones))
    return 1 if infracciones else 0


if __name__ == "__main__":
    sys.exit(main())
