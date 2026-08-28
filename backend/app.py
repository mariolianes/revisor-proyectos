"""Aplicación del revisor: el editor de criterios y el flujo de entregas.

Escucha solo en 127.0.0.1: escribe en el disco y ejecuta git.
"""

from pathlib import Path

from fastapi import FastAPI


def crear_app(raiz: Path, configuracion=None, almacen=None) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta.

    `configuracion` y `almacen` se inyectan en las pruebas. En uso normal se
    cargan del entorno, y si no hay credenciales el almacén es el de
    memoria: el sistema arranca igual y lo avisa por la interfaz.
    """
    from backend.api import documentos, edicion, entregas, estado
    from backend.configuracion import cargar
    from backend.persistencia import crear_almacen

    app = FastAPI(title="Revisor de proyectos", docs_url=None, redoc_url=None)
    app.state.raiz = raiz
    app.state.configuracion = configuracion or cargar(raiz)
    app.state.almacen = almacen or crear_almacen(app.state.configuracion)

    app.include_router(documentos.router)
    app.include_router(edicion.router)
    app.include_router(estado.router)
    app.include_router(entregas.router)

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
