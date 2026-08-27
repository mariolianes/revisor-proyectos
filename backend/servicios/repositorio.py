"""Lectura del árbol de documentos normativos.

Solo lee. Cualquier escritura pasa por servicios/transaccion.py.
"""

import re
from pathlib import Path

from backend.modelos import Documento, Seccion
from tools.gobernanza.criterios import PATRON_ANCLA
from tools.gobernanza.sincronia import _DOCUMENTOS, hash_de_seccion

# Las tres claves válidas y su fichero. Es una lista cerrada a propósito:
# ninguna ruta que venga del cliente se usa para construir un Path.
#
# La lista no se copia: es la misma que usa R2 en tools/gobernanza/sincronia.py
# para saber qué documentos existen. Tenerla escrita dos veces significaba dos
# dueños de la misma lista blanca, y que añadir un documento allí dejara al
# editor sin verlo -o al revés-. El nombre allí es privado y aquí solo se lee;
# esa capa está cerrada y no se toca desde el editor.
DOCUMENTOS = _DOCUMENTOS

PATRON_ENCABEZADO = re.compile(r"^#{2,3}\s+(.+)$", re.M)


def ruta_de_documento(raiz: Path, documento: str) -> Path | None:
    """Ruta del fichero de un documento, o None si la clave no es válida."""
    nombre = DOCUMENTOS.get(documento)
    if nombre is None:
        return None
    ruta = raiz / "docs" / "maestro" / nombre
    return ruta if ruta.is_file() else None


def _titulo_de(texto: str) -> str:
    """Primer encabezado de nivel 1, o cadena vacía."""
    for linea in texto.splitlines():
        if linea.startswith("# "):
            return linea[2:].strip()
    return ""


def _trocear(texto: str) -> list[tuple[str, str, str]]:
    """Devuelve (ancla, titulo, cuerpo) por cada sección anclada del documento."""
    marcas = list(PATRON_ANCLA.finditer(texto))
    troceado = []
    for indice, marca in enumerate(marcas):
        inicio = marca.end()
        fin = marcas[indice + 1].start() if indice + 1 < len(marcas) else len(texto)
        cuerpo = texto[inicio:fin].strip("\n")
        encabezado = PATRON_ENCABEZADO.search(cuerpo)
        titulo = encabezado.group(1).strip() if encabezado else marca.group(1)
        troceado.append((marca.group(1), titulo, cuerpo))
    return troceado


def listar_documentos(raiz: Path) -> list[Documento]:
    """Los documentos presentes, con sus secciones en el orden del fichero."""
    # Import diferido a propósito: si fuera de cabecera, este módulo y
    # dependencias.py se acoplarían al cargar. dependencias.py no debe
    # importar repositorio.py a nivel de módulo; así se queda esa relación
    # en un solo sentido.
    from backend.servicios.dependencias import contar_por_ancla

    conteo = contar_por_ancla(raiz)
    documentos = []
    for clave, nombre in DOCUMENTOS.items():
        ruta = raiz / "docs" / "maestro" / nombre
        if not ruta.is_file():
            continue
        texto = ruta.read_text(encoding="utf-8")
        secciones = [
            Seccion(
                ancla=ancla,
                titulo=titulo,
                texto=cuerpo,
                hash=hash_de_seccion(raiz, ancla) or "",
                criterios_que_la_citan=conteo.get(ancla, 0),
            )
            for ancla, titulo, cuerpo in _trocear(texto)
        ]
        documentos.append(Documento(
            clave=clave,
            titulo=_titulo_de(texto),
            fichero=f"docs/maestro/{nombre}",
            secciones=secciones,
        ))
    return documentos


def leer_seccion(raiz: Path, ancla: str) -> Seccion | None:
    """Una sección concreta por su ancla, o None si no existe."""
    for documento in listar_documentos(raiz):
        for seccion in documento.secciones:
            if seccion.ancla == ancla:
                return seccion
    return None
