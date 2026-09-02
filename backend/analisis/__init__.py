"""Pide el juicio a un modelo de lenguaje y lo comprueba antes de creerlo."""


def crear_proveedor(configuracion):
    """OpenAI si hay clave y modelo configurados; el simulado en cualquier
    otro caso.

    No se falla por falta de configuración: el sistema arranca igual y avisa
    de que el análisis es simulado. Quien está probando el flujo no debería
    necesitar una clave, y quien corrige de verdad verá el aviso -lo enseña
    `ProveedorAnalisis.nombre`, que el frontend muestra.
    """
    from backend.analisis.proveedor import ProveedorSimulado

    if configuracion.clave_openai and configuracion.modelo_analisis:
        from backend.analisis.openai import ProveedorOpenAI

        return ProveedorOpenAI(
            configuracion.clave_openai,
            configuracion.modelo_analisis,
            esfuerzo=configuracion.esfuerzo_analisis,
        )
    return ProveedorSimulado(respuestas=[])
