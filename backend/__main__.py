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

from backend.empaquetado import raiz_de_recursos

from backend.app import crear_app

HOST = "127.0.0.1"
PUERTO = 8000
# Cuántos puertos se prueban a partir del preferido antes de rendirse.
# Hasta el 2026-09-07 no se probaba ninguno: si el 8000 estaba ocupado por
# cualquier otra cosa -y en un equipo cualquiera lo está más a menudo de lo
# que parece-, el programa se negaba a arrancar y ahí se acababa. Para una
# beta que el docente abre con doble clic, eso es un programa que no
# funciona y ninguna forma de averiguar por qué.
PUERTOS_A_PROBAR = 20


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


def _primer_puerto_libre() -> int | None:
    """El primero libre a partir de `PUERTO`, o `None` si no hay ninguno."""
    for candidato in range(PUERTO, PUERTO + PUERTOS_A_PROBAR):
        if not _hay_alguien_escuchando(HOST, candidato):
            return candidato
    return None


def _abrir_navegador_cuando_escuche(puerto: int = PUERTO) -> None:
    """Abre el navegador en cuanto el puerto empieza a aceptar conexiones.

    No basta con engancharse al evento de arranque de FastAPI: uvicorn
    dispara ese evento ANTES de enlazar el socket (ver
    `Server.startup()` en la librería: primero `lifespan.startup()`,
    luego `loop.create_server()`), así que abrir ahí seguiría siendo una
    carrera, solo que movida de sitio. Sondear el puerto de verdad, en un
    hilo aparte, es lo único determinista: el navegador no se abre hasta
    que una conexión real tiene éxito.
    """
    while not _hay_alguien_escuchando(HOST, puerto):
        time.sleep(0.1)
    webbrowser.open(f"http://{HOST}:{puerto}")


if __name__ == "__main__":
    # Empaquetado, esto es la carpeta temporal donde PyInstaller ha dejado
    # los criterios, la prosa normativa y el frontend compilado. El `.env`
    # del docente NO se lee de aquí: ver `backend/empaquetado.py`.
    raiz = raiz_de_recursos()

    # El sondeo del hilo no sabe distinguir «ya escucha el editor» de «ya
    # escuchaba otra cosa»: si se arrancara sobre un puerto ocupado, el
    # navegador se abriría contra el servicio equivocado. Eso sigue sin
    # poder pasar. Lo que cambia desde el 2026-09-07 es qué se hace cuando
    # ocurre: en vez de rendirse, se busca el primer puerto libre. Nunca se
    # comparte puerto con nadie; solo se elige otro.
    #
    # Antes se negaba a arrancar, y para una beta que el docente abre con
    # doble clic eso es un programa que no funciona y ninguna forma de
    # averiguar por qué.
    puerto = _primer_puerto_libre()
    if puerto is None:
        print(f"\nNo hay ningún puerto libre entre el {PUERTO} y el "
              f"{PUERTO + PUERTOS_A_PROBAR - 1} en {HOST}.")
        print("Cierra algún programa que esté usando esos puertos y vuelve a "
              "intentarlo.")
        sys.exit(1)
    if puerto != PUERTO:
        print(f"El puerto {PUERTO} está ocupado por otro programa. Se usa el "
              f"{puerto}.")

    _avisar(raiz)

    threading.Thread(
        target=_abrir_navegador_cuando_escuche, args=(puerto,), daemon=True
    ).start()

    try:
        # Solo 127.0.0.1: esta aplicación escribe en el disco y ejecuta git.
        uvicorn.run(crear_app(raiz), host=HOST, port=puerto, log_level="warning")
    except Exception as error:
        # El .cmd que lanza esto corre en una consola que se cierra sola al
        # terminar el script: sin este mensaje, el profesor solo vería un
        # parpadeo y ningún motivo.
        print(f"\nEl servidor terminó con un error: {error}")
        sys.exit(1)
