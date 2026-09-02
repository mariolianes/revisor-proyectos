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


# --- Las reglas que el docente fijó el 2026-09-02 --------------------------
#
# Estos tests no comprueban código: comprueban que la configuración dice lo
# que él dijo. Es donde se notaría que alguien "afina" un valor suyo.


def test_las_extensiones_y_el_tamano_son_los_que_fijo_el_docente(cfg) -> None:
    """`decisiones#5-extensiones`. Proyecto y defensa admiten cosas distintas
    a propósito: una presentación no sustituye al proyecto final."""
    assert cfg.archivos.extensiones_del_proyecto == ["pdf", "docx"]
    assert cfg.archivos.extensiones_de_defensa == ["pdf", "pptx"]
    assert cfg.archivos.tamano_maximo_mb == 20
    assert cfg.archivos.politica_doc_antiguo == "incidencia"


def test_la_identificacion_es_determinista_y_sin_umbral(cfg) -> None:
    """`decisiones#6-identificacion`: «no estableceremos un porcentaje de
    parecido para asignar automáticamente un trabajo».

    El `None` no es un hueco pendiente: es la respuesta."""
    assert cfg.identificacion.politica == "determinista"
    assert cfg.identificacion.umbral_de_parecido is None


def test_las_dos_ultimas_prioridades_de_identificacion_van_a_incidencias(cfg) -> None:
    """Las tres primeras asignan; las dos últimas no deciden nunca solas."""
    por_prioridad = {
        p.prioridad: p.resultado for p in cfg.identificacion.prioridades
    }

    assert por_prioridad == {
        1: "asignacion_automatica",
        2: "asignacion_automatica",
        3: "asignacion_automatica",
        4: "incidencias",
        5: "incidencias",
    }


def test_un_duplicado_exacto_no_se_analiza_ni_sobrescribe(cfg) -> None:
    """`decisiones#7-versiones`. Que no se analice no es una optimización
    nuestra: «no generar coste API» es parte de su regla."""
    duplicado = cfg.versiones.duplicado_exacto

    assert duplicado.analizar is False
    assert duplicado.sobrescribir_original is False


def test_un_archivo_distinto_para_la_misma_fase_detiene_el_analisis(cfg) -> None:
    conflicto = cfg.versiones.archivo_distinto_misma_fase

    assert conflicto.conservar_como_version_nueva is True
    assert conflicto.detener_analisis_hasta_decision_docente is True


def test_no_hay_borrado_automatico(cfg) -> None:
    """`decisiones#8-retencion`: «no habrá borrado automático de proyectos,
    versiones, informes o evidencias»."""
    assert cfg.retencion.borrado_automatico is False
    assert cfg.retencion.borrar_pasados_dias is None
    assert cfg.versiones.version_elegida.eliminar_anteriores is False


def test_una_configuracion_que_active_el_borrado_no_se_carga() -> None:
    """La guarda, no el valor. Un plazo de borrado escrito a mano en el YAML
    contradice una decisión suya, y el sistema tiene que negarse a arrancar
    con ella en vez de empezar a borrar trabajos de alumnos."""
    from backend.expedientes.estructura import Retencion

    with pytest.raises(ValidationError, match="No hay borrado automático"):
        Retencion(
            politica="retencion_manual",
            borrado_automatico=False,
            borrar_pasados_dias=90,
            al_cerrar_el_curso={
                "mover_a": "99_ARCHIVO_CERRADO",
                "comprobar_copia_de_seguridad": True,
            },
        )


def test_una_configuracion_que_borre_versiones_anteriores_no_se_carga() -> None:
    """Misma guarda para la otra mitad: «nunca se eliminan»."""
    from backend.expedientes.estructura import Versiones

    with pytest.raises(ValidationError, match="no se eliminan nunca"):
        Versiones(
            duplicado_exacto={
                "marca": "DUPLICATE_EXACT", "analizar": False,
                "sobrescribir_original": False, "aviso_bloqueante": False,
            },
            archivo_distinto_misma_fase={
                "marca": "VERSION_CONFLICT",
                "conservar_como_version_nueva": True,
                "detener_analisis_hasta_decision_docente": True,
            },
            version_elegida={
                "anteriores_pasan_a": "historica", "eliminar_anteriores": True,
            },
        )


def test_un_umbral_de_parecido_con_politica_determinista_no_se_carga() -> None:
    """Lo que impide que vuelva a colarse la coincidencia difusa que él
    descartó."""
    from backend.expedientes.estructura import Identificacion

    with pytest.raises(ValidationError, match="no admite un umbral"):
        Identificacion(
            politica="determinista",
            umbral_de_parecido=0.85,
            normalizacion_ignora=["tildes"],
            prioridades=[],
        )
