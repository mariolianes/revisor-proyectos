import json
from pathlib import Path

import pytest

from tools.gobernanza.sincronia import (
    calcular_sincronia,
    escribir_sincronia,
    hash_de_seccion,
    verificar_r2,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(
        "<!-- ancla: maestro#8-dimensiones -->\n"
        "## 8. Dimensiones\n\n"
        "Doce dimensiones comunes.\n\n"
        "<!-- ancla: maestro#19-privacidad -->\n"
        "## 19. Privacidad\n\n"
        "Codigos anonimos.\n",
        encoding="utf-8",
    )
    criterios = tmp_path / "criteria" / "v2026-2027"
    criterios.mkdir(parents=True)
    (criterios / "dimensiones.yaml").write_text(
        "- codigo: D05\n  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    return tmp_path


def test_hash_de_seccion_solo_cubre_su_propia_seccion(repo: Path):
    h1 = hash_de_seccion(repo, "maestro#8-dimensiones")
    h2 = hash_de_seccion(repo, "maestro#19-privacidad")
    assert h1 and h2 and h1 != h2


def test_hash_ignora_cambios_de_espaciado(repo: Path):
    antes = hash_de_seccion(repo, "maestro#8-dimensiones")
    ruta = repo / "docs" / "maestro" / "01-documento-maestro.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Doce dimensiones comunes.", "Doce   dimensiones   comunes.  "
        ),
        encoding="utf-8",
    )
    assert hash_de_seccion(repo, "maestro#8-dimensiones") == antes


def test_hash_cambia_si_cambia_el_contenido(repo: Path):
    antes = hash_de_seccion(repo, "maestro#8-dimensiones")
    ruta = repo / "docs" / "maestro" / "01-documento-maestro.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Doce dimensiones comunes.", "Trece dimensiones comunes."
        ),
        encoding="utf-8",
    )
    assert hash_de_seccion(repo, "maestro#8-dimensiones") != antes


def test_calcular_sincronia_solo_incluye_anclas_referenciadas(repo: Path):
    calculada = calcular_sincronia(repo)
    assert set(calculada) == {"maestro#8-dimensiones"}


def test_r2_pasa_cuando_el_registro_esta_al_dia(repo: Path):
    escribir_sincronia(repo)
    assert verificar_r2(repo) == []


def test_r2_detecta_que_la_prosa_cambio_sin_revisar_el_derivado(repo: Path):
    escribir_sincronia(repo)
    ruta = repo / "docs" / "maestro" / "01-documento-maestro.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Doce dimensiones comunes.", "Trece dimensiones comunes."
        ),
        encoding="utf-8",
    )
    infracciones = verificar_r2(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R2"
    assert "maestro#8-dimensiones" in infracciones[0].detalle


def test_r2_avisa_si_falta_el_registro_de_sincronia(repo: Path):
    infracciones = verificar_r2(repo)
    assert len(infracciones) == 1
    assert ".sincronia.json" in infracciones[0].detalle
