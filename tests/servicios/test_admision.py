"""La admisión: de la bandeja al expediente, o a Incidencias.

Ningún nombre es de una persona real y ningún PDF procede de un trabajo real:
se construyen aquí. Nada de esto toca la carpeta del docente ni la red.
"""

from pathlib import Path

import pymupdf
import pytest

from backend.expedientes.estructura import cargar_estructura
from backend.identificacion.determinista import CandidatoLocal
from backend.servicios.admision import (
    CONFLICTO_DE_VERSION,
    DEMASIADO_GRANDE,
    DOC_ANTIGUO,
    DUPLICADO_EXACTO,
    EXTENSION_NO_ADMITIDA,
    SIN_IDENTIFICAR,
    Admision,
    EntregaAdmitida,
    admitir,
    nombre_normalizado,
)

RAIZ = Path(__file__).resolve().parents[2]

ANA = CandidatoLocal(
    student_id="ALU-260001", nombre="Ana Ficticia Inventada", platform_id="cesur-1"
)
BEA = CandidatoLocal(student_id="ALU-260002", nombre="Beatriz Supuesta Imaginaria")


@pytest.fixture(scope="module")
def cfg():
    return cargar_estructura(RAIZ)


@pytest.fixture
def expedientes(tmp_path: Path) -> Path:
    raiz = tmp_path / "CESUR_2026-2027"
    raiz.mkdir()
    return raiz


def _pdf(destino: Path, texto: str = "Proyecto Intermodular") -> Path:
    documento = pymupdf.open()
    documento.new_page().insert_text((72, 100), texto, fontsize=12)
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento.save(destino)
    documento.close()
    return destino


def _admitir(archivo: Path, cfg, expedientes: Path, **cambios) -> Admision:
    datos = dict(
        archivo=archivo, codigo_comunidad="AND", codigo_fase="E2", cfg=cfg,
        raiz_repositorio=RAIZ, raiz_expedientes=expedientes,
        candidatos=[ANA, BEA], ya_admitidas=[],
    )
    datos.update(cambios)
    return admitir(**datos)


# --- El caso que tiene que funcionar ---------------------------------------


def test_un_archivo_identificable_acaba_en_el_expediente(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """El circuito entero de la admisión, con el nombre que trae de CESUR."""
    archivo = _pdf(tmp_path / "bandeja" / "Ana_Ficticia_Inventada_Entrega_2.pdf")

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.admitido
    assert resultado.student_id == "ALU-260001"
    assert resultado.version == 1
    assert resultado.destino == str(
        Path("02_EXPEDIENTES_ALUMNOS/ALU-260001/03_ENTREGA_2/00_ORIGINAL/"
             "ALU-260001_E2_v01.pdf")
    )
    assert (expedientes / resultado.destino).is_file()


def test_el_original_se_queda_donde_estaba(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """Nada se mueve y nada se borra. El docente no ha dicho qué hacer con el
    original, y adivinarlo puede costarle el trabajo de un alumno."""
    archivo = _pdf(tmp_path / "bandeja" / "Ana_Ficticia_Inventada.pdf")

    _admitir(archivo, cfg, expedientes)

    assert archivo.is_file()


def test_el_expediente_se_crea_con_la_primera_entrega(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """Creación diferida: la carpeta nace ahora, no al importar el listado.
    Es lo que evita doscientas carpetas vacías."""
    expediente = expedientes / "02_EXPEDIENTES_ALUMNOS" / "ALU-260001"
    assert not expediente.exists()

    _admitir(_pdf(tmp_path / "Ana_Ficticia_Inventada.pdf"), cfg, expedientes)

    assert (expediente / "00_FICHA").is_dir()
    assert (expediente / "07_HISTORICO").is_dir()


def test_la_ruta_del_expediente_no_lleva_el_nombre_del_alumno(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """La exigencia expresa del docente, comprobada sobre el disco real."""
    resultado = _admitir(
        _pdf(tmp_path / "Ana_Ficticia_Inventada.pdf"), cfg, expedientes
    )

    ruta = resultado.destino.lower()
    for parte in ("ana", "ficticia", "inventada"):
        assert parte not in ruta


def test_la_presentacion_de_defensa_no_va_a_una_subcarpeta_de_entrega(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """06_DEFENSA no tiene las cinco subcarpetas: la presentación va a la
    carpeta a secas. El docente lo confirmó en decisiones#9-carpetas."""
    archivo = _pdf(tmp_path / "Ana_Ficticia_Inventada.pdf")

    resultado = _admitir(archivo, cfg, expedientes, codigo_fase="DEFENSA")

    assert resultado.destino.endswith("06_DEFENSA/ALU-260001_DEFENSA_v01.pdf".replace(
        "/", str(Path("a/b"))[1]
    ))


# --- Lo que no entra --------------------------------------------------------


def test_una_extension_no_admitida_va_a_incidencias(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    archivo = tmp_path / "Ana_Ficticia_Inventada.txt"
    archivo.write_text("no es un proyecto", encoding="utf-8")

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.a_incidencias
    assert resultado.marca == EXTENSION_NO_ADMITIDA
    assert (expedientes / resultado.destino).is_file()


def test_un_doc_antiguo_es_una_incidencia_tecnica(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """El docente lo dejó dicho: .doc no se analiza directamente."""
    archivo = tmp_path / "Ana_Ficticia_Inventada.doc"
    archivo.write_bytes(b"word antiguo")

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.marca == DOC_ANTIGUO
    assert "conviértelo" in resultado.motivo.lower()


def test_un_archivo_por_encima_del_limite_va_a_incidencias(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    archivo = tmp_path / "Ana_Ficticia_Inventada.pdf"
    archivo.write_bytes(b"x" * (cfg.archivos.tamano_maximo_mb * 1024 * 1024 + 1))

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.marca == DEMASIADO_GRANDE
    assert resultado.a_incidencias


def test_un_archivo_que_no_se_puede_asignar_va_a_incidencias(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """Lo importante: no se asigna al más parecido. Se detiene."""
    archivo = _pdf(tmp_path / "trabajo_final_definitivo.pdf")

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.a_incidencias
    assert resultado.marca == SIN_IDENTIFICAR
    assert resultado.student_id is None
    # Se copia con su nombre original: no hay ID con el que renombrarlo, y
    # ponerle uno inventado sería justo el error que todo esto evita.
    assert resultado.destino.endswith("trabajo_final_definitivo.pdf")


def test_una_incidencia_no_crea_ningun_expediente(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    _admitir(_pdf(tmp_path / "trabajo_sin_dueno.pdf"), cfg, expedientes)

    assert not (expedientes / "02_EXPEDIENTES_ALUMNOS").exists()


# --- Duplicados y versiones (decisiones#7-versiones) ------------------------


def test_el_mismo_archivo_dos_veces_es_un_duplicado_exacto(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """«Registrar, no analizar, no generar coste API, no sobrescribir el
    original.» Es también lo que impide que la bandeja se reprocese sola."""
    archivo = _pdf(tmp_path / "Ana_Ficticia_Inventada.pdf")
    primera = _admitir(archivo, cfg, expedientes)

    segunda = _admitir(
        archivo, cfg, expedientes,
        ya_admitidas=[EntregaAdmitida(
            student_id="ALU-260001", fase="E2", version=1, huella=primera.huella,
        )],
    )

    assert segunda.marca == DUPLICADO_EXACTO
    assert segunda.version == 1
    assert segunda.destino is None
    assert not segunda.admitido


def test_un_archivo_distinto_para_la_misma_fase_es_un_conflicto_de_version(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """Se conserva como versión nueva y el análisis espera a que el docente
    elija cuál vale. La anterior no se toca."""
    primero = _pdf(tmp_path / "Ana_Ficticia_Inventada.pdf", "Primera version")
    inicial = _admitir(primero, cfg, expedientes)
    segundo = _pdf(tmp_path / "otra" / "Ana_Ficticia_Inventada.pdf", "Segunda version")

    resultado = _admitir(
        segundo, cfg, expedientes,
        ya_admitidas=[EntregaAdmitida(
            student_id="ALU-260001", fase="E2", version=1, huella=inicial.huella,
        )],
    )

    assert resultado.marca == CONFLICTO_DE_VERSION
    assert resultado.version == 2
    assert resultado.destino.endswith("ALU-260001_E2_v02.pdf")
    # Y la primera sigue donde estaba: «nunca se eliminan».
    assert (expedientes / inicial.destino).is_file()


def test_una_entrega_de_otra_fase_no_es_un_conflicto(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    archivo = _pdf(tmp_path / "Ana_Ficticia_Inventada.pdf")

    resultado = _admitir(
        archivo, cfg, expedientes, codigo_fase="E3",
        ya_admitidas=[EntregaAdmitida(
            student_id="ALU-260001", fase="E2", version=1, huella="otra",
        )],
    )

    assert resultado.marca is None
    assert resultado.version == 1


# --- La identificación, ya enchufada ---------------------------------------


def test_la_portada_confirma_un_nombre_de_archivo_incompleto(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """La prioridad 3 del docente, funcionando de punta a punta con un PDF."""
    archivo = _pdf(
        tmp_path / "Ana_Ficticia.pdf", "Autora: Ana Ficticia Inventada"
    )

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.student_id == "ALU-260001"


def test_una_portada_que_nombra_a_otro_detiene_la_admision(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """La prioridad 5: «Incidencias siempre». El identificador de plataforma
    habría asignado solo; la contradicción gana."""
    archivo = _pdf(
        tmp_path / "cualquier_nombre.pdf", "Autora: Beatriz Supuesta Imaginaria"
    )

    resultado = _admitir(archivo, cfg, expedientes, platform_id="cesur-1")

    assert resultado.a_incidencias
    assert resultado.student_id is None


def test_un_pdf_ilegible_no_impide_identificar_por_el_nombre(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """La portada es auxiliar: que no se pueda leer no invalida las otras dos
    vías. Si tampoco bastaran, el caso iría a Incidencias con su motivo."""
    archivo = tmp_path / "Ana_Ficticia_Inventada.pdf"
    archivo.write_bytes(b"esto no es un pdf")

    resultado = _admitir(archivo, cfg, expedientes)

    assert resultado.student_id == "ALU-260001"


# --- La garantía de privacidad ----------------------------------------------


def test_lo_que_devuelve_la_admision_nunca_lleva_un_nombre(
    tmp_path: Path, cfg, expedientes: Path
) -> None:
    """`Admision` cruza la frontera hacia el resto del sistema. El nombre
    entra por `candidatos` y no sale.

    El nombre del archivo original sí aparece -es lo que el docente ve en su
    bandeja, y sin él no sabría de cuál se le habla-, así que se comprueba
    sobre un archivo cuyo nombre no lleva el del alumno.
    """
    archivo = _pdf(tmp_path / "entrega2.pdf", "Autora: Ana Ficticia Inventada")

    resultado = _admitir(archivo, cfg, expedientes)

    texto = resultado.model_dump_json().lower()
    for parte in ("ana", "ficticia", "inventada", "beatriz"):
        assert parte not in texto, resultado.motivo


def test_el_nombre_normalizado_solo_lleva_el_identificador() -> None:
    assert nombre_normalizado("ALU-260001", "E2", 1, ".PDF") == "ALU-260001_E2_v01.pdf"
    assert nombre_normalizado("ALU-260001", "FINAL", 12, ".docx") == (
        "ALU-260001_FINAL_v12.docx"
    )
