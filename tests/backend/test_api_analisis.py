"""Los endpoints del análisis."""

import threading
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Valoracion
from backend.analisis.proveedor import ErrorDelProveedor, ProveedorSimulado
from backend.analisis.verificacion import ValoracionVerificada
from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.correccion import (
    LIMITE_DE_OBSERVACION,
    LIMITE_DE_OBSERVACION_DOCENTE,
)
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.persistencia.supabase import ErrorDeAlmacen
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe

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


class _ProveedorNoSimulado:
    """`ProveedorSimulado`, con un `nombre` que no es "simulado".

    La guarda de protección de datos (bug 3, ver
    `test_sin_confirmar_el_analisis_no_llama_al_proveedor`) solo se aplica
    cuando `proveedor.nombre != "simulado"`: es la condición que distingue
    un motor que de verdad enviaría el trabajo del alumno fuera de un motor
    de pruebas que no envía nada a ningún sitio. `ProveedorSimulado` no
    sirve para probar ese lado de la condición porque su propio `nombre` es
    literalmente `"simulado"` -sería probar la guarda contra el caso que
    precisamente la desactiva-. Este envoltorio delega todo el
    comportamiento en un `ProveedorSimulado` interno y solo cambia el
    nombre, para no duplicar la lógica de respuestas y fallos en cola.
    """

    def __init__(self, *args, **kwargs) -> None:
        self._interno = ProveedorSimulado(*args, **kwargs)

    @property
    def nombre(self) -> str:
        return "real-de-prueba"

    @property
    def llamadas(self) -> list[tuple[str, str]]:
        return self._interno.llamadas

    def analizar(self, instruccion: str, texto: str, formato):
        return self._interno.analizar(instruccion, texto, formato)


class _AlmacenQueFallaAlGuardar:
    """Un `AlmacenEnMemoria` de verdad, salvo que `guardar_correccion`
    siempre levanta `ErrorDeAlmacen`, como levantaría `AlmacenSupabase` con
    la red caída, la clave caducada o un 4xx cualquiera de PostgREST.

    Cierra un punto ciego concreto: los tests de este fichero -todos, salvo
    los que usan este doble- pasan por `AlmacenEnMemoria`, y
    `AlmacenEnMemoria.guardar_correccion` nunca levanta `ErrorDeAlmacen` -no
    hay red que tumbar en memoria-. Es el mismo punto ciego que dejó pasar
    el bloqueante original con `TextoFueraDeLimite` sin capturar: aquella
    excepción sí se colaba en un test normal, porque
    `AlmacenEnMemoria.guardar_correccion` valida de verdad el límite de
    longitud del motor y la levanta ella misma; `ErrorDeAlmacen` nace de una
    conexión que el almacén en memoria no tiene, así que ningún test
    existente podía reproducirla sin un doble como este.

    El resto del comportamiento no se inventa: se delega en un
    `AlmacenEnMemoria` real -confirmar la entrega, cambiar su estado, leer
    lo guardado-, para que lo único distinto en el test sea la escritura que
    se quiere ver fallar. Con esto en su sitio, cualquier test futuro de
    este fichero que necesite reproducir un almacén caído -no solo el que
    prueba este bug- ya tiene con qué, sin volver a montar el doble desde
    cero.
    """

    MENSAJE = "Supabase no responde. Vuelve a intentarlo en unos minutos."

    def __init__(self) -> None:
        self._interno = AlmacenEnMemoria()

    @property
    def es_duradero(self) -> bool:
        return self._interno.es_duradero

    def registrar(self, entrega):
        return self._interno.registrar(entrega)

    def listar(self):
        return self._interno.listar()

    def por_id(self, identificador):
        return self._interno.por_id(identificador)

    def por_huella(self, huella):
        return self._interno.por_huella(huella)

    def anterior_de(self, codigo_alumno, fase, version=1):
        return self._interno.anterior_de(codigo_alumno, fase, version)

    def cambiar_estado(self, identificador, estado, motivo):
        return self._interno.cambiar_estado(identificador, estado, motivo)

    def guardar_correccion(self, *args, **kwargs):
        raise ErrorDeAlmacen(self.MENSAJE)

    def correccion_de(self, entrega_id):
        return self._interno.correccion_de(entrega_id)


class _AlmacenQueFallaConCualquierCosa(_AlmacenQueFallaAlGuardar):
    """El mismo doble, pero fallando con la excepción que se le indique.

    Existe para fijar que el revertido no depende de acertar una lista de
    excepciones. `AlmacenSupabase.guardar_correccion` puede fallar de formas
    que no son `ErrorDeAlmacen`: un `criteria/<version>/prioridades.yaml`
    malformado -un fichero que el docente edita a mano- levanta un error de
    YAML; un POST que vuelve sin representación levanta `IndexError`; una
    respuesta que no es JSON levanta un error de decodificación. Las tres
    dejaban la entrega diciendo ANALIZADO sin ninguna corrección detrás, que
    es el mismo callejón sin salida que ya se arregló dos veces enumerando
    tipos, y que por eso ahora se cierra por construcción.
    """

    def __init__(self, fallo: Exception) -> None:
        super().__init__()
        self._fallo = fallo

    def guardar_correccion(self, *args, **kwargs):
        raise self._fallo


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


def _valoracion_de_prueba(
    dimension: str, observacion: str, prioridad: str | None = "P2",
) -> ValoracionVerificada:
    return ValoracionVerificada(
        dimension=dimension, nivel="EN_DESARROLLO", prioridad=prioridad,
        evidencia=Evidencia(cita="cita de prueba", apartado="5"),
        observacion=observacion, evidencia_localizada=True,
    )


def _informe_de_prueba(**cambios) -> Informe:
    """Un `Informe` construido a mano, sin pasar por el motor ni por
    `seleccionar_prioridades`.

    Sirve para preparar directamente el estado guardado que `revisar()` va
    a leer, con listas que -a propósito- no comparten instancia entre sí:
    es justo la situación con la que se topa `revisar()` en producción
    tras una edición anterior, y la más exigente para comprobar que la
    decisión de esta petición se aplica en las tres listas por igual.
    """
    datos = dict(
        identificacion={
            "alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": "1",
            "archivo": "AF023_DAM_E2_20260115_v1.pdf", "criterios": "v2026-2027",
        },
        control_administrativo=[], resumen="Resumen.", valoraciones=[],
        fortalezas=[], prioridades=[], prioridades_descartadas=[], dudas=[],
        indicios=[], reparos=[], dimensiones_ausentes=[], semaforo="AMBAR",
        recomendacion=None, motor="simulado",
    )
    datos.update(cambios)
    return Informe(**datos)


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
    r = cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                      json={"confirmo_datos_reales": True})

    assert r.status_code == 200
    assert r.json()["informe"]["valoraciones"][0]["dimension"] == "D05"
    assert r.json()["devolucion"]["acciones"]
    assert r.json()["aviso"] is None


def test_el_analisis_se_recupera_despues(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})

    r = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 200
    assert r.json()["informe"]["valoraciones"][0]["dimension"] == "D05"


def test_sin_analizar_no_hay_analisis_que_devolver(cliente) -> None:
    r = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 404
    assert "no se ha analizado" in r.json()["detail"].lower()


def test_analizar_no_repite_la_llamada_al_motor(cliente) -> None:
    """Un análisis cuesta dinero: pedir la ficha no puede volver a pagarlo."""
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})
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

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

    assert r.status_code == 503
    assert "sin red" in r.json()["detail"]


def test_el_motor_se_declara(cliente) -> None:
    """Un análisis simulado no es un análisis y el docente debe saberlo."""
    r = cliente.get("/api/motor")

    assert r.status_code == 200
    assert r.json()["es_simulado"] is True
    assert r.json()["avisos"]


def test_la_revision_conserva_solo_lo_aprobado(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})

    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "DESCARTADA", "texto": None}],
    })

    assert r.status_code == 200
    assert r.json()["informe"]["prioridades"] == []


def test_la_revision_admite_editar_el_texto(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})

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

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

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

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

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
        r = c.post(f"/api/entregas/{ident}/analisis",
                    json={"confirmo_datos_reales": True})
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

    c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

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
        r = c.post(f"/api/entregas/{ident}/analisis",
                    json={"confirmo_datos_reales": True})
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
        (503, fallo_motor.post(f"/api/entregas/{ident_fallo}/analisis",
                                json={"confirmo_datos_reales": True}))
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
        (400, ilegible.post(f"/api/entregas/{ident_ilegible}/analisis",
                             json={"confirmo_datos_reales": True}))
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
        (409, en_curso.post(f"/api/entregas/{ident_en_curso}/analisis",
                             json={"confirmo_datos_reales": True}))
    )

    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})
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

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

    assert r.status_code == 503
    assert "fuga-de-prueba" not in r.json()["detail"]
    assert r.json()["detail"] == (
        "No se ha podido completar el análisis: fallo del proveedor de prueba."
    )


# --- Tres fallos encontrados en `analisis.py` en revisión: cada uno tenía --
# un test que comprobaba justo lo único que ya funcionaba, o no tenía
# ninguno. Ver `.superpowers/sdd/2026-08-29-analisis-y-salidas/
# arreglo-revision-report.md`.


def test_editar_una_observacion_llega_tambien_a_prioridades(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Bug 1: `revisar()` reconstruía `prioridades` filtrando los objetos
    ORIGINALES de `guardada.informe.prioridades`, así que una edición
    quedaba aplicada en `valoraciones` y perdida en `prioridades` -el
    Anexo C, lo que de verdad se traslada al alumno-: las dos versiones
    convivían en el mismo informe, sin ningún aviso. El test anterior solo
    comprobaba `valoraciones`, el único campo que sí funcionaba.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(criterios_de_analisis, entregas, ProveedorSimulado())
    ident = _confirmar(c)

    original = "Faltan fuentes que respalden las cifras."
    informe = _informe_de_prueba(
        valoraciones=[_valoracion_de_prueba("D05", original)],
        prioridades=[_valoracion_de_prueba("D05", original)],
    )
    c.app.state.almacen.guardar_correccion(ident, informe, None, "simulado")

    editado = "Justifica las cifras con al menos una fuente primaria."
    r = c.post(f"/api/entregas/{ident}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "EDITADA",
                        "texto": editado}],
    })

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["informe"]["valoraciones"][0]["observacion"] == editado
    assert cuerpo["informe"]["prioridades"][0]["observacion"] == editado

    # Lo guardado tiene que coincidir con lo devuelto: una recarga de la
    # ficha no puede volver a enseñar la versión del motor en `prioridades`.
    r2 = c.get(f"/api/entregas/{ident}/analisis")
    assert r2.json()["informe"]["prioridades"][0]["observacion"] == editado


def test_descartar_una_observacion_la_quita_de_prioridades_descartadas(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Bug 1, la otra mitad: `prioridades_descartadas` ni siquiera entraba
    en el `model_copy` de `revisar()` -no se filtraba, no se editaba, se
    quedaba tal cual estaba guardada-. Si el docente descarta una
    observación por completo, no puede sobrevivir aquí tampoco: sigue
    siendo parte del informe interno que lee el docente, y «descartada»
    tiene que significar lo mismo en las tres listas.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(criterios_de_analisis, entregas, ProveedorSimulado())
    ident = _confirmar(c)

    informe = _informe_de_prueba(
        valoraciones=[_valoracion_de_prueba("D07", "Observación discutible.")],
        prioridades_descartadas=[
            _valoracion_de_prueba("D07", "Observación discutible.")
        ],
    )
    c.app.state.almacen.guardar_correccion(ident, informe, None, "simulado")

    r = c.post(f"/api/entregas/{ident}/revision", json={
        "decisiones": [{"dimension": "D07", "decision": "DESCARTADA",
                        "texto": None}],
    })

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["informe"]["valoraciones"] == []
    assert cuerpo["informe"]["prioridades_descartadas"] == []


def test_revisar_recompone_el_resumen(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """El resumen contradice al informe que tiene debajo si no se
    recompone: `revisar()` ya recompone `valoraciones`, `prioridades` y
    `prioridades_descartadas` (los dos tests anteriores), pero dejaba
    `resumen` guardado tal cual, con el recuento de ANTES de aplicar la
    revisión. El docente que vuelve al día siguiente leía, por ejemplo, «2
    prioridades verificadas (1 P1, 1 P2)» encima de una lista de
    prioridades con una sola entrada y ningún P1 -exactamente lo que este
    test reproduce y comprueba que ya no pasa-.

    El semáforo no se recalcula -no es una de las piezas que el docente
    edita aquí-, así que la primera frase del resumen sigue diciendo lo
    mismo que el campo `semaforo`, sin tocar.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    c = _crear_cliente(criterios_de_analisis, entregas, ProveedorSimulado())
    ident = _confirmar(c)

    p1 = _valoracion_de_prueba(
        "D06", "Carencia crítica sin justificar.", prioridad="P1"
    )
    p2 = _valoracion_de_prueba(
        "D05", "Faltan fuentes que respalden las cifras.", prioridad="P2"
    )
    informe = _informe_de_prueba(
        valoraciones=[p1, p2],
        prioridades=[p1, p2],
        semaforo="ROJO",
        resumen=(
            "Semáforo propuesto: ROJO. 2 prioridades verificadas para la "
            "devolución (1 P1, 1 P2)."
        ),
    )
    c.app.state.almacen.guardar_correccion(ident, informe, None, "simulado")

    r = c.post(f"/api/entregas/{ident}/revision", json={
        "decisiones": [{"dimension": "D06", "decision": "DESCARTADA",
                        "texto": None}],
    })

    assert r.status_code == 200
    cuerpo = r.json()
    assert [v["dimension"] for v in cuerpo["informe"]["prioridades"]] == ["D05"]

    resumen = cuerpo["informe"]["resumen"]
    assert "2 prioridades" not in resumen
    assert "1 P1" not in resumen
    assert "1 prioridad verificada" in resumen
    assert "1 P2" in resumen
    # El semáforo no lo toca la revisión: la primera frase del resumen
    # sigue de acuerdo con el campo `semaforo`, sin recalcular.
    assert cuerpo["informe"]["semaforo"] == "ROJO"
    assert "Semáforo propuesto: ROJO" in resumen

    # Lo guardado coincide con lo devuelto: una recarga de la ficha no
    # vuelve a enseñar el resumen de antes de la revisión.
    r2 = c.get(f"/api/entregas/{ident}/analisis")
    assert r2.json()["informe"]["resumen"] == resumen


def test_una_edicion_demasiado_larga_no_da_un_500_y_no_guarda_nada(
    cliente,
) -> None:
    """Bug 2: `validar_textos_acotados` limita la observación del docente a
    `LIMITE_DE_OBSERVACION_DOCENTE` caracteres y levanta una excepción;
    `revisar()` no la capturaba, así que una edición larga del docente
    reventaba en un «Internal Server Error» crudo y todas las decisiones de
    esa petición se perdían. El mensaje de la excepción de base, además,
    dice «esto indica un fallo del motor»: falso en este canal, el texto lo
    ha escrito el docente a mano, y ese mensaje concreto no puede llegarle
    tal cual.
    """
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})

    texto_largo = "x" * (LIMITE_DE_OBSERVACION_DOCENTE + 1)
    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "EDITADA",
                        "texto": texto_largo}],
    })

    assert r.status_code == 400
    detalle = r.json()["detail"]
    assert "fallo del motor" not in detalle
    assert str(len(texto_largo)) in detalle
    assert str(LIMITE_DE_OBSERVACION_DOCENTE) in detalle
    assert "no se ha guardado" in detalle.lower()
    assert _sin_jerga(detalle)

    # Nada de la revisión ha quedado guardado: la observación sigue siendo
    # la que había, no la editada y rechazada.
    r2 = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")
    observacion_guardada = r2.json()["informe"]["valoraciones"][0]["observacion"]
    assert observacion_guardada != texto_largo


def test_una_edicion_por_debajo_del_limite_del_docente_pero_por_encima_del_motor_se_guarda(
    cliente,
) -> None:
    """El límite del docente es más holgado que el del motor a propósito
    (bug 2): un texto que el motor nunca podría guardar -por encima de
    `LIMITE_DE_OBSERVACION`- tiene que poder guardarse igual cuando lo
    escribe el docente al revisar, siempre que quepa en su propio límite,
    más generoso.
    """
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis",
                 json={"confirmo_datos_reales": True})
    assert LIMITE_DE_OBSERVACION < LIMITE_DE_OBSERVACION_DOCENTE  # la premisa del test

    texto_entre_los_dos_limites = "x" * (LIMITE_DE_OBSERVACION + 100)
    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "EDITADA",
                        "texto": texto_entre_los_dos_limites}],
    })

    assert r.status_code == 200
    assert (
        r.json()["informe"]["valoraciones"][0]["observacion"]
        == texto_entre_los_dos_limites
    )


def test_sin_confirmar_el_analisis_no_llama_al_proveedor(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Bug 3: la raíz de prueba no trae `docs/PENDIENTE_OFICIAL.md` -lo que
    `proteccion_datos_pendiente()` trata igual que si `proteccion_datos`
    siguiera pendiente, con el mismo criterio que ya usaba
    `tools/calibrar.py`-, así que analizar sin confirmar no puede ni tocar
    al proveedor: ese es justo el canal por el que saldría el trabajo real
    de un alumno.

    Con `_ProveedorNoSimulado`, no `ProveedorSimulado`: la guarda ahora solo
    se comprueba cuando el motor configurado no es el simulado -ver
    `test_con_el_motor_simulado_no_hace_falta_confirmar_aunque_siga_pendiente`,
    justo debajo, para el otro lado de esa misma condición-, y este test
    tiene que seguir demostrando el bloqueo con un motor que sí es real.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    proveedor = _ProveedorNoSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 428
    detalle = r.json()["detail"]
    assert "proteccion_datos" in detalle
    assert "confirm" in detalle.lower()
    assert _sin_jerga(detalle)
    assert proveedor.llamadas == []
    assert c.app.state.almacen.correccion_de(ident) is None


def test_con_el_motor_simulado_no_hace_falta_confirmar_aunque_siga_pendiente(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Bug 3, el reverso del test anterior: `AVISO_PROTECCION_DATOS` dice
    que «el texto íntegro del documento se envía a un proveedor de análisis
    externo», y con el motor simulado eso es falso -`ProveedorSimulado` no
    manda nada a ningún sitio-. Pedir una confirmación consciente para un
    envío que no va a ocurrir no protege nada, así que la guarda no debe
    pedirla: el análisis sigue su curso con normalidad, sin
    `confirmo_datos_reales`, aunque `proteccion_datos` siga pendiente -la
    misma raíz de prueba que en el test anterior, sin
    `docs/PENDIENTE_OFICIAL.md`-.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 200
    assert len(proveedor.llamadas) == 2


def test_confirmando_se_puede_analizar_aunque_siga_pendiente(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """El reverso del test anterior: la guarda no es un bloqueo sin
    salida. Con la confirmación explícita, el análisis sigue su curso con
    normalidad -mismo resultado que sin la guarda-.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

    assert r.status_code == 200
    assert len(proveedor.llamadas) == 2


def test_si_proteccion_datos_ya_no_esta_pendiente_no_hace_falta_confirmar(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """Cuando `proteccion_datos` ya no conste en `docs/PENDIENTE_OFICIAL.md`
    -se ha resuelto de verdad-, la guarda deja de pedir nada: es la misma
    lectura que ya hace `tools/calibrar.py` de su propia raíz.
    """
    (criterios_de_analisis / "docs").mkdir()
    (criterios_de_analisis / "docs" / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente\n\nYa no queda nada pendiente de este apartado.\n",
        encoding="utf-8",
    )
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 200
    assert len(proveedor.llamadas) == 2


def test_el_motor_devuelve_una_observacion_demasiado_larga_no_da_un_500(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """La otra mitad del bug 2/3: si es el motor -no el docente- quien
    devuelve una observación por encima de `LIMITE_DE_OBSERVACION`,
    `analizar()` tampoco puede reventar en un «Internal Server Error»
    crudo. Y aquí hay algo más que capturar la excepción: `analizar_entrega`
    ya ha marcado la entrega ANALIZADO antes de que este endpoint intente
    guardar la corrección, así que si no se revirtiera, el docente vería la
    entrega como analizada sin ninguna corrección detrás -`GET /analisis`
    respondería 404 sobre una entrega que dice estar analizada-.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    analisis_con_observacion_larga = AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita=CITA, apartado="5"),
            observacion="x" * (LIMITE_DE_OBSERVACION + 1),
        )],
        fortalezas=[], patrones=[], dudas_para_el_docente=[],
        indicios_de_autoria=[],
    )
    proveedor = ProveedorSimulado(
        respuestas=[analisis_con_observacion_larga, _devolucion()]
    )
    c = _crear_cliente(criterios_de_analisis, entregas, proveedor)
    ident = _confirmar(c)

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

    assert r.status_code == 503
    detalle = r.json()["detail"]
    assert "no es un fallo tuyo" in detalle.lower()
    assert "no se ha guardado" in detalle.lower()
    assert "motor" in detalle.lower()
    assert _sin_jerga(detalle)

    # No queda nada guardado...
    assert c.get(f"/api/entregas/{ident}/analisis").status_code == 404
    # ...y la entrega no se ha quedado marcada ANALIZADO sin nada detrás:
    # el estado no miente, así que ha vuelto a RECIBIDO y se puede volver
    # a intentar.
    entrega = next(e for e in c.get("/api/entregas").json() if e["id"] == ident)
    assert entrega["estado"] == "RECIBIDO"


def test_un_almacen_que_falla_al_guardar_revierte_la_entrega_y_no_da_un_500(
    criterios_de_analisis, entregas, escribir_pdf
) -> None:
    """El mismo bug que la observación demasiado larga del motor -el test
    anterior-, con la otra excepción que `guardar_correccion` puede
    levantar: `ErrorDeAlmacen` (red caída, clave caducada, un 4xx cualquiera
    de PostgREST), no `TextoFueraDeLimite`.

    `analizar_entrega` ya ha marcado la entrega ANALIZADO antes de que este
    endpoint intente guardar la corrección. Antes de este arreglo,
    `_guardar_o_fallar` capturaba `TextoFueraDeLimite` pero no
    `ErrorDeAlmacen`: esta se escapaba directa hacia el manejador global de
    `backend/app.py`, que sí la traducía a un 503 legible, pero sin pasar
    antes por el revertido de estado. El resultado era justo el callejón
    sin salida que describe el encargo: el profesor pagaba la llamada al
    motor, no se llevaba nada, y la entrega se quedaba diciendo ANALIZADO
    sin corrección detrás -`GET /analisis` respondía 404 sobre una entrega
    que decía estar analizada, y en la pantalla no había ningún botón que
    la desatascara, porque «analizar» solo aparece en RECIBIDO y «ver
    revisión» solo en ANALIZADO-.

    Usa `_AlmacenQueFallaAlGuardar`, no `AlmacenEnMemoria`: es el doble que
    cierra el punto ciego real -`AlmacenEnMemoria.guardar_correccion` nunca
    levanta `ErrorDeAlmacen`, así que ningún test que pase por el almacén de
    siempre podía reproducir este bug-.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    app = crear_app(
        criterios_de_analisis,
        configuracion=Configuracion(carpeta_entregas=entregas,
                                    version_criterios="v2026-2027"),
        almacen=_AlmacenQueFallaAlGuardar(),
        proveedor=proveedor,
    )
    c = TestClient(app)
    ident = _confirmar(c)
    estado_antes = next(
        e for e in c.get("/api/entregas").json() if e["id"] == ident
    )["estado"]
    assert estado_antes == "RECIBIDO"

    r = c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

    assert r.status_code == 503
    assert r.json()["detail"] == _AlmacenQueFallaAlGuardar.MENSAJE
    assert _sin_jerga(r.json()["detail"])

    # No queda nada guardado...
    assert c.get(f"/api/entregas/{ident}/analisis").status_code == 404
    # ...y la entrega no se ha quedado marcada ANALIZADO sin nada detrás:
    # ha vuelto a RECIBIDO, tal y como estaba antes de este intento, y se
    # puede volver a analizar.
    entrega = next(e for e in c.get("/api/entregas").json() if e["id"] == ident)
    assert entrega["estado"] == "RECIBIDO"


@pytest.mark.parametrize("fallo", [
    yaml.YAMLError("prioridades.yaml esta malformado"),
    IndexError("el POST volvio sin representacion"),
    ValueError("la respuesta no era JSON"),
])
def test_la_entrega_revierte_falle_el_almacen_como_falle(
    criterios_de_analisis, entregas, escribir_pdf, fallo
) -> None:
    """El revertido no puede depender de acertar la lista de excepciones.

    Esta es la tercera vez que aparece el mismo callejón sin salida. Primero
    solo se capturaba `TextoFueraDeLimite` y `ErrorDeAlmacen` dejaba la
    entrega diciendo ANALIZADO sin corrección detrás; al añadirla, seguían
    escapándose estas tres, todas alcanzables desde
    `AlmacenSupabase.guardar_correccion`: `criteria/<version>/prioridades.yaml`
    es un fichero que el docente edita a mano y puede quedar malformado, un
    POST puede volver sin representación, y una respuesta 2xx puede no ser
    JSON -un proxy, un portal cautivo-.

    Enumerar es justo lo que ha fallado las dos veces, así que la garantía
    dejó de ser una lista: si la corrección no se ha escrito, la entrega no
    puede quedarse diciendo que sí, salga lo que salga de `guardar_correccion`.
    Este test lo fija con tres excepciones que no comparten ninguna clase
    base útil entre ellas.
    """
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    app = crear_app(
        criterios_de_analisis,
        configuracion=Configuracion(carpeta_entregas=entregas,
                                    version_criterios="v2026-2027"),
        almacen=_AlmacenQueFallaConCualquierCosa(fallo),
        proveedor=ProveedorSimulado(respuestas=[_analisis(), _devolucion()]),
    )
    c = TestClient(app)
    ident = _confirmar(c)

    with pytest.raises(type(fallo)):
        c.post(f"/api/entregas/{ident}/analisis",
               json={"confirmo_datos_reales": True})

    # Lo que importa no es qué error salió -ese lo traduce el manejador
    # global, o revienta como un 500 si nadie lo reconoce-, sino que la
    # entrega no se ha quedado mintiendo: vuelve a RECIBIDO y se puede
    # reintentar desde la pantalla.
    entrega = next(e for e in c.get("/api/entregas").json() if e["id"] == ident)
    assert entrega["estado"] == "RECIBIDO"
