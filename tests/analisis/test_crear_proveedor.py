"""Qué proveedor se construye según la configuración.

Ninguno de estos tests toca la red: cuando hay clave y modelo, se comprueba
el tipo del proveedor devuelto, no que responda -eso lo cubre
`test_openai.py` con un cliente simulado inyectado.
"""

from backend.analisis import crear_proveedor
from backend.analisis.openai import ProveedorOpenAI
from backend.analisis.proveedor import ProveedorSimulado
from backend.configuracion import Configuracion


def test_sin_clave_ni_modelo_usa_el_simulado() -> None:
    proveedor = crear_proveedor(Configuracion())

    assert isinstance(proveedor, ProveedorSimulado)
    assert proveedor.nombre == "simulado"


def test_con_clave_pero_sin_modelo_usa_el_simulado() -> None:
    """No basta media configuración: sin modelo no se sabe con qué llamar."""
    proveedor = crear_proveedor(Configuracion(clave_openai="una-clave"))

    assert isinstance(proveedor, ProveedorSimulado)


def test_con_modelo_pero_sin_clave_usa_el_simulado() -> None:
    proveedor = crear_proveedor(Configuracion(modelo_analisis="un-modelo"))

    assert isinstance(proveedor, ProveedorSimulado)


def test_con_clave_y_modelo_usa_openai() -> None:
    """No llega a llamar a la API: construir el cliente no abre conexión,
    solo la guarda para usarla cuando `analizar` la necesite."""
    proveedor = crear_proveedor(
        Configuracion(clave_openai="una-clave", modelo_analisis="un-modelo")
    )

    assert isinstance(proveedor, ProveedorOpenAI)
    assert proveedor.nombre == "openai:un-modelo"
