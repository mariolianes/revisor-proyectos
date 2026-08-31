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


def test_r2_detecta_un_ancla_referenciada_que_falta_en_el_registro(repo: Path):
    escribir_sincronia(repo)
    criterios = repo / "criteria" / "v2026-2027"
    (criterios / "privacidad.yaml").write_text(
        "- codigo: D06\n  fuente: maestro#19-privacidad\n",
        encoding="utf-8",
    )
    infracciones = verificar_r2(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R2"
    assert "maestro#19-privacidad" in infracciones[0].detalle


def test_r2_detecta_un_ancla_sobrante_en_el_registro(repo: Path):
    escribir_sincronia(repo)
    ruta = repo / "criteria" / "v2026-2027" / "dimensiones.yaml"
    ruta.write_text("", encoding="utf-8")
    infracciones = verificar_r2(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R2"
    assert "maestro#8-dimensiones" in infracciones[0].detalle


def test_hash_no_se_extiende_a_la_siguiente_ancla_calibracion(tmp_path: Path):
    """`04-calibracion.md` solo lleva anclas 'calibracion#...': si el patrón
    que busca "la siguiente ancla" no reconoce ese prefijo, el cuerpo de la
    primera sección se traga el de todas las que vienen después, hasta el
    final del fichero. Antes de que 'calibracion' se sumara al patrón, este
    test fallaba tal como se describe: editar la SEGUNDA sección cambiaba el
    hash de la PRIMERA sin que su texto se hubiera tocado."""
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "04-calibracion.md").write_text(
        "<!-- ancla: calibracion#2-rigor-proporcional -->\n"
        "## 2. Rigor proporcional\n\n"
        "Texto del rigor.\n\n"
        "<!-- ancla: calibracion#3-muestra-historica -->\n"
        "## 3. Muestra historica\n\n"
        "Texto de la muestra.\n",
        encoding="utf-8",
    )

    antes = hash_de_seccion(tmp_path, "calibracion#2-rigor-proporcional")

    ruta = maestro / "04-calibracion.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Texto de la muestra.", "Texto nuevo de la muestra."
        ),
        encoding="utf-8",
    )

    assert hash_de_seccion(tmp_path, "calibracion#2-rigor-proporcional") == antes


def test_r2_pasa_sobre_el_repositorio_real():
    # Sin esta prueba, un .sincronia.json desactualizado dejaba la suite en
    # verde: R1, R3, R5 y R6 ya se comprobaban contra el repositorio real y
    # R2 no.
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r2(raiz)
    assert infracciones == [], "\n".join(i.detalle for i in infracciones)
