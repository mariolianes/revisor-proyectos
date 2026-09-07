"""La CLI que importa el listado de alumnos de una comunidad, desde un Excel.

El único fichero `.xlsx` que toca este módulo se genera en `tmp_path` con
`openpyxl`, en cada test: nunca hay un `.xlsx` en el repositorio -R6
(`tools/gobernanza/privacidad.py`) lo prohíbe- ni un dato de alumno real -los
nombres son inventados, los códigos con forma ALU-AANNNN o AND-MAL-01-.
"""

from pathlib import Path

import openpyxl
import pytest

from tools.importar_listado_alumnos import main


def _repositorio(tmp_path: Path) -> Path:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    return raiz


def _configurar_datos_locales(raiz: Path, tmp_path: Path) -> Path:
    datos_locales = tmp_path / "datos_locales"
    datos_locales.mkdir()
    (raiz / ".env").write_text(
        f"REVISOR_DATOS_LOCALES={datos_locales}\n", encoding="utf-8"
    )
    return datos_locales


def _configurar_centros(raiz: Path, centros: dict[str, list[str]]) -> None:
    import yaml

    carpeta = raiz / "config"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "centros.yaml").write_text(
        yaml.safe_dump(centros, allow_unicode=True), encoding="utf-8"
    )


def _excel(tmp_path: Path, cabecera: list[str], filas: list[list[str]]) -> Path:
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(cabecera)
    for fila in filas:
        hoja.append(fila)
    ruta = tmp_path / "listado.xlsx"
    libro.save(ruta)
    return ruta


CABECERA = ["Nombre y apellidos", "Centro", "Ciclo", "Estado", "ID CESUR"]


def test_sin_datos_locales_configurados_no_importa_nada(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    excel = _excel(tmp_path, CABECERA, [["Nombre Uno", "AND-MAL-01", "MYP", "", ""]])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 1
    assert "REVISOR_DATOS_LOCALES" in capsys.readouterr().out


def test_una_comunidad_no_reconocida_se_rechaza(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    excel = _excel(tmp_path, CABECERA, [["Nombre Uno", "AND-MAL-01", "MYP", "", ""]])

    codigo = main(["--excel", str(excel), "--ccaa", "GAL", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 1
    assert "no es una comunidad" in capsys.readouterr().out


def test_un_curso_mal_escrito_se_rechaza(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    excel = _excel(tmp_path, CABECERA, [["Nombre Uno", "AND-MAL-01", "MYP", "", ""]])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "26-27"], raiz=raiz)

    assert codigo == 1
    assert "curso académico" in capsys.readouterr().out


def test_un_excel_inexistente_se_rechaza_con_claridad(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)

    codigo = main(
        ["--excel", str(tmp_path / "no-existe.xlsx"), "--ccaa", "AND", "--curso", "2026-2027"],
        raiz=raiz,
    )

    assert codigo == 1
    assert "No se encuentra" in capsys.readouterr().out


def test_sin_columnas_reconocibles_se_detiene(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    _configurar_centros(raiz, {"AND": ["AND-MAL-01"]})
    excel = _excel(tmp_path, ["Columna Rara Uno", "Columna Rara Dos"], [["x", "y"]])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 1
    assert "No se ha encontrado columna" in capsys.readouterr().out


def test_importa_un_listado_valido_y_no_imprime_ningun_nombre(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    datos_locales = _configurar_datos_locales(raiz, tmp_path)
    _configurar_centros(raiz, {"AND": ["AND-MAL-01", "AND-SEV-02"]})
    excel = _excel(tmp_path, CABECERA, [
        ["Nombre Uno Apellido", "AND-MAL-01", "MYP", "ACTIVO", "cesur-1"],
        ["Nombre Dos Apellido", "AND-SEV-02", "CIN", "", ""],
    ])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 0
    salida = capsys.readouterr().out
    assert "2 alumnos registrados (2 nuevos, 0 actualizados)" in salida
    assert "Ninguna fila pendiente de revisión." in salida
    assert "Nombre Uno Apellido" not in salida
    assert "Nombre Dos Apellido" not in salida
    assert str(datos_locales) in salida

    from backend.privacidad.listado_local import ListadoLocal
    listado = ListadoLocal(datos_locales)
    assert listado.nombre_de("ALU-260001") == "Nombre Uno Apellido"
    assert listado.nombre_de("ALU-260002") == "Nombre Dos Apellido"


def test_una_fila_dudosa_se_lista_por_numero_de_fila_sin_el_nombre(
    tmp_path: Path, capsys,
) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    _configurar_centros(raiz, {"AND": ["AND-MAL-01"]})
    excel = _excel(tmp_path, CABECERA, [
        ["Nombre Uno Apellido", "AND-MAL-01", "MYP", "", ""],
        ["Nombre Secreto Apellido", "", "MYP", "", ""],
    ])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 0
    salida = capsys.readouterr().out
    assert "1 filas pendientes de revisión" in salida
    assert "Fila 3" in salida
    assert "Nombre Secreto Apellido" not in salida
    assert "Nombre Secreto" not in salida


def test_sin_catalogo_de_centros_todo_queda_pendiente(tmp_path: Path, capsys) -> None:
    """Sin config/centros.yaml para la comunidad, nada se acepta a ciegas."""
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    excel = _excel(tmp_path, CABECERA, [["Nombre Uno", "AND-MAL-01", "MYP", "", ""]])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 0
    salida = capsys.readouterr().out
    assert "0 alumnos registrados" in salida
    assert "1 filas pendientes de revisión" in salida


def test_un_excel_sin_filas_de_datos_se_rechaza(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    excel = _excel(tmp_path, CABECERA, [])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 1
    assert "no tiene filas de datos" in capsys.readouterr().out


def test_sin_credenciales_de_supabase_avisa_y_usa_memoria(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    _configurar_datos_locales(raiz, tmp_path)
    _configurar_centros(raiz, {"AND": ["AND-MAL-01"]})
    excel = _excel(tmp_path, CABECERA, [["Nombre Uno", "AND-MAL-01", "MYP", "", ""]])

    codigo = main(["--excel", str(excel), "--ccaa", "AND", "--curso", "2026-2027"], raiz=raiz)

    assert codigo == 0
    assert "se pierde al cerrar" in capsys.readouterr().out
