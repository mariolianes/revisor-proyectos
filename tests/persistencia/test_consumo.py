"""El registro de consumo, en los dos almacenes."""

import httpx

from backend.persistencia.consumo import RegistroDeConsumo
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.supabase import AlmacenSupabase

URL = "https://ejemplo.supabase.co"
CLAVE = "clave-de-servicio"


def _registro(**cambios) -> RegistroDeConsumo:
    datos = dict(
        entrega_id="id-entrega",
        modelo="openai:gpt-4.1",
        tokens_entrada=10290,
        tokens_salida=2054,
        tokens_entrada_cacheados=0,
        coste_estimado_usd=0.037012,
        tarifa_aplicada="gpt-4.1@2026-08-30",
        duracion_ms=4200,
        estado="OK",
        intentos=1,
        causa_error=None,
        paginas=22,
        caracteres_texto=32000,
        reutilizado=False,
    )
    datos.update(cambios)
    return RegistroDeConsumo(**datos)


def test_no_lleva_ningun_campo_de_texto_del_trabajo() -> None:
    """El registro solo admite los campos declarados -`extra="forbid"`-, y
    ninguno de ellos es el texto ni una cita: es la garantía estructural de
    que este registro no puede convertirse, sin que nadie lo note, en un
    sitio donde se cuele el trabajo del alumno."""
    campos = set(RegistroDeConsumo.model_fields)
    assert "texto" not in campos
    assert "cita" not in campos
    assert "instruccion" not in campos
    assert "prompt" not in campos


def test_memoria_guarda_el_registro_y_lo_devuelve() -> None:
    almacen = AlmacenEnMemoria()

    almacen.registrar_consumo(_registro())

    guardados = almacen.consumos()
    assert len(guardados) == 1
    assert guardados[0].tokens_entrada == 10290
    assert guardados[0].coste_estimado_usd == 0.037012


def test_memoria_asigna_id_y_creada_en_aunque_el_registro_no_los_traiga() -> None:
    """Quien construye el registro para guardarlo -`backend/servicios/
    analisis_de_entrega.py`- nunca rellena `id` ni `creada_en`: los asigna
    el almacén, mismo criterio que `EntregaRegistrada.id`/`recibida_en` en
    `registrar()`. Sin esto, un informe por centro que ordenara las
    ejecuciones de una entrega por fecha para distinguir el análisis
    principal de un reanálisis se quedaría sin con qué ordenar."""
    almacen = AlmacenEnMemoria()

    registro = _registro()
    assert registro.id is None
    assert registro.creada_en is None

    almacen.registrar_consumo(registro)

    guardado = almacen.consumos()[0]
    assert guardado.id is not None
    assert guardado.creada_en is not None


def test_memoria_conserva_el_historico_entre_varias_ejecuciones() -> None:
    """Una entrega puede reanalizarse: cada intento es su propio gasto, y
    ninguno debe tapar al anterior."""
    almacen = AlmacenEnMemoria()

    almacen.registrar_consumo(_registro(estado="ERROR", causa_error="sin red"))
    almacen.registrar_consumo(_registro(estado="OK"))

    assert len(almacen.consumos()) == 2


def test_supabase_escribe_en_ejecucion_motor() -> None:
    llamadas: list[str] = []
    cuerpos: list[dict] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        if peticion.content:
            import json
            cuerpos.append(json.loads(peticion.content))
        return httpx.Response(201, json=[{"id": "id-ejecucion"}])

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    almacen = AlmacenSupabase(URL, CLAVE, cliente=cliente)

    almacen.registrar_consumo(_registro())

    assert "POST /rest/v1/ejecucion_motor" in llamadas
    assert cuerpos[0]["entrega_id"] == "id-entrega"
    assert cuerpos[0]["tokens_entrada"] == 10290
    assert cuerpos[0]["modelo"] == "openai:gpt-4.1"


def test_supabase_no_manda_id_ni_creada_en_como_nulos() -> None:
    """`id` y `creada_en` tienen `default gen_random_uuid()` y `default
    now()` en la migración. Un `null` explícito sobre una columna con
    `default` la sustituye por `null` en vez de dejar que Postgres aplique
    el suyo -es la regla que ya explica el comentario de `_viola_el_
    esquema` en `tests/conftest.py`-, así que si `registrar_consumo`
    mandara estas dos claves con valor `None`, cada ejecución guardada
    perdería su fecha de creación y Postgres tendría que generar el `id` de
    otra forma o rechazar la fila. Ninguna de las dos claves debe aparecer
    en absoluto en el cuerpo de la petición."""
    cuerpos: list[dict] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        if peticion.content:
            import json
            cuerpos.append(json.loads(peticion.content))
        return httpx.Response(201, json=[{"id": "id-ejecucion"}])

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    almacen = AlmacenSupabase(URL, CLAVE, cliente=cliente)

    almacen.registrar_consumo(_registro())

    assert "id" not in cuerpos[0]
    assert "creada_en" not in cuerpos[0]
