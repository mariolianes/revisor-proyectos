"""El almacén de Supabase, contra un transporte simulado.

No se toca la base de datos real: las pruebas no deben depender de la red ni
dejar filas en un proyecto de verdad. Lo que se comprueba aquí es que se
llama a las tablas correctas, con los filtros correctos, y que un error se
convierte en un mensaje que el docente entiende.
"""

from datetime import datetime

import httpx
import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva, EntregaRegistrada
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


def _entrega(**cambios) -> EntregaNueva:
    datos = dict(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        version_criterios="v2026-2027",
    )
    datos.update(cambios)
    return EntregaNueva(**datos)


def _fila(
    fase: str, version: int = 1, *, codigo_alumno: str = "AF023",
    ciclo: str = "DAM", huella: str | None = None,
) -> dict:
    """Una fila de `entrega` tal como la devolvería PostgREST con SELECCION.

    Para los tests de `anterior_de`: hace falta el `proyecto.alumno`
    anidado -si no, `_componer` lee un alumno vacío-, y un `id` distinto por
    fila para poder distinguirlas.
    """
    return {
        **ENTREGA,
        "id": f"id-{fase}-{version}-{codigo_alumno}",
        "fase": fase,
        "version": version,
        "huella_archivo": huella or "9" * 64,
        "proyecto": {"alumno": {"codigo": codigo_alumno, "ciclo": ciclo}},
    }


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

    Se lee el valor ya decodificado de `select` (`peticion.url.params`), no
    la representación literal de la URL: httpx transmite `!` como `%21` al
    construir la query string desde `params=`, y eso es irrelevante para
    PostgREST -el servidor decodifica la query string antes de que su
    parser de filtros vea el valor-, así que comprobar el texto crudo de la
    URL sería fijar un detalle de cómo httpx escribe la petición, no la
    intención real de la consulta.
    """
    vistas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion.url.params["select"])
        return httpx.Response(200, json=[])

    _almacen(responder).listar()

    assert "proyecto!inner" in vistas[0]
    assert "alumno!inner" in vistas[0]


def test_un_error_del_servidor_se_traduce() -> None:
    """Y dice que mirar, no solo que algo ha fallado.

    Las tablas tienen RLS activo y ninguna politica, asi que esto solo
    funciona con la clave de servicio: un 401 significa que la clave no vale
    o ha caducado, y el docente tiene que saber donde esta esa clave.
    """
    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    with pytest.raises(ErrorDeAlmacen) as fallo:
        _almacen(responder).listar()

    assert "Supabase" in str(fallo.value)
    assert "401" in str(fallo.value)
    assert "SUPABASE_SERVICE_KEY" in str(fallo.value)
    assert ".env" in str(fallo.value)


def test_un_error_del_servidor_que_no_es_de_credenciales_no_habla_de_la_clave() -> None:
    """No se afirma lo que no se sabe: un 500 no es una clave caducada."""
    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "boom"})

    with pytest.raises(ErrorDeAlmacen) as fallo:
        _almacen(responder).listar()

    assert "500" in str(fallo.value)
    assert "SUPABASE_SERVICE_KEY" not in str(fallo.value)


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

    # El identificador tiene que tener forma de UUID: es lo que la guarda de
    # `_es_uuid` exige antes de dejar pasar la petición a la red.
    cambiada = _almacen(responder).cambiar_estado(
        "11111111-1111-1111-1111-111111111111", "ANALIZADO", None
    )

    assert vistos == ["PATCH"]
    assert cambiada is not None
    assert cambiada.estado == "ANALIZADO"


def test_cambiar_estado_pide_el_alumno_en_la_representacion() -> None:
    """Sin `select`, PostgREST devuelve la fila de `entrega` a secas.

    Y entonces `_componer` compone una entrega con el codigo de alumno y el
    ciclo vacios, que es lo que este metodo devolvia -y lo que acababa en la
    ficha y en la respuesta de la API- mientras AlmacenEnMemoria devolvia la
    entrega entera. Lo encontro el test de paridad entre los dos almacenes.
    """
    vistos: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistos.append(peticion.url.params.get("select", ""))
        return httpx.Response(200, json=[{
            **ENTREGA, "estado": "ANALIZADO",
            "proyecto": {"alumno": {"codigo": "AF023", "ciclo": "DAM"}},
        }])

    cambiada = _almacen(responder).cambiar_estado(
        "11111111-1111-1111-1111-111111111111", "ANALIZADO", None
    )

    assert "proyecto" in vistos[0]
    assert "alumno" in vistos[0]
    assert cambiada is not None
    assert cambiada.codigo_alumno == "AF023"
    assert cambiada.ciclo == "DAM"


def test_bloquear_sin_motivo_gana_sobre_un_identificador_invalido_sin_llegar_a_la_red() -> None:
    """El mensaje del motivo gana aunque el identificador tampoco valga.

    El nombre anterior de este test -`..._antes_de_la_red`- solo hablaba
    del motivo, y el test protege algo más: `"id-entrega"` no tiene forma
    de UUID, así que este test también es el cruce "estado inválido +
    identificador inválido" que la sección de paridad del informe daba por
    no probado. Verificado invirtiendo el orden de las dos validaciones en
    `cambiar_estado` -`_es_uuid` antes que `validar_estado`- y comprobando
    que entonces el test falla (`Failed: DID NOT RAISE <class
    'ValueError'>`, porque el identificador inválido devuelve `None` en
    silencio antes de llegar al estado).
    """

    def responder(peticion: httpx.Request) -> httpx.Response:
        raise AssertionError("no debería llegar a la red")

    with pytest.raises(ValueError, match="motivo"):
        _almacen(responder).cambiar_estado("id-entrega", "BLOQUEADO", None)


def test_el_almacen_de_supabase_es_duradero() -> None:
    assert _almacen(lambda p: httpx.Response(200, json=[])).es_duradero is True


def test_una_fase_desconocida_en_anterior_de_da_el_mismo_mensaje_en_los_dos_almacenes() -> None:
    """El docente tiene que ver el mismo fallo, tenga o no credenciales.

    `AlmacenEnMemoria.anterior_de` valida la fase antes de indexar `FASES` y
    falla en castellano. El brief de Supabase no llamaba a `validar_fase`, así
    que una fase inventada llegaba a `FASES.index(fase)` y reventaba con el
    `ValueError` de `tuple.index`, en inglés -y solo después de una llamada
    de red que además sobraba-. Se comprueba que los dos den literalmente el
    mismo mensaje, no que cada uno tenga por separado uno en castellano: lo
    que hay que impedir es que diverjan según cómo esté configurado el
    almacén.
    """

    def responder(peticion: httpx.Request) -> httpx.Response:
        raise AssertionError("no debería llegar a la red: la fase se valida antes")

    with pytest.raises(ValueError) as fallo_memoria:
        AlmacenEnMemoria().anterior_de("AF023", "FASE_INVENTADA")

    with pytest.raises(ValueError) as fallo_supabase:
        _almacen(responder).anterior_de("AF023", "FASE_INVENTADA")

    assert str(fallo_memoria.value) == str(fallo_supabase.value)


def test_un_identificador_sin_forma_de_uuid_da_none_en_los_dos_almacenes() -> None:
    """`entrega.id` es `uuid` en la base de datos.

    Sin guardar antes, `AlmacenSupabase.por_id` con un identificador que no
    tiene forma de UUID no da «no existe»: Postgres rechaza la consulta con
    un 400 -«invalid input syntax for type uuid»- antes de mirar si hay una
    fila así, y eso se traduce en `ErrorDeAlmacen`. `AlmacenEnMemoria.por_id`
    simplemente no lo encuentra en su diccionario y da `None`. Es la misma
    clase de divergencia que la de la fase: un identificador inventado en
    una URL -`GET /api/entregas/no-existe`- tiene que dar lo mismo, tenga o
    no el sistema credenciales de Supabase.
    """

    def responder(peticion: httpx.Request) -> httpx.Response:
        raise AssertionError("no debería llegar a la red: el identificador se valida antes")

    resultado_memoria = AlmacenEnMemoria().por_id("no-es-un-uuid")
    resultado_supabase = _almacen(responder).por_id("no-es-un-uuid")

    assert resultado_memoria is None
    assert resultado_supabase == resultado_memoria


def test_por_id_con_identificador_invalido_no_hace_ninguna_peticion() -> None:
    llamadas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        return httpx.Response(200, json=[])

    resultado = _almacen(responder).por_id("no-es-un-uuid")

    assert resultado is None
    assert llamadas == []


def test_por_id_con_uuid_valido_pero_inexistente_da_none_en_los_dos_almacenes() -> None:
    """El gemelo feliz de la guarda de UUID: no basta con parecerlo.

    La guarda de `_es_uuid` solo demuestra que un identificador con forma
    de UUID *llega* a la red; no demuestra que, una vez allí, una consulta
    sin resultados se traduzca en `None` y no en un error. Un UUID válido
    que no está en la tabla da una lista vacía en la respuesta de
    PostgREST, y `por_id` la traduce a `None` -el mismo `None` que da
    `AlmacenEnMemoria` cuando el identificador no está en su diccionario-.
    """
    uuid_valido = "22222222-2222-2222-2222-222222222222"

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    resultado_memoria = AlmacenEnMemoria().por_id(uuid_valido)
    resultado_supabase = _almacen(responder).por_id(uuid_valido)

    assert resultado_memoria is None
    assert resultado_supabase == resultado_memoria


def test_cambiar_estado_con_identificador_invalido_no_hace_ninguna_peticion() -> None:
    """La guarda del identificador vale también para `cambiar_estado`.

    El orden importa: primero se valida el estado -es el error más
    informativo de los dos si también hay un problema con el
    identificador-, y solo si el estado es válido se comprueba la forma del
    identificador, antes de la red.
    """
    llamadas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        return httpx.Response(200, json=[])

    resultado = _almacen(responder).cambiar_estado("no-es-un-uuid", "ANALIZADO", None)

    assert resultado is None
    assert llamadas == []


def test_cambiar_estado_con_uuid_valido_pero_inexistente_da_none_en_los_dos_almacenes() -> None:
    """El mismo patrón que en `por_id`, aplicado a `cambiar_estado`.

    Tras el `PATCH`, `filas` vacío -PostgREST no encontró ninguna fila con
    ese `id`- se traduce en `None`, igual que `AlmacenEnMemoria` cuando el
    identificador no está en su diccionario.
    """
    uuid_valido = "33333333-3333-3333-3333-333333333333"

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    resultado_memoria = AlmacenEnMemoria().cambiar_estado(
        uuid_valido, "ANALIZADO", None
    )
    resultado_supabase = _almacen(responder).cambiar_estado(
        uuid_valido, "ANALIZADO", None
    )

    assert resultado_memoria is None
    assert resultado_supabase == resultado_memoria


def test_una_fase_huerfana_en_una_fila_guardada_da_el_mismo_resultado_en_los_dos_almacenes() -> None:
    """La simetría inversa del bug de la fase inválida de entrada.

    Una fila ya guardada puede llevar una fase que ya no está en `FASES`
    -un dato heredado de otra versión de criterios-. `AlmacenSupabase.
    anterior_de` ya la descartaba con `entrega.fase in FASES`;
    `AlmacenEnMemoria` no, e indexaba `FASES.index(entrega.fase)`
    directamente, reventando con el `ValueError` en inglés de
    `tuple.index`. Se inserta la fila huérfana directamente en el almacén
    -no vía `registrar`, que la rechazaría por tener una fase que
    `validar_fase` no admite- y se compara el resultado de los dos frente
    a la misma búsqueda.
    """
    huerfana = EntregaRegistrada(
        id="id-huerfana", codigo_alumno="AF023", ciclo="DAM",
        fase="FASE_ANTIGUA", version=1, nombre_archivo="viejo.pdf",
        huella="f" * 64, recibida_en=datetime.now(), estado="RECIBIDO",
        motivo_bloqueo=None, version_criterios="v2025-2026",
    )
    almacen_memoria = AlmacenEnMemoria()
    almacen_memoria._entregas[huerfana.id] = huerfana

    fila_huerfana = {
        **ENTREGA, "id": "id-huerfana", "fase": "FASE_ANTIGUA",
        "proyecto": {"alumno": {"codigo": "AF023", "ciclo": "DAM"}},
    }

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[fila_huerfana])

    resultado_memoria = almacen_memoria.anterior_de("AF023", "E2")
    resultado_supabase = _almacen(responder).anterior_de("AF023", "E2")

    assert resultado_memoria is None
    assert resultado_supabase == resultado_memoria


def test_anterior_de_elige_la_inmediatamente_previa_entre_varias_candidatas_fuera_de_orden() -> None:
    """Blinda `max(previas, key=...)` en supabase.py, igual que el test
    equivalente de memoria.py (`test_la_anterior_es_la_inmediatamente_previa_entre_varias_candidatas`).

    PostgREST no promete ningún orden en las filas de esta consulta -no se
    pide `order` aquí, la selección es cosa de esta función, no de la base
    de datos-. Se simula una respuesta con las candidatas fuera de orden:
    TEMA, luego E2, luego E1. Si la selección fuera «la primera de la
    lista» en vez de la más avanzada, este test fallaría: TEMA es la
    primera fila y no es la inmediatamente anterior a E3, E2 sí lo es. La
    última aserción lo deja explícito.
    """
    filas = [_fila("TEMA", huella="1" * 64), _fila("E2", huella="2" * 64),
              _fila("E1", huella="3" * 64)]

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=filas)

    almacen_memoria = AlmacenEnMemoria()
    almacen_memoria.registrar(_entrega(fase="TEMA", huella="1" * 64))
    almacen_memoria.registrar(_entrega(fase="E2", huella="2" * 64))
    almacen_memoria.registrar(_entrega(fase="E1", huella="3" * 64))

    anterior_supabase = _almacen(responder).anterior_de("AF023", "E3")
    anterior_memoria = almacen_memoria.anterior_de("AF023", "E3")

    assert anterior_supabase is not None
    assert anterior_supabase.fase == "E2"
    assert anterior_supabase.fase == anterior_memoria.fase
    assert anterior_supabase.version == anterior_memoria.version
    # Si la implementación tomara la primera fila de la respuesta en vez de
    # la máxima, esta aserción fallaría: la primera fila es TEMA.
    assert filas[0]["fase"] != anterior_supabase.fase


def test_anterior_de_puede_ser_una_version_previa_de_la_misma_fase() -> None:
    """Equivalente de
    `test_memoria.py::test_la_anterior_puede_ser_una_version_previa_de_la_misma_fase`.
    """
    fila = _fila("E2", version=1)

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[fila])

    almacen_memoria = AlmacenEnMemoria()
    almacen_memoria.registrar(_entrega(fase="E2", version=1))

    anterior_supabase = _almacen(responder).anterior_de("AF023", "E2", version=2)
    anterior_memoria = almacen_memoria.anterior_de("AF023", "E2", version=2)

    assert anterior_supabase is not None
    assert anterior_supabase.version == 1
    assert anterior_supabase.version == anterior_memoria.version
    assert anterior_supabase.fase == anterior_memoria.fase


def test_anterior_de_descarta_filas_de_otro_alumno_aunque_el_servidor_las_devuelva() -> None:
    """Última defensa contra atribuir a un alumno el trabajo de otro.

    La consulta ya filtra `proyecto.alumno.codigo=eq.{codigo_alumno}` en el
    servidor, pero esta prueba no confía en eso: simula justo el fallo
    -el filtro del servidor no filtrando, o alguien tocando la consulta y
    dejándola sin ese filtro- devolviendo una fila de un alumno distinto
    del pedido, y comprueba que el filtrado en Python
    (`entrega.codigo_alumno == codigo_alumno`, ya presente en el código)
    la descarta igual. Equivalente de
    `test_memoria.py::test_la_anterior_es_de_ese_alumno_y_no_de_otro`.
    """
    fila_de_otro = _fila("E1", codigo_alumno="AF024")

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[fila_de_otro])

    almacen_memoria = AlmacenEnMemoria()
    almacen_memoria.registrar(_entrega(codigo_alumno="AF024", fase="E1"))

    resultado_supabase = _almacen(responder).anterior_de("AF023", "E2")
    resultado_memoria = almacen_memoria.anterior_de("AF023", "E2")

    assert resultado_supabase is None
    assert resultado_supabase == resultado_memoria


def test_anterior_de_sin_entrega_previa_da_none_en_los_dos_almacenes() -> None:
    """Equivalente de
    `test_memoria.py::test_sin_entrega_previa_no_hay_anterior`: una entrega
    en la propia fase TEMA no cuenta como anterior a sí misma -ninguna fase
    la precede-.
    """
    fila = _fila("TEMA")

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[fila])

    almacen_memoria = AlmacenEnMemoria()
    almacen_memoria.registrar(_entrega(fase="TEMA"))

    resultado_supabase = _almacen(responder).anterior_de("AF023", "TEMA")
    resultado_memoria = almacen_memoria.anterior_de("AF023", "TEMA")

    assert resultado_supabase is None
    assert resultado_supabase == resultado_memoria
