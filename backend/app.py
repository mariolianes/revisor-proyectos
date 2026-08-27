"""Aplicación del editor de criterios.

Escucha solo en 127.0.0.1: escribe en el disco y ejecuta git.
"""

from pathlib import Path

from fastapi import FastAPI


def crear_app(raiz: Path) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta."""
    app = FastAPI(title="Editor de criterios", docs_url=None, redoc_url=None)
    app.state.raiz = raiz

    @app.get("/api/salud")
    def salud() -> dict[str, str]:
        return {"estado": "vivo", "raiz": str(raiz)}

    return app
