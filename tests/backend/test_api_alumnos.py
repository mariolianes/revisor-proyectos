"""El alta de alumnos desde el programa, sin consola.

Los nombres son inventados y los Excel se construyen aquí: ninguno procede de
un listado real.
"""

from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app

CABECERA = ["Nombre y apellidos", "Centro", "Ciclo", "Estado", "ID CESUR"]


def _excel(ruta: Path, filas: list[list[str]]) -> Path:
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(CABECERA)
    for fila in filas:
        hoja.append(fila)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta)
    libro.close()
    return ruta


@pytest.fixture
def cliente(criterios_de_analisis: Path, tmp_path: Path):
    expedientes = tmp_path / "CESUR_2026-2027"
    (expedientes / "00_LISTADOS_ALUMNOS").mkdir(parents=True)
    locales = tmp_path / "datos-locales"
    locales.mkdir()
    entregas = tmp_path / "entregas"
    entregas.mkdir()

    # El catálogo de centros. Vacío, la importación rechaza TODAS las filas
    # -es el fallo seguro que declara `config/centros.yaml`: «no "cualquier
    # centro vale"»-, así que sin esto ninguna prueba del alta llegaría a
    # dar de alta a nadie.
    (criterios_de_analisis / "config").mkdir(parents=True, exist_ok=True)
    (criterios_de_analisis / "config" / "centros.yaml").write_text(
        "AND:\n  - AND-MAL-01\n  - AND-SEV-02\n", encoding="utf-8"
    )

    app = crear_app(criterios_de_analisis, configuracion=None)
    from backend.configuracion import cargar

    app.state.configuracion = cargar(criterios_de_analisis, entorno={
        "REVISOR_CARPETA_ENTREGAS": str(entregas),
        "REVISOR_RAIZ_EXPEDIENTES": str(expedientes),
        "REVISOR_DATOS_LOCALES": str(locales),
    })
    from backend.privacidad.listado_local import ListadoLocal

    app.state.listado_local = ListadoLocal(locales)
    cliente = TestClient(app)
    cliente.listados = expedientes / "00_LISTADOS_ALUMNOS"
    cliente.locales = locales
    return cliente


# --- Qué listados hay ------------------------------------------------------


def test_enumera_los_excel_de_la_carpeta_de_listados(cliente) -> None:
    _excel(cliente.listados / "andalucia.xlsx", [["Ana Ficticia", "AND-MAL-01", "MYP", "", ""]])
    (cliente.listados / "notas.txt").write_text("nada", encoding="utf-8")

    r = cliente.get("/api/alumnos/listados")

    assert r.status_code == 200
    assert [x["nombre"] for x in r.json()] == ["andalucia.xlsx"]


def test_sin_ningun_listado_la_lista_esta_vacia(cliente) -> None:
    assert cliente.get("/api/alumnos/listados").json() == []


# --- La importación --------------------------------------------------------


def test_importar_da_de_alta_a_los_alumnos(cliente) -> None:
    _excel(cliente.listados / "and.xlsx", [
        ["Ana Ficticia Inventada", "AND-MAL-01", "MYP", "", "cesur-1"],
        ["Beatriz Supuesta Imaginaria", "AND-MAL-01", "CIN", "", "cesur-2"],
    ])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "and.xlsx", "ccaa_code": "AND", "curso": "2026-2027",
    })

    assert r.status_code == 200
    assert r.json()["nuevas"] == 2
    assert r.json()["pendientes"] == []


def test_una_fila_dudosa_no_se_registra_y_se_dice_por_que(cliente) -> None:
    """El principio del docente aplicado al alta: la automatización puede
    detenerse; lo que no puede es asignar mal."""
    _excel(cliente.listados / "and.xlsx", [
        ["Ana Ficticia Inventada", "", "MYP", "", ""],
    ])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "and.xlsx", "ccaa_code": "AND", "curso": "2026-2027",
    })

    assert r.json()["nuevas"] == 0
    pendiente = r.json()["pendientes"][0]
    # La fila 2 del Excel: la 1 es la cabecera. Es el número que él ve al
    # abrir su fichero, que es de lo que se trata.
    assert pendiente["fila"] == 2
    assert pendiente["motivo"] == "SIN_CENTRO"


def test_el_nombre_del_alumno_no_sale_en_la_respuesta(cliente) -> None:
    """Lo que cruza esta frontera se identifica por número de fila y por
    identificador. La correspondencia con el nombre se queda en el equipo."""
    _excel(cliente.listados / "and.xlsx", [
        ["Ana Ficticia Inventada", "AND-MAL-01", "MYP", "", "cesur-1"],
        ["Beatriz Supuesta Imaginaria", "", "MYP", "", ""],
    ])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "and.xlsx", "ccaa_code": "AND", "curso": "2026-2027",
    })

    entero = r.text.lower()
    for parte in ("ana", "beatriz", "ficticia", "supuesta", "inventada"):
        assert parte not in entero


def test_el_nombre_si_queda_en_el_equipo_del_docente(cliente) -> None:
    """La otra mitad de lo anterior: la correspondencia se guarda, solo que
    en local. Si no se guardara, la minimización no sabría qué tachar."""
    from backend.privacidad.listado_local import ListadoLocal

    _excel(cliente.listados / "and.xlsx", [
        ["Ana Ficticia Inventada", "AND-MAL-01", "MYP", "", "cesur-1"],
    ])

    cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "and.xlsx", "ccaa_code": "AND", "curso": "2026-2027",
    })

    assert "Ana Ficticia Inventada" in ListadoLocal(cliente.locales).todos().values()


# --- Lo que no se admite ---------------------------------------------------


def test_una_ruta_no_puede_salirse_de_la_carpeta_de_listados(cliente) -> None:
    """Sin esto, un «../../algo.xlsx» leería un Excel de cualquier parte del
    disco del docente."""
    _excel(cliente.listados.parent.parent / "fuera.xlsx", [
        ["Ana Ficticia Inventada", "AND-MAL-01", "MYP", "", ""],
    ])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "../../fuera.xlsx", "ccaa_code": "AND",
        "curso": "2026-2027",
    })

    assert r.status_code == 404


def test_una_comunidad_que_no_existe_se_rechaza(cliente) -> None:
    _excel(cliente.listados / "and.xlsx", [["Ana Ficticia", "AND-MAL-01", "MYP", "", ""]])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "and.xlsx", "ccaa_code": "ZZZ", "curso": "2026-2027",
    })

    assert r.status_code == 400
    assert "no es una comunidad" in r.json()["detail"]


def test_un_curso_mal_escrito_se_rechaza(cliente) -> None:
    _excel(cliente.listados / "and.xlsx", [["Ana Ficticia", "AND-MAL-01", "MYP", "", ""]])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "and.xlsx", "ccaa_code": "AND", "curso": "2026",
    })

    assert r.status_code == 400


def test_un_excel_que_no_esta_se_dice_en_castellano(cliente) -> None:
    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "no-existe.xlsx", "ccaa_code": "AND",
        "curso": "2026-2027",
    })

    assert r.status_code == 404
    assert "no se encuentra" in r.json()["detail"].lower()


def test_un_excel_sin_filas_lo_dice(cliente) -> None:
    _excel(cliente.listados / "vacio.xlsx", [])

    r = cliente.post("/api/alumnos/importacion", json={
        "nombre_archivo": "vacio.xlsx", "ccaa_code": "AND", "curso": "2026-2027",
    })

    assert r.status_code == 400
    assert "nada que importar" in r.json()["detail"].lower()
