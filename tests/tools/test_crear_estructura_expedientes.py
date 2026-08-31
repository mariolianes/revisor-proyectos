"""La CLI que crea la arquitectura de expedientes en el equipo del docente.

Por omisión, la CLI no escribe nada -solo enumera el plan-: cada prueba que
no pasa `--confirmo` comprueba precisamente eso, que el disco sigue vacío
después de ejecutarla.
"""

from pathlib import Path

from tools.crear_estructura_expedientes import main


def _con_raiz_expedientes(raiz: Path, expedientes: Path) -> None:
    (raiz / ".env").write_text(
        f"REVISOR_RAIZ_EXPEDIENTES={expedientes}\n", encoding="utf-8"
    )


def test_sin_raiz_configurada_no_hace_nada(
    raiz_con_estructura_expedientes: Path, capsys
) -> None:
    codigo = main(["--base"], raiz=raiz_con_estructura_expedientes)

    assert codigo == 1
    assert "REVISOR_RAIZ_EXPEDIENTES" in capsys.readouterr().out


def test_base_sin_confirmar_solo_enumera(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)

    codigo = main(["--base"], raiz=raiz_con_estructura_expedientes)

    assert codigo == 0
    salida = capsys.readouterr().out
    assert "Nada escrito todavía" in salida
    assert list(expedientes.iterdir()) == []


def test_base_confirmada_escribe(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)

    codigo = main(["--base", "--confirmo"], raiz=raiz_con_estructura_expedientes)

    assert codigo == 0
    assert (expedientes / "01_ENTRADA_TRABAJOS" / "AND_ANDALUCIA" / "E01" / "PENDIENTES").is_dir()
    assert "carpetas nuevas" in capsys.readouterr().out


def test_un_alumno_confirmado_crea_solo_su_expediente(
    raiz_con_estructura_expedientes: Path, tmp_path: Path
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)

    codigo = main(
        ["--alumno", "ALU-260087", "--confirmo"], raiz=raiz_con_estructura_expedientes
    )

    assert codigo == 0
    assert (expedientes / "02_EXPEDIENTES_ALUMNOS" / "ALU-260087" / "00_FICHA").is_dir()
    # Sin --base, la estructura fija no se ha tocado.
    assert not (expedientes / "01_ENTRADA_TRABAJOS").exists()


def test_un_id_de_alumno_invalido_se_rechaza(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)

    codigo = main(["--alumno", "trabajo de juan"], raiz=raiz_con_estructura_expedientes)

    assert codigo == 1
    assert list(expedientes.iterdir()) == []


def test_un_csv_de_alumnos_sin_confirmar_no_escribe(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)
    csv = tmp_path / "alumnos.csv"
    csv.write_text("id\nALU-260001\nALU-260002\n", encoding="utf-8")

    codigo = main(["--alumnos-csv", str(csv)], raiz=raiz_con_estructura_expedientes)

    assert codigo == 0
    assert "2 IDs leídos" in capsys.readouterr().out
    assert list((expedientes).glob("**/ALU-*")) == []


def test_un_csv_de_alumnos_confirmado_crea_cada_uno(
    raiz_con_estructura_expedientes: Path, tmp_path: Path
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)
    csv = tmp_path / "alumnos.csv"
    csv.write_text("id\nALU-260001\nALU-260002\n", encoding="utf-8")

    codigo = main(
        ["--alumnos-csv", str(csv), "--confirmo"], raiz=raiz_con_estructura_expedientes
    )

    assert codigo == 0
    carpeta = expedientes / "02_EXPEDIENTES_ALUMNOS"
    assert sorted(p.name for p in carpeta.iterdir()) == ["ALU-260001", "ALU-260002"]


def test_un_csv_sin_columna_id_se_rechaza(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)
    csv = tmp_path / "alumnos.csv"
    csv.write_text("codigo\nALU-260001\n", encoding="utf-8")

    codigo = main(["--alumnos-csv", str(csv)], raiz=raiz_con_estructura_expedientes)

    assert codigo == 1
    assert "columna" in capsys.readouterr().out


def test_un_csv_grande_sin_confirmar_no_falla_al_solo_enumerar(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    """Enumerar un lote grande no exige --confirmo: el aviso de lote
    demasiado grande solo aparece al intentar escribir de verdad."""
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)
    csv = tmp_path / "alumnos.csv"
    filas = "\n".join(f"ALU-26{n:04d}" for n in range(30))
    csv.write_text(f"id\n{filas}\n", encoding="utf-8")

    codigo = main(["--alumnos-csv", str(csv)], raiz=raiz_con_estructura_expedientes)

    assert codigo == 0
    assert "30 IDs leídos" in capsys.readouterr().out


def test_un_csv_grande_confirmado_crea_todos_los_expedientes(
    raiz_con_estructura_expedientes: Path, tmp_path: Path, capsys
) -> None:
    """--confirmo en la línea de órdenes ya es la autorización explícita del
    docente: un lote por encima del umbral interno de
    `crear_expedientes_en_lote` (ver `tests/expedientes/test_creacion.py`
    para esa guarda probada por su cuenta, llamando a la función
    directamente) se crea igualmente, porque la CLI ya mostró el plan y el
    docente ya lo confirmó."""
    expedientes = tmp_path / "CESUR_2026-2027"
    expedientes.mkdir()
    _con_raiz_expedientes(raiz_con_estructura_expedientes, expedientes)
    csv = tmp_path / "alumnos.csv"
    filas = "\n".join(f"ALU-26{n:04d}" for n in range(30))
    csv.write_text(f"id\n{filas}\n", encoding="utf-8")

    codigo = main(
        ["--alumnos-csv", str(csv), "--confirmo"], raiz=raiz_con_estructura_expedientes
    )

    assert codigo == 0
    carpeta = expedientes / "02_EXPEDIENTES_ALUMNOS"
    assert len(list(carpeta.iterdir())) == 30
