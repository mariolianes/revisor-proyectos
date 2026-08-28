"""Dónde se guarda la ficha de una entrega. El puerto y sus dos almacenes."""

from backend.persistencia.modelos import Almacen


def crear_almacen(configuracion) -> Almacen:
    """Supabase si hay credenciales; memoria si no.

    No se falla por falta de credenciales: el sistema arranca igual y avisa
    de que lo guardado se pierde al cerrar. Quien está probando la lectura
    de un PDF no debería necesitar una base de datos, y quien corrige de
    verdad verá el aviso.
    """
    from backend.persistencia.memoria import AlmacenEnMemoria

    if configuracion.url_supabase and configuracion.clave_supabase:
        from backend.persistencia.supabase import AlmacenSupabase

        return AlmacenSupabase(
            configuracion.url_supabase, configuracion.clave_supabase
        )
    return AlmacenEnMemoria()
