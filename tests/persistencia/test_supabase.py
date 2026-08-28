"""El almacén de Supabase, contra un transporte simulado.

No se toca la base de datos real: las pruebas no deben depender de la red ni
dejar filas en un proyecto de verdad. Lo que se comprueba aquí es que se
llama a las tablas correctas, con los filtros correctos, y que un error se
convierte en un mensaje que el docente entiende.
"""

import httpx
import pytest

from backend.persistencia.modelos import EntregaNueva
from backend.persistencia.supabase import AlmacenSupabase, ErrorDeAlmacen

URL = "https://ejemplo.supabase.co"
CLAVE = "clave-de-servicio"

ALUMNO = {"id": "id-alumno", "codigo": "AF023", "ciclo": "DAM"}
PROYECTO = {"id": "id-proyecto", "alumno_id": "id-alumno",
            "version_criterios": "v2026-2027"}
ENTREGA = {
    "id": "id-entrega", "proyecto_id": "id-proyecto", "fase": "E2", "version": 1,
    "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf", "huella_archivo": "a" * 64,
    "recibida_en": "2026-08-27T10:00:00+00:00", "estado": "RECIBIDO",
    "motivo_bloqueo": None, "version_criterios": "v2026-2027",
}


def _entrega() -> EntregaNueva:
    return EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        version_criterios="v2026-2027",
    )


def _almacen(responder) -> AlmacenSupabase:
    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    return AlmacenSupabase(URL, CLAVE, cliente=cliente)


def test_registrar_reutiliza_el_alumno_existente() -> None:
    llamadas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        if peticion.url.path.endswith("/alumno"):
            return httpx.Response(200, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            return httpx.Response(200, json=[PROYECTO])
        # La huella no está registrada: hay que insertar de verdad.
        if peticion.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[ENTREGA])

    registrada = _almacen(responder).registrar(_entrega())

    assert registrada.id == "id-entrega"
    assert registrada.codigo_alumno == "AF023"
    assert "POST /rest/v1/alumno" not in llamadas
    assert "POST /rest/v1/entrega" in llamadas


def test_registrar_crea_el_alumno_si_no_existe() -> None:
    llamadas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        if peticion.url.path.endswith("/alumno"):
            if peticion.method == "GET":
                return httpx.Response(200, json=[])
            return httpx.Response(201, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            if peticion.method == "GET":
                return httpx.Response(200, json=[])
            return httpx.Response(201, json=[PROYECTO])
        if peticion.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[ENTREGA])

    _almacen(responder).registrar(_entrega())

    assert "POST /rest/v1/alumno" in llamadas
    assert "POST /rest/v1/proyecto" in llamadas


def test_lleva_la_clave_en_las_cabeceras() -> None:
    vistas: dict[str, str] = {}

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.update(peticion.headers)
        return httpx.Response(200, json=[])

    _almacen(responder).listar()

    assert vistas["apikey"] == CLAVE
    assert vistas["authorization"] == f"Bearer {CLAVE}"


def test_no_envia_el_texto_del_trabajo() -> None:
    """D-001: ni el PDF ni el texto salen hacia la base de datos."""
    cuerpos: list[bytes] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        cuerpos.append(peticion.content)
        if peticion.url.path.endswith("/alumno"):
            return httpx.Response(200, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            return httpx.Response(200, json=[PROYECTO])
        if peticion.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[ENTREGA])

    _almacen(responder).registrar(_entrega())

    enviado = b"".join(cuerpos).decode()
    assert "texto_plano" not in enviado
    assert "%PDF" not in enviado


def test_una_huella_ya_conocida_no_se_duplica() -> None:
    # La consulta por huella pide `proyecto!inner(alumno!inner(...))`: una
    # respuesta real de PostgREST trae ese embebido. Sin él, `_componer`
    # leería un alumno vacío y lo compararía como si no coincidiera con lo
    # declarado ahora, disparando el rechazo de la ficha 143 en vano.
    entrega_con_alumno = {
        **ENTREGA,
        "proyecto": {"alumno": {"codigo": "AF023", "ciclo": "DAM"}},
    }

    def responder(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path.endswith("/entrega") and peticion.method == "GET":
            return httpx.Response(200, json=[entrega_con_alumno])
        if peticion.url.path.endswith("/alumno"):
            return httpx.Response(200, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            return httpx.Response(200, json=[PROYECTO])
        raise AssertionError("no debería insertar")

    registrada = _almacen(responder).registrar(_entrega())

    assert registrada.id == "id-entrega"


def test_la_misma_huella_con_datos_declarados_distintos_se_rechaza() -> None:
    """Error de atribución: no se resuelve en silencio a favor del primero.

    Mismo criterio que `AlmacenEnMemoria.registrar` (ver test_memoria.py):
    el brief de esta tarea no lo describía, pero dejar a Supabase resolver
    la huella repetida en silencio, sin comparar lo declarado, sería un
    comportamiento distinto entre los dos almacenes para el mismo caso.
    """
    entrega_con_alumno = {
        **ENTREGA,
        "proyecto": {"alumno": {"codigo": "AF023", "ciclo": "DAM"}},
    }

    def responder(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path.endswith("/entrega") and peticion.method == "GET":
            return httpx.Response(200, json=[entrega_con_alumno])
        raise AssertionError("no debería llegar más lejos")

    with pytest.raises(ValueError, match="AF023") as fallo:
        _almacen(responder).registrar(_entrega().model_copy(
            update={"codigo_alumno": "AF999"}
        ))

    assert "id-entrega" in str(fallo.value)
    assert "AF999" in str(fallo.value)


def test_la_consulta_fuerza_el_cruce_interno() -> None:
    """Sin `!inner`, PostgREST no filtra la tabla raíz.

    Un filtro sobre un recurso embebido sin cruce interno devuelve TODAS las
    filas de la raíz, con el embebido a null en las que no casan. Es decir:
    devolvería las entregas de todos los alumnos. Se comprueba en la petición
    porque contra un transporte simulado no hay servidor que lo demuestre.
    """
    vistas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(str(peticion.url))
        return httpx.Response(200, json=[])

    _almacen(responder).listar()

    assert "proyecto!inner" in vistas[0]
    assert "alumno!inner" in vistas[0]


def test_un_error_del_servidor_se_traduce() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    with pytest.raises(ErrorDeAlmacen) as fallo:
        _almacen(responder).listar()

    assert "Supabase" in str(fallo.value)
    assert "401" in str(fallo.value)


def test_sin_red_el_error_lo_dice() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(ErrorDeAlmacen) as fallo:
        _almacen(responder).listar()

    assert "conectar" in str(fallo.value).lower()


def test_cambiar_estado_manda_un_patch() -> None:
    vistos: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistos.append(peticion.method)
        return httpx.Response(200, json=[{**ENTREGA, "estado": "ANALIZADO"}])

    cambiada = _almacen(responder).cambiar_estado("id-entrega", "ANALIZADO", None)

    assert vistos == ["PATCH"]
    assert cambiada is not None
    assert cambiada.estado == "ANALIZADO"


def test_bloquear_sin_motivo_se_rechaza_antes_de_la_red() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        raise AssertionError("no debería llegar a la red")

    with pytest.raises(ValueError, match="motivo"):
        _almacen(responder).cambiar_estado("id-entrega", "BLOQUEADO", None)


def test_el_almacen_de_supabase_es_duradero() -> None:
    assert _almacen(lambda p: httpx.Response(200, json=[])).es_duradero is True
