"""La escalera de identificación del docente (`decisiones#6-identificacion`).

Ningún nombre de estos tests es de una persona real: son inventados, como
exige `CLAUDE.md`.
"""

from backend.identificacion.determinista import (
    ASIGNADO,
    CONTRADICCION,
    INCIDENCIAS,
    POR_NOMBRE_COMPLETO,
    POR_NOMBRE_Y_PORTADA,
    POR_PLATAFORMA,
    SIN_CONFIRMAR,
    CandidatoLocal,
    identificar,
)

ANA = CandidatoLocal(
    student_id="ALU-260001", nombre="Ana Ficticia Inventada",
    platform_id="cesur-1",
)
BEA = CandidatoLocal(
    student_id="ALU-260002", nombre="Beatriz Supuesta Imaginaria",
    platform_id="cesur-2",
)
# Mismo nombre, distinto alumno: el caso que obliga a detenerse.
OTRA_ANA = CandidatoLocal(
    student_id="ALU-260003", nombre="Ana Ficticia Inventada",
)


# --- Prioridad 1: el identificador de plataforma ---------------------------


def test_el_identificador_de_plataforma_asigna_solo() -> None:
    resultado = identificar(candidatos=[ANA, BEA], platform_id="cesur-2")

    assert resultado.student_id == "ALU-260002"
    assert resultado.prioridad == POR_PLATAFORMA
    assert resultado.resultado == ASIGNADO


def test_un_identificador_de_plataforma_repetido_se_detiene() -> None:
    """El listado se contradice a sí mismo: no se elige el primero."""
    repetido = CandidatoLocal(
        student_id="ALU-260009", nombre="Otra Persona Distinta",
        platform_id="cesur-1",
    )

    resultado = identificar(candidatos=[ANA, repetido], platform_id="cesur-1")

    assert resultado.student_id is None
    assert resultado.a_incidencias


# --- Prioridad 2: el nombre completo ---------------------------------------


def test_el_nombre_completo_unico_asigna_solo() -> None:
    resultado = identificar(
        candidatos=[ANA, BEA], nombre_del_archivo="Ana Ficticia Inventada"
    )

    assert resultado.student_id == "ALU-260001"
    assert resultado.prioridad == POR_NOMBRE_COMPLETO


def test_el_orden_apellidos_nombre_da_lo_mismo() -> None:
    """El docente lo pide expresamente: ignorar el orden «apellidos,
    nombre»."""
    resultado = identificar(
        candidatos=[ANA, BEA], nombre_del_archivo="Ficticia Inventada, Ana"
    )

    assert resultado.student_id == "ALU-260001"


def test_las_tildes_y_las_mayusculas_dan_lo_mismo() -> None:
    con_tildes = CandidatoLocal(
        student_id="ALU-260004", nombre="Mario Jesús Rodríguez Peña"
    )

    resultado = identificar(
        candidatos=[con_tildes], nombre_del_archivo="MARIO JESUS RODRIGUEZ PENA"
    )

    assert resultado.student_id == "ALU-260004"


def test_dos_alumnos_con_el_mismo_nombre_se_detienen() -> None:
    """El límite que él pone: dos personas homónimas del mismo curso no se
    resuelven eligiendo una."""
    resultado = identificar(
        candidatos=[ANA, OTRA_ANA], nombre_del_archivo="Ana Ficticia Inventada"
    )

    assert resultado.student_id is None
    assert resultado.prioridad == SIN_CONFIRMAR
    assert resultado.resultado == INCIDENCIAS


# --- Prioridad 3: nombre parcial confirmado por la portada -----------------


def test_el_nombre_parcial_con_candidato_unico_y_portada_compatible_asigna() -> None:
    resultado = identificar(
        candidatos=[ANA, BEA],
        nombre_del_archivo="Ana Ficticia",
        nombre_de_portada="Ana Ficticia Inventada",
    )

    assert resultado.student_id == "ALU-260001"
    assert resultado.prioridad == POR_NOMBRE_Y_PORTADA


def test_sin_portada_el_nombre_parcial_no_asigna() -> None:
    """La prioridad 3 exige las tres condiciones, no dos. Sin portada no hay
    con qué confirmar, y confirmar es lo que la separa de adivinar."""
    resultado = identificar(candidatos=[ANA, BEA], nombre_del_archivo="Ana Ficticia")

    assert resultado.student_id is None
    assert resultado.a_incidencias


def test_una_sola_palabra_no_identifica_a_nadie() -> None:
    """«Nombre más al menos un apellido». En 200-250 alumnos, un nombre de
    pila no distingue."""
    resultado = identificar(
        candidatos=[ANA],
        nombre_del_archivo="Ana",
        nombre_de_portada="Ana Ficticia Inventada",
    )

    assert resultado.student_id is None
    assert resultado.a_incidencias


def test_un_nombre_incompleto_que_encaja_con_dos_se_detiene() -> None:
    otra = CandidatoLocal(
        student_id="ALU-260005", nombre="Ana Ficticia Distinta"
    )

    resultado = identificar(
        candidatos=[ANA, otra],
        nombre_del_archivo="Ana Ficticia",
        nombre_de_portada="Ana Ficticia Inventada",
    )

    assert resultado.student_id is None
    assert resultado.a_incidencias


# --- Prioridad 5: la contradicción gana a todo -----------------------------


def test_la_portada_que_contradice_al_identificador_detiene_la_asignacion() -> None:
    """Lo más importante de este módulo. La prioridad 1 habría asignado sola;
    la prioridad 5 dice «Incidencias siempre», y siempre gana."""
    resultado = identificar(
        candidatos=[ANA, BEA],
        platform_id="cesur-1",
        nombre_de_portada="Beatriz Supuesta Imaginaria",
    )

    assert resultado.student_id is None
    assert resultado.prioridad == CONTRADICCION
    assert resultado.resultado == INCIDENCIAS
    assert "portada" in resultado.motivo


def test_el_nombre_del_archivo_que_contradice_al_identificador_detiene() -> None:
    resultado = identificar(
        candidatos=[ANA, BEA],
        platform_id="cesur-1",
        nombre_del_archivo="Beatriz Supuesta Imaginaria",
    )

    assert resultado.student_id is None
    assert resultado.prioridad == CONTRADICCION


def test_una_portada_parcial_no_es_una_contradiccion() -> None:
    """«Si falta el segundo apellido, cambia el orden o existen pequeñas
    diferencias ortográficas, se aplican las reglas de normalización.» Una
    portada que dice menos no dice otra cosa."""
    resultado = identificar(
        candidatos=[ANA, BEA],
        platform_id="cesur-1",
        nombre_de_portada="Ana Ficticia",
    )

    assert resultado.student_id == "ALU-260001"
    assert resultado.prioridad == POR_PLATAFORMA


# --- Prioridad 4: lo que no encaja en ninguna ------------------------------


def test_sin_nada_con_lo_que_identificar_va_a_incidencias() -> None:
    resultado = identificar(candidatos=[ANA, BEA])

    assert resultado.student_id is None
    assert resultado.prioridad == SIN_CONFIRMAR


def test_un_nombre_que_no_es_de_nadie_del_curso_va_a_incidencias() -> None:
    resultado = identificar(
        candidatos=[ANA, BEA], nombre_del_archivo="Persona Que No Existe"
    )

    assert resultado.student_id is None
    assert resultado.a_incidencias


# --- La garantía de privacidad ---------------------------------------------


def test_lo_que_devuelve_la_identificacion_nunca_lleva_un_nombre() -> None:
    """Es el objeto que cruza la frontera hacia el resto del sistema. Si no
    lleva nombre, no puede filtrarlo.

    Se comprueba sobre los tres desenlaces -asignado, sin confirmar y
    contradicción-, porque el motivo de una contradicción es justo donde
    resultaría más natural escribir «uno dice una cosa y otro otra» con los
    nombres delante.
    """
    casos = [
        identificar(candidatos=[ANA, BEA], platform_id="cesur-1"),
        identificar(candidatos=[ANA, OTRA_ANA],
                    nombre_del_archivo="Ana Ficticia Inventada"),
        identificar(candidatos=[ANA, BEA], platform_id="cesur-1",
                    nombre_de_portada="Beatriz Supuesta Imaginaria"),
    ]

    for resultado in casos:
        texto = resultado.model_dump_json().lower()
        for parte in ("ana", "beatriz", "ficticia", "supuesta", "inventada"):
            assert parte not in texto, resultado.motivo
