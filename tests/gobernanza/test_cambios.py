from pathlib import Path

import pytest

from tools.gobernanza.cambios import (
    verificar_cambio_acompanado,
    verificar_formato_cambios,
)

CAMBIO_VALIDO = """# Minimo de paginas de 20 a 25

**Fecha:** 2026-09-15
**Autor:** Marcos

## Que cambia

El minimo de contenido pasa de 20 a 25 paginas.

## Por que

## Fuente que lo respalda

Programacion didactica 2026-2027, apartado 4.2.

## Que arrastra

- `docs/maestro/03-guia-desarrollo.md`
- `criteria/v2026-2027/formato.yaml`

## Correcciones cerradas afectadas

Ninguna.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "changes").mkdir(parents=True)
    (tmp_path / "criteria" / "v2026-2027").mkdir(parents=True)
    return tmp_path


def test_acepta_un_documento_de_cambio_completo(repo: Path):
    (repo / "docs" / "changes" / "2026-09-15-minimo-paginas.md").write_text(
        CAMBIO_VALIDO, encoding="utf-8"
    )
    assert verificar_formato_cambios(repo) == []


def test_rechaza_un_nombre_de_fichero_sin_fecha(repo: Path):
    (repo / "docs" / "changes" / "minimo-paginas.md").write_text(
        CAMBIO_VALIDO, encoding="utf-8"
    )
    infracciones = verificar_formato_cambios(repo)
    assert len(infracciones) == 1
    assert "AAAA-MM-DD" in infracciones[0].detalle


def test_rechaza_un_documento_al_que_le_falta_una_seccion(repo: Path):
    incompleto = CAMBIO_VALIDO.replace("## Fuente que lo respalda", "## Otra cosa")
    (repo / "docs" / "changes" / "2026-09-15-minimo-paginas.md").write_text(
        incompleto, encoding="utf-8"
    )
    infracciones = verificar_formato_cambios(repo)
    assert len(infracciones) == 1
    assert "Fuente que lo respalda" in infracciones[0].detalle


def test_la_plantilla_no_se_valida_como_cambio(repo: Path):
    (repo / "docs" / "changes" / "PLANTILLA.md").write_text("# Plantilla\n", encoding="utf-8")
    assert verificar_formato_cambios(repo) == []


def test_tocar_criterios_sin_documentar_el_cambio_es_infraccion(repo: Path):
    tocados = ["criteria/v2026-2027/formato.yaml"]
    infracciones = verificar_cambio_acompanado(repo, tocados)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R5"
    assert "docs/changes/" in infracciones[0].detalle


def test_tocar_criterios_con_su_documento_de_cambio_pasa(repo: Path):
    tocados = [
        "criteria/v2026-2027/formato.yaml",
        "docs/changes/2026-09-15-minimo-paginas.md",
    ]
    assert verificar_cambio_acompanado(repo, tocados) == []


def test_tocar_solo_codigo_no_exige_documento_de_cambio(repo: Path):
    tocados = ["tools/gobernanza/criterios.py", "tests/gobernanza/test_criterios.py"]
    assert verificar_cambio_acompanado(repo, tocados) == []


def test_tocar_la_prosa_maestra_tambien_exige_documento_de_cambio(repo: Path):
    tocados = ["docs/maestro/01-documento-maestro.md"]
    infracciones = verificar_cambio_acompanado(repo, tocados)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R5"
