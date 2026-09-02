"""El registro maestro de alumnos: los modelos y las funciones puras."""

import pytest

from backend.persistencia.alumnos import (
    AlumnoNuevo,
    codigo_de_curso,
    error_de_platform_id_duplicado,
    generar_student_id,
    validar_alumno,
    validar_curso,
)


def _alumno(**cambios) -> AlumnoNuevo:
    datos = dict(
        curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
        ciclo_code="MYP",
    )
    datos.update(cambios)
    return AlumnoNuevo(**datos)


# --- curso -------------------------------------------------------------


def test_codigo_de_curso_toma_los_dos_ultimos_digitos_del_primer_ano() -> None:
    assert codigo_de_curso("2026-2027") == "26"


@pytest.mark.parametrize("curso", ["2026", "2026-27", "26-27", "2026/2027", ""])
def test_un_curso_mal_formado_se_rechaza(curso: str) -> None:
    with pytest.raises(ValueError, match="curso académico"):
        validar_curso(curso)


def test_un_curso_con_anos_no_consecutivos_se_rechaza() -> None:
    with pytest.raises(ValueError, match="siguiente al primero"):
        validar_curso("2026-2029")


# --- generar_student_id -------------------------------------------------


def test_el_primer_alumno_del_curso_es_0001() -> None:
    assert generar_student_id("2026-2027", []) == "ALU-260001"


def test_el_siguiente_alumno_continua_la_secuencia() -> None:
    existentes = ["ALU-260001", "ALU-260002"]
    assert generar_student_id("2026-2027", existentes) == "ALU-260003"


def test_no_se_deja_enganar_por_huecos_usa_el_maximo() -> None:
    """Si se ha borrado el 2, el siguiente sigue siendo el 4, no el 2 libre:
    un student_id no se reutiliza nunca, ni por accidente."""
    existentes = ["ALU-260001", "ALU-260003"]
    assert generar_student_id("2026-2027", existentes) == "ALU-260004"


def test_cada_curso_numera_por_su_cuenta() -> None:
    """Un student_id de un curso no cuenta para el contador de otro."""
    existentes_de_otro_curso = ["ALU-270001", "ALU-270002", "ALU-270003"]
    assert generar_student_id("2026-2027", existentes_de_otro_curso) == "ALU-260001"


def test_ids_que_no_encajan_en_el_patron_se_ignoran() -> None:
    """Un AF023 heredado del sistema anterior no confunde el contador."""
    existentes = ["AF023", "ALU-260001", "no-es-un-id"]
    assert generar_student_id("2026-2027", existentes) == "ALU-260002"


# --- AlumnoNuevo: nunca admite nombre -----------------------------------


def test_alumno_nuevo_rechaza_un_campo_nombre() -> None:
    """`extra='forbid'`: colar un nombre hacia el registro maestro falla en
    el momento de construir el objeto, no más tarde al guardar."""
    with pytest.raises(Exception):
        AlumnoNuevo(
            curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
            ciclo_code="MYP", nombre="Nombre Apellido",
        )


def test_alumno_nuevo_normaliza_los_codigos() -> None:
    alumno = _alumno(ccaa_code=" and ", centro_code=" and-mal-01 ", ciclo_code="myp")

    assert alumno.ccaa_code == "AND"
    assert alumno.centro_code == "AND-MAL-01"
    assert alumno.ciclo_code == "MYP"


def test_platform_id_solo_se_recorta_no_se_pone_en_mayusculas() -> None:
    alumno = _alumno(platform_id="  cesur-Ab12  ")

    assert alumno.platform_id == "cesur-Ab12"


def test_platform_id_vacio_se_trata_como_ausente() -> None:
    alumno = _alumno(platform_id="   ")

    assert alumno.platform_id is None


# --- validar_alumno ------------------------------------------------------


def test_una_comunidad_no_reconocida_se_rechaza() -> None:
    with pytest.raises(ValueError, match="comunidad autónoma"):
        validar_alumno(_alumno(ccaa_code="XXX"))


def test_sin_centro_se_rechaza() -> None:
    with pytest.raises(ValueError, match="necesita un centro"):
        validar_alumno(_alumno(centro_code=""))


def test_un_ciclo_no_reconocido_se_rechaza() -> None:
    with pytest.raises(ValueError, match="ciclo reconocido"):
        validar_alumno(_alumno(ciclo_code="DAM"))


def test_un_estado_de_matricula_no_reconocido_se_rechaza() -> None:
    with pytest.raises(ValueError, match="matrícula"):
        validar_alumno(_alumno(estado_matricula="EXPULSADO"))


def test_un_student_id_con_forma_invalida_se_rechaza() -> None:
    with pytest.raises(ValueError, match="student_id"):
        validar_alumno(_alumno(student_id="AF023"))


def test_un_student_id_bien_formado_pasa() -> None:
    validar_alumno(_alumno(student_id="ALU-260001"))


def test_un_alumno_valido_no_falla() -> None:
    validar_alumno(_alumno())


# --- mensaje compartido de choque de platform_id -------------------------


def test_el_mensaje_de_choque_de_platform_id_nombra_el_id_y_el_student_id() -> None:
    mensaje = str(error_de_platform_id_duplicado("cesur-99", "ALU-260001"))

    assert "cesur-99" in mensaje
    assert "ALU-260001" in mensaje
