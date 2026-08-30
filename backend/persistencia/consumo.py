"""Lo que ha costado un intento de análisis: nunca el trabajo del alumno.

El profesor lo pidió para poder decidir si corregir con esta herramienta
compensa: modelo, tokens, coste, duración, estado, reintentos, causa de
error, páginas, volumen de texto y si hizo falta una llamada nueva o se
reutilizó un resultado. Ninguno de esos datos es el trabajo del alumno ni
una cita de él -son cifras y etiquetas, la misma frontera que ya traza D-001
para `Correccion`-, así que este registro no necesita las mismas cautelas
que `validar_textos_acotados` (`backend/persistencia/correccion.py`).

`entrega_id` es lo único que ata este registro a un alumno, y es el mismo
código anónimo que ya usa todo lo demás (§19): esta tabla no sabe ni
necesita saber ningún nombre.
"""

from pydantic import BaseModel, ConfigDict

ESTADOS_DE_EJECUCION: tuple[str, ...] = ("OK", "PARCIAL", "ERROR")


class RegistroDeConsumo(BaseModel):
    """Una fila del registro de consumo, por ejecución de análisis.

    "Ejecución" es una llamada a `POST /entregas/{id}/analisis`, no cada
    llamada individual al proveedor: una ejecución puede hacer hasta dos
    llamadas reales -la del análisis y la de la redacción del borrador-, y
    hasta dos intentos de cada una si la primera respuesta no encaja
    (`RespuestaNoValida`). `tokens_entrada`, `tokens_salida`, `duracion_ms` e
    `intentos` son la suma de todo lo que ocurrió dentro de esa ejecución,
    no de una sola llamada.
    """

    model_config = ConfigDict(extra="forbid")

    entrega_id: str
    modelo: str
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    tokens_entrada_cacheados: int | None = None
    coste_estimado_usd: float | None = None
    # Qué fila de `config/precios_openai.yaml` se aplicó -"modelo@fecha"-, o
    # `None` si no había ninguna tarifa vigente y por eso el coste tampoco
    # se pudo calcular. Sin este dato, un coste guardado hoy sería
    # irreproducible en cuanto la tabla de precios cambiara.
    tarifa_aplicada: str | None = None
    duracion_ms: int
    estado: str
    intentos: int
    causa_error: str | None = None
    paginas: int | None = None
    caracteres_texto: int | None = None
    # Si esta ejecución sirvió un resultado ya guardado sin volver a llamar
    # al proveedor. Hoy ninguna ruta del sistema hace eso: el endpoint que
    # pide un análisis nuevo siempre llama al proveedor, y el que relee lo
    # ya guardado no ejecuta nada -no genera ningún registro de consumo en
    # absoluto-, así que este campo nunca tiene ocasión de valer `True`. Se
    # declara ahora para que el registro no cambie de forma el día que
    # exista una vía real de reutilización -una caché de resultados, por
    # ejemplo-, no porque haya una hoy.
    reutilizado: bool = False
