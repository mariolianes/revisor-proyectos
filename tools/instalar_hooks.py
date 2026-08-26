"""Instala el hook de pre-commit que ejecuta el verificador de gobernanza."""

import stat
import sys
from pathlib import Path

HOOK = """#!/bin/sh
# Verificador de gobernanza. Instalado por tools/instalar_hooks.py
python tools/verificar_gobernanza.py --staged
estado=$?
if [ $estado -ne 0 ]; then
    echo ""
    echo "Commit detenido: hay infracciones de gobernanza."
    echo "Corrigelas, o usa 'git commit --no-verify' si sabes lo que haces."
    exit 1
fi
exit 0
"""


def main() -> int:
    raiz = Path(__file__).resolve().parents[1]
    carpeta = raiz / ".git" / "hooks"
    if not carpeta.is_dir():
        print(f"No encuentro {carpeta}. ¿Estas en un repositorio git?")
        return 1

    ruta = carpeta / "pre-commit"
    ruta.write_text(HOOK, encoding="utf-8", newline="\n")
    ruta.chmod(ruta.stat().st_mode | stat.S_IEXEC)
    print(f"Hook instalado en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
