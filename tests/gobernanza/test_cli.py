from pathlib import Path

import pytest

from tools.verificar_gobernanza import ejecutar, main


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(
        "<!-- ancla: maestro#8-dimensiones -->\n## 8. Dimensiones\n\nTexto.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "changes").mkdir()
    (tmp_path / "docs" / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente\n", encoding="utf-8"
    )
    criterios = tmp_path / "criteria" / "v2026-2027"
    criterios.mkdir(parents=True)
    (criterios / "dimensiones.yaml").write_text(
        "- codigo: D05\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    from tools.gobernanza.sincronia import escribir_sincronia
    escribir_sincronia(tmp_path)
    return tmp_path


def test_un_repositorio_conforme_no_devuelve_infracciones(repo: Path):
    assert ejecutar(repo, ficheros=[], solo_staged=False) == []


def test_agrega_infracciones_de_varias_reglas(repo: Path):
    # R1: criterio sin fuente.
    (repo / "criteria" / "v2026-2027" / "roto.yaml").write_text(
        "- codigo: D99\n  nombre: sin fuente\n", encoding="utf-8"
    )
    # R6: dato personal.
    (repo / "docs" / "ficha.md").write_text("DNI 12345678Z\n", encoding="utf-8")

    infracciones = ejecutar(repo, ficheros=[], solo_staged=False)
    reglas = {i.regla for i in infracciones}
    assert "R1" in reglas
    assert "R6" in reglas


def test_r5_solo_se_evalua_sobre_los_ficheros_indicados(repo: Path):
    # Sin lista de ficheros, R5 no puede saber que se esta commiteando.
    assert not [i for i in ejecutar(repo, [], False) if i.regla == "R5"]
    # Con lista, si.
    infracciones = ejecutar(
        repo, ficheros=["criteria/v2026-2027/dimensiones.yaml"], solo_staged=False
    )
    assert [i for i in infracciones if i.regla == "R5"]


def test_congelar_desde_la_cli_crea_el_sello(repo: Path, capsys):
    codigo = main(["--congelar", "v2026-2027"], raiz=repo)
    assert codigo == 0
    assert (repo / "criteria" / "v2026-2027" / ".congelada").is_file()
    salida = capsys.readouterr().out
    assert "congelada" in salida
    # El consejo tiene que ser copiar solo los YAML: una copia recursiva
    # arrastraria el sello y la version nueva naceria cerrada.
    assert "*.yaml" in salida


def test_congelar_una_version_inexistente_no_crea_nada(repo: Path, capsys):
    codigo = main(["--congelar", "v2099-2100"], raiz=repo)
    assert codigo == 1
    assert not (repo / "criteria" / "v2099-2100").exists()
    assert "No se ha congelado nada" in capsys.readouterr().out


def test_congelar_dos_veces_desde_la_cli_se_niega(repo: Path, capsys):
    assert main(["--congelar", "v2026-2027"], raiz=repo) == 0
    capsys.readouterr()
    assert main(["--congelar", "v2026-2027"], raiz=repo) == 1
    assert "ya esta congelada" in capsys.readouterr().out


def test_congelar_no_ejecuta_las_reglas_ni_sella(repo: Path):
    # Congelar es una accion, no una verificacion: no debe tocar el registro
    # de sincronia ni confundirse con --sellar.
    antes = (repo / "criteria" / ".sincronia.json")
    marca = antes.read_text(encoding="utf-8") if antes.is_file() else None
    main(["--congelar", "v2026-2027"], raiz=repo)
    despues = antes.read_text(encoding="utf-8") if antes.is_file() else None
    assert marca == despues
