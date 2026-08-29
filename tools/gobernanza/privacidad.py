"""R6: nada personal entra en el repositorio.

Es un cedazo, no una garantia. Atrapa el descuido tipico -arrastrar una
entrega, pegar una ficha con datos- y no pretende sustituir el criterio de
quien commitea.
"""

import re
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

EXTENSIONES_PROHIBIDAS = {
    ".pdf", ".doc", ".docx", ".odt", ".rtf", ".pptx", ".xls", ".xlsx", ".ods",
}

CARPETAS_IGNORADAS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "dist",
    # Scratch git-ignored de las herramientas de trabajo: no forma parte del
    # repositorio versionado y contiene copias de planes con ejemplos.
    ".superpowers",
    # Arboles de trabajo aislados de los agentes. Son copias enteras del repo,
    # así que sin esto cada fichero del proyecto se inspecciona una vez por
    # copia y los ejemplos sinteticos de tests/gobernanza/ se denuncian a si
    # mismos desde una ruta que no coincide con su excepcion.
    ".claude",
}

# Solo se inspecciona el contenido de texto plano.
EXTENSIONES_DE_TEXTO = {
    ".md", ".yaml", ".yml", ".json", ".py", ".txt", ".ts", ".tsx", ".sql",
    ".csv", ".tsv",
}

# El DNI espanol lleva 8 digitos y una letra de control; se exige limite de
# palabra a ambos lados para no capturar hashes ni identificadores largos.
# Admite un guion opcional antes de la letra y la letra en minuscula, que son
# formas habituales de escribirlo a mano. El rango de letras excluye I, Ñ, O
# y U, que el algoritmo del DNI no usa.
PATRON_DNI = re.compile(r"\b\d{8}-?[A-HJ-NP-TV-Za-hj-np-tv-z]\b")
PATRON_CORREO = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
# Movil o fijo espanol: empieza por 6, 7, 8 o 9 y tiene nueve digitos, con
# prefijo internacional +34 opcional. Los limites excluyen también letras y
# guion bajo (no solo digitos y guion), para que una secuencia de nueve
# digitos embebida en un hash hexadecimal -que tiene letras alrededor- no
# dispare el patron. Solo se reconocen las agrupaciones reales con las que
# se escribe un telefono espanol: nueve digitos seguidos, 3-3-3 (612 345
# 678) o 3-2-2-2 (612 34 56 78); un separador suelto en cualquier otra
# posicion -como en "612-345678", que es un 3-6- no forma un telefono.
PATRON_TELEFONO = re.compile(
    r"(?<![\w-])(?:\+34[ -]?)?"
    r"(?:[6789]\d{8}"
    r"|[6789]\d{2}[ -]\d{3}[ -]\d{3}"
    r"|[6789]\d{2}[ -]\d{2}[ -]\d{2}[ -]\d{2})"
    r"(?![\w-])"
)

# Ficheros y arboles que hablan de estos patrones sin contener datos reales:
# el propio verificador, sus tests, y los planes y specs, que incluyen
# ejemplos de DNI y correo precisamente para explicar que se detecta.
EXENTOS = {
    "tools/gobernanza/privacidad.py",
    "tests/gobernanza/test_privacidad.py",
    # Comprueba que la CLI agrega la infraccion R6, y para ello necesita un
    # DNI de ejemplo en su cuerpo.
    "tests/gobernanza/test_cli.py",
}
PREFIJOS_EXENTOS = ("docs/superpowers/",)


def _esta_exento(relativa: str) -> bool:
    return relativa in EXENTOS or relativa.startswith(PREFIJOS_EXENTOS)


def _candidatos(raiz: Path) -> list[str]:
    """Todos los ficheros del arbol, ignorando carpetas de trabajo."""
    encontrados: list[str] = []
    for ruta in raiz.rglob("*"):
        if not ruta.is_file():
            continue
        if any(parte in CARPETAS_IGNORADAS for parte in ruta.parts):
            continue
        encontrados.append(ruta.relative_to(raiz).as_posix())
    return sorted(encontrados)


def verificar_r6(raiz: Path, ficheros: list[str]) -> list[Infraccion]:
    """Busca documentos ofimaticos y datos identificativos en los ficheros dados."""
    objetivos = [f.replace("\\", "/") for f in ficheros] or _candidatos(raiz)
    infracciones: list[Infraccion] = []

    for relativa in objetivos:
        if _esta_exento(relativa):
            continue
        ruta = raiz / relativa
        if not ruta.is_file():
            continue

        sufijo = ruta.suffix.lower()

        if sufijo in EXTENSIONES_PROHIBIDAS:
            infracciones.append(Infraccion(
                regla="R6",
                fichero=relativa,
                detalle=(
                    f"Documento ofimático en el repositorio. Las entregas de "
                    f"alumnos no se versionan. Sácalo del repositorio y, si "
                    f"llegó a commitearse, limpia el historial."
                ),
            ))
            continue

        if sufijo not in EXTENSIONES_DE_TEXTO:
            continue

        try:
            texto = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for patron, etiqueta in (
            (PATRON_DNI, "un DNI"),
            (PATRON_CORREO, "un correo electrónico"),
            (PATRON_TELEFONO, "un teléfono"),
        ):
            # Se usa .search(), no .finditer(): basta una senal por tipo para
            # bloquear el commit, no hace falta enumerar todas las apariciones.
            encontrado = patron.search(texto)
            if encontrado:
                linea = texto[:encontrado.start()].count("\n") + 1
                infracciones.append(Infraccion(
                    regla="R6",
                    fichero=relativa,
                    detalle=(
                        f"Línea {linea}: parece {etiqueta}. El sistema trabaja "
                        f"con códigos anónimos de alumno. Si es un dato real, "
                        f"retíralo; si es un ejemplo, usa un código tipo AF023."
                    ),
                ))

    return infracciones
