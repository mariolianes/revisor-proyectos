"""Los endpoints del análisis."""

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Valoracion
from backend.analisis.proveedor import ErrorDelProveedor, ProveedorSimulado
from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.salidas.borrador import Devolucion

CITA = "El presupuesto inicial asciende a 4.500 euros"


def _analisis():
    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita=CITA, apartado="5"),
            observacion="Faltan fuentes que respalden las cifras.",
        )],
        fortalezas=[], patrones=[], dudas_para_el_docente=[],
        indicios_de_autoria=[],
    )


def _devolucion():
    return Devolucion(
        apertura="Has avanzado.", fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con fuentes."], cierre="Sigue asi.",
    )


def _devolucion_con_nota():
    """Un borrador que viola una regla dura -menciona una nota numérica-.

    `componer()` lo rechaza con `BorradorNoValido` después de pedirlo al
    motor, así que sirve para llegar a `InformeSinBorrador` sin tocar la
    red: el análisis (primera llamada) sale bien, y solo falla la redacción
    del borrador (segunda llamada).
    """
    return Devolucion(
        apertura="Tu nota final es un 8 sobre 10.",
        fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con fuentes."],
        cierre="Sigue asi.",
    )


@pytest.fixture
def entregas(tmp_path: Path) -> Path:
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    return carpeta


def _crear_cliente(criterios_de_analisis, entregas, proveedor):
    app = crear_app(
        criterios_de_analisis,
        configuracion=Configuracion(carpeta_entregas=entregas,
                                    version_criterios="v2026-2027"),
        almacen=AlmacenEnMemoria(),
        proveedor=proveedor,
    )
    return TestClient(app)


def _confirmar(
    cliente: TestClient, nombre_archivo: str = "AF023_DAM_E2_20260115_v1.pdf"
) -> str:
    cliente.post("/api/entregas", json={
        "nombre_archivo": nombre_archivo,
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })
    entregas_registradas = cliente.get("/api/entregas").json()
    return next(e["id"] for e in entregas_registradas
                if e["nombre_archivo"] == nombre_archivo)


@pytest.fixture
def cliente(criterios_de_analisis: Path, entregas: Path, escribir_pdf):
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    c.identificador = _confirmar(c)
    return c


def test_analizar_devuelve_las_dos_salidas(cliente) -> None:
    r = cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 200
    assert r.json()["informe"]["valoraciones"][0]["dimension"] == "D05"
    assert r.json()["devolucion"]["acciones"]
    assert r.json()["aviso"] is None


def test_el_analisis_se_recupera_despues(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    r = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 200
    assert r.json()["informe"]["valoraciones"][0]["dimension"] == "D05"


def test_sin_analizar_no_hay_analisis_que_devolver(cliente) -> None:
    r = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 404
    assert "no se ha analizado" in r.json()["detail"].lower()


def test_analizar_no_repite_la_llamada_al_motor(cliente) -> None:
    """Un análisis cuesta dinero: pedir la ficha no puede volver a pagarlo."""
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")
    cliente.get(f"/api/entregas/{cliente.identificador}/analisis")
    cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert len(cliente.app.state.proveedor.llamadas) == 2


def test_una_entrega_inexistente_da_404(cliente) -> None:
    assert cliente.post("/api/entregas/no-existe/analisis").status_code == 404


def test_un_fallo_del_motor_llega_en_castellano(criterios_de_analisis, entregas,
                                                escribir_pdf) -> None:
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(
        criterios_de_analisis, entregas,
        ProveedorSimulado(fallos=[ErrorDelProveedor("sin red")]),
    )
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 503
    assert "sin red" in r.json()["detail"]


def test_el_motor_se_declara(cliente) -> None:
    """Un análisis simulado no es un análisis y el docente debe saberlo."""
    r = cliente.get("/api/motor")

    assert r.status_code == 200
    assert r.json()["es_simulado"] is True
    assert r.json()["avisos"]


def test_la_revision_conserva_solo_lo_aprobado(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "DESCARTADA", "texto": None}],
    })

    assert r.status_code == 200
    assert r.json()["informe"]["prioridades"] == []


def test_la_revision_admite_editar_el_texto(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "EDITADA",
                        "texto": "Justifica las cifras con una fuente."}],
    })

    assert r.status_code == 200
    valorada = r.json()["informe"]["valoraciones"][0]
    assert valorada["observacion"] == "Justifica las cifras con una fuente."


def test_no_hay_endpoint_que_apruebe_ni_califique(cliente) -> None:
    """El §13 reserva eso al profesor: la forma de respetarlo es que no exista."""
    rutas = [r.path for r in cliente.app.routes]

    assert not any("aprobar" in r or "nota" in r or "calificar" in r for r in rutas)


# --- Lo que el brief no cubría: InformeSinBorrador, PdfIlegible, la fuga --
# de la clave y del texto del alumno, y el doble clic. Cada uno de estos
# casos se quedó sin manejador o sin test en el primer paso, y los tres
# formularios que aquí se cruzan -análisis, borrador, revisión- son
# justo donde el proyecto ya ha perdido cobertura ocho veces antes.


def test_un_informe_sin_borrador_no_se_trata_como_un_fallo(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """`InformeSinBorrador` no es un fallo total: el informe es válido.

    Tratarlo como un `ErrorDelProveedor` cualquiera -o dejar que suba sin
    manejador- tiraría a la papelera un análisis que sí se pudo completar.
    Aquí el análisis (primera llamada al motor) sale bien; solo la
    redacción del borrador (segunda llamada) viola una regla dura y hace
    que `componer()` levante `BorradorNoValido`, que `analizar_entrega`
    traduce a `InformeSinBorrador`.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion_con_nota()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["devolucion"] is None
    assert cuerpo["informe"]["valoraciones"][0]["dimension"] == "D05"
    assert "borrador" in cuerpo["aviso"].lower()
    assert cuerpo["entrega"]["estado"] == "ANALIZADO"

    # El aviso no puede prometer una acción que esta API no ofrece: no hay
    # forma de pedir solo el borrador otra vez, así que el texto no puede
    # sugerirlo -ni con la frase exacta que usa `BorradorNoValido`, ni con
    # una jerga distinta que diga lo mismo-, y sí tiene que decir cuál es
    # la acción real: repetir el análisis entero.
    aviso = cuerpo["aviso"].lower()
    assert "pide de nuevo la redacción" not in aviso
    # sin-tilde: variante deliberadamente sin tilde de la comprobación de
    # arriba, por si alguien reescribe el mensaje sin acentuar y el defecto
    # se cuela igual: esta línea no describe nada, solo repite la frase
    # prohibida en su forma sin tilde para que la denuncie también así.
    assert "pide de nuevo la redaccion" not in aviso
    assert "análisis completo" in aviso or "análisis entero" in aviso
    assert "informe es válido" in aviso or "informe" in aviso

    # El informe válido queda guardado y se recupera sin volver a pagar el
    # motor: dos llamadas en total, ni una más por el GET posterior.
    r2 = c.get(f"/api/entregas/{ident}/analisis")
    assert r2.status_code == 200
    assert r2.json()["devolucion"] is None
    assert r2.json()["aviso"] == cuerpo["aviso"]
    assert len(proveedor.llamadas) == 2


def test_el_aviso_del_borrador_incompleto_no_reenvia_el_texto_de_dominio(
) -> None:
    """Prueba de unidad sobre `_aviso_de_borrador_incompleto`, sin pasar
    por la API: cubre también la causa `ErrorDelProveedor`, que el flujo
    completo no puede provocar con `ProveedorSimulado` -sus fallos se
    consumen en la primera llamada, no en la segunda-.
    """
    from backend.api.analisis import _aviso_de_borrador_incompleto
    from backend.persistencia.modelos import EntregaRegistrada
    from backend.salidas.borrador import BorradorNoValido
    from backend.salidas.informe import Informe
    from backend.servicios.analisis_de_entrega import InformeSinBorrador

    entrega = EntregaRegistrada(
        id="e1", codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="a.pdf", huella="h", recibida_en="2026-01-15T00:00:00",
        estado="ANALIZADO", motivo_bloqueo=None, version_criterios="v1",
    )
    informe = Informe(
        identificacion={}, control_administrativo=[], resumen="r",
        valoraciones=[], fortalezas=[], prioridades=[],
        prioridades_descartadas=[], dudas=[], indicios=[], reparos=[],
        dimensiones_ausentes=[], semaforo="GRIS", recomendacion=None,
        motor="simulado",
    )

    causa_regla = BorradorNoValido(
        "El motor ha devuelto un borrador que viola la regla "
        "«nota_o_calificacion»; no se entrega. Corrígelo a mano o pide de "
        "nuevo la redacción."
    )
    try:
        raise InformeSinBorrador("mensaje interno", entrega, informe) from causa_regla
    except InformeSinBorrador as fallo_regla:
        aviso_regla = _aviso_de_borrador_incompleto(fallo_regla)

    assert "pide de nuevo la redacción" not in aviso_regla
    assert "«nota_o_calificacion»" not in aviso_regla  # jerga: un slug interno
    assert "análisis completo" in aviso_regla

    causa_proveedor = ErrorDelProveedor(
        "No se ha podido obtener el análisis: OpenAI no ha respondido en "
        "los 120 segundos de espera configurados. Puede ser una entrega "
        "larga o el servicio estar saturado; se puede reintentar."
    )
    try:
        raise InformeSinBorrador("mensaje interno", entrega, informe) from causa_proveedor
    except InformeSinBorrador as fallo_proveedor:
        aviso_proveedor = _aviso_de_borrador_incompleto(fallo_proveedor)

    assert "OpenAI no ha respondido" in aviso_proveedor
    assert "análisis completo" in aviso_proveedor


def test_un_archivo_que_desaparece_no_da_un_error_de_servidor(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """`PdfIlegible` es la parada del §18.2, no un 500 con una traza dentro."""
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(criterios_de_analisis, entregas, ProveedorSimulado())
    ident = _confirmar(c)
    (entregas / "AF023_DAM_E2_20260115_v1.pdf").unlink()

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 400
    assert "ya no está en la carpeta" in r.json()["detail"]


def test_el_esquema_openapi_no_lleva_el_texto_del_alumno(cliente) -> None:
    """El texto se excluye en el modelo (Task 8); aquí solo se comprueba
    que ningún tipo de esta API lo reintroduce por otra puerta.

    Se mira el esquema, no una respuesta concreta: una respuesta sin el
    campo no demuestra que el tipo no lo tenga, solo que en ese caso estaba
    vacío o no se sirvió. Y se mira la propiedad de verdad -las claves de
    `properties` en cada tipo del esquema-, no el texto entero del JSON: la
    palabra «texto_plano» sí aparece ahí, pero solo dentro de la
    descripción en prosa de `Medidas`, que la nombra entre comillas para
    explicar por qué está excluida. Buscarla como subcadena habría dado un
    falso positivo con esa misma frase.
    """
    esquema = cliente.get("/openapi.json").json()

    for nombre, tipo in esquema["components"]["schemas"].items():
        propiedades = tipo.get("properties", {})
        assert "texto_plano" not in propiedades, (
            f"«{nombre}» expone texto_plano como propiedad del esquema."
        )


def test_una_segunda_peticion_simultanea_no_paga_el_motor_dos_veces(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Dos clics sobre el mismo botón, casi a la vez: uno gana, el otro
    recibe 409 y no llega a tocar el proveedor.

    El proveedor simulado solo tiene una respuesta programada para cada
    formulario; si el segundo hilo también llegara a pedir un análisis,
    `ProveedorSimulado.analizar` fallaría con un `AssertionError` en vez de
    devolver un 409 ordenado, así que este test también sirve de guarda
    contra que alguien quite el candado sin darse cuenta.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    # El candado se toma antes de la primera llamada al motor: simular la
    # carrera basta con ocupar el hueco a mano, como haría un segundo hilo
    # que llegara una fracción de segundo antes que el que hace la llamada
    # real. Es determinista, a diferencia de lanzar dos hilos de verdad.
    c.app.state.analisis_en_curso.add(ident)
    try:
        r = c.post(f"/api/entregas/{ident}/analisis")
    finally:
        c.app.state.analisis_en_curso.discard(ident)

    assert r.status_code == 409
    assert "en curso" in r.json()["detail"].lower()
    assert proveedor.llamadas == []


def test_el_candado_se_libera_incluso_si_el_analisis_falla(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Un fallo del motor no puede dejar la entrega bloqueada para siempre."""
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(
        criterios_de_analisis, entregas,
        ProveedorSimulado(fallos=[ErrorDelProveedor("sin red")]),
    )
    ident = _confirmar(c)

    c.post(f"/api/entregas/{ident}/analisis")

    assert ident not in c.app.state.analisis_en_curso


def test_dos_hilos_a_la_vez_solo_uno_analiza(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """La carrera real, con hilos de verdad, sin trucar el estado a mano."""
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    resultados: list[int] = []
    listos = threading.Barrier(2)

    def _pedir() -> None:
        listos.wait()
        r = c.post(f"/api/entregas/{ident}/analisis")
        resultados.append(r.status_code)

    hilos = [threading.Thread(target=_pedir) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert sorted(resultados) == [200, 409]


# --- Todo mensaje que llega a un docente, y no a un programador ---------

# Marcadores de una traza de Python o del nombre crudo de una excepción,
# ninguno de los cuales debería aparecer en ningún texto que lea el
# docente. No es una lista exhaustiva -no puede serlo-, pero cubre lo que
# ya se ha colado alguna vez en este tipo de sistema: una traza entera, el
# nombre de una clase de excepción sin traducir, o la representación en
# bruto de un objeto de Python.
_MARCAS_DE_JERGA = (
    "Traceback",
    "traceback",
    "line ",
    "Error(",
    "Exception(",
    " at 0x",
    "__main__",
    "self.",
    "raise ",
)


def _sin_jerga(texto: str) -> bool:
    return not any(marca in texto for marca in _MARCAS_DE_JERGA)


def test_ningun_mensaje_de_error_deja_pasar_jerga_de_programador(
    cliente, criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Un barrido por los caminos de error de esta API: el código de
    estado de cada uno, además del mensaje.

    Un mensaje limpio en el código equivocado también engaña al docente
    -un 409 le dice «falta configurar algo», un 500 le diría «esto se ha
    roto», y son dos pantallas distintas en el frontend-, así que este
    barrido no se conforma con mirar `detail`: fija también el código
    esperado de cada camino. Es, además, el único sitio que toca alguno de
    estos caminos -«sin carpeta configurada» y «decisión inválida en la
    revisión» no tienen test propio-, así que sin esta aserción un cambio
    de código en cualquiera de los dos pasaría inadvertido.

    Cubre 404 (entrega inexistente, en `POST` y en `GET`), 409 (sin
    carpeta, y candado en uso), 503 (fallo del proveedor), 400 (archivo
    desaparecido, y decisión inválida en la revisión).
    """
    respuestas: list[tuple[int, object]] = []  # (codigo_esperado, respuesta)

    respuestas.append((404, cliente.post("/api/entregas/no-existe/analisis")))
    respuestas.append((404, cliente.get("/api/entregas/no-existe/analisis")))

    escribir_pdf(entregas / "otra.pdf", [["1. Introduccion", "Texto suficiente."]])
    sin_carpeta = _crear_cliente(
        criterios_de_analisis, entregas, ProveedorSimulado()
    )
    ident_temporal = sin_carpeta.app.state.almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="otra.pdf", huella="huella-1",
        version_criterios="v2026-2027",
    )).id
    # Se quita la carpeta después de registrar: registrar la exige.
    sin_carpeta.app.state.configuracion.carpeta_entregas = None
    respuestas.append(
        (409, sin_carpeta.post(f"/api/entregas/{ident_temporal}/analisis"))
    )

    fallo_motor = _crear_cliente(
        criterios_de_analisis, entregas,
        ProveedorSimulado(fallos=[ErrorDelProveedor("sin red")]),
    )
    ident_fallo = _confirmar(fallo_motor)
    respuestas.append(
        (503, fallo_motor.post(f"/api/entregas/{ident_fallo}/analisis"))
    )

    # Su propio archivo, no el que ya usan `cliente` y `fallo_motor`: al
    # final de este test se vuelve a usar `cliente` para la revisión, y
    # borrar el archivo compartido lo habría dejado también sin poder
    # analizarse a él.
    escribir_pdf(entregas / "ilegible.pdf", [["1. Introduccion", "Texto suficiente."]])
    ilegible = _crear_cliente(criterios_de_analisis, entregas, ProveedorSimulado())
    ident_ilegible = _confirmar(ilegible, "ilegible.pdf")
    (entregas / "ilegible.pdf").unlink()
    respuestas.append(
        (400, ilegible.post(f"/api/entregas/{ident_ilegible}/analisis"))
    )

    # El candado necesita una entrega real -y su propio archivo, distinto
    # del que el paso anterior acaba de borrar de la carpeta compartida-:
    # si se apunta a una entrega inexistente, el 404 de «no existe esa
    # entrega» se dispara antes de llegar a mirar el candado, y esta rama
    # dejaría de probar lo que dice probar.
    escribir_pdf(entregas / "candado.pdf", [["1. Introduccion", "Texto suficiente."]])
    en_curso = _crear_cliente(criterios_de_analisis, entregas, ProveedorSimulado())
    ident_en_curso = _confirmar(en_curso, "candado.pdf")
    en_curso.app.state.analisis_en_curso.add(ident_en_curso)
    respuestas.append(
        (409, en_curso.post(f"/api/entregas/{ident_en_curso}/analisis"))
    )

    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")
    respuestas.append((400, cliente.post(
        f"/api/entregas/{cliente.identificador}/revision", json={
            "decisiones": [{"dimension": "D05", "decision": "INVENTADA",
                            "texto": None}],
        },
    )))

    for codigo_esperado, respuesta in respuestas:
        assert respuesta.status_code == codigo_esperado, respuesta.json()
        mensaje = respuesta.json()["detail"]
        assert isinstance(mensaje, str) and mensaje, mensaje
        assert _sin_jerga(mensaje), mensaje


def test_el_fallo_del_motor_usa_el_contrato_del_tipo_no_str_crudo(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """La capa de API no puede confiar en que `str(fallo)` esté limpio por
    pura coincidencia con lo que hoy escribe el adaptador de OpenAI: tiene
    que pasar por `mensaje_para_el_profesor`, el contrato explícito de
    `ErrorDelProveedor`. Aquí se construye un proveedor de prueba cuya
    `str()` lleva algo que nunca debería llegar a la pantalla, y cuyo
    `mensaje_para_el_profesor` sí es el texto correcto, para comprobar
    cuál de los dos usa la API.

    Si `analizar()` volviera a hacer `detail=str(fallo)`, este test
    fallaría: el texto sucio aparecería en la respuesta.
    """

    class _FalloConMensajeSucio(ErrorDelProveedor):
        def __str__(self) -> str:
            return "fuga-de-prueba-sk-nunca-deberia-salir"

        @property
        def mensaje_para_el_profesor(self) -> str:
            return "No se ha podido completar el análisis: fallo del proveedor de prueba."

    class _ProveedorConMensajeSucio:
        nombre = "sucio-de-prueba"

        def analizar(self, instruccion, texto, formato):
            raise _FalloConMensajeSucio("fuga-de-prueba-sk-nunca-deberia-salir")

    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(criterios_de_analisis, entregas, _ProveedorConMensajeSucio())
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 503
    assert "fuga-de-prueba" not in r.json()["detail"]
    assert r.json()["detail"] == (
        "No se ha podido completar el análisis: fallo del proveedor de prueba."
    )
