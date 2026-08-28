"""Los endpoints de entregas."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.memoria import AlmacenEnMemoria

# `criterios_de_formato` y los PDF vienen de tests/conftest.py.


@pytest.fixture
def cliente(criterios_de_formato: Path, tmp_path: Path, pdf_con_indice: Path):
    raiz = criterios_de_formato

    entregas = tmp_path / "entregas"
    entregas.mkdir()
    (entregas / "AF023_DAM_E2_20260115_v1.pdf").write_bytes(pdf_con_indice.read_bytes())
    (entregas / "cosa rara.pdf").write_bytes(pdf_con_indice.read_bytes())

    app = crear_app(
        raiz,
        configuracion=Configuracion(
            carpeta_entregas=entregas, version_criterios="v2026-2027"
        ),
        almacen=AlmacenEnMemoria(),
    )
    return TestClient(app)


def test_pendientes_devuelve_los_archivos_sin_registrar(cliente) -> None:
    respuesta = cliente.get("/api/entregas/pendientes")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 2


def test_pendientes_marca_cual_se_puede_confirmar_de_un_clic(cliente) -> None:
    pendientes = cliente.get("/api/entregas/pendientes").json()

    por_nombre = {p["nombre"]: p for p in pendientes}
    assert por_nombre["AF023_DAM_E2_20260115_v1.pdf"]["propuesta"]["completa"] is True
    assert por_nombre["cosa rara.pdf"]["propuesta"]["completa"] is False
    assert por_nombre["cosa rara.pdf"]["propuesta"]["motivo"]


def test_confirmar_registra_la_entrega(cliente) -> None:
    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert respuesta.status_code == 200
    assert respuesta.json()["entrega"]["estado"] == "RECIBIDO"
    assert respuesta.json()["medidas"]["total_paginas"] == 7


def test_lo_registrado_desaparece_de_pendientes(cliente) -> None:
    cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    pendientes = cliente.get("/api/entregas/pendientes").json()

    assert [p["nombre"] for p in pendientes] == ["cosa rara.pdf"]


def test_confirmar_un_archivo_que_no_esta_da_404(cliente) -> None:
    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "fantasma.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert respuesta.status_code == 404
    assert "fantasma.pdf" in respuesta.json()["detail"]


def test_una_fase_desconocida_da_400_con_motivo(cliente) -> None:
    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E9", "version": 1,
    })

    assert respuesta.status_code == 400
    assert "no es una fase" in respuesta.json()["detail"]


def test_la_ficha_se_recupera_por_su_identificador(cliente) -> None:
    creada = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.get(f"/api/entregas/{creada['entrega']['id']}")

    assert respuesta.status_code == 200
    assert len(respuesta.json()["comprobaciones"]) == 9


def test_una_ficha_inexistente_da_404(cliente) -> None:
    assert cliente.get("/api/entregas/no-existe").status_code == 404


def test_el_texto_del_trabajo_no_viaja_por_la_api(cliente) -> None:
    """Hermano del `test_no_envia_el_texto_del_trabajo` de
    `tests/persistencia/test_supabase.py`, pero para la API: D-001 no solo
    prohíbe que el texto llegue a la base de datos, tampoco tiene nada que
    hacer viajando por la red ni quedando en el registro de peticiones de
    nadie. `texto_plano` vive en `Medidas` porque lo necesita la
    comparación evolutiva (test siguiente), pero ahora lleva
    `Field(exclude=True)`.

    Se busca el texto del PDF de prueba (`pdf_con_indice`, conftest.py) en
    el cuerpo crudo de la respuesta, no solo la ausencia de la clave
    `texto_plano`: lo que hay que garantizar es que el contenido no viaja,
    no que el campo se llame de otra forma.
    """
    fragmento_reconocible = "Texto de la introduccion del trabajo"

    confirmar = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })
    assert fragmento_reconocible not in confirmar.text
    assert "texto_plano" not in confirmar.text

    identificador = confirmar.json()["entrega"]["id"]
    ficha = cliente.get(f"/api/entregas/{identificador}")
    assert fragmento_reconocible not in ficha.text
    assert "texto_plano" not in ficha.text


def test_la_comparacion_evolutiva_sigue_funcionando_tras_excluir_el_texto(
    criterios_de_formato: Path, tmp_path: Path,
    pdf_simple: Path, pdf_con_indice: Path,
) -> None:
    """`texto_plano` sigue viviendo en el objeto `Medidas` en memoria -es un
    atributo de Python que lee `backend/evolucion/comparacion.py`
    directamente, no algo que se reconstruya a partir de la respuesta
    serializada-, así que excluirlo de la API no puede romper la
    comparación con la entrega anterior. Sin este test, ese arreglo podría
    dejar la comparación muda sin que nadie se enterase.

    Las dos entregas usan PDFs con contenido distinto (`pdf_simple` y
    `pdf_con_indice`) a propósito: con el mismo contenido las dos tendrían
    la misma huella, y `registrar` rechazaría la segunda por chocar con lo
    ya declarado en la primera -otro caso, no el que aquí se comprueba.
    """
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    (entregas / "AF023_DAM_E1_20251201_v1.pdf").write_bytes(pdf_simple.read_bytes())
    (entregas / "AF023_DAM_E2_20260115_v1.pdf").write_bytes(pdf_con_indice.read_bytes())

    app = crear_app(
        criterios_de_formato,
        configuracion=Configuracion(
            carpeta_entregas=entregas, version_criterios="v2026-2027"
        ),
        almacen=AlmacenEnMemoria(),
    )
    cliente = TestClient(app)

    cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E1_20251201_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E1", "version": 1,
    })
    segunda = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    assert segunda["comparada_con"] == "AF023_DAM_E1_20251201_v1.pdf"
    assert segunda["evolucion"] is not None
    assert isinstance(segunda["evolucion"]["proporcion_conservada"], float)


def test_listar_devuelve_lo_registrado(cliente) -> None:
    cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert len(cliente.get("/api/entregas").json()) == 1


def test_cambiar_de_estado(cliente) -> None:
    creada = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{creada['entrega']['id']}/estado",
        json={"estado": "BLOQUEADO", "motivo": "Falta la portada."},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "BLOQUEADO"


def test_bloquear_sin_motivo_da_400(cliente) -> None:
    creada = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{creada['entrega']['id']}/estado",
        json={"estado": "BLOQUEADO", "motivo": ""},
    )

    assert respuesta.status_code == 400
    assert "motivo" in respuesta.json()["detail"]


@pytest.mark.parametrize("estado", ["APROBADO", "COMUNICADO"])
def test_esta_api_no_aprueba_ni_comunica(cliente, estado: str) -> None:
    """§13: la forma de que el sistema no decida es que la operación no exista.

    Los siete estados siguen en el modelo y en el enum de la tabla, porque
    la segunda parte del flujo los necesitará. Lo que se cierra es la
    puerta de esta API.
    """
    ficha = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{ficha['entrega']['id']}/estado",
        json={"estado": estado, "motivo": None},
    )

    assert respuesta.status_code == 400
    motivo = respuesta.json()["detail"]
    assert estado in motivo
    assert "segunda parte del flujo" in motivo
    assert "profesor" in motivo


@pytest.mark.parametrize("estado,motivo", [
    ("RECIBIDO", None),
    ("BLOQUEADO", "Falta el anexo."),
    ("ANALIZADO", None),
])
def test_los_tres_estados_de_esta_parte_siguen_funcionando(
    cliente, estado: str, motivo: str | None
) -> None:
    ficha = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{ficha['entrega']['id']}/estado",
        json={"estado": estado, "motivo": motivo},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == estado


def test_un_estado_que_no_existe_lo_sigue_explicando_el_almacen(cliente) -> None:
    """La puerta cerrada no debe tapar el mensaje de una errata."""
    ficha = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{ficha['entrega']['id']}/estado",
        json={"estado": "ANALIZDO", "motivo": None},
    )

    assert respuesta.status_code == 400
    assert "no es un estado del flujo" in respuesta.json()["detail"]


def test_el_entorno_avisa_de_que_no_se_guarda(cliente) -> None:
    """El almacén en memoria pierde lo guardado, y el docente ha de saberlo."""
    entorno = cliente.get("/api/entorno").json()

    assert entorno["persistencia_duradera"] is False
    assert entorno["hay_carpeta"] is True
    assert entorno["avisos"]


def test_sin_carpeta_los_pendientes_estan_vacios(tmp_path: Path) -> None:
    app = crear_app(
        tmp_path, configuracion=Configuracion(), almacen=AlmacenEnMemoria()
    )
    cliente = TestClient(app)

    assert cliente.get("/api/entregas/pendientes").json() == []
    assert cliente.get("/api/entorno").json()["hay_carpeta"] is False


def _entorno_con_carpeta(raiz: Path, ruta: Path) -> dict:
    """El aviso que ve el docente cuando REVISOR_CARPETA_ENTREGAS es «ruta»."""
    from backend.configuracion import cargar

    app = crear_app(
        raiz,
        configuracion=cargar(raiz, entorno={"REVISOR_CARPETA_ENTREGAS": str(ruta)}),
        almacen=AlmacenEnMemoria(),
    )
    return TestClient(app).get("/api/entorno").json()


def test_una_carpeta_que_no_existe_se_dice_tal_cual(tmp_path: Path) -> None:
    """El docente sí la había indicado: decirle que no hay ninguna es falso."""
    raiz = tmp_path / "repo"
    raiz.mkdir()

    entorno = _entorno_con_carpeta(raiz, tmp_path / "no-existe")

    assert entorno["hay_carpeta"] is False
    aviso = " ".join(entorno["avisos"])
    assert "no existe" in aviso
    assert "no-existe" in aviso
    assert "No hay carpeta de entregas configurada" not in aviso


def test_una_ruta_que_es_un_fichero_se_dice_tal_cual(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    fichero = tmp_path / "cosa.txt"
    fichero.write_text("x", encoding="utf-8")

    entorno = _entorno_con_carpeta(raiz, fichero)

    aviso = " ".join(entorno["avisos"])
    assert "no es una carpeta" in aviso
    # El resto del proyecto dice «fichero», no «archivo».
    assert "no a un fichero" in aviso
    assert "No hay carpeta de entregas configurada" not in aviso


def test_una_carpeta_dentro_del_repositorio_se_dice_tal_cual(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    dentro = raiz / "01_ALUMNOS"
    dentro.mkdir(parents=True)

    entorno = _entorno_con_carpeta(raiz, dentro)

    aviso = " ".join(entorno["avisos"])
    assert "dentro del repositorio" in aviso
    assert "No hay carpeta de entregas configurada" not in aviso


def test_sin_ninguna_carpeta_indicada_el_aviso_es_el_generico(tmp_path: Path) -> None:
    """El genérico sigue estando, para cuando de verdad no hay nada puesto."""
    from backend.configuracion import cargar

    app = crear_app(
        tmp_path, configuracion=cargar(tmp_path, entorno={}),
        almacen=AlmacenEnMemoria(),
    )

    avisos = TestClient(app).get("/api/entorno").json()["avisos"]

    assert any("No hay carpeta de entregas configurada" in a for a in avisos)


def test_la_version_de_criterios_elige_el_fichero_con_el_que_se_corrige(
    criterios_de_formato: Path, tmp_path: Path, pdf_con_indice: Path
) -> None:
    """REVISOR_VERSION_CRITERIOS no es decorativa.

    Elige el fichero de criterios con el que se contrasta el trabajo de un
    alumno. Se monta una segunda version que pide 999 paginas de contenido
    -donde la primera pide 4- y se comprueba que el veredicto cambia con
    ella, que es la unica forma de ver que la version configurada llega
    hasta donde se corrige.
    """
    raiz = criterios_de_formato
    otra = raiz / "criteria" / "v2027-2028"
    otra.mkdir(parents=True)
    (otra / "formato.yaml").write_text(
        "extension:\n"
        "  minimo_paginas_contenido: 999\n"
        "  fuente: maestro#6-estandar-academico\n",
        encoding="utf-8",
    )

    entregas = tmp_path / "entregas-version"
    entregas.mkdir()
    (entregas / "AF023_DAM_E2_20260115_v1.pdf").write_bytes(
        pdf_con_indice.read_bytes()
    )

    def veredicto(version: str) -> str:
        app = crear_app(
            raiz,
            configuracion=Configuracion(
                carpeta_entregas=entregas, version_criterios=version
            ),
            almacen=AlmacenEnMemoria(),
        )
        ficha = TestClient(app).post("/api/entregas", json={
            "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
            "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2",
            "version": 1,
        }).json()
        extension = next(
            c for c in ficha["comprobaciones"] if c["criterio"] == "extension"
        )
        return extension["veredicto"]

    assert veredicto("v2026-2027") == "CUMPLE"
    assert veredicto("v2027-2028") == "NO_CUMPLE"


def test_el_entorno_dice_con_que_version_se_esta_corrigiendo(cliente) -> None:
    """El docente tiene que poder ver cual esta en uso."""
    assert cliente.get("/api/entorno").json()["version_criterios"] == "v2026-2027"


@pytest.fixture
def cliente_dos_archivos(
    criterios_de_formato: Path, tmp_path: Path, pdf_con_indice: Path,
    pdf_simple: Path,
):
    """Dos archivos distintos, para poder confirmar dos entregas seguidas.

    El `cliente` de arriba deja dos copias del mismo PDF, asi que tienen la
    misma huella y la segunda choca con el error de atribucion: para probar
    dos entregas del mismo alumno hacen falta dos archivos de verdad
    distintos.
    """
    entregas = tmp_path / "dos-archivos"
    entregas.mkdir()
    (entregas / "AF023_DAM_E1_20260115_v1.pdf").write_bytes(
        pdf_con_indice.read_bytes()
    )
    (entregas / "AF023_DAM_E2_20260220_v1.pdf").write_bytes(
        pdf_simple.read_bytes()
    )
    app = crear_app(
        criterios_de_formato,
        configuracion=Configuracion(
            carpeta_entregas=entregas, version_criterios="v2026-2027"
        ),
        almacen=AlmacenEnMemoria(),
    )
    return TestClient(app)


def test_declarar_otro_ciclo_para_el_mismo_alumno_se_avisa(
    cliente_dos_archivos,
) -> None:
    """El ciclo es del alumno y manda el primero. Callarlo seria mentir.

    Registrar al mismo alumno con dos ciclos es casi siempre un error del
    profesor -una errata, o un codigo de alumno reutilizado-. El sistema usa
    el ciclo guardado, y tiene que decir que lo ha hecho: si es una errata,
    que la vea; y si el alumno ha cambiado de ciclo de verdad, que sepa que
    tiene que corregirlo el.
    """
    cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E1_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E1", "version": 1,
    })

    respuesta = cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260220_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAW", "fase": "E2", "version": 1,
    })

    # Es un aviso, no un error: la entrega queda registrada.
    assert respuesta.status_code == 200
    ficha = respuesta.json()
    assert ficha["entrega"]["ciclo"] == "DAM"

    aviso = ficha["aviso"]
    # Dice el declarado, el guardado, y que se ha usado el guardado.
    assert "DAW" in aviso
    assert "DAM" in aviso
    assert "AF023" in aviso
    assert "errata" in aviso
    assert "ficha de alumno" in aviso

    # Y no se ha quedado fuera: sigue en la lista, con el ciclo del alumno.
    listadas = cliente_dos_archivos.get("/api/entregas").json()
    assert len(listadas) == 2
    assert {e["ciclo"] for e in listadas} == {"DAM"}


def test_reconfirmar_con_los_mismos_datos_no_acusa_al_profesor(
    cliente_dos_archivos,
) -> None:
    """El profesor no cambia nada entre los dos intentos. Antes daba 400.

    Con «ciclo» dentro de los campos de identidad pasaba esto: el primer
    intento se aceptaba y el sistema guardaba el ciclo del alumno -que es lo
    correcto-, y el segundo, con EXACTAMENTE los mismos datos, se rechazaba
    diciendo «ahora se declara como AF023/DAW». El que había cambiado el
    dato era el sistema.

    Y es justo el caso legítimo que el aviso de «este archivo ya estaba
    registrado» existe para cubrir: mover un trabajo de carpeta y volver a
    confirmarlo.
    """
    datos = {
        "nombre_archivo": "AF023_DAM_E2_20260220_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAW", "fase": "E2", "version": 1,
    }
    cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E1_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E1", "version": 1,
    })

    primera = cliente_dos_archivos.post("/api/entregas", json=datos)
    segunda = cliente_dos_archivos.post("/api/entregas", json=datos)

    assert primera.status_code == 200
    assert segunda.status_code == 200, segunda.text
    # La misma ficha, no una segunda.
    assert segunda.json()["entrega"]["id"] == primera.json()["entrega"]["id"]
    assert len(cliente_dos_archivos.get("/api/entregas").json()) == 2
    # Y el aviso del ciclo sale las dos veces: informa, no bloquea.
    assert "DAW" in primera.json()["aviso"]
    assert "DAW" in segunda.json()["aviso"]
    # La segunda dice además que ya estaba registrado, que es lo que pasa.
    assert "ya estaba registrado" in segunda.json()["aviso"]


def test_con_el_ciclo_correcto_no_hay_aviso_de_ciclo(cliente_dos_archivos) -> None:
    """Un aviso que salta cuando no toca deja de leerse."""
    cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E1_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E1", "version": 1,
    })

    ficha = cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260220_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    assert "ciclo" not in ficha["aviso"]


def test_el_ciclo_escrito_con_espacios_o_en_minusculas_no_avisa(
    cliente_dos_archivos,
) -> None:
    """Lo que se compara es lo normalizado, no el texto crudo del formulario.

    `EntregaNueva` quita los espacios -tambien los de en medio- y pasa a
    mayusculas. Comparar el texto tal cual llega haria saltar el aviso por
    un espacio de mas al copiar y pegar, que es un aviso falso.
    """
    cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E1_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E1", "version": 1,
    })

    ficha = cliente_dos_archivos.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260220_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": " d am ", "fase": "E2", "version": 1,
    }).json()

    assert ficha["entrega"]["ciclo"] == "DAM"
    assert "ciclo" not in ficha["aviso"]


def test_el_editor_de_criterios_sigue_funcionando(cliente) -> None:
    """La app es una sola: añadir entregas no rompe lo que ya había."""
    assert cliente.get("/api/salud").status_code == 200


def test_confirmar_dos_veces_la_misma_entrega_no_duplica_y_avisa(cliente) -> None:
    """El caso legítimo: mismos datos declarados, misma huella.

    No es un error de atribución -eso ya lo cubre `registrar` con su
    `ValueError`-, así que no puede dar 400. Pero tampoco puede ser mudo:
    si el docente confirma dos veces el mismo archivo -por ejemplo, porque
    lo movió de carpeta y volvió a verlo como pendiente-, tiene que
    enterarse de que ya estaba registrado, no recibir una ficha como si
    fuera nueva.
    """
    primera = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    segunda = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert segunda.status_code == 200
    cuerpo = segunda.json()
    assert cuerpo["entrega"]["id"] == primera["entrega"]["id"]
    assert "ya estaba registrad" in cuerpo["aviso"].lower()


def test_confirmar_un_archivo_movido_de_subcarpeta_avisa_de_que_ya_estaba(
    criterios_de_formato: Path, tmp_path: Path, pdf_con_indice: Path,
) -> None:
    """El docente mueve el trabajo de subcarpeta y vuelve a aparecer como
    pendiente con una ruta relativa distinta. Al confirmarlo, `registrar`
    reconoce la misma huella y no crea una segunda ficha; el endpoint tiene
    que decir que ya existía, no callarlo."""
    entregas = tmp_path / "entregas"
    (entregas / "AF023").mkdir(parents=True)
    (entregas / "AF023" / "trabajo.pdf").write_bytes(pdf_con_indice.read_bytes())

    app = crear_app(
        criterios_de_formato,
        configuracion=Configuracion(
            carpeta_entregas=entregas, version_criterios="v2026-2027"
        ),
        almacen=AlmacenEnMemoria(),
    )
    cliente = TestClient(app)

    primera = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023/trabajo.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    (entregas / "AF023" / "OTROS").mkdir()
    (entregas / "AF023" / "trabajo.pdf").rename(
        entregas / "AF023" / "OTROS" / "trabajo.pdf"
    )

    pendientes = cliente.get("/api/entregas/pendientes").json()
    assert [p["nombre"] for p in pendientes] == ["AF023/OTROS/trabajo.pdf"]

    segunda = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023/OTROS/trabajo.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert segunda.status_code == 200
    cuerpo = segunda.json()
    assert cuerpo["entrega"]["id"] == primera["entrega"]["id"]
    assert "ya estaba registrad" in cuerpo["aviso"].lower()


def test_confirmar_con_otro_alumno_da_400_y_nombra_la_ficha_que_choca(cliente) -> None:
    """El mismo archivo -misma huella-, declarado ahora con otro alumno.

    No es el caso legítimo de moverlo de carpeta: es un error de
    atribución, y `AlmacenEnMemoria.registrar` lo rechaza con un
    `ValueError` que nombra bajo qué ficha está ya registrado ese
    contenido. El endpoint tiene que convertirlo en un 400 con ese mismo
    mensaje, no en un 500: es el aviso que evita colgarle a un alumno el
    trabajo de otro, y el profesor lo lee aquí.
    """
    primera = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "BX999", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert respuesta.status_code == 400
    detalle = respuesta.json()["detail"]
    assert "ya está registrado" in detalle
    assert primera["entrega"]["id"] in detalle
    assert "AF023" in detalle
    assert "BX999" in detalle
