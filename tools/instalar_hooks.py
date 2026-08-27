"""Instala el hook de pre-commit que ejecuta el verificador de gobernanza."""

import stat
import sys
from pathlib import Path

# Un verificador que no llega a ejecutarse tiene que decirlo con sus palabras.
# Anunciar "hay infracciones" cuando lo que falta es el interprete manda a
# quien commitea a buscar un problema que no existe, y le sugiere --no-verify
# como remedio de una instalacion rota.
HOOK = """#!/bin/sh
# Verificador de gobernanza. Instalado por tools/instalar_hooks.py

no_puedo_ejecutarlo() {
    echo ""
    echo "Commit detenido: no se ha podido ejecutar el verificador de gobernanza."
    echo "$1"
    echo "Esto no es una infraccion: es que la herramienta no ha llegado a"
    echo "arrancar. Revisa la instalacion segun 'Puesta en marcha' de"
    echo "GOVERNANCE.md; si usas un entorno virtual, activalo antes."
    exit 1
}

if ! command -v python > /dev/null 2>&1; then
    no_puedo_ejecutarlo "No encuentro 'python' en el PATH."
fi

# Codigos del verificador: 0 conforme, 1 hay infracciones, 2 no ha podido
# comprobar nada. El 127 lo pone el propio shell cuando no encuentra la orden.
python tools/verificar_gobernanza.py --staged
estado=$?

if [ $estado -eq 127 ]; then
    no_puedo_ejecutarlo "El interprete de Python no se ha podido ejecutar."
fi

if [ $estado -eq 2 ]; then
    no_puedo_ejecutarlo "El verificador ha fallado antes de comprobar nada."
fi

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
