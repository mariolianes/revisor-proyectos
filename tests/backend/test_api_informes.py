"""El endpoint del informe por centro (punto 7 del orden de implantación)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.alumnos import AlumnoNuevo
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva


@pytest.fixture
def almacen() -> AlmacenEnMemoria:
    return AlmacenEnMemoria()


@pytest.fixture
def cliente(tmp_path: Path, almacen: AlmacenEnMemoria):
    app = crear_app(
        tmp_path,
        configuracion=Configuracion(version_criterios="v2026-2027"),
        almacen=almacen,
    )
    return TestClient(app)


def test_sin_filtros_responde_200_con_el_informe_del_curso_entero(cliente) -> None:
    respuesta = cliente.get("/api/informes/centro")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["filtro"] == {
        "ccaa": None, "centro": None, "ciclo": None, "curso": None, "fase": None,
    }
    assert cuerpo["cobertura"]["matriculados"] == 0


def test_con_filtros_los_devuelve_dentro_del_informe(cliente) -> None:
    respuesta = cliente.get(
        "/api/informes/centro", params={"ccaa": "AND", "ciclo": "MYP", "fase": "E1"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["filtro"] == {
        "ccaa": "AND", "centro": None, "ciclo": "MYP", "curso": None, "fase": "E1",
    }


def test_una_ccaa_desconocida_es_400_no_500(cliente) -> None:
    respuesta = cliente.get("/api/informes/centro", params={"ccaa": "XXX"})

    assert respuesta.status_code == 400
    assert "comunidad autónoma" in respuesta.json()["detail"]


def test_refleja_alumnos_y_entregas_ya_registrados(
    cliente, almacen: AlmacenEnMemoria,
) -> None:
    student_id = almacen.dar_de_alta_alumno(AlumnoNuevo(
        curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
        ciclo_code="MYP",
    )).student_id
    almacen.registrar(EntregaNueva(
        codigo_alumno=student_id, ciclo="MYP", fase="E1", version=1,
        nombre_archivo="entrega.pdf", huella="huella-1",
        version_criterios="v2026-2027",
    ))

    respuesta = cliente.get("/api/informes/centro", params={"fase": "E1"})

    cobertura = respuesta.json()["cobertura"]
    assert cobertura["matriculados"] == 1
    assert cobertura["por_fase"][0] == {
        "fase": "E1", "entregados": 1, "sin_entregar": 0,
        "sin_entregar_codigos": None,
    }


def test_ningun_campo_de_la_respuesta_lleva_un_nombre_de_alumno(
    cliente, almacen: AlmacenEnMemoria,
) -> None:
    """El endpoint entero, de punta a punta: ni un `nombre`, ni un `dni`, ni
    un `email` en ninguna parte del cuerpo JSON. Solo `student_id` -que
    viaja dentro de `sin_entregar_codigos`, nunca solo, y solo con
    ámbitos de al menos `UMBRAL_GRUPO_PEQUENO` matriculados-."""
    import json

    from backend.servicios.informe_centro import UMBRAL_GRUPO_PEQUENO

    for _ in range(UMBRAL_GRUPO_PEQUENO):
        almacen.dar_de_alta_alumno(AlumnoNuevo(
            curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
            ciclo_code="MYP",
        ))

    cuerpo = cliente.get("/api/informes/centro").json()
    texto = json.dumps(cuerpo, ensure_ascii=False).lower()

    for palabra_prohibida in ("nombre", "\"dni\"", "email", "correo", "telefono", "teléfono"):
        assert palabra_prohibida not in texto
