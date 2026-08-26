from pathlib import Path

import pytest

from tools.gobernanza.privacidad import verificar_r6


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    return tmp_path


def test_un_repositorio_limpio_pasa(repo: Path):
    (repo / "docs" / "notas.md").write_text("Sin datos personales.\n", encoding="utf-8")
    assert verificar_r6(repo, ["docs/notas.md"]) == []


def test_rechaza_un_pdf(repo: Path):
    (repo / "entrega.pdf").write_bytes(b"%PDF-1.7\n")
    infracciones = verificar_r6(repo, ["entrega.pdf"])
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R6"
    assert "entrega.pdf" in infracciones[0].fichero


def test_rechaza_un_documento_de_word(repo: Path):
    (repo / "trabajo.docx").write_bytes(b"PK\x03\x04")
    infracciones = verificar_r6(repo, ["trabajo.docx"])
    assert len(infracciones) == 1


def test_detecta_un_dni_espanol(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Alumno con DNI 12345678Z matriculado.\n", encoding="utf-8"
    )
    infracciones = verificar_r6(repo, ["docs/ficha.md"])
    assert len(infracciones) == 1
    assert "DNI" in infracciones[0].detalle


def test_detecta_un_correo_electronico(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Contacto: alumno.ejemplo@centro.es\n", encoding="utf-8"
    )
    infracciones = verificar_r6(repo, ["docs/ficha.md"])
    assert len(infracciones) == 1
    assert "correo" in infracciones[0].detalle


def test_detecta_un_telefono_espanol(repo: Path):
    (repo / "docs" / "ficha.md").write_text("Telefono 612345678\n", encoding="utf-8")
    infracciones = verificar_r6(repo, ["docs/ficha.md"])
    assert len(infracciones) == 1
    assert "telefono" in infracciones[0].detalle


def test_no_confunde_un_codigo_anonimo_con_un_dato_personal(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Codigo de alumno AF023, ciclo Marketing, fase E2.\n", encoding="utf-8"
    )
    assert verificar_r6(repo, ["docs/ficha.md"]) == []


def test_no_confunde_una_fecha_con_un_telefono(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Version 2026-08-26, hash 16 caracteres.\n", encoding="utf-8"
    )
    assert verificar_r6(repo, ["docs/ficha.md"]) == []


def test_los_planes_y_specs_estan_exentos(repo: Path):
    ruta = repo / "docs" / "superpowers" / "plans"
    ruta.mkdir(parents=True)
    (ruta / "plan.md").write_text(
        "Ejemplo de deteccion: DNI 12345678Z y correo alumno@centro.es\n",
        encoding="utf-8",
    )
    assert verificar_r6(repo, ["docs/superpowers/plans/plan.md"]) == []


def test_el_repositorio_real_esta_limpio():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r6(raiz, [])
    assert infracciones == [], "\n".join(
        f"{i.fichero}: {i.detalle}" for i in infracciones
    )
