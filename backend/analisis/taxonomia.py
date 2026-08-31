"""La taxonomía de incidencias del §13 del calibrador.

El docente, 2026-08-31: «la comparación debería realizarse mediante una
taxonomía estable de incidencias [...] El sistema y la referencia humana
coinciden cuando detectan la misma categoría con una severidad equivalente
y evidencias compatibles, aunque la redacción sea diferente». Este módulo
carga esa taxonomía -`criteria/<version>/taxonomia-incidencias.yaml`, nunca
una constante de este fichero: es un criterio del docente, y su sitio es
`criteria/`, con su `fuente` (R1) apuntando al §13 del calibrador- y resuelve
la única pregunta que de verdad hacía falta decidir: de dónde sale la
categoría de cada observación.

**De la dimensión valorada, no del motor.** Ver el docstring del propio
fichero YAML para el razonamiento completo; en resumen: pedirle la
categoría al motor añadiría una afirmación más del motor sin manera de
comprobarla, y encima la usaríamos para medir al propio motor -la fuente
que se quiere auditar no puede ser también el árbitro-. La dimensión
(`Valoracion.dimension`, una de las doce que valida
`backend.analisis.contrato`) ya es un dato que pasa por el esquema
estricto del proveedor, y la correspondencia dimensión-categoría vive en un
fichero que el docente puede auditar y corregir, no en una decisión nueva
del motor en cada llamada.

El precio es la granularidad: una dimensión no siempre implica una única
categoría (D07 puede ser DEV-INSUF, APL-FALTA o TEO-EXCESO), así que
`categorias_de_dimension` devuelve una lista, nunca un código suelto.
`tools/calibrar.py` compara contra esa lista, no contra un valor único: es
una medida más gruesa que "acierto exacto", y se dice así donde se usa.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

FICHERO = "taxonomia-incidencias.yaml"


class CategoriaDeIncidencia(BaseModel):
    """Una entrada de la taxonomía del §13: su código, su nombre, la fuente
    que la respalda (R1) y las dimensiones del §8 de las que puede salir.

    `dimensiones` vacía es válida -no toda categoría tiene por qué listar
    dimensiones si el docente amplía el fichero-, y una dimensión ausente de
    todas las listas también lo es: son las cuatro que la taxonomía no
    cubre (ver el docstring del YAML). Ninguna de las dos cosas es un
    error de configuración.
    """

    model_config = ConfigDict(extra="forbid")

    codigo: str
    nombre: str
    fuente: str
    dimensiones: list[str] = []


def _fichero_taxonomia(raiz: Path, version: str) -> Path:
    return raiz / "criteria" / version / FICHERO


def cargar_taxonomia(raiz: Path, version: str) -> list[CategoriaDeIncidencia]:
    """Las categorías declaradas para `version`, o `[]` si el fichero no
    existe -una versión de criterios que todavía no tiene taxonomía propia
    no debe reventar la calibración, solo dejarla sin este dato-.
    """
    import yaml

    fichero = _fichero_taxonomia(raiz, version)
    if not fichero.is_file():
        return []
    bruto = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    return [CategoriaDeIncidencia(**entrada) for entrada in bruto]


def codigos_validos(raiz: Path, version: str) -> set[str]:
    """Los códigos que existen de verdad en la taxonomía cargada.

    Sirve para que quien declare un caso de calibración con un código que
    no está en `criteria/<version>/taxonomia-incidencias.yaml` lo sepa por
    un error claro, no por una comparación que en silencio nunca coincide.
    """
    return {c.codigo for c in cargar_taxonomia(raiz, version)}


def categorias_de_dimension(raiz: Path, version: str, dimension: str) -> list[str]:
    """Los códigos de incidencia plausibles para una dimensión del §8.

    Vacía cuando la dimensión no aparece en ninguna categoría -D01, D02,
    D06 y D12 hoy, ver el docstring del YAML-: no es que la dimensión no
    tenga categoría "todavía", es que la taxonomía del docente no la cubre,
    y una lista vacía lo dice sin inventar una categoría que nadie declaró.
    """
    return [
        categoria.codigo
        for categoria in cargar_taxonomia(raiz, version)
        if dimension in categoria.dimensiones
    ]
