"""Qué almacén se elige, y con qué.

`crear_almacen` no tenía ninguna prueba: haciendo que nunca eligiera
Supabase, los 387 tests de la rama seguían pasando. Es la función que
decide si lo que el docente registra sobrevive a cerrar el programa, así
que la elección se fija aquí.
"""

from backend.configuracion import Configuracion
from backend.persistencia import crear_almacen
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.supabase import AlmacenSupabase

URL = "https://ejemplo.supabase.co"
CLAVE = "clave-de-servicio"


def test_con_las_dos_credenciales_se_elige_supabase() -> None:
    almacen = crear_almacen(Configuracion(url_supabase=URL, clave_supabase=CLAVE))

    assert isinstance(almacen, AlmacenSupabase)
    assert almacen.es_duradero is True


def test_sin_credenciales_se_elige_memoria() -> None:
    """No se falla por falta de credenciales: se arranca y se avisa."""
    almacen = crear_almacen(Configuracion())

    assert isinstance(almacen, AlmacenEnMemoria)
    assert almacen.es_duradero is False


def test_con_la_url_pero_sin_clave_se_elige_memoria() -> None:
    """Media credencial no es una credencial.

    Las tablas tienen RLS activo y ninguna política: sin la clave de
    servicio no entra nadie. Intentarlo daría un almacén que dice ser
    duradero y falla en la primera petición.
    """
    almacen = crear_almacen(Configuracion(url_supabase=URL))

    assert isinstance(almacen, AlmacenEnMemoria)


def test_con_la_clave_pero_sin_url_se_elige_memoria() -> None:
    almacen = crear_almacen(Configuracion(clave_supabase=CLAVE))

    assert isinstance(almacen, AlmacenEnMemoria)


def test_una_credencial_vacia_no_cuenta_como_credencial() -> None:
    """Una línea `SUPABASE_SERVICE_KEY=` en el .env no da credenciales."""
    almacen = crear_almacen(
        Configuracion(url_supabase=URL, clave_supabase="")
    )

    assert isinstance(almacen, AlmacenEnMemoria)


def test_la_url_y_la_clave_llegan_al_almacen_elegido() -> None:
    """No basta con elegir Supabase: hay que dárselas."""
    almacen = crear_almacen(Configuracion(url_supabase=URL, clave_supabase=CLAVE))

    assert almacen._base == f"{URL}/rest/v1"
    assert almacen._cabeceras["apikey"] == CLAVE
    assert almacen._cabeceras["Authorization"] == f"Bearer {CLAVE}"
