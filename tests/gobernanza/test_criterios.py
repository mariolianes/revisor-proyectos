from pathlib import Path

import pytest

from tools.gobernanza.criterios import cargar_anclas, entradas_de, verificar_r1


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repositorio minimo con un documento maestro y una carpeta de criterios."""
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(
        "<!-- ancla: maestro#8-dimensiones -->\n"
        "## 8. Dimensiones de evaluacion\n\n"
        "Texto.\n",
        encoding="utf-8",
    )
    (tmp_path / "criteria" / "v2026-2027").mkdir(parents=True)
    return tmp_path


def test_cargar_anclas_encuentra_las_declaradas(repo: Path):
    assert cargar_anclas(repo) == {"maestro#8-dimensiones"}


def test_entradas_de_aplana_una_lista(tmp_path: Path):
    ruta = tmp_path / "d.yaml"
    ruta.write_text(
        "- codigo: D05\n"
        "  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    entradas = entradas_de(ruta)
    assert len(entradas) == 1
    assert entradas[0]["codigo"] == "D05"


def test_entradas_de_aplana_un_mapa_con_listas_anidadas(tmp_path: Path):
    ruta = tmp_path / "f.yaml"
    ruta.write_text(
        "extension:\n"
        "  minimo_paginas: 20\n"
        "  fuente: guia#6-evaluacion-continua\n"
        "tipografia:\n"
        "  familia: Arial\n"
        "  fuente: maestro#6-estandar-academico\n",
        encoding="utf-8",
    )
    entradas = entradas_de(ruta)
    assert len(entradas) == 2
    assert {e["fuente"] for e in entradas} == {
        "guia#6-evaluacion-continua",
        "maestro#6-estandar-academico",
    }


def test_entradas_de_no_desciende_en_una_lista_anidada_de_una_entrada_ya_identificada(
    tmp_path: Path,
):
    ruta = tmp_path / "m.yaml"
    ruta.write_text(
        "E1:\n"
        "  evaluable: true\n"
        "  fuente: maestro#9-matriz-entregas\n"
        "  debe_existir:\n"
        "    - portada_y_titulo_provisional\n"
        "    - presentacion_del_tema\n",
        encoding="utf-8",
    )
    entradas = entradas_de(ruta)
    assert len(entradas) == 1
    assert entradas[0]["fuente"] == "maestro#9-matriz-entregas"
    assert entradas[0]["debe_existir"] == [
        "portada_y_titulo_provisional",
        "presentacion_del_tema",
    ]


def test_r1_acepta_un_criterio_con_fuente_existente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  nombre: Fundamentacion y fuentes\n"
        "  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    assert verificar_r1(repo) == []


def test_r1_rechaza_un_criterio_sin_campo_fuente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  nombre: Fundamentacion y fuentes\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R1"
    assert "D05" in infracciones[0].detalle
    assert "sin campo 'fuente'" in infracciones[0].detalle


def test_r1_rechaza_una_fuente_que_apunta_a_un_ancla_inexistente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  fuente: maestro#seccion-que-no-existe\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R1"
    assert "maestro#seccion-que-no-existe" in infracciones[0].detalle


def test_r1_rechaza_una_fuente_con_formato_invalido(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  fuente: el documento maestro, seccion 8\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert "formato" in infracciones[0].detalle


def test_r1_pasa_sobre_los_criterios_reales_del_repositorio():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r1(raiz)
    assert infracciones == [], "\n".join(i.detalle for i in infracciones)
