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
