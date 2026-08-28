"""R1: ningun criterio sin origen. R3: lo pendiente se marca, no se inventa."""

import re
from pathlib import Path

import yaml

from tools.gobernanza.resultado import Infraccion

PATRON_ANCLA = re.compile(
    r"^<!-- ancla: ((?:maestro|indice|guia|calibracion)#[a-z0-9-]+) -->$", re.M
)
PATRON_FUENTE = re.compile(r"^(?:maestro|indice|guia|calibracion)#[a-z0-9-]+$")


def cargar_anclas(raiz: Path) -> set[str]:
    """Devuelve todas las anclas declaradas en los documentos maestros."""
    anclas: set[str] = set()
    carpeta = raiz / "docs" / "maestro"
    if not carpeta.is_dir():
        return anclas
    for ruta in sorted(carpeta.glob("*.md")):
        texto = ruta.read_text(encoding="utf-8")
        anclas.update(m.group(1) for m in PATRON_ANCLA.finditer(texto))
    return anclas


def entradas_de(ruta_yaml: Path) -> list[dict]:
    """Aplana un YAML de criterios a la lista de sus entradas con criterio.

    Un fichero de criterios puede ser una lista de entradas o un mapa cuyos
    valores son entradas. Se considera entrada todo diccionario que declare
    'fuente' o 'codigo': son los que R1 debe examinar.
    """
    datos = yaml.safe_load(ruta_yaml.read_text(encoding="utf-8"))
    entradas: list[dict] = []

    def recorrer(nodo, clave_padre: str | None) -> None:
        if isinstance(nodo, dict):
            if "fuente" in nodo or "codigo" in nodo:
                entrada = dict(nodo)
                entrada.setdefault("_clave", clave_padre)
                entradas.append(entrada)
                return
            for clave, valor in nodo.items():
                recorrer(valor, clave)
        elif isinstance(nodo, list):
            for elemento in nodo:
                recorrer(elemento, clave_padre)

    recorrer(datos, None)
    return entradas


def bloques_raiz(ruta_yaml: Path) -> list[tuple[str, object]]:
    """Hijos directos de la raiz del YAML, con el nombre por el que citarlos.

    Si la raiz es una lista, cada elemento es un bloque y se nombra por su
    'codigo' o por su posicion. Si es un mapa, cada par clave/valor lo es y se
    nombra por la clave. No se desciende mas: esta funcion existe para poder
    exigir 'fuente' en el primer nivel, que es donde R1 se quedaba ciega.
    """
    datos = yaml.safe_load(ruta_yaml.read_text(encoding="utf-8"))

    if isinstance(datos, list):
        bloques: list[tuple[str, object]] = []
        for posicion, elemento in enumerate(datos, start=1):
            nombre = None
            if isinstance(elemento, dict):
                nombre = elemento.get("codigo")
            bloques.append((str(nombre or f"elemento {posicion}"), elemento))
        return bloques

    if isinstance(datos, dict):
        return [(str(clave), valor) for clave, valor in datos.items()]

    return []


def _identificar(entrada: dict) -> str:
    """Nombre con el que referirse a una entrada en el mensaje de error."""
    return str(entrada.get("codigo") or entrada.get("_clave") or "entrada sin codigo")


def _verificar_primer_nivel(ruta_yaml: Path, relativa: str) -> list[Infraccion]:
    """Exige 'fuente' en todo hijo directo de la raiz del fichero.

    'entradas_de' reconoce un criterio por llevar 'fuente' o 'codigo'. En los
    ficheros con forma de mapa -formato, calendario, ponderaciones,
    matriz-fases- ningun bloque lleva 'codigo', asi que lo unico que los hacia
    visibles para R1 era justamente el campo que R1 existe para exigir: un
    bloque sin 'fuente' no era un criterio incompleto, era un bloque invisible.

    Este invariante cierra ese hueco sin tocar 'entradas_de', de la que
    dependen otros modulos: todo hijo directo de la raiz -elemento de la lista
    o valor del mapa- declara de donde sale, y si no, se ve.
    """
    infracciones: list[Infraccion] = []
    for nombre, bloque in bloques_raiz(ruta_yaml):
        if isinstance(bloque, dict):
            if "fuente" in bloque:
                continue
            # Un bloque con 'codigo' ya lo recoge el recorrido de entradas,
            # con este mismo motivo: no se avisa dos veces de lo mismo.
            if "codigo" in bloque:
                continue
        infracciones.append(Infraccion(
            regla="R1",
            fichero=relativa,
            detalle=(
                f"El bloque '{nombre}' del primer nivel no declara de dónde "
                f"sale: sin campo 'fuente'. Todo bloque de un fichero de "
                f"criterios apunta a la sección de docs/maestro/ que lo "
                f"respalda; si no la tiene, no es un criterio."
            ),
        ))
    return infracciones


def verificar_r1(raiz: Path) -> list[Infraccion]:
    """Comprueba que todo criterio declara una fuente valida y existente."""
    anclas = cargar_anclas(raiz)
    infracciones: list[Infraccion] = []
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return infracciones

    for ruta in sorted(carpeta.rglob("*.yaml")):
        relativa = ruta.relative_to(raiz).as_posix()
        infracciones += _verificar_primer_nivel(ruta, relativa)
        for entrada in entradas_de(ruta):
            nombre = _identificar(entrada)
            fuente = entrada.get("fuente")

            if fuente is None:
                infracciones.append(Infraccion(
                    regla="R1",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' no declara de dónde sale: sin campo 'fuente'. "
                        f"Añade 'fuente: documento#ancla' apuntando a la sección "
                        f"de docs/maestro/ que lo respalda."
                    ),
                ))
                continue

            if not PATRON_FUENTE.match(str(fuente)):
                infracciones.append(Infraccion(
                    regla="R1",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' tiene una fuente con formato inválido: "
                        f"'{fuente}'. Se espera 'documento#ancla', donde documento "
                        f"es maestro, índice, guía o calibración."
                    ),
                ))
                continue

            if fuente not in anclas:
                infracciones.append(Infraccion(
                    regla="R1",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' apunta a '{fuente}', que no existe en "
                        f"docs/maestro/. O el ancla se ha renombrado, o el criterio "
                        f"no tiene respaldo en la prosa."
                    ),
                ))

    return infracciones


CLAVES_DE_VALOR_PROHIBIDAS = ("valor", "valores", "fechas", "porcentajes")


def _pendientes_documentados(raiz: Path) -> set[str]:
    """Claves listadas en docs/PENDIENTE_OFICIAL.md como '- **clave** —'."""
    ruta = raiz / "docs" / "PENDIENTE_OFICIAL.md"
    if not ruta.is_file():
        return set()
    texto = ruta.read_text(encoding="utf-8")
    return set(re.findall(r"^- \*\*([a-z0-9_]+)\*\* —", texto, re.M))


def verificar_r3(raiz: Path) -> list[Infraccion]:
    """Comprueba que lo pendiente esta marcado, acotado y documentado."""
    documentados = _pendientes_documentados(raiz)
    infracciones: list[Infraccion] = []
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return infracciones

    for ruta in sorted(carpeta.rglob("*.yaml")):
        relativa = ruta.relative_to(raiz).as_posix()
        for entrada in entradas_de(ruta):
            if entrada.get("estado") != "PENDIENTE_OFICIAL":
                continue

            nombre = _identificar(entrada)

            if "bloquea" not in entrada:
                infracciones.append(Infraccion(
                    regla="R3",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' está PENDIENTE_OFICIAL pero no declara "
                        f"'bloquea'. Indica qué juicios no pueden emitirse sin "
                        f"este dato, o '[]' si no bloquea ninguno."
                    ),
                ))

            inventados = [c for c in CLAVES_DE_VALOR_PROHIBIDAS if c in entrada]
            if inventados:
                infracciones.append(Infraccion(
                    regla="R3",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' está PENDIENTE_OFICIAL pero ya trae "
                        f"{inventados}. Un criterio pendiente no lleva valor: "
                        f"eso es inventarlo. Retira el valor o retira el estado."
                    ),
                ))

            if nombre not in documentados:
                infracciones.append(Infraccion(
                    regla="R3",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' está PENDIENTE_OFICIAL pero no aparece en "
                        f"docs/PENDIENTE_OFICIAL.md. Añádelo allí con la forma "
                        f"'- **{nombre}** — qué falta y de quién se espera.'"
                    ),
                ))

    return infracciones
