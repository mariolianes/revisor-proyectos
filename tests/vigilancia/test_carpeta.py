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


def test_mismo_nombre_en_subcarpetas_distintas_no_se_pisa(tmp_path: Path) -> None:
    """Registrar el archivo de un alumno no debe tapar al de otro alumno."""
    carpeta_af024 = tmp_path / "AF024"
    carpeta_af024.mkdir()
    _pdf(carpeta_af024, "AF024_DAM_E2_20260115_v1.pdf")

    carpeta_af099 = tmp_path / "AF099"
    carpeta_af099.mkdir()
    _pdf(carpeta_af099, "AF024_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, {"AF024/AF024_DAM_E2_20260115_v1.pdf"})

    assert len(vistos) == 1
    assert vistos[0].ruta.parent == carpeta_af099


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


def test_la_deduccion_funciona_dentro_de_una_subcarpeta(tmp_path: Path) -> None:
    """La subcarpeta no debe estropear la deducción: se deduce del nombre."""
    subcarpeta = tmp_path / "AF023"
    subcarpeta.mkdir()
    _pdf(subcarpeta, "AF023_DAM_E2_20260115_v1.pdf")

    visto = mirar(tmp_path, set())[0]

    assert visto.propuesta.codigo_alumno == "AF023"
    assert visto.propuesta.completa is True


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


def test_un_archivo_que_no_se_puede_leer_no_tumba_el_listado(
    tmp_path: Path, monkeypatch
) -> None:
    """Un permiso denegado en un archivo no debe ocultar los demás."""
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    roto = _pdf(tmp_path, "AF024_DAM_E2_20260115_v1.pdf")

    stat_original = Path.stat

    def stat_que_falla(self: Path, *args: object, **kwargs: object):
        if self == roto:
            raise OSError("permiso denegado (simulado)")
        return stat_original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_que_falla)

    vistos = mirar(tmp_path, set())
    por_nombre = {visto.nombre: visto for visto in vistos}

    assert len(vistos) == 2
    assert por_nombre["AF023_DAM_E2_20260115_v1.pdf"].problema == ""
    assert por_nombre["AF023_DAM_E2_20260115_v1.pdf"].modificado_en is not None

    roto_visto = por_nombre["AF024_DAM_E2_20260115_v1.pdf"]
    assert roto_visto.modificado_en is None
    assert "AF024_DAM_E2_20260115_v1.pdf" in roto_visto.problema


def test_encuentra_la_extension_en_mayusculas(tmp_path: Path) -> None:
    """En un sistema que distingue mayúsculas de minúsculas, .PDF no debe
    quedar invisible solo porque el patrón del glob buscaba minúsculas."""
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.PDF")

    vistos = mirar(tmp_path, set())

    assert [visto.nombre for visto in vistos] == ["AF023_DAM_E2_20260115_v1.PDF"]
