"""Qué encuentra el vigilante en la carpeta."""

from pathlib import Path

from backend.vigilancia.carpeta import mirar


def _pdf(carpeta: Path, nombre: str) -> Path:
    """Un archivo con extensión .pdf. Mirar no lo abre, así que basta."""
    ruta = carpeta / nombre
    ruta.write_bytes(b"%PDF-1.4\n")
    return ruta


def test_encuentra_los_pdf(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    _pdf(tmp_path, "AF024_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, set())

    assert len(vistos) == 2


def test_ignora_lo_que_no_es_pdf(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    (tmp_path / "notas.txt").write_text("x", encoding="utf-8")
    (tmp_path / "trabajo.docx").write_bytes(b"x")

    vistos = mirar(tmp_path, set())

    assert [visto.nombre for visto in vistos] == ["AF023_DAM_E2_20260115_v1.pdf"]


def test_no_repite_lo_ya_registrado(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    _pdf(tmp_path, "AF024_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, {"AF023_DAM_E2_20260115_v1.pdf"})

    assert [visto.nombre for visto in vistos] == ["AF024_DAM_E2_20260115_v1.pdf"]


def test_cada_archivo_llega_con_su_propuesta(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")

    visto = mirar(tmp_path, set())[0]

    assert visto.propuesta.codigo_alumno == "AF023"
    assert visto.propuesta.completa is True


def test_un_nombre_raro_llega_con_la_propuesta_vacia(tmp_path: Path) -> None:
    _pdf(tmp_path, "trabajo de clase.pdf")

    visto = mirar(tmp_path, set())[0]

    assert visto.propuesta.completa is False
    assert visto.propuesta.motivo


def test_mira_dentro_de_las_subcarpetas(tmp_path: Path) -> None:
    """El §15.2 organiza por alumno y curso: hay subcarpetas."""
    subcarpeta = tmp_path / "AF023"
    subcarpeta.mkdir()
    _pdf(subcarpeta, "AF023_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, set())

    assert len(vistos) == 1
    assert vistos[0].ruta.parent == subcarpeta


def test_el_orden_es_el_mas_reciente_primero(tmp_path: Path) -> None:
    import os
    import time

    viejo = _pdf(tmp_path, "AF023_DAM_E1_20260115_v1.pdf")
    nuevo = _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    antiguo = time.time() - 3600
    os.utime(viejo, (antiguo, antiguo))

    vistos = mirar(tmp_path, set())

    assert vistos[0].ruta == nuevo


def test_una_carpeta_que_no_existe_no_revienta(tmp_path: Path) -> None:
    assert mirar(tmp_path / "fantasma", set()) == []


def test_no_toca_ningun_archivo(tmp_path: Path) -> None:
    """El §18.1: se mira y no se toca."""
    ruta = _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    antes = sorted(p.name for p in tmp_path.rglob("*"))
    momento = ruta.stat().st_mtime

    mirar(tmp_path, set())

    assert sorted(p.name for p in tmp_path.rglob("*")) == antes
    assert ruta.stat().st_mtime == momento
