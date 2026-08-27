"""Arranca el editor en local.

    python -m backend
"""

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from backend.app import crear_app

HOST = "127.0.0.1"
PUERTO = 8000


def _abrir_navegador_cuando_escuche() -> None:
    """Abre el navegador en cuanto el puerto empieza a aceptar conexiones.

    No basta con engancharse al evento de arranque de FastAPI: uvicorn
    dispara ese evento ANTES de enlazar el socket (ver
    `Server.startup()` en la librería: primero `lifespan.startup()`,
    luego `loop.create_server()`), así que abrir ahí seguiría siendo una
    carrera, solo que movida de sitio. Sondear el puerto de verdad, en un
    hilo aparte, es lo único determinista: el navegador no se abre hasta
    que una conexión real tiene éxito.
    """
    while True:
        try:
            with socket.create_connection((HOST, PUERTO), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    webbrowser.open(f"http://{HOST}:{PUERTO}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    threading.Thread(target=_abrir_navegador_cuando_escuche, daemon=True).start()

    try:
        # Solo 127.0.0.1: esta aplicación escribe en el disco y ejecuta git.
        uvicorn.run(crear_app(raiz), host=HOST, port=PUERTO, log_level="warning")
    except Exception as error:
        # El .cmd que lanza esto corre en una consola que se cierra sola al
        # terminar el script: sin este mensaje, el profesor solo vería un
        # parpadeo y ningún motivo.
        print(f"\nEl servidor terminó con un error: {error}")
        sys.exit(1)
