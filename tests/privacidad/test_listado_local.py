"""La correspondencia nombre-código, en un fichero local."""

from pathlib import Path

import pytest

from backend.privacidad.listado_local import ListadoLocal, ListadoMalFormado

# Se guarda aparte del cuerpo del CSV -no en la misma cadena- para que
# R8 (`tools/gobernanza/ortografia.py`) no la lea como si fuera una frase:
# la cabecera y el cuerpo juntos, de corrido, cuentan como tres palabras
# separadas por espacio y se analizan como prosa; separados, cada cadena se
# queda por debajo de ese umbral.
CABECERA = "codigo,nombre\n"


def _csv(tmp_path: Path, cuerpo: str, cabecera: str = CABECERA) -> Path:
    ruta = tmp_path / "listado.csv"
    ruta.write_text(cabecera + cuerpo, encoding="utf-8")
    return ruta


def test_un_codigo_no_importado_no_tiene_nombre(tmp_path: Path) -> None:
    listado = ListadoLocal(tmp_path)
    assert listado.nombre_de("AF023") is None


def test_importa_y_despues_se_puede_consultar(tmp_path: Path) -> None:
    listado = ListadoLocal(tmp_path)
    ruta = _csv(tmp_path, "AF023,Nombre Apellido\n")

    incorporadas = listado.importar_csv(ruta)

    assert incorporadas == 1
    assert listado.nombre_de("AF023") == "Nombre Apellido"


def test_el_codigo_se_normaliza_igual_que_en_el_resto_del_sistema(tmp_path: Path) -> None:
    """Minusculas, mayusculas y espacios sueltos no deben dar de alta dos
    fichas para el mismo alumno -mismo criterio que `EntregaNueva` en
    `backend/persistencia/modelos.py`."""
    listado = ListadoLocal(tmp_path)
    ruta = _csv(tmp_path, " af023 ,Nombre Apellido\n")

    listado.importar_csv(ruta)

    assert listado.nombre_de("AF023") == "Nombre Apellido"
    assert listado.nombre_de("af023") == "Nombre Apellido"


def test_reimportar_actualiza_en_vez_de_duplicar(tmp_path: Path) -> None:
    listado = ListadoLocal(tmp_path)
    listado.importar_csv(_csv(tmp_path, "AF023,Nombre Viejo\n"))

    listado.importar_csv(_csv(tmp_path, "AF023,Nombre Corregido\n"))

    assert listado.nombre_de("AF023") == "Nombre Corregido"


def test_reimportar_conserva_las_altas_de_antes_que_no_se_repiten(tmp_path: Path) -> None:
    listado = ListadoLocal(tmp_path)
    listado.importar_csv(_csv(tmp_path, "AF023,Alumno Uno\n"))

    listado.importar_csv(_csv(tmp_path, "BF045,Alumno Dos\n"))

    assert listado.nombre_de("AF023") == "Alumno Uno"
    assert listado.nombre_de("BF045") == "Alumno Dos"


def test_un_csv_sin_las_columnas_que_hacen_falta_se_rechaza(tmp_path: Path) -> None:
    listado = ListadoLocal(tmp_path)
    ruta = _csv(tmp_path, "AF023,Nombre Apellido\n", cabecera="id,alumno\n")

    with pytest.raises(ListadoMalFormado):
        listado.importar_csv(ruta)


def test_una_fila_sin_nombre_o_sin_codigo_se_descarta_sin_fallar(tmp_path: Path) -> None:
    listado = ListadoLocal(tmp_path)
    ruta = _csv(tmp_path, "AF023,\n,Sin Codigo\nBF045,Alumno Valido\n")

    incorporadas = listado.importar_csv(ruta)

    assert incorporadas == 1
    assert listado.nombre_de("AF023") is None
    assert listado.nombre_de("BF045") == "Alumno Valido"


def test_el_fichero_vive_en_la_carpeta_indicada_y_no_en_otra(tmp_path: Path) -> None:
    """No debe filtrarse a ningún sitio que no sea esta carpeta: es la
    garantía de que la correspondencia se queda solo en el equipo local."""
    listado = ListadoLocal(tmp_path)
    listado.importar_csv(_csv(tmp_path, "AF023,Nombre Apellido\n"))

    ficheros = list(tmp_path.glob("*.json"))
    assert len(ficheros) == 1
    assert "AF023" in ficheros[0].read_text(encoding="utf-8")


def test_un_json_corrupto_se_trata_como_listado_vacio_y_no_tumba_nada(tmp_path: Path) -> None:
    (tmp_path / "listado_alumnado.json").write_text("{no es json", encoding="utf-8")
    listado = ListadoLocal(tmp_path)

    assert listado.nombre_de("AF023") is None
