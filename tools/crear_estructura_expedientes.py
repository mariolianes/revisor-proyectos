"""Crea, en el equipo del docente, la arquitectura de expedientes descrita en
`config/estructura_expedientes.yaml`.

Se invoca a mano::

    python tools/crear_estructura_expedientes.py --base
    python tools/crear_estructura_expedientes.py --alumno ALU-260087
    python tools/crear_estructura_expedientes.py --alumnos-csv listado.csv

Por omisión, este comando **no escribe nada**: cuenta y enumera las carpetas
que crearía, y se detiene ahí. Hace falta `--confirmo` para que escriba de
verdad. No es una cautela decorativa: `--base` y `--alumnos-csv` pueden
suponer varios cientos de carpetas de golpe, y un acierto de más -una ruta
mal escrita en REVISOR_RAIZ_EXPEDIENTES, un CSV que en realidad era el del
curso pasado- no debe poder escribir nada hasta que alguien mire el plan y lo
confirme.

La raíz donde se escribe nunca la decide este comando: la fija
REVISOR_RAIZ_EXPEDIENTES, igual que REVISOR_CARPETA_ENTREGAS decide dónde
llegan las entregas. Tiene que existir y estar fuera del repositorio; si no,
`backend.configuracion.cargar` ya lo dice con detalle y este comando se
detiene antes de plantear nada.

El CSV de `--alumnos-csv` trae una columna `id`, con el ID de expediente de
cada alumno -`ALU-260087`, por ejemplo-, uno por fila. No es el mismo fichero
que importa `tools/importar_listado.py`: aquel trae nombre y código para el
listado local que vive fuera del repositorio; este solo trae IDs, y no debe
llevar ningún nombre.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _configurar_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Crea la arquitectura de expedientes del docente. Por omisión "
            "solo enumera lo que crearía; hace falta --confirmo para "
            "escribir de verdad."
        )
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--base", action="store_true",
        help="Crea la estructura fija del curso: las ocho carpetas de primer "
             "nivel y la bandeja de entrada de cada comunidad y fase.",
    )
    grupo.add_argument(
        "--alumno", metavar="ID",
        help="Crea el expediente de un único alumno, por ejemplo ALU-260087.",
    )
    grupo.add_argument(
        "--alumnos-csv", type=Path, metavar="RUTA",
        help="Crea el expediente de cada alumno de un CSV con una columna «id».",
    )
    parser.add_argument(
        "--confirmo", action="store_true",
        help="Escribe de verdad. Sin esto, el comando solo enumera el plan.",
    )
    return parser


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    """0 hecho (o plan mostrado sin --confirmo); 1 no se ha podido -falta
    configuración, entrada inválida-; 2 fallo inesperado."""
    try:
        return _resolver(argv, raiz)
    except Exception as fallo:  # noqa: BLE001 - se traduce a código 2 a propósito
        print("No se ha podido crear la estructura de expedientes.")
        print(f"Motivo: {type(fallo).__name__}: {fallo}")
        return 2


def _leer_ids_del_csv(ruta_csv: Path) -> list[str]:
    with ruta_csv.open(encoding="utf-8-sig", newline="") as fichero:
        lector = csv.DictReader(fichero)
        if "id" not in (lector.fieldnames or []):
            raise ValueError(
                f"«{ruta_csv}» tiene que traer una columna «id». Cabecera "
                f"encontrada: {', '.join(lector.fieldnames or []) or '(vacía)'}."
            )
        return [fila["id"].strip() for fila in lector if (fila.get("id") or "").strip()]


def _resolver(argv: list[str] | None, raiz: Path | None) -> int:
    if raiz is None:
        raiz = Path(__file__).resolve().parents[1]
    args = _configurar_argumentos().parse_args(argv)

    from backend.configuracion import cargar
    from backend.expedientes.creacion import (
        LimiteDeSeguridadSuperado,
        LoteDemasiadoGrande,
        crear_expediente,
        crear_expedientes_en_lote,
        construir_estructura_base,
        planificar_estructura_base,
        planificar_expediente,
    )
    from backend.expedientes.estructura import EstructuraInvalida, cargar_estructura

    configuracion = cargar(raiz)
    if configuracion.raiz_expedientes is None:
        if configuracion.problema_raiz_expedientes:
            print(configuracion.problema_raiz_expedientes)
        else:
            print(
                "No hay raíz de expedientes configurada. Indícala en "
                "REVISOR_RAIZ_EXPEDIENTES, en el entorno o en el fichero "
                ".env, apuntando a una carpeta que exista fuera de este "
                "repositorio."
            )
        return 1

    try:
        cfg = cargar_estructura(raiz)
    except EstructuraInvalida as fallo:
        print(str(fallo))
        return 1

    if args.base:
        plan = planificar_estructura_base(cfg)
        print(f"Se crearían (o ya existen) {len(plan)} carpetas de la estructura base.")
        if not args.confirmo:
            for relativa in plan[:10]:
                print(f"  - {relativa}")
            if len(plan) > 10:
                print(f"  ... y {len(plan) - 10} más.")
            print("Nada escrito todavía. Repite con --confirmo para crearlas.")
            return 0
        resultado = construir_estructura_base(raiz, configuracion.raiz_expedientes, cfg)

    elif args.alumno:
        try:
            plan = planificar_expediente(cfg, args.alumno)
        except ValueError as fallo:
            print(str(fallo))
            return 1
        print(f"Se crearían (o ya existen) {len(plan)} carpetas para «{args.alumno}».")
        if not args.confirmo:
            for relativa in plan:
                print(f"  - {relativa}")
            print("Nada escrito todavía. Repite con --confirmo para crearlas.")
            return 0
        resultado = crear_expediente(raiz, configuracion.raiz_expedientes, cfg, args.alumno)

    else:
        assert args.alumnos_csv is not None
        if not args.alumnos_csv.is_file():
            print(f"No se encuentra «{args.alumnos_csv}».")
            return 1
        try:
            ids = _leer_ids_del_csv(args.alumnos_csv)
        except ValueError as fallo:
            print(str(fallo))
            return 1
        print(f"{len(ids)} IDs leídos de «{args.alumnos_csv}».")
        if not args.confirmo:
            for id_alumno in ids[:10]:
                print(f"  - {id_alumno}")
            if len(ids) > 10:
                print(f"  ... y {len(ids) - 10} más.")
            print(
                "Nada escrito todavía. Repite con --confirmo para crear estos "
                "expedientes."
            )
            return 0
        try:
            resultado = crear_expedientes_en_lote(
                raiz, configuracion.raiz_expedientes, cfg, ids, confirmar=True,
            )
        except (LoteDemasiadoGrande, LimiteDeSeguridadSuperado, ValueError) as fallo:
            print(str(fallo))
            return 1

    print(f"{len(resultado.creadas)} carpetas nuevas, {len(resultado.ya_existian)} ya existían.")
    print(f"Raíz: «{configuracion.raiz_expedientes}».")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada de CLI
    raise SystemExit(main())
