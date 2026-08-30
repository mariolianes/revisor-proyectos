"""La CLI que importa el listado de un curso."""

from pathlib import Path

from tools.importar_listado import main


def _repositorio(tmp_path: Path) -> Path:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    return raiz


# Aparte del cuerpo, no en la misma cadena: juntos cuentan como tres
# palabras separadas por espacio para R8 (`tools/gobernanza/ortografia.py`)
# y se analizan como si fueran prosa.
CABECERA = "codigo,nombre\n"


def _csv(tmp_path: Path, cuerpo: str, cabecera: str = CABECERA) -> Path:
    ruta = tmp_path / "listado.csv"
    ruta.write_text(cabecera + cuerpo, encoding="utf-8")
    return ruta


def test_sin_datos_locales_configurados_no_importa_nada(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    csv = _csv(tmp_path, "AF023,Nombre Apellido\n")

    codigo = main(["--csv", str(csv)], raiz=raiz)

    assert codigo == 1
    assert "REVISOR_DATOS_LOCALES" in capsys.readouterr().out


def test_importa_cuando_hay_datos_locales_configurados(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    datos_locales = tmp_path / "datos_locales"
    datos_locales.mkdir()
    (raiz / ".env").write_text(
        f"REVISOR_DATOS_LOCALES={datos_locales}\n", encoding="utf-8"
    )
    csv = _csv(tmp_path, "AF023,Nombre Apellido\n")

    codigo = main(["--csv", str(csv)], raiz=raiz)

    assert codigo == 0
    salida = capsys.readouterr().out
    assert "1 altas incorporadas" in salida
    # El nombre no se imprime nunca, ni siquiera al confirmar el éxito.
    assert "Nombre Apellido" not in salida

    from backend.privacidad.listado_local import ListadoLocal
    assert ListadoLocal(datos_locales).nombre_de("AF023") == "Nombre Apellido"


def test_un_csv_inexistente_se_rechaza_con_claridad(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    datos_locales = tmp_path / "datos_locales"
    datos_locales.mkdir()
    (raiz / ".env").write_text(
        f"REVISOR_DATOS_LOCALES={datos_locales}\n", encoding="utf-8"
    )

    codigo = main(["--csv", str(tmp_path / "no-existe.csv")], raiz=raiz)

    assert codigo == 1
    assert "No se encuentra" in capsys.readouterr().out


def test_un_csv_mal_formado_se_rechaza(tmp_path: Path, capsys) -> None:
    raiz = _repositorio(tmp_path)
    datos_locales = tmp_path / "datos_locales"
    datos_locales.mkdir()
    (raiz / ".env").write_text(
        f"REVISOR_DATOS_LOCALES={datos_locales}\n", encoding="utf-8"
    )
    csv = _csv(tmp_path, "AF023,Nombre Apellido\n", cabecera="id,alumno\n")

    codigo = main(["--csv", str(csv)], raiz=raiz)

    assert codigo == 1
    assert "columnas" in capsys.readouterr().out
