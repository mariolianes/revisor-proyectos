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
