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


def _hay_alguien_escuchando(host: str, puerto: int) -> bool:
    """Si algo ya acepta conexiones en ese puerto."""
    try:
        with socket.create_connection((host, puerto), timeout=0.3):
            return True
    except OSError:
        return False


def _avisar(raiz: Path) -> None:
    """Dice por consola lo que falta, antes de que el docente lo descubra."""
    from backend.configuracion import cargar

    configuracion = cargar(raiz)
    if configuracion.carpeta_entregas is None:
        print(
            "AVISO: no hay carpeta de entregas configurada. Indícala en "
            "REVISOR_CARPETA_ENTREGAS, dentro del fichero .env, y ha de estar "
            "fuera de este repositorio."
        )
    if not (configuracion.url_supabase and configuracion.clave_supabase):
        print(
            "AVISO: sin credenciales de Supabase. Lo que registres se pierde "
            "al cerrar el programa."
        )


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
    while not _hay_alguien_escuchando(HOST, PUERTO):
        time.sleep(0.1)
    webbrowser.open(f"http://{HOST}:{PUERTO}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]

    # El sondeo del hilo no sabe distinguir «ya escucha el editor» de «ya
    # escuchaba otra cosa»: si el puerto está ocupado por otro programa, se
    # conecta con él y abre el navegador contra el servicio equivocado,
    # mientras uvicorn falla por debajo. Se comprueba antes de arrancar nada
    # y se dice qué puerto es, que es lo que hace falta para liberarlo.
    if _hay_alguien_escuchando(HOST, PUERTO):
        print(f"\nEl puerto {PUERTO} de {HOST} ya está ocupado por otro programa.")
        print("El editor no se arranca para no abrir el navegador contra algo "
              "que no es él.")
        print(f"Cierra lo que esté usando el puerto {PUERTO} -puede ser otro "
              "editor ya abierto- y vuelve a intentarlo.")
        sys.exit(1)

    _avisar(raiz)

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
