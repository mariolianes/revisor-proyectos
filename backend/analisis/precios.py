"""La tarifa de OpenAI, leída de una tabla fechada, nunca escrita en Python.

El profesor lo pidió así: «una tabla de precios configurable y fechada -no
un número escrito en el código: las tarifas cambian». `config/
precios_openai.yaml` es esa tabla; este módulo solo sabe leerla, elegir la
fila vigente para una fecha y un modelo, y hacer la cuenta.

Elegir la fila vigente y no siempre la última es lo que permite fechar el
coste: si OpenAI sube un precio hoy, un análisis hecho la semana pasada
sigue costando, en el registro, lo que costó de verdad -la tarifa vigente
`vigente_desde` esa fecha-, no lo que costaría si se repitiera hoy. Ver el
comentario del propio YAML para el porqué de no editar filas existentes.

Si un modelo no tiene ninguna fila que le sirva -no está en la tabla, o toda
fila conocida de ese modelo empieza después de la fecha que se pregunta-,
`tarifa_vigente` devuelve `None` y no un precio inventado. R3 no distingue
entre inventar un criterio de corrección y inventar un precio: los dos son
un dato que nadie ha fijado, presentado como si alguien lo hubiera fijado.
`backend/persistencia/consumo.py` guarda ese `None` tal cual -coste no
calculable-, no un cero, que diría «gratis» y sería mentira.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

FICHERO_TARIFAS = "config/precios_openai.yaml"

TOKENS_POR_MILLON = 1_000_000


class Tarifa(BaseModel):
    """Una fila de la tabla: lo que cuesta un modelo a partir de una fecha."""

    modelo: str
    vigente_desde: date
    entrada_por_millon: float
    salida_por_millon: float
    entrada_cacheada_por_millon: float | None = None


def cargar_tarifas(raiz: Path) -> list[Tarifa]:
    """Todas las filas de `config/precios_openai.yaml`, o una lista vacía si
    el fichero no existe -el sistema arranca igual, y el coste de cada
    análisis queda como no calculable en vez de impedir analizar nada-.
    """
    fichero = raiz / FICHERO_TARIFAS
    if not fichero.is_file():
        return []
    bruto = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    if not isinstance(bruto, list):
        return []
    return [Tarifa.model_validate(entrada) for entrada in bruto]


def tarifa_vigente(tarifas: list[Tarifa], modelo: str, fecha: date) -> Tarifa | None:
    """La tarifa de ese modelo más reciente que ya regía en `fecha`.

    Entre varias filas del mismo modelo con `vigente_desde` anterior o igual
    a `fecha`, gana la de fecha más alta -la corrección más reciente antes
    de ese día-. Si ninguna fila de ese modelo llega a `fecha` -el modelo no
    está en la tabla, o toda tarifa conocida de ese modelo es posterior-, no
    hay tarifa vigente.
    """
    candidatas = [
        tarifa for tarifa in tarifas
        if tarifa.modelo == modelo and tarifa.vigente_desde <= fecha
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda tarifa: tarifa.vigente_desde)


def calcular_coste(
    tarifa: Tarifa,
    tokens_entrada: int,
    tokens_salida: int,
    tokens_entrada_cacheados: int = 0,
) -> float:
    """El coste en dólares de una llamada, según esta tarifa.

    `tokens_entrada_cacheados` es un subconjunto de `tokens_entrada`, no una
    cantidad aparte -así los devuelve `usage` de OpenAI-: se descuenta del
    total antes de aplicar el precio normal, y se factura por separado al
    precio reducido, cuando la tarifa lo trae. Si la tarifa no distingue
    precio para los cacheados (`entrada_cacheada_por_millon` a `None`), esos
    tokens se cobran al precio normal de entrada -es lo que ocurriría si de
    verdad no hay descuento para ese modelo-.
    """
    cacheados = max(min(tokens_entrada_cacheados, tokens_entrada), 0)
    entrada_normal = max(tokens_entrada - cacheados, 0)

    coste_entrada = entrada_normal / TOKENS_POR_MILLON * tarifa.entrada_por_millon
    if cacheados and tarifa.entrada_cacheada_por_millon is not None:
        coste_entrada += cacheados / TOKENS_POR_MILLON * tarifa.entrada_cacheada_por_millon
    else:
        coste_entrada += cacheados / TOKENS_POR_MILLON * tarifa.entrada_por_millon

    coste_salida = tokens_salida / TOKENS_POR_MILLON * tarifa.salida_por_millon
    return round(coste_entrada + coste_salida, 6)


def estimar_coste(
    raiz: Path,
    modelo: str,
    tokens_entrada: int,
    tokens_salida: int,
    tokens_entrada_cacheados: int = 0,
    fecha: date | None = None,
) -> tuple[float | None, str | None]:
    """El coste estimado y la tarifa aplicada, o `(None, None)` si no hay
    ninguna tarifa vigente para ese modelo en esa fecha.

    Es la función que usa el registro de consumo
    (`backend/servicios/analisis_de_entrega.py`): junta cargar la tabla,
    elegir la fila y hacer la cuenta, para que el punto de llamada no tenga
    que conocer `Tarifa` ni el orden de los pasos.
    """
    tarifas = cargar_tarifas(raiz)
    tarifa = tarifa_vigente(tarifas, modelo, fecha or date.today())
    if tarifa is None:
        return None, None
    coste = calcular_coste(tarifa, tokens_entrada, tokens_salida, tokens_entrada_cacheados)
    return coste, f"{tarifa.modelo}@{tarifa.vigente_desde.isoformat()}"
