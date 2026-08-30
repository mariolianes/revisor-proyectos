"""La correspondencia entre el nombre real de un alumno y su código.

El profesor lo pidió así, literalmente: «asignar un ID numérico a cada
alumno y mantener la correspondencia entre nombre e ID únicamente en el
equipo local». El sistema ya tiene ese ID: `codigo_alumno` (por ejemplo
`AF023`) es exactamente eso -un código estable, no personal, asignado antes
de que el trabajo llegue al sistema-, y ya es lo único que viaja por
Supabase, por la API y por cualquier informe (`backend/persistencia/
modelos.py`, y el propio esquema de Supabase lo dice en su comentario: «Aquí
NO se guardan nombres, DNI, correos ni teléfonos»). Crear un segundo
identificador numérico en paralelo fragmentaría ese modelo sin necesidad:
el nombre de archivo, la ficha de la entrega, la tabla `alumno` de Supabase
y este listado tendrían que ponerse de acuerdo sobre dos códigos distintos
para la misma persona. Este módulo reutiliza `codigo_alumno` como el ID que
pide el profesor, y solo añade lo que faltaba: dónde vive la correspondencia
con el nombre, y que viva SOLO aquí.

Este listado no se guarda en Supabase, no lo lee ninguna API pensada para
salir del equipo, y no lo toca R6: R6 (`tools/gobernanza/privacidad.py`)
impide que un DNI, un correo o un teléfono entren en el repositorio, pero un
nombre suelto no tiene un patrón reconocible que R6 pueda buscar sin
inundarse de falsos positivos -no hay forma de distinguir por regex «Ana
García» de dos palabras cualquiera-. La protección real no es que R6 lo
detecte si se cuela: es que este fichero vive fuera del repositorio por
construcción, en la misma carpeta de datos locales que exige
`REVISOR_DATOS_LOCALES` (`backend/configuracion.py`), con la misma
comprobación de que esa ruta no está dentro del árbol versionado que ya
protege `REVISOR_CARPETA_ENTREGAS`.

El fichero es JSON plano, sin cifrar: es el mismo nivel de protección que ya
tienen los PDFs originales de los alumnos, que llevan meses viviendo sin
cifrar en la carpeta de entregas de este mismo equipo. Cifrar solo la
correspondencia nombre-código y no los PDFs de los que sale esa
correspondencia habría sido una protección de cristal, cara de mantener y
fácil de rodear.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

COLUMNA_CODIGO = "codigo"
COLUMNA_NOMBRE = "nombre"

NOMBRE_DEL_FICHERO = "listado_alumnado.json"


class ListadoMalFormado(ValueError):
    """El CSV que se intenta importar no trae lo que hace falta."""


def _normalizar_codigo(codigo: str) -> str:
    return "".join(codigo.split()).upper()


class ListadoLocal:
    """La correspondencia código -> nombre, en un fichero JSON local.

    No cachea nada en memoria entre llamadas: cada `nombre_de` relee el
    fichero. La correspondencia se actualiza importando un CSV nuevo -una
    vez al curso, o cuando cambia la matrícula-, nunca en el camino
    caliente de un análisis, así que el coste de releer un fichero pequeño
    en cada consulta no importa, y evita el error de clase «el proceso
    lleva abierto tres días y el listado que ve es el de hace tres días»
    tras una reimportación.
    """

    def __init__(self, carpeta: Path) -> None:
        self._fichero = carpeta / NOMBRE_DEL_FICHERO

    def _leer(self) -> dict[str, str]:
        if not self._fichero.is_file():
            return {}
        try:
            datos = json.loads(self._fichero.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Un listado corrupto no debe tumbar un análisis: se trata como
            # si no hubiera listado. `minimizacion.py` ya sabe decir que no
            # conoce el nombre de un alumno; es la misma situación.
            return {}
        return datos if isinstance(datos, dict) else {}

    def _escribir(self, datos: dict[str, str]) -> None:
        self._fichero.parent.mkdir(parents=True, exist_ok=True)
        self._fichero.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def nombre_de(self, codigo: str) -> str | None:
        """El nombre del alumno con ese código, o `None` si no está en el
        listado -el código no se ha importado todavía, o no tiene nombre
        asociado-.
        """
        return self._leer().get(_normalizar_codigo(codigo)) or None

    def importar_csv(self, ruta_csv: Path) -> int:
        """Añade o actualiza altas desde un CSV con columnas `codigo` y
        `nombre`. Devuelve cuántas filas se han incorporado.

        Actualiza, no sustituye: importar un curso nuevo no borra el de
        cursos anteriores, porque una entrega de un alumno de un curso
        anterior puede seguir necesitando su nombre para minimizarla si se
        reanaliza. Una fila con el mismo código que ya había sobrescribe su
        nombre -para corregir una errata de matrícula, por ejemplo-, no
        añade una segunda entrada.
        """
        with ruta_csv.open(encoding="utf-8-sig", newline="") as fichero:
            lector = csv.DictReader(fichero)
            cabecera = lector.fieldnames or []
            if COLUMNA_CODIGO not in cabecera or COLUMNA_NOMBRE not in cabecera:
                raise ListadoMalFormado(
                    f"El listado tiene que traer las columnas «{COLUMNA_CODIGO}» "
                    f"y «{COLUMNA_NOMBRE}». Cabecera encontrada: "
                    + (", ".join(cabecera) if cabecera else "(vacía)") + "."
                )
            filas = list(lector)

        datos = self._leer()
        incorporadas = 0
        for fila in filas:
            codigo = _normalizar_codigo(fila.get(COLUMNA_CODIGO) or "")
            nombre = (fila.get(COLUMNA_NOMBRE) or "").strip()
            if not codigo or not nombre:
                continue
            datos[codigo] = nombre
            incorporadas += 1

        self._escribir(datos)
        return incorporadas
