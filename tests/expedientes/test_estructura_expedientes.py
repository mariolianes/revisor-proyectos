"""La arquitectura de expedientes: nombres exactos, códigos y rutas.

Se carga siempre el `config/estructura_expedientes.yaml` real del
repositorio -no una copia inventada-, para que estas pruebas comprueben lo
mismo que ve el docente cuando el sistema arranca. Ningún test de este
fichero escribe en disco: `cargar_estructura` solo lee.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.expedientes.estructura import (
    CarpetaRaiz,
    ConfiguracionExpedientes,
    EstructuraInvalida,
    cargar_estructura,
    codigo_de_centro_valido,
    id_de_alumno_valido,
    ruta_entrada_incidencias,
    ruta_entrada_pendientes,
    ruta_expediente,
    rutas_del_expediente,
)

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cfg() -> ConfiguracionExpedientes:
    return cargar_estructura(RAIZ_DEL_REPOSITORIO)


# --- La forma exacta que pidió el docente -----------------------------------


def test_las_ocho_carpetas_de_primer_nivel_en_orden(cfg: ConfiguracionExpedientes) -> None:
    assert [c.carpeta for c in cfg.carpetas_raiz] == [
        "00_LISTADOS_ALUMNOS",
        "01_ENTRADA_TRABAJOS",
        "02_EXPEDIENTES_ALUMNOS",
        "03_INFORMES_CENTROS",
        "04_DOCUMENTACION_MAESTRA",
        "05_CALIBRACION",
        "06_LOGS_Y_COSTES",
        "99_ARCHIVO_CERRADO",
    ]


def test_las_comunidades_del_curso(cfg: ConfiguracionExpedientes) -> None:
    codigos_y_carpetas = {(c.codigo, c.carpeta) for c in cfg.comunidades}
    assert codigos_y_carpetas == {
        ("AND", "AND_ANDALUCIA"),
        ("MAD", "MAD_MADRID"),
        ("CAN", "CAN_CANARIAS"),
        ("MUR", "MUR_MURCIA"),
        ("ARA", "ARA_ARAGON"),
        ("EXT", "EXT_EXTREMADURA"),
    }


def test_las_fases_de_la_bandeja_de_entrada(cfg: ConfiguracionExpedientes) -> None:
    assert [f.codigo for f in cfg.fases] == ["E01", "E02", "E03", "FINAL"]
    assert [f.carpeta for f in cfg.fases] == ["E01", "E02", "E03", "FINAL"]


def test_las_subcarpetas_vigiladas_de_entrada(cfg: ConfiguracionExpedientes) -> None:
    assert cfg.entrada_trabajos.subcarpeta_vigilada == "PENDIENTES"
    assert cfg.entrada_trabajos.subcarpeta_incidencias == "INCIDENCIAS"


def test_los_ciclos_del_curso(cfg: ConfiguracionExpedientes) -> None:
    assert cfg.ciclos == ["MYP", "CIN", "AYF"]


def test_las_carpetas_del_expediente_de_alumno_en_orden(cfg: ConfiguracionExpedientes) -> None:
    assert [c.carpeta for c in cfg.expediente_alumno.carpetas] == [
        "00_FICHA",
        "01_TEMA",
        "02_ENTREGA_1",
        "03_ENTREGA_2",
        "04_ENTREGA_3",
        "05_ENTREGA_FINAL",
        "06_DEFENSA",
        "07_HISTORICO",
    ]


def test_las_subcarpetas_de_cada_entrega(cfg: ConfiguracionExpedientes) -> None:
    assert cfg.expediente_alumno.subcarpetas_de_entrega == [
        "00_ORIGINAL",
        "01_PROCESADO",
        "02_INFORME_INTERNO",
        "03_FEEDBACK_DOCENTE",
        "04_EVIDENCIAS",
    ]


def test_solo_las_carpetas_de_entrega_llevan_subestructura(
    cfg: ConfiguracionExpedientes,
) -> None:
    con_entregas = {
        c.carpeta for c in cfg.expediente_alumno.carpetas if c.tiene_entregas
    }
    assert con_entregas == {"02_ENTREGA_1", "03_ENTREGA_2", "04_ENTREGA_3", "05_ENTREGA_FINAL"}


# --- Ningún nombre de carpeta lleva tilde ni carácter fuera de lo admitido --


def test_ningun_nombre_de_carpeta_lleva_tilde_ni_caracter_raro(
    cfg: ConfiguracionExpedientes,
) -> None:
    nombres = (
        [c.carpeta for c in cfg.carpetas_raiz]
        + [c.carpeta for c in cfg.comunidades]
        + [f.carpeta for f in cfg.fases]
        + [cfg.entrada_trabajos.subcarpeta_vigilada, cfg.entrada_trabajos.subcarpeta_incidencias]
        + [c.carpeta for c in cfg.expediente_alumno.carpetas]
        + cfg.expediente_alumno.subcarpetas_de_entrega
        + [cfg.raiz.nombre_carpeta]
    )
    for nombre in nombres:
        assert nombre.isascii(), f"«{nombre}» no es ASCII puro."
        assert " " not in nombre, f"«{nombre}» lleva un espacio."


def test_un_nombre_de_carpeta_con_tilde_no_carga(tmp_path: Path) -> None:
    """Rotura deliberada: si algún día se edita el YAML y se cuela una
    tilde en un nombre de carpeta, la carga debe fallar aquí, no crear una
    carpeta que luego dé problemas en una ruta larga de Windows."""
    with pytest.raises(ValidationError):
        CarpetaRaiz(carpeta="ARCHIVO_CERRADO_ÑOÑO", vigilada=False, descripcion="x")


def test_un_codigo_de_comunidad_repetido_no_carga(tmp_path: Path) -> None:
    bruto = {
        "version_configuracion": "x",
        "raiz": {"nombre_carpeta": "X", "variable_de_entorno": "X"},
        "carpetas_raiz": [],
        "comunidades": [
            {"codigo": "AND", "carpeta": "AND_UNO", "nombre": "Uno"},
            {"codigo": "AND", "carpeta": "AND_DOS", "nombre": "Dos"},
        ],
        "fases": [],
        "entrada_trabajos": {"subcarpeta_vigilada": "PENDIENTES", "subcarpeta_incidencias": "INCIDENCIAS"},
        "ciclos": [],
        "centros": {"patron": "^X$", "ejemplo": "X", "descripcion": "x"},
        "expediente_alumno": {
            "patron_id": "^X$", "ejemplo_id": "X", "carpetas": [], "subcarpetas_de_entrega": [],
        },
        "pendiente_de_definir": {},
    }
    with pytest.raises(ValidationError):
        ConfiguracionExpedientes.model_validate(bruto)


def test_sin_fichero_de_configuracion_no_hay_estructura(tmp_path: Path) -> None:
    with pytest.raises(EstructuraInvalida):
        cargar_estructura(tmp_path)


# --- Validación de códigos sueltos ------------------------------------------


@pytest.mark.parametrize("id_alumno", ["ALU-260087", "ALU-000001"])
def test_ids_de_alumno_con_la_forma_correcta(
    cfg: ConfiguracionExpedientes, id_alumno: str
) -> None:
    assert id_de_alumno_valido(cfg, id_alumno) is True


@pytest.mark.parametrize(
    "id_alumno", ["260087", "ALU-26008", "ALU-2600877", "alu-260087", "AF023"]
)
def test_ids_de_alumno_sin_la_forma_correcta(
    cfg: ConfiguracionExpedientes, id_alumno: str
) -> None:
    assert id_de_alumno_valido(cfg, id_alumno) is False


def test_un_codigo_de_centro_bien_formado_y_de_comunidad_conocida(
    cfg: ConfiguracionExpedientes,
) -> None:
    assert codigo_de_centro_valido(cfg, "AND-MAL-01") is True


def test_un_codigo_de_centro_bien_formado_pero_de_comunidad_desconocida(
    cfg: ConfiguracionExpedientes,
) -> None:
    """Tiene la forma de un código de centro, pero XYZ no es una comunidad
    de este curso: no basta con que la forma encaje."""
    assert codigo_de_centro_valido(cfg, "XYZ-MAL-01") is False


@pytest.mark.parametrize("codigo", ["AND-MAL-1", "AND-MAL", "and-mal-01", "AND_MAL_01"])
def test_un_codigo_de_centro_mal_formado(
    cfg: ConfiguracionExpedientes, codigo: str
) -> None:
    assert codigo_de_centro_valido(cfg, codigo) is False


# --- Rutas relativas, sin tocar disco ---------------------------------------


def test_ruta_de_entrada_pendientes(cfg: ConfiguracionExpedientes) -> None:
    ruta = ruta_entrada_pendientes(cfg, "AND", "E01")
    assert ruta == Path("01_ENTRADA_TRABAJOS", "AND_ANDALUCIA", "E01", "PENDIENTES")


def test_ruta_de_entrada_incidencias(cfg: ConfiguracionExpedientes) -> None:
    ruta = ruta_entrada_incidencias(cfg, "MAD")
    assert ruta == Path("01_ENTRADA_TRABAJOS", "MAD_MADRID", "INCIDENCIAS")


def test_una_comunidad_desconocida_no_construye_una_ruta(cfg: ConfiguracionExpedientes) -> None:
    with pytest.raises(ValueError, match="comunidad"):
        ruta_entrada_pendientes(cfg, "XYZ", "E01")


def test_una_fase_desconocida_no_construye_una_ruta(cfg: ConfiguracionExpedientes) -> None:
    with pytest.raises(ValueError, match="fase"):
        ruta_entrada_pendientes(cfg, "AND", "E99")


def test_la_ruta_del_expediente_lleva_solo_el_id(cfg: ConfiguracionExpedientes) -> None:
    ruta = ruta_expediente(cfg, "ALU-260087")
    assert ruta == Path("02_EXPEDIENTES_ALUMNOS", "ALU-260087")


def test_un_id_mal_formado_no_construye_una_ruta_de_expediente(
    cfg: ConfiguracionExpedientes,
) -> None:
    with pytest.raises(ValueError, match="ID de expediente"):
        ruta_expediente(cfg, "trabajo de juan")


def test_las_rutas_del_expediente_incluyen_las_ocho_carpetas(
    cfg: ConfiguracionExpedientes,
) -> None:
    rutas = rutas_del_expediente(cfg, "ALU-260087")
    base = Path("02_EXPEDIENTES_ALUMNOS", "ALU-260087")
    for nombre in [
        "00_FICHA", "01_TEMA", "02_ENTREGA_1", "03_ENTREGA_2", "04_ENTREGA_3",
        "05_ENTREGA_FINAL", "06_DEFENSA", "07_HISTORICO",
    ]:
        assert base / nombre in rutas


def test_solo_las_entregas_llevan_las_cinco_subcarpetas(
    cfg: ConfiguracionExpedientes,
) -> None:
    rutas = rutas_del_expediente(cfg, "ALU-260087")
    base = Path("02_EXPEDIENTES_ALUMNOS", "ALU-260087")

    assert base / "02_ENTREGA_1" / "00_ORIGINAL" in rutas
    assert base / "05_ENTREGA_FINAL" / "04_EVIDENCIAS" in rutas
    # 00_FICHA no es una carpeta de entrega: no lleva subcarpetas.
    assert base / "00_FICHA" / "00_ORIGINAL" not in rutas
    assert base / "06_DEFENSA" / "00_ORIGINAL" not in rutas


def test_ninguna_ruta_de_expediente_lleva_el_nombre_ni_la_comunidad_del_alumno(
    cfg: ConfiguracionExpedientes,
) -> None:
    """El profesor lo exige expresamente: el expediente se nombra solo con
    el ID."""
    rutas = rutas_del_expediente(cfg, "ALU-260087")
    for ruta in rutas:
        partes = ruta.parts
        assert "AND_ANDALUCIA" not in partes
        assert "MAD_MADRID" not in partes
        assert not any(parte.lower().startswith("juan") for parte in partes)


def test_el_total_de_carpetas_por_expediente_es_el_esperado(
    cfg: ConfiguracionExpedientes,
) -> None:
    """8 carpetas de primer nivel + 4 entregas x 5 subcarpetas = 28."""
    rutas = rutas_del_expediente(cfg, "ALU-260087")
    assert len(rutas) == 28
