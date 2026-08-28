"""Lo que ve el docente cuando el almacén falla, y el camino real con Supabase.

Dos cosas distintas, juntas porque las dos miran la misma costura:

1. Un `ErrorDeAlmacen` lleva un mensaje escrito en castellano para el
   docente. Sin un manejador en la aplicación, ese mensaje se perdía y el
   frontend recibía «Internal Server Error».
2. Hasta aquí `AlmacenSupabase` solo aparecía en sus propias pruebas
   unitarias: el camino que corre de verdad en casa del profesor -la
   aplicación con el almacén de Supabase detrás- no se había probado nunca
   de punta a punta. Estas pruebas lo montan entero contra el PostgREST
   simulado de `tests/conftest.py`.
"""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.supabase import (
    AlmacenSupabase,
    ChoqueDeAlmacen,
    ErrorDeAlmacen,
)

# `criterios_de_formato`, `postgrest` y los PDF vienen de tests/conftest.py.

MENSAJE = (
    "No se ha podido conectar con Supabase. Comprueba la conexión y que "
    "SUPABASE_URL es correcta."
)

UUID_CUALQUIERA = "11111111-2222-3333-4444-555555555555"


class AlmacenCaido:
    """Un almacén al que todo le falla, con el mensaje que trae el de verdad."""

    es_duradero = True

    def _caer(self, *_argumentos, **_nombrados):
        raise ErrorDeAlmacen(MENSAJE)

    registrar = listar = por_id = por_huella = _caer
    anterior_de = cambiar_estado = _caer


@pytest.fixture
def carpeta_de_entregas(tmp_path: Path, pdf_con_indice: Path, pdf_simple: Path) -> Path:
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    (entregas / "AF023_DAM_E2_20260115_v1.pdf").write_bytes(pdf_con_indice.read_bytes())
    (entregas / "AF023_DAM_E2_20260120_v1.pdf").write_bytes(pdf_simple.read_bytes())
    return entregas


def _aplicacion(raiz: Path, entregas: Path, almacen) -> TestClient:
    app = crear_app(
        raiz,
        configuracion=Configuracion(
            carpeta_entregas=entregas, version_criterios="v2026-2027"
        ),
        almacen=almacen,
    )
    return TestClient(app)


@pytest.fixture
def cliente_con_almacen_caido(
    criterios_de_formato: Path, carpeta_de_entregas: Path
) -> TestClient:
    return _aplicacion(criterios_de_formato, carpeta_de_entregas, AlmacenCaido())


@pytest.fixture
def cliente_con_supabase(
    criterios_de_formato: Path, carpeta_de_entregas: Path, postgrest
) -> TestClient:
    """La aplicación entera con AlmacenSupabase detrás del PostgREST simulado."""
    almacen = AlmacenSupabase(
        "https://ejemplo.supabase.co", "clave-de-servicio",
        cliente=postgrest.cliente(),
    )
    return _aplicacion(criterios_de_formato, carpeta_de_entregas, almacen)


# --- 1. Un almacén caído no da «Internal Server Error» ---------------------

CONFIRMACION = {
    "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
    "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
}


@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("GET", "/api/entregas/pendientes", None),
    ("GET", "/api/entregas", None),
    ("POST", "/api/entregas", CONFIRMACION),
    ("GET", f"/api/entregas/{UUID_CUALQUIERA}", None),
    ("POST", f"/api/entregas/{UUID_CUALQUIERA}/estado",
     {"estado": "ANALIZADO", "motivo": None}),
])
def test_cada_endpoint_que_toca_el_almacen_da_503_y_el_motivo(
    cliente_con_almacen_caido: TestClient, metodo: str, ruta: str, cuerpo
) -> None:
    """El docente lee el motivo, no un error del servidor."""
    respuesta = cliente_con_almacen_caido.request(metodo, ruta, json=cuerpo)

    assert respuesta.status_code == 503
    assert respuesta.json()["detail"] == MENSAJE


def test_el_motivo_viaja_en_detail_como_el_de_httpexception(
    cliente_con_almacen_caido: TestClient,
) -> None:
    """El frontend lee `detail` y no debe aprender una segunda forma de error."""
    caido = cliente_con_almacen_caido.get("/api/entregas")
    # Un 404 de los de siempre, para comparar. `confirmar` comprueba que el
    # archivo esté en la carpeta antes de tocar el almacén, así que este
    # sale de una HTTPException aunque el almacén esté caído.
    no_existe = cliente_con_almacen_caido.post("/api/entregas", json={
        **CONFIRMACION, "nombre_archivo": "fantasma.pdf",
    })

    assert caido.status_code == 503
    assert no_existe.status_code == 404
    assert set(caido.json()) == set(no_existe.json()) == {"detail"}


# --- 2. El camino real: la aplicación con AlmacenSupabase detrás -----------


def test_confirmar_y_abrir_ficha_con_el_almacen_de_supabase(
    cliente_con_supabase: TestClient, postgrest
) -> None:
    """Confirmar, listar y volver a abrir la ficha, todo contra Supabase."""
    confirmada = cliente_con_supabase.post("/api/entregas", json=CONFIRMACION)

    assert confirmada.status_code == 200, confirmada.text
    ficha = confirmada.json()
    assert ficha["entrega"]["codigo_alumno"] == "AF023"
    assert ficha["entrega"]["ciclo"] == "DAM"
    assert ficha["entrega"]["estado"] == "RECIBIDO"
    assert ficha["medidas"]["total_paginas"] == 7
    assert ficha["comprobaciones"]

    # Las tres tablas del esquema se han rellenado, no solo la de entregas.
    assert len(postgrest.tablas["alumno"]) == 1
    assert len(postgrest.tablas["proyecto"]) == 1
    assert len(postgrest.tablas["entrega"]) == 1

    identificador = ficha["entrega"]["id"]
    listadas = cliente_con_supabase.get("/api/entregas").json()
    assert [e["id"] for e in listadas] == [identificador]

    releida = cliente_con_supabase.get(f"/api/entregas/{identificador}")
    assert releida.status_code == 200
    assert releida.json()["entrega"]["id"] == identificador
    assert releida.json()["medidas"]["total_paginas"] == 7


def test_el_texto_del_trabajo_no_llega_a_ninguna_tabla(
    cliente_con_supabase: TestClient, postgrest
) -> None:
    """D-001, comprobado sobre lo que de verdad ha quedado guardado."""
    cliente_con_supabase.post("/api/entregas", json=CONFIRMACION)

    guardado = str(postgrest.tablas)
    assert "PROYECTO INTERMODULAR" not in guardado
    assert "Introduccion" not in guardado


def test_cambiar_el_estado_llega_hasta_la_tabla(
    cliente_con_supabase: TestClient, postgrest
) -> None:
    ficha = cliente_con_supabase.post("/api/entregas", json=CONFIRMACION).json()

    respuesta = cliente_con_supabase.post(
        f"/api/entregas/{ficha['entrega']['id']}/estado",
        json={"estado": "ANALIZADO", "motivo": None},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ANALIZADO"
    assert postgrest.tablas["entrega"][0]["estado"] == "ANALIZADO"


# --- 3. El choque de la restricción `unique` -------------------------------


def test_una_reentrega_de_la_misma_fase_y_version_da_409_y_se_explica(
    cliente_con_supabase: TestClient,
) -> None:
    """`unique (proyecto_id, fase, version)`: el caso más probable de todos.

    El alumno vuelve a entregar la misma fase con el mismo número de
    versión y otro archivo. PostgREST responde 409 con su mensaje en inglés;
    lo que tiene que llegar al profesor es qué ha pasado y qué hacer, y con
    un código que no le pida al navegador que reintente.
    """
    primera = cliente_con_supabase.post("/api/entregas", json=CONFIRMACION)
    assert primera.status_code == 200

    segunda = cliente_con_supabase.post("/api/entregas", json={
        **CONFIRMACION, "nombre_archivo": "AF023_DAM_E2_20260120_v1.pdf",
    })

    assert segunda.status_code == 409
    motivo = segunda.json()["detail"]
    assert motivo.startswith("Ya hay una entrega registrada")
    assert "misma fase" in motivo
    assert "versión" in motivo
    # Y dice las dos cosas que el profesor puede hacer.
    assert "número de versión siguiente" in motivo
    assert "ábrela desde la lista" in motivo


def test_el_choque_y_la_red_caida_no_se_confunden(
    criterios_de_formato: Path, carpeta_de_entregas: Path, postgrest
) -> None:
    """Los dos son fallos del almacén, y son dos cosas distintas.

    Reintentar arregla el segundo y nunca el primero, así que no pueden
    compartir código de respuesta. Si alguien borrase el manejador de
    `ChoqueDeAlmacen`, el choque volvería a salir como 503 sin que nada
    fallara: esto es lo que lo impide.
    """
    def sin_red(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    caido = _aplicacion(
        criterios_de_formato, carpeta_de_entregas,
        AlmacenSupabase("https://ejemplo.supabase.co", "clave",
                        cliente=httpx.Client(transport=httpx.MockTransport(sin_red))),
    )
    en_conflicto = _aplicacion(
        criterios_de_formato, carpeta_de_entregas,
        AlmacenSupabase("https://ejemplo.supabase.co", "clave",
                        cliente=postgrest.cliente()),
    )
    en_conflicto.post("/api/entregas", json=CONFIRMACION)

    respuesta_caido = caido.get("/api/entregas")
    respuesta_choque = en_conflicto.post("/api/entregas", json={
        **CONFIRMACION, "nombre_archivo": "AF023_DAM_E2_20260120_v1.pdf",
    })

    assert respuesta_caido.status_code == 503
    assert "conectar" in respuesta_caido.json()["detail"].lower()

    assert respuesta_choque.status_code == 409
    assert "Ya hay una entrega registrada" in respuesta_choque.json()["detail"]

    assert respuesta_caido.status_code != respuesta_choque.status_code


def test_el_choque_es_un_error_de_almacen_pero_de_su_propia_clase() -> None:
    """La traducción ocurre en el almacén, no en el endpoint.

    `ChoqueDeAlmacen` hereda de `ErrorDeAlmacen` -viene de la misma costura
    y quien no distinga puede seguir capturando el padre-, pero es su propia
    clase, que es lo que permite responderle con otro código.
    """
    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={
            "code": "23505",
            "message": "duplicate key value violates unique constraint",
        })

    almacen = AlmacenSupabase(
        "https://ejemplo.supabase.co", "clave",
        cliente=httpx.Client(transport=httpx.MockTransport(responder)),
    )

    with pytest.raises(ChoqueDeAlmacen) as fallo:
        almacen.listar()

    assert isinstance(fallo.value, ErrorDeAlmacen)
    assert "Ya hay una entrega registrada" in str(fallo.value)


def test_un_choque_en_otra_tabla_no_habla_de_entregas() -> None:
    """No se afirma lo que no se sabe: el 409 de `alumno` no es una reentrega."""
    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"code": "23505", "message": "duplicate"})

    almacen = AlmacenSupabase(
        "https://ejemplo.supabase.co", "clave",
        cliente=httpx.Client(transport=httpx.MockTransport(responder)),
    )

    with pytest.raises(ChoqueDeAlmacen) as fallo:
        almacen._uno("alumno", codigo="eq.AF023")

    assert "«alumno»" in str(fallo.value)
    assert "entrega registrada" not in str(fallo.value)
