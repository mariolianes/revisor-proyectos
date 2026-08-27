"""Aplicación del editor de criterios.

Escucha solo en 127.0.0.1: escribe en el disco y ejecuta git.
"""

from pathlib import Path

from fastapi import FastAPI


def crear_app(raiz: Path) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta."""
    from backend.api import documentos, edicion, estado

    app = FastAPI(title="Editor de criterios", docs_url=None, redoc_url=None)
    app.state.raiz = raiz

    app.include_router(documentos.router)
    app.include_router(edicion.router)
    app.include_router(estado.router)

    @app.get("/api/salud")
    def salud() -> dict[str, str]:
        return {"estado": "vivo", "raiz": str(raiz)}

    # El front compilado se sirve desde el propio backend: una sola pieza
    # que arrancar, no dos.
    dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if dist.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app
