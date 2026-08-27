from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app


@pytest.fixture
def cliente(repo: Path) -> TestClient:
    return TestClient(crear_app(repo))


def test_documentos_devuelve_el_maestro_con_sus_secciones(cliente: TestClient):
    respuesta = cliente.get("/api/documentos")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos[0]["clave"] == "maestro"
    assert len(datos[0]["secciones"]) == 3


def test_una_seccion_trae_sus_criterios(cliente: TestClient):
    respuesta = cliente.get("/api/secciones/maestro%236-estandar-academico")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["seccion"]["ancla"] == "maestro#6-estandar-academico"
    assert len(datos["criterios"]) == 2


def test_una_seccion_inexistente_da_404(cliente: TestClient):
    assert cliente.get("/api/secciones/maestro%23no-existe").status_code == 404


def test_propuesta_devuelve_el_valor_inferido(cliente: TestClient):
    respuesta = cliente.post("/api/propuesta", json={
        "ancla": "maestro#6-estandar-academico",
        "texto_nuevo": (
            "## 6. Estándar académico\n\nEl contenido principal tendrá un mínimo "
            "de 25 páginas, excluidas portada, índice y anexos. La tipografía "
            "será Arial 11.\n"
        ),
    })
    assert respuesta.status_code == 200
    propuestas = respuesta.json()
    extension = next(p for p in propuestas if p["clave"] == "minimo_paginas_contenido")
    assert extension["valor_propuesto"] == "25"


def test_guardar_sin_motivo_devuelve_error_legible(cliente: TestClient):
    respuesta = cliente.post("/api/guardar", json={
        "ancla": "maestro#6-estandar-academico",
        "texto_nuevo": "## 6\n\ntexto\n",
        "cambios": [],
        "motivo": "",
        "fuente": "algo",
        "hash_esperado": "x",
    })
    assert respuesta.status_code == 200
    assert respuesta.json()["exito"] is False
    assert "motivo" in respuesta.json()["mensaje"]


def test_estado_enumera_las_seis_reglas_con_sus_limites(cliente: TestClient):
    datos = cliente.get("/api/estado").json()
    assert [r["codigo"] for r in datos["reglas"]] == ["R1", "R2", "R3", "R4", "R5", "R6"]
    r2 = next(r for r in datos["reglas"] if r["codigo"] == "R2")
    assert r2["limite"]
    assert datos["conforme"] is True


def test_pendientes_lee_el_documento(cliente: TestClient):
    datos = cliente.get("/api/pendientes").json()
    assert [p["clave"] for p in datos] == ["rubrica"]
