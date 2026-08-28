"""De dónde salen los PDFs y con qué credenciales se guarda.

La carpeta de entregas vive FUERA del repositorio, y no es una
preferencia: la regla R6 impide que un PDF entre en el árbol versionado,
así que una carpeta interior dejaría el repositorio sin poder comitear en
cuanto llegase el primer trabajo. Por eso se comprueba aquí, al arrancar,
y no se descubre más tarde.
"""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

VERSION_CRITERIOS_POR_OMISION = "v2026-2027"

CARPETA = "REVISOR_CARPETA_ENTREGAS"
URL = "SUPABASE_URL"
CLAVE = "SUPABASE_SERVICE_KEY"
VERSION = "REVISOR_VERSION_CRITERIOS"


@dataclass(frozen=True)
class ProblemaDeCarpeta:
    """Por qué una ruta no sirve como carpeta de entregas."""

    motivo: str


class Configuracion(BaseModel):
    """Lo que el backend necesita saber antes de vigilar nada.

    `problema_carpeta` lleva el motivo por el que la ruta indicada no sirve,
    cuando se ha indicado una y no sirve. Es lo que distingue «no has puesto
    ninguna carpeta» de «la que has puesto no existe», y sin él las tres
    explicaciones que `revisar_carpeta` redacta con detalle se perdían: el
    docente con una ruta mal escrita leía «No hay carpeta de entregas
    configurada», y él sí la había indicado.
    """

    carpeta_entregas: Path | None = None
    problema_carpeta: str | None = None
    url_supabase: str | None = None
    clave_supabase: str | None = None
    version_criterios: str = VERSION_CRITERIOS_POR_OMISION


def revisar_carpeta(raiz: Path, carpeta: Path) -> ProblemaDeCarpeta | None:
    """Devuelve el problema que impide usar esa carpeta, o None si sirve."""
    raiz = raiz.resolve()
    carpeta = carpeta.resolve()

    if carpeta == raiz or raiz in carpeta.parents:
        return ProblemaDeCarpeta(
            f"La carpeta de entregas «{carpeta}» está dentro del repositorio. "
            "Los trabajos de los alumnos no pueden vivir en el árbol "
            "versionado: el primero que llegara impediría guardar cualquier "
            f"cambio. Indica en {CARPETA} una carpeta de fuera."
        )
    if not carpeta.exists():
        return ProblemaDeCarpeta(
            f"La carpeta de entregas «{carpeta}» no existe. Créala o corrige "
            f"{CARPETA}."
        )
    if not carpeta.is_dir():
        return ProblemaDeCarpeta(
            f"«{carpeta}» no es una carpeta. {CARPETA} debe apuntar a la "
            "carpeta donde se dejan los trabajos, no a un fichero."
        )
    return None


def _leer_env(raiz: Path) -> dict[str, str]:
    """Pares clave=valor del fichero .env de la raíz, si lo hay."""
    fichero = raiz / ".env"
    if not fichero.is_file():
        return {}
    leido: dict[str, str] = {}
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        leido[clave.strip()] = valor.strip().strip('"').strip("'")
    return leido


def cargar(raiz: Path, entorno: dict[str, str] | None = None) -> Configuracion:
    """Configuración efectiva: el entorno manda sobre el fichero .env.

    Una carpeta que no sirve se descarta entera y se deja a None. Arrastrar
    media configuración solo consigue que el fallo aparezca más tarde y más
    lejos de su causa. Lo que sí se conserva es el motivo por el que no
    sirve, para que el aviso que lee el docente sea el concreto y no el
    genérico.
    """
    import os

    valores = _leer_env(raiz)
    valores.update(dict(os.environ) if entorno is None else entorno)

    carpeta: Path | None = None
    problema: ProblemaDeCarpeta | None = None
    if valores.get(CARPETA):
        candidata = Path(valores[CARPETA])
        problema = revisar_carpeta(raiz, candidata)
        if problema is None:
            carpeta = candidata.resolve()

    return Configuracion(
        carpeta_entregas=carpeta,
        problema_carpeta=problema.motivo if problema else None,
        url_supabase=valores.get(URL) or None,
        clave_supabase=valores.get(CLAVE) or None,
        version_criterios=valores.get(VERSION) or VERSION_CRITERIOS_POR_OMISION,
    )
