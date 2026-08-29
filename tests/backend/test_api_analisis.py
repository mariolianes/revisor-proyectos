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


def _confirmar(cliente: TestClient) -> str:
    cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })
    return cliente.get("/api/entregas").json()[0]["id"]


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

    # El informe válido queda guardado y se recupera sin volver a pagar el
    # motor: dos llamadas en total, ni una más por el GET posterior.
    r2 = c.get(f"/api/entregas/{ident}/analisis")
    assert r2.status_code == 200
    assert r2.json()["devolucion"] is None
    assert len(proveedor.llamadas) == 2


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
