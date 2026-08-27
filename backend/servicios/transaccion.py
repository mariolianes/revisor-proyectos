"""El guardado, como transacción atómica.

O se completa entera, o el repositorio queda byte a byte como estaba y sin
commits nuevos. Un guardado a medias deja el repositorio en un estado que
nadie sabe interpretar después, que es justo lo que la gobernanza evita.
"""

import io
import re
import subprocess
import unicodedata
from datetime import date
from pathlib import Path

from pydantic import BaseModel
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import ScalarString

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


# --------------------------------------------------------------------------
# La edición del criterio derivado, sobre el árbol del YAML.
#
# Localizar el valor con una expresión regular sobre las líneas fue el origen
# de cinco defectos seguidos, todos de la misma familia: un patrón de texto
# sabe encontrar 'clave:' dentro de un texto, pero no sabe si esa clave es
# del criterio que se pidió cambiar o de otra con el mismo nombre anidada más
# adentro. Eso es estructura, no texto. Aquí el fichero se parsea en modo ida
# y vuelta -conserva comentarios, orden y formato-, se baja hasta el nodo por
# su ruta real -el identificador da el bloque, la clave da el campo de ese
# bloque- y se muta ese nodo concreto.
#
# Los comentarios de 'criteria/' son normativos: cabeceras del tipo «NO
# EDITAR sin cambiar antes la prosa. Ver GOVERNANCE.md» y notas que explican
# de dónde sale cada valor. Perderlos al guardar destruiría documentación que
# forma parte de la gobernanza, así que conservarlos no es un detalle
# estético: es parte de lo que esta transacción promete.
# --------------------------------------------------------------------------

# Sangrías con las que se intenta releer un fichero de criterios: (mapa,
# lista, desplazamiento del guion de la lista). La biblioteca no deduce la
# sangría del fichero que lee, así que se prueban las formas que se usan en
# 'criteria/' y se acepta la primera que reproduce el fichero tal cual.
_SANGRIAS = ((2, 2, 0), (2, 4, 2), (4, 4, 0), (4, 8, 4))

# Marca para distinguir «la clave no está» de «la clave está y no vale nada».
_AUSENTE = object()


def _lector(mapa: int, lista: int, desplazamiento: int) -> YAML:
    """Un lector de ida y vuelta: conserva comentarios, orden y comillas."""
    lector = YAML()
    lector.preserve_quotes = True
    # Sin esto reparte en varias líneas cualquier valor que pase de 80
    # caracteres, y reescribiría líneas que nadie ha pedido cambiar.
    lector.width = 4096
    lector.indent(mapping=mapa, sequence=lista, offset=desplazamiento)
    return lector


def _volcar(lector: YAML, datos) -> str:
    memoria = io.StringIO()
    lector.dump(datos, memoria)
    return memoria.getvalue()


def _abrir_sin_reformatear(ruta: Path) -> tuple[YAML, object] | None:
    """Abre el YAML de modo que volcarlo sin tocar nada lo deje igual.

    Devuelve (lector, árbol), o None si no se ha conseguido. Antes de cambiar
    ningún valor se comprueba que volver a escribir el fichero *sin* cambiar
    nada lo reproduce carácter a carácter. Con esa comprobación hecha, el
    único cambio que puede aparecer en el fichero es el valor que el docente
    pidió cambiar: comentarios, orden, sangría y líneas en blanco quedan
    donde estaban. Si ninguna sangría lo consigue, se prefiere no guardar a
    reformatear de oficio el fichero de criterios.
    """
    texto = ruta.read_text(encoding="utf-8")
    for sangria in _SANGRIAS:
        lector = _lector(*sangria)
        try:
            datos = lector.load(texto)
        except Exception:
            # Un fichero que no parsea no lo va a arreglar otra sangría.
            return None
        if _volcar(lector, datos) == texto:
            return lector, datos
    return None


def _bloque_de(datos, identificador: str):
    """El nodo del criterio 'identificador', o '_AUSENTE' si no está.

    Nombra los bloques igual que 'bloques_raiz' de
    tools.gobernanza.criterios: por la clave si la raíz del fichero es un
    mapa, y por el 'codigo' -o por la posición, si no lo tiene- si es una
    lista. Así el docente cita un criterio con el mismo nombre con el que lo
    citan las reglas de gobernanza.
    """
    if isinstance(datos, dict):
        return datos[identificador] if identificador in datos else _AUSENTE
    if isinstance(datos, list):
        for posicion, elemento in enumerate(datos, start=1):
            codigo = elemento.get("codigo") if isinstance(elemento, dict) else None
            if str(codigo or f"elemento {posicion}") == identificador:
                return elemento
    return _AUSENTE


def _es_grupo(valor) -> bool:
    """Si el valor es una lista o un grupo de datos, no un dato suelto."""
    return isinstance(valor, (list, dict))


def _es_texto_de_varias_lineas(valor) -> bool:
    return isinstance(valor, str) and "\n" in valor


def _escrito_en_la_misma_linea(valor) -> bool:
    """Si una lista o un grupo está escrito entre corchetes o llaves.

    Es la distinción que el mecanismo anterior no podía hacer de verdad:
    sobre el árbol, la biblioteca conserva cómo estaba escrito cada nodo, así
    que se sabe si el valor ocupaba una línea o varias en vez de deducirlo de
    la forma del texto.
    """
    formato = getattr(valor, "fa", None)
    return bool(formato is not None and formato.flow_style())


def _con_el_estilo_de(anterior, nuevo):
    """Conserva las comillas del valor anterior cuando el nuevo es texto."""
    if isinstance(anterior, ScalarString) and type(nuevo) is str:
        return type(anterior)(nuevo)
    return nuevo


def _valor_como_lo_leeria_el_yaml(valor_nuevo: str):
    """Interpreta lo que escribió el docente como lo interpreta el fichero.

    '25' es el número 25 y 'Arial' es el texto Arial, igual que si estuvieran
    escritos a mano en el YAML. Sin esto, un '25' se escribiría entre
    comillas para conservar que es texto, y el criterio dejaría de ser un
    número sin que nadie lo hubiera pedido.
    """
    return _lector(*_SANGRIAS[0]).load(valor_nuevo)


def _aplicar_cambio(raiz: Path, cambio: CambioDeValor) -> tuple[str | None, str]:
    """Devuelve el fichero entero con el valor ya cambiado, o el motivo.

    Exactamente uno de los dos viene lleno: si el cambio se puede aplicar, el
    texto nuevo del fichero y un motivo vacío; si no, None y un mensaje para
    el docente. No escribe nada: quien llama decide cuándo se escribe.
    """
    ruta = raiz / cambio.fichero
    abierto = _abrir_sin_reformatear(ruta)
    if abierto is None:
        return None, (
            f"«{cambio.fichero}» tiene una forma que este editor no sabe "
            f"volver a escribir sin cambiarle el formato al resto del "
            f"fichero. No se ha tocado: cambia ese valor a mano."
        )
    lector, datos = abierto

    bloque = _bloque_de(datos, cambio.identificador)
    if bloque is _AUSENTE:
        return None, (
            f"No se encontró el criterio «{cambio.identificador}» en "
            f"«{cambio.fichero}»."
        )
    if not isinstance(bloque, dict):
        return None, (
            f"El criterio «{cambio.identificador}» de «{cambio.fichero}» no "
            f"es un grupo de datos con claves, así que no tiene ninguna "
            f"«{cambio.clave}» que cambiar."
        )
    # La clave se busca entre las propias del bloque, nunca dentro de lo que
    # el bloque contiene: si el criterio tiene un grupo anidado con una clave
    # del mismo nombre, la que se cambia es la del criterio.
    if cambio.clave not in bloque:
        return None, (
            f"El criterio «{cambio.identificador}» de «{cambio.fichero}» "
            f"no tiene la clave «{cambio.clave}»."
        )

    valor_actual = bloque[cambio.clave]
    if _es_grupo(valor_actual):
        if _escrito_en_la_misma_linea(valor_actual):
            return None, (
                f"«{cambio.clave}» en «{cambio.identificador}» de "
                f"«{cambio.fichero}» es una lista o un grupo de datos "
                f"escrito en una sola línea. Este editor no puede cambiar "
                f"ese tipo de valor: edítalo a mano en el fichero de "
                f"criterios."
            )
        return None, (
            f"«{cambio.clave}» en «{cambio.identificador}» de "
            f"«{cambio.fichero}» tiene un valor de varias líneas -una "
            f"lista o un grupo de datos-. Este editor no puede "
            f"cambiar ese tipo de valor: edítalo a mano en el "
            f"fichero de criterios."
        )
    if _es_texto_de_varias_lineas(valor_actual):
        return None, (
            f"«{cambio.clave}» en «{cambio.identificador}» de "
            f"«{cambio.fichero}» tiene un texto de varias líneas. Este "
            f"editor no puede cambiar ese tipo de valor: edítalo a mano en "
            f"el fichero de criterios."
        )

    try:
        valor = _valor_como_lo_leeria_el_yaml(cambio.valor_nuevo)
    except Exception:
        valor = _AUSENTE
    if valor is _AUSENTE or _es_grupo(valor) or _es_texto_de_varias_lineas(valor):
        return None, (
            f"El valor «{cambio.valor_nuevo}» para «{cambio.clave}» no es un "
            f"dato suelto: tiene que ser un número o un texto de una línea."
        )

    bloque[cambio.clave] = _con_el_estilo_de(valor_actual, valor)
    return _volcar(lector, datos), ""


# Caracteres con los que no puede empezar un valor que se empalma crudo tras
# 'clave: ' en una línea YAML: son indicadores de sintaxis (listas, mapas,
# citas, comentarios, anclas...) que cambiarían lo que YAML entiende que hay
# ahí, no el valor del criterio.
_CARACTERES_INICIALES_INSEGUROS = "-?:,[]{}&*!|>'\"%@`#"


def _valor_seguro(valor: str) -> bool:
    """Un valor de criterio con una forma sencilla de leer en el fichero.

    Ya no hace falta para no romper el YAML -ahora el valor lo escribe la
    biblioteca, que entrecomilla ella sola lo que lo necesite-, pero se
    mantiene como política: 'criteria/' está pensado para leerse y editarse
    a mano, y un valor con comillas, corchetes o almohadillas dentro convierte
    una línea legible en algo que hay que descifrar. No es una regla de
    gobernanza -no decide si el valor es correcto-, es la forma mínima que se
    le pide: una sola línea, sin caracteres de sintaxis.
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

    try:
        # 'leer_seccion' recorre 'docs/maestro/' y, para contar cuántos
        # criterios cita cada sección, también parsea con YAML todos los
        # ficheros de 'criteria/' -no solo el que esta transacción va a
        # tocar-. Si alguno estuviera mal formado, lanzaría aquí, antes de
        # escribir nada: se captura para devolver un 'Resultado', nunca una
        # excepción sin capturar.
        seccion = leer_seccion(raiz, ancla)
    except Exception as error:
        return Resultado(
            exito=False,
            mensaje=(
                "No se han podido leer los documentos o los criterios del "
                "repositorio. Puede haber un error de formato: revísalo "
                "antes de reintentar."
            ),
            detalle_tecnico=f"{type(error).__name__}: {error}",
        )
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
    # nada: la forma del valor nuevo, y que el criterio y la clave existan de
    # verdad y admitan un valor suelto. '_aplicar_cambio' calcula el fichero
    # resultante pero aquí solo se mira el motivo del rechazo; se vuelve a
    # llamar más abajo, ya en el camino de escritura, por si algo cambiara
    # entre esta comprobación y aquella. No hace falta protegerlas contra un
    # YAML mal formado: el 'leer_seccion' de más arriba ya parseó con éxito
    # todos los ficheros de 'criteria/' -incluido cualquiera de los que
    # toquen estos cambios-, así que si llegamos aquí, ya se sabe que
    # parsean.
    for cambio in cambios:
        if not _valor_seguro(cambio.valor_nuevo):
            return Resultado(exito=False, mensaje=(
                f"El valor «{cambio.valor_nuevo}» para «{cambio.clave}» no es "
                f"válido: tiene que ser una sola línea, sin comillas, "
                f"corchetes ni almohadillas, que son caracteres con "
                f"significado especial en el fichero de criterios."
            ))
        _, problema = _aplicar_cambio(raiz, cambio)
        if problema:
            return Resultado(exito=False, mensaje=problema)

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
            nuevo_texto, _ = _aplicar_cambio(raiz, cambio)
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

    # El commit ya existe: a partir de aquí no se revierte nada. Si algo de
    # lo que sigue lanzara, atraparlo y llamar a 'revertir()' dejaría el
    # árbol restaurado pero el commit todavía en el historial -el estado a
    # medias que esta función entera existe para que no pueda ocurrir-. Por
    # el mismo motivo, este 'try' es solo para leer el hash: si falla, el
    # guardado ya ha ocurrido y se informa como éxito, sin identificador.
    try:
        commit_hash = _git(raiz, "rev-parse", "--short", "HEAD").stdout.strip()
    except Exception as error:
        return Resultado(
            exito=True,
            commit=None,
            mensaje=(
                "El cambio se ha guardado y registrado, pero no se ha "
                "podido leer el identificador del commit."
            ),
            detalle_tecnico=f"{type(error).__name__}: {error}",
        )

    return Resultado(
        exito=True,
        commit=commit_hash,
        mensaje="Cambio guardado, verificado y registrado.",
    )
