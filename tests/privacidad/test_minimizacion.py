"""Lo que la minimización retira -y lo que no puede prometer retirar-."""

from backend.privacidad.minimizacion import (
    MARCADOR_ALUMNO,
    MARCADOR_CORREO,
    MARCADOR_DNI,
    MARCADOR_TELEFONO,
    minimizar,
)


def test_sustituye_el_nombre_conocido() -> None:
    texto = "Trabajo presentado por Nombre Apellido para el modulo de FCT."

    resultado = minimizar(texto, "Nombre Apellido")

    assert "Nombre Apellido" not in resultado.texto
    assert MARCADOR_ALUMNO in resultado.texto
    assert resultado.veces_nombre_sustituido == 1
    assert resultado.nombre_conocido is True
    assert resultado.avisos == []


def test_reconoce_el_nombre_invertido_apellido_coma_nombre() -> None:
    texto = "Autor: Apellido Segundo, Nombre"

    resultado = minimizar(texto, "Nombre Apellido Segundo")

    assert MARCADOR_ALUMNO in resultado.texto
    assert resultado.veces_nombre_sustituido == 1


def test_sin_nombre_en_el_listado_no_sustituye_nada_y_avisa() -> None:
    texto = "Trabajo presentado por Nombre Apellido para el modulo de FCT."

    resultado = minimizar(texto, None)

    assert "Nombre Apellido" in resultado.texto
    assert resultado.veces_nombre_sustituido == 0
    assert resultado.nombre_conocido is False
    assert len(resultado.avisos) == 1
    assert "listado local" in resultado.avisos[0]


def test_retira_un_dni_con_las_mismas_reglas_de_r6() -> None:
    resultado = minimizar("Contacto: DNI 12345678Z para cualquier duda.", None)

    assert "12345678Z" not in resultado.texto
    assert MARCADOR_DNI in resultado.texto
    assert resultado.veces_dni_sustituido == 1


def test_retira_un_correo() -> None:
    resultado = minimizar("Escribir a alumno.ejemplo@centro.es si hay dudas.", None)

    assert "alumno.ejemplo@centro.es" not in resultado.texto
    assert MARCADOR_CORREO in resultado.texto


def test_retira_un_telefono() -> None:
    resultado = minimizar("Telefono de contacto: 612345678.", None)

    assert "612345678" not in resultado.texto
    assert MARCADOR_TELEFONO in resultado.texto


def test_no_confunde_un_codigo_de_alumno_con_un_dato_personal() -> None:
    """Mismo caso que ya prueba R6: un código como AF023 no es un dato
    personal y no debe tocarse."""
    resultado = minimizar("Código de alumno AF023, ciclo DAM, fase E2.", None)

    assert resultado.texto == "Código de alumno AF023, ciclo DAM, fase E2."
    assert resultado.veces_dni_sustituido == 0
    assert resultado.veces_telefono_sustituido == 0


def test_retira_varios_tipos_a_la_vez_sin_que_se_estorben() -> None:
    texto = (
        "Autor: Nombre Apellido. Contacto: alumno@centro.es o 612345678. "
        "DNI 12345678Z."
    )

    resultado = minimizar(texto, "Nombre Apellido")

    assert "Nombre Apellido" not in resultado.texto
    assert "alumno@centro.es" not in resultado.texto
    assert "612345678" not in resultado.texto
    assert "12345678Z" not in resultado.texto
    assert resultado.veces_nombre_sustituido == 1
    assert resultado.veces_correo_sustituido == 1
    assert resultado.veces_telefono_sustituido == 1
    assert resultado.veces_dni_sustituido == 1


def test_un_nombre_escrito_distinto_al_del_listado_no_se_reconoce() -> None:
    """Esto es exactamente el límite que el módulo documenta: no es una
    garantía. Un apodo, una errata o un segundo apellido de más no encajan
    con la coincidencia literal."""
    texto = "Trabajo de Nombrecito Apellido, alumno de segundo curso."

    resultado = minimizar(texto, "Nombre Apellido")

    assert "Nombrecito Apellido" in resultado.texto
    assert resultado.veces_nombre_sustituido == 0
