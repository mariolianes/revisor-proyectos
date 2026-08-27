"""Arranca el editor en local.

    python -m backend
"""

from pathlib import Path

import uvicorn

from backend.app import crear_app

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    # Solo 127.0.0.1: esta aplicación escribe en el disco y ejecuta git.
    uvicorn.run(crear_app(raiz), host="127.0.0.1", port=8000, log_level="warning")
