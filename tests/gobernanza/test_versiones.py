from pathlib import Path

import pytest

from tools.gobernanza.versiones import congelar, verificar_r4


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    carpeta = tmp_path / "criteria" / "v2026-2027"
    carpeta.mkdir(parents=True)
    (carpeta / "dimensiones.yaml").write_text(
        "- codigo: D05\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    return tmp_path


def test_una_version_sin_congelar_se_puede_cambiar(repo: Path):
    assert verificar_r4(repo) == []
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D06\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    assert verificar_r4(repo) == []


def test_congelar_crea_el_sello(repo: Path):
    congelar(repo, "v2026-2027")
    assert (repo / "criteria" / "v2026-2027" / ".congelada").is_file()


def test_una_version_congelada_intacta_pasa(repo: Path):
    congelar(repo, "v2026-2027")
    assert verificar_r4(repo) == []


def test_r4_rechaza_modificar_una_version_congelada(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n  nombre: cambiado\n  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R4"
    assert "dimensiones.yaml" in infracciones[0].detalle
    assert "nueva versión" in infracciones[0].detalle


def test_r4_rechaza_borrar_un_fichero_de_una_version_congelada(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").unlink()
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert "ha desaparecido" in infracciones[0].detalle


def test_r4_rechaza_anadir_un_fichero_a_una_version_congelada(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "nuevo.yaml").write_text(
        "clave:\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert "nuevo.yaml" in infracciones[0].detalle


def test_congelar_dos_veces_la_misma_version_lanza_excepcion(repo: Path):
    congelar(repo, "v2026-2027")
    with pytest.raises(RuntimeError):
        congelar(repo, "v2026-2027")


def test_resellar_no_borra_la_evidencia_de_una_alteracion(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n  nombre: cambiado\n  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError):
        congelar(repo, "v2026-2027")
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert "dimensiones.yaml" in infracciones[0].detalle
