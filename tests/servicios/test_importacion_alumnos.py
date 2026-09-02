"""El importador de listados de alumnos: mapeo de columnas, validación de
filas dudosas, y el registro maestro que resulta.

Ningún test de este fichero toca un Excel real ni un dato de alumno real:
las filas se construyen a mano, como `{columna: valor}`, con nombres
inventados. La lectura del `.xlsx` en sí vive en
`tools/importar_listado_alumnos.py` y se prueba en
`tests/tools/test_importar_listado_alumnos.py`, con un libro generado en
`tmp_path` -nunca uno que viva en el repositorio, porque R6
(`tools/gobernanza/privacidad.py`) prohíbe cualquier `.xlsx` versionado-.
"""

from pathlib import Path

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.privacidad.listado_local import ListadoLocal
from backend.servicios.importacion_alumnos import (
    CENTRO_DESCONOCIDO,
    CICLO_DESCONOCIDO,
    COINCIDENCIA_DE_NOMBRE,
    ESTADO_DESCONOCIDO,
    FILA_DUPLICADA,
    REPETIDOR_POSIBLE,
    SIN_CENTRO,
    SIN_CICLO,
    ColumnasNoMapeadas,
    cargar_centros_conocidos,
    importar,
    mapear_cabecera,
)

CURSO = "2026-2027"
CCAA = "AND"
CENTROS = {"AND-MAL-01", "AND-SEV-02"}

# Cabecera con los nombres de columna "de fábrica": los que usan los
# ejemplos de este fichero salvo que un test declare otros, para probar los
# alias.
CABECERA = ["Nombre y apellidos", "Centro", "Ciclo", "Estado", "ID CESUR"]


def _fila(nombre="", centro="AND-MAL-01", ciclo="MYP", estado="", id_cesur=""):
    return {
        "Nombre y apellidos": nombre, "Centro": centro, "Ciclo": ciclo,
        "Estado": estado, "ID CESUR": id_cesur,
    }


def _importar(filas, *, cabecera=CABECERA, centros=CENTROS, almacen=None, listado_local=None, ccaa=CCAA, curso=CURSO):
    return importar(
        filas, cabecera, ccaa_code=ccaa, curso=curso,
        almacen=almacen if almacen is not None else AlmacenEnMemoria(),
        listado_local=listado_local,
        centros_conocidos=centros,
    )


@pytest.fixture
def listado_local(tmp_path: Path) -> ListadoLocal:
    return ListadoLocal(tmp_path)


# --- mapear_cabecera ---------------------------------------------------


def test_reconoce_la_cabecera_de_fabrica() -> None:
    mapa = mapear_cabecera(CABECERA)

    assert mapa["nombre_apellidos"] == "Nombre y apellidos"
    assert mapa["centro_code"] == "Centro"
    assert mapa["ciclo_code"] == "Ciclo"


def test_reconoce_alias_con_otras_palabras_mayusculas_y_acentos() -> None:
    """El docente advirtió que los Excel de CESUR no comparten estructura
    entre comunidades: distinta capitalización, con o sin tildes, otro
    orden de columnas."""
    cabecera = ["ALUMNO/A", "Código Centro", "CICLO FORMATIVO", "Situación"]

    mapa = mapear_cabecera(cabecera)

    assert mapa["nombre_apellidos"] == "ALUMNO/A"
    assert mapa["centro_code"] == "Código Centro"
    assert mapa["ciclo_code"] == "CICLO FORMATIVO"
    assert mapa["estado_matricula"] == "Situación"


def test_el_orden_de_las_columnas_es_indiferente() -> None:
    cabecera = ["Ciclo", "Nombre y apellidos", "Centro"]

    mapa = mapear_cabecera(cabecera)

    assert mapa["nombre_apellidos"] == "Nombre y apellidos"


def test_sin_columna_de_centro_se_detiene_con_claridad() -> None:
    with pytest.raises(ColumnasNoMapeadas, match="centro_code"):
        mapear_cabecera(["Nombre y apellidos", "Ciclo"])


def test_platform_id_y_estado_son_opcionales() -> None:
    mapa = mapear_cabecera(["Nombre y apellidos", "Centro", "Ciclo"])

    assert "estado_matricula" not in mapa
    assert "platform_id" not in mapa


# --- filas en blanco -----------------------------------------------------


def test_una_fila_sin_nombre_se_cuenta_como_en_blanco_y_no_como_error(listado_local) -> None:
    resultado = _importar([_fila(nombre="")], listado_local=listado_local)

    assert resultado.en_blanco == 1
    assert resultado.pendientes == []
    assert resultado.nuevas == 0


# --- registro correcto ----------------------------------------------------


def test_una_fila_valida_se_registra_y_su_nombre_va_solo_al_listado_local(
    listado_local,
) -> None:
    almacen = AlmacenEnMemoria()

    resultado = _importar(
        [_fila(nombre="Nombre Uno")], almacen=almacen, listado_local=listado_local,
    )

    assert resultado.nuevas == 1
    assert resultado.pendientes == []
    alumnos = almacen.listar_alumnos()
    assert len(alumnos) == 1
    assert alumnos[0].student_id == "ALU-260001"
    assert listado_local.nombre_de("ALU-260001") == "Nombre Uno"


def test_el_estado_por_omision_es_activo_si_la_columna_viene_vacia(listado_local) -> None:
    almacen = AlmacenEnMemoria()

    _importar([_fila(nombre="Nombre Uno", estado="")], almacen=almacen, listado_local=listado_local)

    assert almacen.listar_alumnos()[0].estado_matricula == "ACTIVO"


def test_varias_filas_validas_reciben_student_id_consecutivos(listado_local) -> None:
    almacen = AlmacenEnMemoria()

    resultado = _importar(
        [_fila(nombre="Nombre Uno"), _fila(nombre="Nombre Dos")],
        almacen=almacen, listado_local=listado_local,
    )

    assert resultado.nuevas == 2
    ids = sorted(a.student_id for a in almacen.listar_alumnos())
    assert ids == ["ALU-260001", "ALU-260002"]


# --- filas dudosas: no se registran, quedan pendientes --------------------


def test_una_fila_sin_centro_no_se_registra(listado_local) -> None:
    almacen = AlmacenEnMemoria()

    resultado = _importar(
        [_fila(nombre="Nombre Uno", centro="")], almacen=almacen, listado_local=listado_local,
    )

    assert resultado.nuevas == 0
    assert almacen.listar_alumnos() == []
    assert listado_local.todos() == {}
    assert len(resultado.pendientes) == 1
    assert resultado.pendientes[0].motivo == SIN_CENTRO
    assert "Nombre Uno" not in resultado.pendientes[0].detalle


def test_una_fila_con_centro_desconocido_no_se_registra(listado_local) -> None:
    resultado = _importar(
        [_fila(nombre="Nombre Uno", centro="AND-NO-EXISTE")], listado_local=listado_local,
    )

    assert resultado.nuevas == 0
    assert resultado.pendientes[0].motivo == CENTRO_DESCONOCIDO


def test_sin_catalogo_de_centros_ninguna_fila_se_acepta_a_ciegas(listado_local) -> None:
    """`centros_conocidos=None` -sin catálogo para la comunidad- es el
    fallo seguro: nada se verifica, así que nada se acepta sin más."""
    resultado = _importar(
        [_fila(nombre="Nombre Uno")], centros=None, listado_local=listado_local,
    )

    assert resultado.nuevas == 0
    assert resultado.pendientes[0].motivo == CENTRO_DESCONOCIDO


def test_una_fila_sin_ciclo_no_se_registra(listado_local) -> None:
    resultado = _importar(
        [_fila(nombre="Nombre Uno", ciclo="")], listado_local=listado_local,
    )

    assert resultado.pendientes[0].motivo == SIN_CICLO


def test_un_ciclo_no_reconocido_no_se_registra(listado_local) -> None:
    resultado = _importar(
        [_fila(nombre="Nombre Uno", ciclo="DAM")], listado_local=listado_local,
    )

    assert resultado.pendientes[0].motivo == CICLO_DESCONOCIDO


def test_un_estado_no_reconocido_no_se_registra(listado_local) -> None:
    resultado = _importar(
        [_fila(nombre="Nombre Uno", estado="EXPULSADO")], listado_local=listado_local,
    )

    assert resultado.pendientes[0].motivo == ESTADO_DESCONOCIDO


def test_una_fila_exactamente_repetida_no_se_registra_dos_veces(listado_local) -> None:
    almacen = AlmacenEnMemoria()

    resultado = _importar(
        [_fila(nombre="Nombre Uno"), _fila(nombre="Nombre Uno")],
        almacen=almacen, listado_local=listado_local,
    )

    assert resultado.nuevas == 1
    assert len(almacen.listar_alumnos()) == 1
    assert resultado.pendientes[0].motivo == FILA_DUPLICADA
    assert resultado.pendientes[0].fila == 3


def test_dos_filas_con_el_mismo_nombre_y_distinto_centro_no_se_registran_solas(
    listado_local,
) -> None:
    """Dos personas reales con el mismo nombre: el sistema no decide cuál es
    cuál, aunque un dato (el centro) ya las distinga. NINGUNA de las dos se
    registra -no solo la segunda que se encuentra-, porque hasta ver el
    listado entero no se sabe que hay una coincidencia."""
    almacen = AlmacenEnMemoria()

    resultado = _importar(
        [
            _fila(nombre="Nombre Uno", centro="AND-MAL-01"),
            _fila(nombre="Nombre Uno", centro="AND-SEV-02"),
        ],
        almacen=almacen, listado_local=listado_local,
    )

    assert resultado.nuevas == 0
    assert almacen.listar_alumnos() == []
    assert len(resultado.pendientes) == 2
    assert {p.fila for p in resultado.pendientes} == {2, 3}
    assert all(p.motivo == COINCIDENCIA_DE_NOMBRE for p in resultado.pendientes)


def test_un_nombre_que_ya_esta_en_el_listado_local_sin_platform_id_se_detiene(
    listado_local,
) -> None:
    """El nombre ya está en la correspondencia local -de una importación
    anterior-, y esta fila no trae ID de CESUR con el que confirmar que es
    la misma persona: no se fusiona ni se da de alta una segunda vez a
    ciegas."""
    listado_local.importar_pares({"ALU-260001": "Nombre Uno"})

    resultado = _importar([_fila(nombre="Nombre Uno")], listado_local=listado_local)

    assert resultado.nuevas == 0
    assert resultado.pendientes[0].motivo == COINCIDENCIA_DE_NOMBRE


# --- emparejar por platform_id, preferible al nombre -----------------------


def test_reimportar_con_el_mismo_platform_id_del_mismo_curso_actualiza(
    listado_local,
) -> None:
    almacen = AlmacenEnMemoria()
    _importar(
        [_fila(nombre="Nombre Uno", id_cesur="cesur-1", estado="ACTIVO")],
        almacen=almacen, listado_local=listado_local,
    )

    resultado = _importar(
        [_fila(nombre="Nombre Uno", id_cesur="cesur-1", estado="BAJA")],
        almacen=almacen, listado_local=listado_local,
    )

    assert resultado.nuevas == 0
    assert resultado.actualizadas == 1
    alumnos = almacen.listar_alumnos()
    assert len(alumnos) == 1
    assert alumnos[0].estado_matricula == "BAJA"


def test_un_platform_id_de_otro_curso_no_se_reutiliza_solo(listado_local) -> None:
    """El caso del repetidor: no se decide en automático si conserva su
    student_id anterior o si es un alta nueva -D-024-."""
    almacen = AlmacenEnMemoria()
    _importar(
        [_fila(nombre="Nombre Uno", id_cesur="cesur-1")],
        almacen=almacen, listado_local=listado_local, curso="2025-2026",
    )

    resultado = _importar(
        [_fila(nombre="Nombre Uno", id_cesur="cesur-1")],
        almacen=almacen, listado_local=listado_local, curso=CURSO,
    )

    assert resultado.nuevas == 0
    assert resultado.pendientes[0].motivo == REPETIDOR_POSIBLE
    # El alta del curso anterior sigue siendo la única: no se ha creado
    # ninguna fila nueva a partir de la fila dudosa.
    assert len(almacen.listar_alumnos()) == 1


# --- cargar_centros_conocidos ----------------------------------------------


def test_cargar_centros_conocidos_sin_fichero_da_none(tmp_path: Path) -> None:
    assert cargar_centros_conocidos(tmp_path / "no-existe.yaml", "AND") is None


def test_cargar_centros_conocidos_sin_entradas_para_la_comunidad_da_none(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "centros.yaml"
    ruta.write_text("AND: []\nMAD:\n  - MAD-01\n", encoding="utf-8")

    assert cargar_centros_conocidos(ruta, "AND") is None


def test_cargar_centros_conocidos_normaliza_mayusculas_y_espacios(tmp_path: Path) -> None:
    ruta = tmp_path / "centros.yaml"
    ruta.write_text("AND:\n  - ' and-mal-01 '\n", encoding="utf-8")

    assert cargar_centros_conocidos(ruta, "AND") == {"AND-MAL-01"}
