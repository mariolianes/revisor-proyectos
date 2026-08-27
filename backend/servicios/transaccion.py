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
from tools.gobernanza.criterios import bloques_raiz
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
    # Detalle técnico opcional -salida de git, repr de una excepción-. Nunca
    # va en 'mensaje': eso lo lee el docente, esto es para quien depure.
    detalle_tecnico: str | None = None


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


# Un bloque de primer nivel de un YAML empieza en una línea sin sangría: o
# bien una clave de mapa ('extension:'), o bien una entrada de lista
# ('- codigo: D05'). Acaba justo antes del siguiente bloque, o al final del
# fichero. Se usa para acotar la sustitución de un valor al bloque de su
# propio criterio, y no al fichero entero.
_PATRON_BLOQUE = re.compile(r"^(?:[A-Za-z0-9_.-]+:|-(?:\s|$))", re.M)


def _bloques_de(ruta: Path) -> list[tuple[str, int, int]]:
    """(nombre, inicio, fin) de cada bloque de primer nivel del fichero.

    'nombre' es el mismo identificador que usa 'bloques_raiz' de
    tools.gobernanza.criterios -la clave del mapa, o el 'codigo' de la
    entrada si el fichero es una lista-, así que ambas listas recorren el
    fichero en el mismo orden y se pueden emparejar por posición. Si el
    número de bloques detectado por el patrón de texto no coincide con el
    que ve 'bloques_raiz' -un YAML con una forma que este patrón simplifica
    de más-, se devuelve una lista vacía: mejor no localizar el bloque que
    localizar el equivocado.
    """
    texto = ruta.read_text(encoding="utf-8")
    nombres = [nombre for nombre, _ in bloques_raiz(ruta)]
    inicios = [m.start() for m in _PATRON_BLOQUE.finditer(texto)]
    if len(nombres) != len(inicios):
        return []
    limites = []
    for indice, inicio in enumerate(inicios):
        fin = inicios[indice + 1] if indice + 1 < len(inicios) else len(texto)
        limites.append((nombres[indice], inicio, fin))
    return limites


def _localizar_bloque(ruta: Path, identificador: str) -> tuple[int, int] | None:
    """Offsets (inicio, fin) del bloque de un criterio, o None si no existe."""
    for nombre, inicio, fin in _bloques_de(ruta):
        if nombre == identificador:
            return inicio, fin
    return None


def _clave_presente(bloque: str, clave: str) -> bool:
    return re.search(rf"^\s*{re.escape(clave)}:\s*.*$", bloque, re.M) is not None


def _sustituir_valor_acotado(ruta: Path, identificador: str, clave: str,
                              valor_nuevo: str) -> str | None:
    """Sustituye 'clave: valor' solo dentro del bloque 'identificador'.

    Devuelve el texto completo del fichero con el cambio aplicado, o None si
    no se encuentra el bloque o la clave dentro de él. Nunca se sustituye
    contra el fichero entero: varios bloques de un mismo fichero de
    criterios suelen compartir el nombre de clave -'fuente' lo tienen casi
    todos-, y sustituir sin acotar reescribiría el bloque equivocado sin que
    ninguna regla de gobernanza lo note.
    """
    limites = _localizar_bloque(ruta, identificador)
    if limites is None:
        return None
    texto = ruta.read_text(encoding="utf-8")
    inicio, fin = limites
    bloque = texto[inicio:fin]
    nuevo_bloque, sustituciones = re.subn(
        rf"^(\s*{re.escape(clave)}:\s*).*$",
        lambda m: f"{m.group(1)}{valor_nuevo}",
        bloque, count=1, flags=re.M,
    )
    if sustituciones == 0:
        return None
    return texto[:inicio] + nuevo_bloque + texto[fin:]


# Caracteres con los que no puede empezar un valor que se empalma crudo tras
# 'clave: ' en una línea YAML: son indicadores de sintaxis (listas, mapas,
# citas, comentarios, anclas...) que cambiarían lo que YAML entiende que hay
# ahí, no el valor del criterio.
_CARACTERES_INICIALES_INSEGUROS = "-?:,[]{}&*!|>'\"%@`#"


def _valor_seguro(valor: str) -> bool:
    """Un valor apto para escribirse crudo tras 'clave: ' sin romper el YAML.

    No es una regla de gobernanza -no decide si el valor es correcto-, es la
    comprobación mínima de forma: una sola línea, sin los caracteres que
    convertirían la línea en otra cosa distinta de 'clave: valor' cuando
    YAML la vuelva a leer.
    """
    if not valor or valor != valor.strip():
        return False
    if any(c in valor for c in "\n\r\t"):
        return False
    if valor[0] in _CARACTERES_INICIALES_INSEGUROS:
        return False
    if ": " in valor or valor.endswith(":"):
        return False
    if " #" in valor:
        return False
    return True


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

    # Guardas baratas sobre el contenido de cada cambio, todavía sin escribir
    # nada: forma del valor, y que el criterio y la clave existan de verdad.
    for cambio in cambios:
        if not _valor_seguro(cambio.valor_nuevo):
            return Resultado(exito=False, mensaje=(
                f"El valor «{cambio.valor_nuevo}» para «{cambio.clave}» no es "
                f"válido: tiene que ser una sola línea, sin comillas, "
                f"corchetes ni almohadillas, que son caracteres con "
                f"significado especial en el fichero de criterios."
            ))
        ruta = raiz / cambio.fichero
        limites = _localizar_bloque(ruta, cambio.identificador)
        if limites is None:
            return Resultado(exito=False, mensaje=(
                f"No se encontró el criterio «{cambio.identificador}» en "
                f"«{cambio.fichero}»."
            ))
        inicio, fin = limites
        bloque = ruta.read_text(encoding="utf-8")[inicio:fin]
        if not _clave_presente(bloque, cambio.clave):
            return Resultado(exito=False, mensaje=(
                f"El criterio «{cambio.identificador}» de «{cambio.fichero}» "
                f"no tiene la clave «{cambio.clave}»."
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

    # El nombre del documento de cambio es determinista -fecha más las
    # primeras palabras del motivo-, así que dos guardados el mismo día con
    # un motivo parecido pueden apuntar al mismo fichero. Si ya existía, se
    # le da el mismo trato que al sello: guardar su contenido y restaurarlo
    # al revertir, nunca borrarlo.
    nombre_cambio = f"{date.today().isoformat()}-{_asunto(motivo)}.md"
    ruta_cambio = raiz / CARPETA_CAMBIOS / nombre_cambio
    ruta_cambio_existia = ruta_cambio.is_file()
    if ruta_cambio_existia:
        tocados[ruta_cambio] = ruta_cambio.read_bytes()

    def revertir() -> None:
        for ruta, contenido in tocados.items():
            ruta.write_bytes(contenido)
        if not ruta_cambio_existia:
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
            nuevo_texto = _sustituir_valor_acotado(
                ruta, cambio.identificador, cambio.clave, cambio.valor_nuevo
            )
            if nuevo_texto is None:
                # No debería llegar aquí tras las guardas de arriba, pero si
                # algo cambió por debajo entre la comprobación y la
                # escritura, se trata igual que cualquier otro fallo: se
                # revierte todo y no se finge un éxito.
                revertir()
                return Resultado(exito=False, mensaje=(
                    f"No se pudo aplicar el cambio en «{cambio.identificador}» "
                    f"de «{cambio.fichero}». No se ha guardado nada."
                ))
            ruta.write_text(nuevo_texto, encoding="utf-8")

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

        # Solo se comitea lo que ha tocado esta transacción, no el árbol
        # entero: el hueco de guarda ya comprobó que no había nada más
        # pendiente, pero un 'git add -A' comitearía igual cualquier cosa
        # que apareciera entre esa comprobación y este punto.
        rutas_para_commit = {documento, ruta_cambio, sincronia}
        rutas_para_commit.update(raiz / cambio.fichero for cambio in cambios)
        relativas = sorted(r.relative_to(raiz).as_posix() for r in rutas_para_commit)
        _git(raiz, "add", "--", *relativas)

        commit = _git(raiz, "commit", "-q", "-m", f"docs: {motivo.strip()}")
        if commit.returncode != 0:
            revertir()
            _git(raiz, "reset")
            return Resultado(
                exito=False,
                mensaje=(
                    "No se ha podido registrar el cambio en git. No se ha "
                    "guardado nada: puedes reintentarlo, y si se repite, "
                    "avisa al administrador."
                ),
                detalle_tecnico=commit.stderr,
            )

        return Resultado(
            exito=True,
            commit=_git(raiz, "rev-parse", "--short", "HEAD").stdout.strip(),
            mensaje="Cambio guardado, verificado y registrado.",
        )

    except Exception as error:
        revertir()
        return Resultado(
            exito=False,
            mensaje=(
                "No se ha podido escribir el cambio. No se ha guardado "
                "nada: puedes reintentarlo."
            ),
            detalle_tecnico=f"{type(error).__name__}: {error}",
        )
