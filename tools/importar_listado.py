"""Importa el listado de un curso: la correspondencia nombre-código.

Se invoca a mano, una vez por curso o cuando cambia la matrícula::

    python tools/importar_listado.py --csv <ruta-al-listado.csv>

El CSV lo prepara el docente, con dos columnas: `codigo,nombre`. El código es
el mismo que ya usa el resto del sistema -el que llevan los nombres de
archivo, por ejemplo `AF023`-, no uno nuevo: ver el docstring de
`backend.privacidad.listado_local` para por qué.

No hace falta abrir el backend para esto: es una operación de una vez,
sobre un fichero que vive en el equipo del docente, y montar un endpoint de
API para ella habría abierto una vía de red -por pequeña que fuera- hacia
un fichero que existe precisamente para no salir del equipo.

La salida por consola dice cuántas filas se han incorporado, nunca cuáles:
imprimir un nombre en una terminal no es peor que tenerlo en el CSV de
origen, pero tampoco hace falta, y "cero avisos innecesarios" es más fácil
de razonar que "avisos que nunca incluyen un nombre".
"""

import argparse
from pathlib import Path


def _configurar_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa la correspondencia nombre-código de un listado de curso."
    )
    parser.add_argument(
        "--csv", type=Path, required=True,
        help="Ruta al CSV del listado, con columnas `codigo` y `nombre`.",
    )
    return parser


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    """0 importado; 1 no se ha podido -falta configuración, CSV inválido-;
    2 fallo inesperado."""
    try:
        return _resolver(argv, raiz)
    except Exception as fallo:  # noqa: BLE001 - se traduce a código 2 a propósito
        print("No se ha podido importar el listado.")
        print(f"Motivo: {type(fallo).__name__}: {fallo}")
        return 2


def _resolver(argv: list[str] | None, raiz: Path | None) -> int:
    if raiz is None:
        raiz = Path(__file__).resolve().parents[1]
    args = _configurar_argumentos().parse_args(argv)

    if not args.csv.is_file():
        print(f"No se encuentra el fichero «{args.csv}».")
        return 1

    from backend.configuracion import cargar
    from backend.privacidad.listado_local import ListadoLocal, ListadoMalFormado

    configuracion = cargar(raiz)
    if configuracion.datos_locales is None:
        if configuracion.problema_datos_locales:
            print(configuracion.problema_datos_locales)
        else:
            print(
                "No hay carpeta de datos locales configurada. Indícala en "
                "REVISOR_DATOS_LOCALES, en el fichero .env, y tiene que "
                "estar fuera de este repositorio -igual que "
                "REVISOR_CARPETA_ENTREGAS-."
            )
        return 1

    listado = ListadoLocal(configuracion.datos_locales)
    try:
        incorporadas = listado.importar_csv(args.csv)
    except ListadoMalFormado as fallo:
        print(str(fallo))
        return 1

    print(f"{incorporadas} altas incorporadas al listado local.")
    print(f"Guardado en «{configuracion.datos_locales}», fuera del repositorio.")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada de CLI
    raise SystemExit(main())
