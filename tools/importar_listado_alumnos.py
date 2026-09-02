"""Importa el listado de alumnos de una comunidad: un Excel al registro
maestro y a la correspondencia local nombre-student_id.

Se invoca a mano, una vez por comunidad al principio del curso, o cuando
llega un listado corregido::

    python tools/importar_listado_alumnos.py --excel <ruta.xlsx> --ccaa AND --curso 2026-2027

Marcos guardará un Excel por comunidad dentro de `00_LISTADOS_ALUMNOS`, y esos
Excel «pueden proceder directamente de CESUR y no tienen que conservar la
misma estructura entre comunidades»: por eso `--ccaa` y `--curso` son
parámetros explícitos y no algo que esta herramienta adivine del nombre del
fichero o de una columna. Adivinarlo de un nombre de fichero como
«Andalucia_definitivo_v2.xlsx» es exactamente la clase de suposición que este
sistema evita en cualquier otro sitio: es un dato que Marcos ya sabe al
ejecutar el comando, así que lo escribe él, con el mismo dedo con el que
escribe la ruta del fichero.

El mapeo de columnas -qué columna del Excel es el centro, cuál es el ciclo,
cuál es el nombre- sí es automático: `backend/servicios/importacion_alumnos.py`
reconoce varios nombres de columna habituales por alias. Una fila que no se
pueda registrar con seguridad -sin centro, con un centro que no está en el
catálogo, con un nombre que coincide con otro y no hay ID de CESUR con el que
distinguirlos- no se registra: queda pendiente de revisión, y esta CLI la
lista al terminar. Ningún nombre se imprime nunca, ni siquiera al listar una
fila pendiente: se identifica por su número de fila en el Excel, que Marcos
puede localizar sin que el nombre tenga que pasar por esta terminal.

Como `tools/importar_listado.py`, no hace falta abrir el backend para esto:
es una operación de mantenimiento sobre ficheros que viven en el equipo del
docente, no una vía de red hacia un dato que existe precisamente para no
salir del equipo.
"""

import argparse
from pathlib import Path


def _configurar_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa el listado de alumnos de una comunidad, desde un Excel."
    )
    parser.add_argument(
        "--excel", type=Path, required=True,
        help="Ruta al Excel del listado de esa comunidad.",
    )
    parser.add_argument(
        "--ccaa", required=True,
        help="Comunidad autónoma del listado: AND, MAD, CAN, MUR, ARA o EXT.",
    )
    parser.add_argument(
        "--curso", required=True,
        help="Curso académico del listado, por ejemplo 2026-2027.",
    )
    return parser


def _leer_excel(ruta: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Las filas de datos -como `{columna: valor}`- y la cabecera, de la
    primera hoja del Excel.

    Solo lee: ningún libro se modifica ni se reescribe. Una fila entera en
    blanco se descarta aquí -es habitual al final de un listado exportado-,
    para que `importar()` no tenga que distinguir «fila en blanco de
    verdad» de «fila con celdas vacías pero con algún valor perdido en
    medio»; el nombre en blanco de una fila que sí tiene algún otro dato
    sigue tratándose como «en blanco» más adelante, en
    `backend/servicios/importacion_alumnos.py`.
    """
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        hoja = libro.active
        iterador = hoja.iter_rows(values_only=True)
        primera = next(iterador, None)
        if primera is None:
            return [], []
        cabecera = [str(c).strip() if c is not None else "" for c in primera]

        filas: list[dict[str, str]] = []
        for fila in iterador:
            valores = {
                cabecera[indice]: (str(valor).strip() if valor is not None else "")
                for indice, valor in enumerate(fila)
                if indice < len(cabecera) and cabecera[indice]
            }
            if any(valores.values()):
                filas.append(valores)
        return filas, cabecera
    finally:
        libro.close()


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    """0 importado (con o sin filas pendientes de revisión); 1 no se ha
    podido -falta configuración, Excel inválido, comunidad o curso mal
    escritos-; 2 fallo inesperado."""
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

    if not args.excel.is_file():
        print(f"No se encuentra el fichero «{args.excel}».")
        return 1

    from backend.configuracion import cargar
    from backend.persistencia import crear_almacen
    from backend.persistencia.alumnos import CCAA_CODES, validar_curso
    from backend.privacidad.listado_local import ListadoLocal
    from backend.servicios.importacion_alumnos import (
        ColumnasNoMapeadas,
        cargar_centros_conocidos,
        importar,
    )

    ccaa_code = args.ccaa.strip().upper()
    if ccaa_code not in CCAA_CODES:
        print(
            f"«{args.ccaa}» no es una comunidad autónoma reconocida. Las "
            "comunidades son: " + ", ".join(CCAA_CODES) + "."
        )
        return 1

    try:
        validar_curso(args.curso)
    except ValueError as fallo:
        print(str(fallo))
        return 1

    configuracion = cargar(raiz)
    if configuracion.datos_locales is None:
        if configuracion.problema_datos_locales:
            print(configuracion.problema_datos_locales)
        else:
            print(
                "No hay carpeta de datos locales configurada. Indícala en "
                "REVISOR_DATOS_LOCALES, en el fichero .env: es donde vive la "
                "correspondencia nombre-student_id, y tiene que estar fuera "
                "de este repositorio -igual que REVISOR_CARPETA_ENTREGAS-."
            )
        return 1

    try:
        filas, cabecera = _leer_excel(args.excel)
    except Exception as fallo:
        print(f"No se ha podido leer «{args.excel}»: {fallo}")
        return 1

    if not filas:
        print(f"El Excel «{args.excel}» no tiene filas de datos. Nada que importar.")
        return 1

    almacen = crear_almacen(configuracion)
    listado_local = ListadoLocal(configuracion.datos_locales)
    centros_conocidos = cargar_centros_conocidos(raiz / "config" / "centros.yaml", ccaa_code)

    try:
        resultado = importar(
            filas, cabecera, ccaa_code=ccaa_code, curso=args.curso,
            almacen=almacen, listado_local=listado_local,
            centros_conocidos=centros_conocidos,
        )
    except ColumnasNoMapeadas as fallo:
        print(str(fallo))
        return 1

    _imprimir_resultado(resultado, ccaa_code, args.curso, almacen, configuracion.datos_locales)
    return 0


def _imprimir_resultado(resultado, ccaa_code: str, curso: str, almacen, datos_locales: Path) -> None:
    print(
        f"Listado de {ccaa_code} (curso {curso}): {resultado.total_filas} "
        f"filas leídas, {resultado.en_blanco} en blanco."
    )
    print(
        f"{resultado.nuevas + resultado.actualizadas} alumnos registrados "
        f"({resultado.nuevas} nuevos, {resultado.actualizadas} actualizados)."
    )
    if resultado.pendientes:
        print(f"{len(resultado.pendientes)} filas pendientes de revisión:")
        for pendiente in resultado.pendientes:
            print(f"  - {pendiente.detalle}")
    else:
        print("Ninguna fila pendiente de revisión.")
    if not almacen.es_duradero:
        print(
            "Aviso: no hay credenciales de Supabase configuradas, así que "
            "el registro maestro se ha guardado solo en memoria y se pierde "
            "al cerrar. Configura SUPABASE_URL y SUPABASE_SERVICE_KEY antes "
            "de importar un listado real."
        )
    print(f"Nombres guardados solo en «{datos_locales}», nunca en la base de datos.")


if __name__ == "__main__":  # pragma: no cover - punto de entrada de CLI
    raise SystemExit(main())
