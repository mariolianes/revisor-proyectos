"""Crear en disco la estructura de expedientes, siempre dentro de `tmp_path`.

Ninguna prueba de este fichero toca una carpeta real del docente: la
`raiz_expedientes` de cada prueba es un `tmp_path` cualquiera, y la
`raiz_repositorio` que se le pasa como referencia para "¿esto cae dentro del
repositorio?" es también un `tmp_path`, nunca la raíz real de este proyecto.
"""

from pathlib import Path

import pytest

from backend.expedientes import creacion
from backend.expedientes.creacion import (
    LimiteDeSeguridadSuperado,
    LoteDemasiadoGrande,
    construir_estructura_base,
    crear_expediente,
    crear_expedientes_en_lote,
    planificar_estructura_base,
    planificar_expediente,
    problema_de_raiz,
)
from backend.expedientes.estructura import cargar_estructura

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cfg():
    return cargar_estructura(RAIZ_DEL_REPOSITORIO)


def test_no_escribe_dentro_del_repositorio(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    dentro = raiz_repo / "expedientes"
    dentro.mkdir()

    with pytest.raises(ValueError, match="dentro del repositorio"):
        construir_estructura_base(raiz_repo, dentro, cfg)

    # Nada se ha creado: el árbol de `dentro` sigue vacío.
    assert list(dentro.iterdir()) == []


def test_construye_la_estructura_base(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()

    resultado = construir_estructura_base(raiz_repo, expedientes, cfg)

    planificadas = planificar_estructura_base(cfg)
    assert len(resultado.creadas) == len(planificadas)
    assert resultado.ya_existian == []
    for relativa in planificadas:
        assert (expedientes / relativa).is_dir()


def test_construir_la_estructura_base_es_idempotente(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()

    primera = construir_estructura_base(raiz_repo, expedientes, cfg)
    segunda = construir_estructura_base(raiz_repo, expedientes, cfg)

    assert segunda.creadas == []
    assert len(segunda.ya_existian) == len(primera.creadas)


def test_las_carpetas_pendientes_estan_dentro_de_su_comunidad_y_fase(
    tmp_path: Path, cfg
) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()

    construir_estructura_base(raiz_repo, expedientes, cfg)

    ruta = expedientes / "01_ENTRADA_TRABAJOS" / "AND_ANDALUCIA" / "E01" / "PENDIENTES"
    assert ruta.is_dir()
    ruta_incidencias = expedientes / "01_ENTRADA_TRABAJOS" / "AND_ANDALUCIA" / "INCIDENCIAS"
    assert ruta_incidencias.is_dir()


def test_crea_el_expediente_de_un_alumno(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()

    resultado = crear_expediente(raiz_repo, expedientes, cfg, "ALU-260087")

    base = expedientes / "02_EXPEDIENTES_ALUMNOS" / "ALU-260087"
    assert base.is_dir()
    assert (base / "02_ENTREGA_1" / "00_ORIGINAL").is_dir()
    assert (base / "00_FICHA").is_dir()
    assert len(resultado.creadas) == len(planificar_expediente(cfg, "ALU-260087"))


def test_el_expediente_no_lleva_ninguna_otra_carpeta_del_alumno(tmp_path: Path, cfg) -> None:
    """Comprobación de disco de la exigencia del docente: la carpeta del
    expediente no debe llevar nada más que su ID."""
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()

    crear_expediente(raiz_repo, expedientes, cfg, "ALU-260087")

    carpeta_de_alumnos = expedientes / "02_EXPEDIENTES_ALUMNOS"
    assert [p.name for p in carpeta_de_alumnos.iterdir()] == ["ALU-260087"]


def test_un_id_mal_formado_no_crea_nada(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()

    with pytest.raises(ValueError):
        crear_expediente(raiz_repo, expedientes, cfg, "trabajo de juan")

    assert list(expedientes.iterdir()) == []


# --- El lote: el guardián contra "ochocientas carpetas de golpe" -----------


def test_un_lote_pequeno_no_necesita_confirmar(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    ids = [f"ALU-26{n:04d}" for n in range(5)]

    resultado = crear_expedientes_en_lote(raiz_repo, expedientes, cfg, ids)

    assert len(resultado.creadas) == 5 * len(planificar_expediente(cfg, ids[0]))


def test_un_lote_grande_sin_confirmar_no_crea_nada(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    ids = [f"ALU-26{n:04d}" for n in range(creacion.LIMITE_LOTE_SIN_CONFIRMAR + 1)]

    with pytest.raises(LoteDemasiadoGrande):
        crear_expedientes_en_lote(raiz_repo, expedientes, cfg, ids)

    assert list((expedientes / "02_EXPEDIENTES_ALUMNOS").glob("*")) == []


def test_un_lote_grande_confirmado_si_crea(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    ids = [f"ALU-26{n:04d}" for n in range(creacion.LIMITE_LOTE_SIN_CONFIRMAR + 1)]

    resultado = crear_expedientes_en_lote(raiz_repo, expedientes, cfg, ids, confirmar=True)

    assert len(resultado.creadas) == len(ids) * len(planificar_expediente(cfg, ids[0]))


def test_un_id_invalido_en_el_lote_no_crea_ningun_expediente(tmp_path: Path, cfg) -> None:
    """Se planifica el lote entero antes de escribir: un ID roto detiene
    todo el lote, no solo el suyo."""
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    ids = ["ALU-260001", "ALU-260002", "codigo-malo"]

    with pytest.raises(ValueError):
        crear_expedientes_en_lote(raiz_repo, expedientes, cfg, ids, confirmar=True)

    assert list((expedientes / "02_EXPEDIENTES_ALUMNOS").glob("*")) == []


def test_el_lote_no_escribe_dentro_del_repositorio(tmp_path: Path, cfg) -> None:
    raiz_repo = tmp_path / "repo"
    dentro = raiz_repo / "expedientes"
    dentro.mkdir(parents=True)

    with pytest.raises(ValueError, match="dentro del repositorio"):
        crear_expedientes_en_lote(raiz_repo, dentro, cfg, ["ALU-260001"], confirmar=True)


def test_el_limite_de_seguridad_absoluto_se_respeta_aunque_se_confirme(
    tmp_path: Path, cfg, monkeypatch
) -> None:
    """Ni siquiera `confirmar=True` salta el tope absoluto de directorios:
    es la última guarda contra una configuración rota, no una decisión que
    el docente pueda anular sin querer con un flag pensado para otra cosa."""
    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    monkeypatch.setattr(creacion, "LIMITE_DIRECTORIOS_DE_SEGURIDAD", 10)
    ids = [f"ALU-26{n:04d}" for n in range(3)]  # 3 x 28 = 84 > 10

    with pytest.raises(LimiteDeSeguridadSuperado):
        crear_expedientes_en_lote(raiz_repo, expedientes, cfg, ids, confirmar=True)

    assert list((expedientes / "02_EXPEDIENTES_ALUMNOS").glob("*")) == []


def test_problema_de_raiz_es_la_misma_guarda_que_backend_configuracion(
    tmp_path: Path,
) -> None:
    """No una copia de la regla: la misma función."""
    from backend.configuracion import revisar_carpeta

    raiz_repo = tmp_path / "repo"
    raiz_repo.mkdir()
    fuera = tmp_path / "fuera"
    fuera.mkdir()

    assert problema_de_raiz(raiz_repo, fuera) == revisar_carpeta(raiz_repo, fuera)
