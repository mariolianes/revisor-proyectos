"""El guardado, como transacción atómica.

O se completa entera, o el repositorio queda byte a byte como estaba y sin
commits nuevos. Un guardado a medias deja el repositorio en un estado que
nadie sabe interpretar después, que es justo lo que la gobernanza evita.
"""

import re
import subprocess
import unicodedata
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from backend.servicios.repositorio import DOCUMENTOS, leer_seccion
from tools.gobernanza.cambios import CARPETA as CARPETA_CAMBIOS
from tools.gobernanza.sincronia import FICHERO_SINCRONIA, escribir_sincronia
from tools.verificar_gobernanza import ejecutar


class CambioDeValor(BaseModel):
    """Un valor de un criterio que el docente ha decidido cambiar."""

    fichero: str
    identificador: str
    clave: str
    valor_nuevo: str


class Resultado(BaseModel):
    """Cómo acabó el guardado."""

    exito: bool
    commit: str | None = None
    infracciones: list[dict] = []
    mensaje: str = ""


def _git(raiz: Path, *argumentos: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *argumentos], cwd=raiz, capture_output=True, text=True, check=False
    )


def _arbol_limpio(raiz: Path) -> bool:
    return not _git(raiz, "status", "--porcelain").stdout.strip()


def _asunto(motivo: str) -> str:
    """Convierte el motivo en un asunto apto para el nombre del fichero."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", motivo.lower())
        if unicodedata.category(c) != "Mn"
    )
    palabras = re.findall(r"[a-z0-9]+", sin_tildes)[:6]
    return "-".join(palabras) or "cambio"


def _fichero_de(ancla: str) -> str:
    documento, _, _ = ancla.partition("#")
    return DOCUMENTOS[documento]


def _documento_de_cambio(ancla: str, cambios: list[CambioDeValor],
                         motivo: str, fuente: str) -> str:
    """El documento que R5 exige, con sus cinco secciones."""
    if cambios:
        lista = "\n".join(
            f"- `{c.fichero}` · {c.identificador}.{c.clave} → {c.valor_nuevo}"
            for c in cambios
        )
    else:
        lista = "Ningún criterio derivado cambia de valor."

    return (
        f"# {motivo.strip().rstrip('.')}\n\n"
        f"**Fecha:** {date.today().isoformat()}\n"
        f"**Autor:** editor de criterios\n\n"
        f"## Que cambia\n\n"
        f"Se ha modificado la sección `{ancla}` de la prosa normativa.\n\n"
        f"{lista}\n\n"
        f"## Por que\n\n{motivo.strip()}\n\n"
        f"## Fuente que lo respalda\n\n{fuente.strip()}\n\n"
        f"## Que arrastra\n\n"
        f"- La sección `{ancla}` de `docs/maestro/`\n"
        f"- Los criterios listados arriba\n\n"
        f"## Correcciones cerradas afectadas\n\n"
        f"Pendiente de revisar por el docente.\n"
    )


def _sustituir_seccion(texto: str, ancla: str, cuerpo_nuevo: str) -> str | None:
    """Reemplaza el cuerpo de una sección conservando su marca de ancla."""
    marca = f"<!-- ancla: {ancla} -->"
    inicio = texto.find(marca)
    if inicio == -1:
        return None
    desde = inicio + len(marca)
    siguiente = re.search(
        r"^<!-- ancla: (?:maestro|indice|guia)#[a-z0-9-]+ -->$",
        texto[desde:], re.M,
    )
    hasta = desde + siguiente.start() if siguiente else len(texto)
    return texto[:desde] + "\n" + cuerpo_nuevo.strip("\n") + "\n\n" + texto[hasta:]


def _sustituir_valor(contenido: str, clave: str, valor_nuevo: str) -> str:
    """Cambia `clave: valor` conservando la indentación de la línea."""
    return re.sub(
        rf"^(\s*{re.escape(clave)}:\s*).*$",
        lambda m: f"{m.group(1)}{valor_nuevo}",
        contenido, count=1, flags=re.M,
    )


def guardar(raiz: Path, ancla: str, texto_nuevo: str, cambios: list[CambioDeValor],
            motivo: str, fuente: str, hash_esperado: str) -> Resultado:
    """Ejecuta el procedimiento completo, o no deja rastro."""
    if not motivo.strip():
        return Resultado(exito=False, mensaje=(
            "Falta el motivo del cambio. Es lo que permitirá entender esta "
            "decisión dentro de un año."
        ))
    if not fuente.strip():
        return Resultado(exito=False, mensaje=(
            "Falta la fuente que respalda el cambio. Si no hay ninguna, este "
            "cambio no debería hacerse."
        ))

    seccion = leer_seccion(raiz, ancla)
    if seccion is None:
        return Resultado(exito=False, mensaje=f"La sección «{ancla}» no existe.")

    if seccion.hash != hash_esperado:
        return Resultado(exito=False, mensaje=(
            "La sección ha cambiado desde que la abriste. Recarga antes de "
            "guardar para no pisar el otro cambio."
        ))

    if not _arbol_limpio(raiz):
        return Resultado(exito=False, mensaje=(
            "El repositorio tiene cambios sin comitear. Resuélvelos antes de "
            "guardar desde aquí."
        ))

    for cambio in cambios:
        ruta = (raiz / cambio.fichero).resolve()
        carpeta = (raiz / "criteria").resolve()
        if not str(ruta).startswith(str(carpeta)) or not ruta.is_file():
            return Resultado(exito=False, mensaje=(
                f"«{cambio.fichero}» no es un fichero de criterios de este "
                f"repositorio."
            ))

    # A partir de aquí se escribe. Todo lo que se toque se guarda para revertir.
    documento = raiz / "docs" / "maestro" / _fichero_de(ancla)
    tocados: dict[Path, bytes] = {documento: documento.read_bytes()}
    for cambio in cambios:
        ruta = raiz / cambio.fichero
        tocados.setdefault(ruta, ruta.read_bytes())
    # El registro de sincronía se reescribe siempre. Si no existiera, habría
    # que borrarlo al revertir en vez de restaurarlo: por eso se distingue.
    sincronia = raiz / FICHERO_SINCRONIA
    sincronia_existia = sincronia.is_file()
    if sincronia_existia:
        tocados[sincronia] = sincronia.read_bytes()

    nombre_cambio = f"{date.today().isoformat()}-{_asunto(motivo)}.md"
    ruta_cambio = raiz / CARPETA_CAMBIOS / nombre_cambio

    def revertir() -> None:
        for ruta, contenido in tocados.items():
            ruta.write_bytes(contenido)
        ruta_cambio.unlink(missing_ok=True)
        if not sincronia_existia:
            sincronia.unlink(missing_ok=True)
        _git(raiz, "reset")

    try:
        texto_actualizado = _sustituir_seccion(
            documento.read_text(encoding="utf-8"), ancla, texto_nuevo
        )
        if texto_actualizado is None:
            revertir()
            return Resultado(exito=False, mensaje="No se encontró el ancla en el documento.")
        documento.write_text(texto_actualizado, encoding="utf-8")

        for cambio in cambios:
            ruta = raiz / cambio.fichero
            ruta.write_text(
                _sustituir_valor(ruta.read_text(encoding="utf-8"),
                                 cambio.clave, cambio.valor_nuevo),
                encoding="utf-8",
            )

        ruta_cambio.write_text(
            _documento_de_cambio(ancla, cambios, motivo, fuente), encoding="utf-8"
        )

        escribir_sincronia(raiz)

        infracciones = ejecutar(raiz, [], False)
        if infracciones:
            revertir()
            return Resultado(
                exito=False,
                infracciones=[
                    {"regla": i.regla, "fichero": i.fichero, "detalle": i.detalle}
                    for i in infracciones
                ],
                mensaje=(
                    f"El cambio no se ha guardado: {len(infracciones)} "
                    f"infracción(es) de gobernanza."
                ),
            )

        _git(raiz, "add", "-A")
        commit = _git(raiz, "commit", "-q", "-m", f"docs: {motivo.strip()}")
        if commit.returncode != 0:
            revertir()
            _git(raiz, "reset")
            return Resultado(exito=False, mensaje=f"Git rechazó el commit: {commit.stderr}")

        return Resultado(
            exito=True,
            commit=_git(raiz, "rev-parse", "--short", "HEAD").stdout.strip(),
            mensaje="Cambio guardado, verificado y registrado.",
        )

    except OSError as error:
        revertir()
        return Resultado(exito=False, mensaje=f"Error al escribir: {error}")
