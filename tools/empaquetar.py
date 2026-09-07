"""Construye el ejecutable que recibe el docente para la beta.

Un solo fichero, que él abre con doble clic. Sin instalar Python, sin
instalar Node, sin línea de órdenes. Todo lo que el programa necesita para
funcionar viaja dentro; lo suyo -sus claves y la ruta de sus entregas- se
queda al lado, en un `.env` que sobrevive a las actualizaciones.

    python tools/empaquetar.py

Deja `dist/RevisorDeProyectos.exe`. Para dárselo, se copia ese fichero y
nada más.

**Qué NO viaja dentro, y es deliberado:**

- El `.env`. Son sus claves. Si viajaran dentro del ejecutable, cualquiera
  que lo recibiera se llevaría la clave de OpenAI y la de la base de datos.
- Los trabajos de los alumnos, obviamente.
- `docs/decisions.md`, `docs/changes/` y las pruebas: son la memoria del
  desarrollo, no el programa. Él no las necesita para corregir.

**Qué sí viaja, y por qué:** los criterios (`criteria/`), la prosa normativa
(`docs/maestro/`), la configuración (`config/`) y el frontend compilado. Los
cuatro son el programa: si se actualiza, se actualizan con él.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOMBRE = "RevisorDeProyectos"

# Lo que se mete dentro del ejecutable, con la ruta que tendrá al
# desempaquetarse. `backend/empaquetado.py` es quien luego la encuentra.
RECURSOS = [
    ("criteria", "criteria"),
    ("config", "config"),
    ("docs/maestro", "docs/maestro"),
    ("frontend/dist", "frontend/dist"),
]

# PyInstaller no ve lo que se importa dentro de una función o por nombre.
# Estos tres se cargan así, y sin declararlos el ejecutable arranca y falla
# al primer análisis, que es el peor momento para descubrirlo.
OCULTOS = ["uvicorn.logging", "uvicorn.protocols.http.h11_impl", "encodings.idna"]


def paso(texto: str) -> None:
    print(f"\n=== {texto} ===", flush=True)


def compilar_el_frontend() -> None:
    """Sin esto, el ejecutable serviría la interfaz que hubiera compilada de
    antes -o ninguna-. Es el mismo motivo por el que `editor.cmd` compila
    siempre: una interfaz vieja con un backend nuevo no da ningún error, solo
    pantallas que no cuadran."""
    paso("Compilando la interfaz")
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit(
            "No se encuentra npm. Hace falta para compilar la interfaz que "
            "va dentro del ejecutable. Instala Node.js desde "
            "https://nodejs.org/ y vuelve a intentarlo."
        )
    subprocess.run([npm, "install"], cwd=RAIZ / "frontend", check=True, shell=True)
    subprocess.run([npm, "run", "build"], cwd=RAIZ / "frontend", check=True, shell=True)
    if not (RAIZ / "frontend" / "dist" / "index.html").is_file():
        raise SystemExit("La compilación no ha dejado frontend/dist/index.html.")


def construir() -> Path:
    paso("Empaquetando")
    separador = ";" if sys.platform == "win32" else ":"
    orden = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--name", NOMBRE,
        "--distpath", str(RAIZ / "dist"),
        "--workpath", str(RAIZ / "build"),
        "--specpath", str(RAIZ / "build"),
        "--noconfirm",
    ]
    for origen, destino in RECURSOS:
        ruta = RAIZ / origen
        if not ruta.exists():
            raise SystemExit(f"Falta {origen}: no se puede empaquetar sin ello.")
        orden += ["--add-data", f"{ruta}{separador}{destino}"]
    for modulo in OCULTOS:
        orden += ["--hidden-import", modulo]
    orden.append(str(RAIZ / "backend" / "__main__.py"))

    subprocess.run(orden, check=True)
    ejecutable = RAIZ / "dist" / (f"{NOMBRE}.exe" if sys.platform == "win32" else NOMBRE)
    if not ejecutable.is_file():
        raise SystemExit("PyInstaller no ha dejado el ejecutable donde se esperaba.")
    return ejecutable


def main() -> None:
    compilar_el_frontend()
    ejecutable = construir()
    tamano = ejecutable.stat().st_size / (1024 * 1024)
    paso("Listo")
    print(f"{ejecutable}  ({tamano:.0f} MB)")
    print()
    print("Para dárselo al docente: cópiale ese fichero y el .env de ejemplo.")
    print("El .env va AL LADO del ejecutable, no dentro: son sus claves, y")
    print("así sobreviven cuando le mandes una versión nueva del programa.")


if __name__ == "__main__":
    main()
