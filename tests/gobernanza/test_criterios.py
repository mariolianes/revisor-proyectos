from pathlib import Path

import pytest

from tools.gobernanza.criterios import (
    bloques_raiz,
    cargar_anclas,
    entradas_de,
    verificar_r1,
)


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


def test_r1_rechaza_un_bloque_sin_fuente_en_un_fichero_con_forma_de_mapa(repo: Path):
    # Reproduce el hueco que demostro el revisor: en un fichero de mapa, un
    # bloque sin 'fuente' era invisible para R1, porque 'entradas_de' decide
    # que algo es un criterio por la presencia de 'fuente' o 'codigo'.
    (repo / "criteria" / "v2026-2027" / "formato.yaml").write_text(
        "tipografia:\n"
        "  familia: Arial\n"
        "  fuente: maestro#8-dimensiones\n"
        "citas:\n"
        "  estilo: APA\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R1"
    assert "citas" in infracciones[0].detalle
    assert "'fuente'" in infracciones[0].detalle


def test_r1_rechaza_un_fichero_entero_sin_ninguna_fuente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "rubrica.yaml").write_text(
        "estado: PENDIENTE_OFICIAL\n"
        "niveles:\n"
        "  - Solido\n"
        "  - Adecuado\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert infracciones
    assert {i.regla for i in infracciones} == {"R1"}
    detalles = " ".join(i.detalle for i in infracciones)
    assert "estado" in detalles
    assert "niveles" in detalles


def test_r1_no_avisa_dos_veces_del_mismo_bloque_de_una_lista(repo: Path):
    # Una entrada de lista sin 'fuente' ya la detecta el recorrido de
    # entradas: el invariante de primer nivel no debe duplicar el aviso.
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  nombre: Fundamentacion y fuentes\n",
        encoding="utf-8",
    )
    assert len(verificar_r1(repo)) == 1


def test_bloques_raiz_nombra_los_hijos_de_una_lista_y_de_un_mapa(tmp_path: Path):
    lista = tmp_path / "l.yaml"
    lista.write_text("- codigo: D01\n- nombre: sin codigo\n", encoding="utf-8")
    assert [nombre for nombre, _ in bloques_raiz(lista)] == ["D01", "elemento 2"]

    mapa = tmp_path / "m.yaml"
    mapa.write_text(
        "extension:\n  minimo: 20\ncitas:\n  estilo: APA\n", encoding="utf-8"
    )
    assert [nombre for nombre, _ in bloques_raiz(mapa)] == ["extension", "citas"]


def test_r1_pasa_sobre_los_criterios_reales_del_repositorio():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r1(raiz)
    assert infracciones == [], "\n".join(i.detalle for i in infracciones)


def test_la_calibracion_es_un_documento_valido_en_una_fuente() -> None:
    """El cuarto documento entró después que los tres primeros.

    Se comprueba aquí porque ampliar la lista de documentos válidos es un
    cambio de una palabra en una expresión regular, y sin este test nadie
    notaría que se ha quitado: los criterios que citan la calibración
    dejarían de tener fuente válida y R1 los rechazaría en bloque.
    """
    from tools.gobernanza.criterios import PATRON_FUENTE

    assert PATRON_FUENTE.match("calibracion#7-prioridades")
    assert PATRON_FUENTE.match("maestro#8-dimensiones")
    assert not PATRON_FUENTE.match("inventado#8-dimensiones")


def test_las_anclas_de_la_calibracion_se_reconocen(repo: Path) -> None:
    """Un ancla del documento nuevo se lee igual que la de los otros tres."""
    from tools.gobernanza.criterios import PATRON_ANCLA

    encontradas = PATRON_ANCLA.findall(
        "<!-- ancla: calibracion#9-semaforo -->\n"
        "<!-- ancla: maestro#6-estandar-academico -->\n"
        "<!-- ancla: ajeno#9-semaforo -->\n"
    )
    assert encontradas == ["calibracion#9-semaforo", "maestro#6-estandar-academico"]
