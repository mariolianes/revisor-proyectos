from pathlib import Path

import pytest

from tools.gobernanza.criterios import verificar_r3


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "criteria" / "v2026-2027").mkdir(parents=True)
    (tmp_path / "docs" / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente oficial\n\n"
        "- **ponderaciones** — a la espera de la programacion didactica.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_r3_acepta_un_pendiente_bien_declarado(repo: Path):
    (repo / "criteria" / "v2026-2027" / "ponderaciones.yaml").write_text(
        "ponderaciones:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  bloquea: [nota_final]\n"
        "  fuente: maestro#10-evaluacion-continua\n",
        encoding="utf-8",
    )
    assert verificar_r3(repo) == []


def test_r3_rechaza_un_pendiente_sin_campo_bloquea(repo: Path):
    (repo / "criteria" / "v2026-2027" / "ponderaciones.yaml").write_text(
        "ponderaciones:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  fuente: maestro#10-evaluacion-continua\n",
        encoding="utf-8",
    )
    infracciones = verificar_r3(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R3"
    assert "bloquea" in infracciones[0].detalle


def test_r3_rechaza_un_pendiente_no_documentado(repo: Path):
    (repo / "criteria" / "v2026-2027" / "calendario.yaml").write_text(
        "calendario:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  bloquea: [plazo]\n"
        "  fuente: maestro#14-fuentes-y-criterios\n",
        encoding="utf-8",
    )
    infracciones = verificar_r3(repo)
    assert len(infracciones) == 1
    assert "PENDIENTE_OFICIAL.md" in infracciones[0].detalle


def test_r3_rechaza_un_pendiente_que_ya_trae_valor_inventado(repo: Path):
    (repo / "criteria" / "v2026-2027" / "ponderaciones.yaml").write_text(
        "ponderaciones:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  bloquea: [nota_final]\n"
        "  valor: 20\n"
        "  fuente: maestro#10-evaluacion-continua\n",
        encoding="utf-8",
    )
    infracciones = verificar_r3(repo)
    assert len(infracciones) == 1
    assert "valor" in infracciones[0].detalle


def test_r3_pasa_sobre_el_repositorio_real():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r3(raiz)
    assert infracciones == [], "\n".join(i.detalle for i in infracciones)
