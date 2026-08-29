"""Aplicación del revisor: el editor de criterios y el flujo de entregas.

Escucha solo en 127.0.0.1: escribe en el disco y ejecuta git.
"""

from pathlib import Path
from threading import Lock

from fastapi import FastAPI


def crear_app(raiz: Path, configuracion=None, almacen=None, proveedor=None) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta.

    `configuracion`, `almacen` y `proveedor` se inyectan en las pruebas. En
    uso normal `configuracion` y `almacen` se cargan del entorno -y si no
    hay credenciales el almacén es el de memoria: el sistema arranca igual
    y lo avisa por la interfaz-, y `proveedor` lo elige `crear_proveedor`
    según haya o no clave y modelo configurados: el real si los hay, el
    simulado en cualquier otro caso.
    """
    from fastapi.responses import JSONResponse

    from backend.analisis import crear_proveedor
    from backend.api import analisis, documentos, edicion, entregas, estado
    from backend.configuracion import cargar
    from backend.persistencia import crear_almacen
    from backend.persistencia.supabase import ChoqueDeAlmacen, ErrorDeAlmacen

    app = FastAPI(title="Revisor de proyectos", docs_url=None, redoc_url=None)
    app.state.raiz = raiz
    app.state.configuracion = configuracion or cargar(raiz)
    app.state.almacen = almacen or crear_almacen(app.state.configuracion)
    app.state.proveedor = proveedor or crear_proveedor(app.state.configuracion)
    # Los análisis de esta sesión. Persistirlos en las tablas es la Task 12;
    # hasta entonces, pedir la ficha de una entrega analizada no puede
    # volver a llamar al motor, y esta caché en memoria es lo que evita esa
    # segunda llamada.
    app.state.correcciones = {}
    # El candado que impide que un segundo clic sobre la misma entrega
    # lance una segunda llamada al motor mientras la primera sigue en
    # marcha. Ver el docstring de `backend/api/analisis.py`.
    app.state.candado_analisis = Lock()
    app.state.analisis_en_curso = set()

    @app.exception_handler(ErrorDeAlmacen)
    def almacen_caido(peticion, fallo: ErrorDeAlmacen) -> JSONResponse:
        """El mensaje del almacén llega entero al docente.

        `ErrorDeAlmacen` se levanta con un texto en castellano que dice qué
        ha pasado y qué mirar. Sin este manejador, cualquier fallo de
        Supabase -la red caída, la clave caducada, RLS rechazando, o una
        reentrega que choca con `unique (proyecto_id, fase, version)`- se
        convertía en un «Internal Server Error» y ese texto se perdía por el
        camino.

        Va en la aplicación y no en cada endpoint a propósito: así cubre
        también los que se escriban después, que es justo donde se olvidaría.
        El campo se llama `detail` porque es el que ya usa `HTTPException` y
        el que el frontend lee para pintar el aviso; un nombre distinto
        obligaría al frontend a aprender una segunda forma de error.

        503 es «vuelve a intentarlo»: la red caída, la clave caducada o RLS
        rechazando pueden dejar de pasar solos. Un choque con una
        restricción `unique` no, y por eso tiene su propio manejador aquí
        abajo.
        """
        return JSONResponse(status_code=503, content={"detail": str(fallo)})

    @app.exception_handler(ChoqueDeAlmacen)
    def almacen_en_conflicto(peticion, fallo: ChoqueDeAlmacen) -> JSONResponse:
        """Un choque de datos es 409, no 503.

        Reintentar un choque con una restricción `unique` da exactamente el
        mismo choque: no es una indisponibilidad del servicio, y decir 503
        le pide al navegador -y a cualquier proxy o reintento automático que
        se ponga por delante mañana- justo lo único que no sirve de nada. El
        profesor tiene que cambiar algo, y el mensaje le dice qué.

        Starlette elige el manejador recorriendo la jerarquía de la
        excepción, así que este gana sobre el de `ErrorDeAlmacen` por ser el
        de la clase más concreta. Si algún día se borra este manejador, los
        choques volverían a salir como 503 sin que nada fallara: lo que lo
        impide son los dos tests que comprueban que los dos códigos no se
        confunden.
        """
        return JSONResponse(status_code=409, content={"detail": str(fallo)})

    app.include_router(documentos.router)
    app.include_router(edicion.router)
    app.include_router(estado.router)
    app.include_router(entregas.router)
    app.include_router(analisis.router)

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
