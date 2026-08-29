"""R8: el texto en castellano lleva sus tildes.

Este sistema produce texto que leen un profesor y sus alumnos: la instruccion
que se manda al motor, el informe tecnico y el borrador de devolucion. Un
informe que escribe "Redaccion y presentacion" mientras valora la redaccion de
un trabajo academico se desautoriza solo.

La regla mira **solo prosa**: cadenas de texto, comentarios y docstrings en
Python, y el cuerpo de los documentos Markdown. No mira identificadores, porque
el proyecto los escribe sin tildes a proposito -`analisis`, `codigo`,
`dimension`- y eso es una convencion deliberada, no un descuido.

El vocabulario es corto y solo contiene palabras cuya forma sin tilde **no
existe** en castellano. Nada de "mas", "solo", "el", "si", "seria" ni "limite":
todas son palabras validas sin tilde y denunciarlas daria falsos positivos que
acabarian con la regla desactivada, que es el peor final posible para un
verificador.
"""

import io
import re
import tokenize
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

# Cada entrada es (forma sin tilde, forma correcta). Solo palabras cuya version
# sin tilde no es una palabra castellana valida por si misma.
PALABRAS: tuple[tuple[str, str], ...] = (
    ("analisis", "análisis"),
    ("correccion", "corrección"),
    ("correcciones", "correcciones"),  # plural llano: se acentua el singular
    ("formacion", "formación"),
    ("redaccion", "redacción"),
    ("presentacion", "presentación"),
    ("fundamentacion", "fundamentación"),
    ("adecuacion", "adecuación"),
    ("justificacion", "justificación"),
    ("interpretacion", "interpretación"),
    ("evolucion", "evolución"),
    ("verificacion", "verificación"),
    ("instruccion", "instrucción"),
    ("informacion", "información"),
    ("valoracion", "valoración"),
    ("revision", "revisión"),
    ("seleccion", "selección"),
    ("decision", "decisión"),
    ("dimension", "dimensión"),
    ("version", "versión"),
    ("conexion", "conexión"),
    ("metodologia", "metodología"),
    ("autoria", "autoría"),
    ("categoria", "categoría"),
    ("garantia", "garantía"),
    ("pedagogico", "pedagógico"),
    ("academico", "académico"),
    ("tecnico", "técnico"),
    ("critico", "crítico"),
    ("automatico", "automático"),
    ("parrafo", "párrafo"),
    ("pagina", "página"),
    ("parafrasis", "paráfrasis"),
    ("deberia", "debería"),
    ("podria", "podría"),
    ("tendria", "tendría"),
    ("habria", "habría"),
    ("aqui", "aquí"),
    ("asi", "así"),
    ("tambien", "también"),
    ("segun", "según"),
    ("despues", "después"),
    ("ademas", "además"),
    ("quiza", "quizá"),
    ("proposito", "propósito"),
    ("numero", "número"),
    ("codigo", "código"),
    ("minimo", "mínimo"),
    ("maximo", "máximo"),
    ("ultimo", "último"),
    ("unico", "único"),
    ("valido", "válido"),
    ("rapido", "rápido"),
)

# Se construye un patron por palabra para poder nombrar la correccion exacta.
# \b no basta: "version" aparece dentro de "versionado", que es correcto.
_PATRONES = tuple(
    (re.compile(rf"(?<![\w-]){sin}(?![\w-])", re.IGNORECASE), sin, con)
    for sin, con in PALABRAS
)

CARPETAS_IGNORADAS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv",
    "dist", ".superpowers", ".claude",
}

EXTENSIONES = {".py", ".md", ".yaml", ".ts", ".tsx"}

# Este fichero contiene el vocabulario, asi que se denuncia a si mismo. Los
# planes y specs de superpowers son cuadernos de trabajo, no producto.
EXENTOS = {
    "tools/gobernanza/ortografia.py",
    "tests/gobernanza/test_ortografia.py",
}
PREFIJOS_EXENTOS = ("docs/superpowers/", "docs/changes/", "docs/decisions.md")


def _esta_exento(relativa: str) -> bool:
    return relativa in EXENTOS or relativa.startswith(PREFIJOS_EXENTOS)


# Lo que parece prosa pero no lo es. Se borra antes de buscar faltas. El orden
# importa: las rutas se quitan antes que las claves, porque "formato.yaml"
# contiene un punto y no dos puntos.
_CODIGO_EN_LINEA = re.compile(r"`[^`]*`|'[^']*'")
_INTERPOLACION = re.compile(r"\{[^{}]*\}")
# Un grupo con nombre de una expresion regular: `(?P<codigo>...)`. El nombre es
# un identificador, y ponerle una tilde rompe el codigo en silencio.
_GRUPO_NOMBRADO = re.compile(r"\(\?P[=<][^>)]*>?")
# Una ruta necesita contenido a los dos lados del separador. Exigirlo no es un
# detalle: con `[\w./-]*[./][\w./-]*` el punto que cierra una frase convertia su
# ultima palabra en una ruta, y la regla quedaba ciega al final de cada oracion
# -justo donde mas caen las palabras largas que llevan tilde-.
_RUTA = re.compile(r"[\w<>-]+(?:[./\\][\w<>-]+)+")
# Una referencia a la prosa maestra: `calibracion#9-semaforo`. Es un ancla, no
# una frase, y va sin tildes a proposito para que sea estable como enlace.
_ANCLA = re.compile(r"\w+#[\w-]+")
_CLAVE = re.compile(r"\b\w+(?=:)")
_MAYUSCULAS = re.compile(r"\b[A-Z][A-Z_0-9]{2,}\b")
# Un nombre propio o de clase en mitad de una frase: `Evolucion`, `Medidas`.
# No se filtra la primera palabra de la linea ni la que sigue a un punto,
# porque ahi una mayuscula es ortografia normal y la falta seria real.
_NOMBRE_INTERIOR = re.compile(r"(?<=[a-z,;] )\b[A-Z][a-záéíóúñ]+\b")


def _limpiar(texto: str) -> str:
    """Quita del texto lo que es codigo y no lengua.

    Una cadena de Python puede ser prosa -"no se ha localizado la cita"- o un
    dato -"version", "codigo_alumno", "criteria/<version>/formato.yaml"-. Solo
    la primera esta escrita en castellano y solo ella debe llevar tildes.
    """
    texto = _CODIGO_EN_LINEA.sub(" ", texto)
    texto = _INTERPOLACION.sub(" ", texto)
    texto = _GRUPO_NOMBRADO.sub(" ", texto)
    texto = _ANCLA.sub(" ", texto)
    texto = _RUTA.sub(" ", texto)
    texto = _CLAVE.sub(" ", texto)
    texto = _MAYUSCULAS.sub(" ", texto)
    return _NOMBRE_INTERIOR.sub(" ", texto)


def _es_prosa(texto: str) -> bool:
    """Una cadena de una sola palabra es una clave o un identificador."""
    return len(texto.split()) >= 3


def prosa_de_python(fuente: str) -> list[tuple[int, str]]:
    """Devuelve (linea, texto) de cada cadena y comentario de un modulo.

    Se usa el analizador lexico de Python en vez de una expresion regular
    porque hace falta distinguir una cadena de un identificador: `analisis` es
    un nombre de variable correcto y "el analisis" es una falta.

    Los docstrings ocupan varias lineas, asi que se parten: sin eso, la falta
    se denunciaria siempre en la primera linea del bloque y quien lo lea no
    encontraria la palabra alli.
    """
    trozos: list[tuple[int, str]] = []
    try:
        piezas = list(tokenize.generate_tokens(io.StringIO(fuente).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Un fichero que no compila ya lo denuncian los tests; aqui no se
        # inventa una infraccion de ortografia por ello.
        return []

    for pieza in piezas:
        if pieza.type not in (tokenize.STRING, tokenize.COMMENT):
            continue
        for desplazamiento, linea in enumerate(pieza.string.splitlines()):
            limpia = _limpiar(linea)
            if _es_prosa(limpia):
                trozos.append((pieza.start[0] + desplazamiento, limpia))
    return trozos


# En un fichero de interfaz la lengua vive en las cadenas, en los comentarios
# y en el texto que va entre etiquetas. Todo lo demas es codigo: `const
# analisis = await api.analisis(id)` no es una falta de ortografia.
_CADENA_TS = re.compile(r"""(["'`])((?:\\.|(?!\1).)*)\1""", re.S)
_TEXTO_ENTRE_ETIQUETAS = re.compile(r">([^<>{}]+)<")
_COMENTARIO_TS = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def prosa_de_typescript(fuente: str) -> list[tuple[int, str]]:
    """Devuelve (linea, texto) de las cadenas, comentarios y texto visible.

    No hay analizador lexico de TypeScript a mano, asi que se extrae con
    expresiones regulares lo que puede ser lengua y se deja fuera el resto.
    Es menos fino que el de Python y lo es a proposito: ante la duda se calla,
    porque una regla con falsos positivos acaba desactivada.
    """
    trozos: list[tuple[int, str]] = []
    for patron, grupo in (
        (_CADENA_TS, 2),
        (_TEXTO_ENTRE_ETIQUETAS, 1),
        (_COMENTARIO_TS, 0),
    ):
        for hallazgo in patron.finditer(fuente):
            texto = hallazgo.group(grupo)
            if not texto or not texto.strip():
                continue
            primera = fuente.count("\n", 0, hallazgo.start(grupo)) + 1
            for desplazamiento, linea in enumerate(texto.splitlines()):
                limpia = _limpiar(linea)
                if _es_prosa(limpia):
                    trozos.append((primera + desplazamiento, limpia))
    return trozos


def prosa_de_markdown(fuente: str) -> list[tuple[int, str]]:
    """Devuelve (linea, texto) del cuerpo, saltando los bloques de codigo."""
    trozos: list[tuple[int, str]] = []
    dentro_de_codigo = False
    for numero, linea in enumerate(fuente.splitlines(), start=1):
        if linea.lstrip().startswith("```"):
            dentro_de_codigo = not dentro_de_codigo
            continue
        if dentro_de_codigo:
            continue
        # El codigo en linea tampoco es prosa: `version` es un campo, no una
        # palabra mal escrita.
        limpia = _limpiar(linea)
        if _es_prosa(limpia):
            trozos.append((numero, limpia))
    return trozos


_MARCA_DE_LINEA = re.compile(r"(?<!-)sin-tilde:\s*(\S.*)$")
# La marca de fichero se busca sobre el fuente entero, asi que necesita que `$`
# signifique fin de linea y no fin de cadena.
_MARCA_DE_FICHERO = re.compile(r"sin-tilde-fichero:\s*(\S.*)$", re.M)


def fichero_eximido(fuente: str) -> bool:
    """Cierto si el fichero entero declara, con motivo, que va sin tildes."""
    marca = _MARCA_DE_FICHERO.search(fuente)
    return bool(marca and marca.group(1).strip())


def _lineas_eximidas(fuente: str) -> set[int]:
    """Lineas cubiertas por una marca `sin-tilde:` con su motivo.

    La valvula existe porque hay texto sin tildes que es correcto: la salida de
    `normalizar_para_buscar`, que las quita a proposito, o el contenido
    simulado de un PDF que se compara caracter a caracter con lo extraido.
    Se exige el motivo escrito para que la exencion sea una decision y no un
    silenciador que alguien pega sin pensar.

    La marca cubre su propia linea y sigue cubriendo mientras el comentario
    continue, hasta la primera linea de codigo inclusive. Asi el motivo puede
    ocupar las lineas que necesite y escribirse encima de lo que exime, en vez
    de apretujado al final de una linea ya larga.
    """
    lineas = fuente.splitlines()
    eximidas: set[int] = set()
    for indice, linea in enumerate(lineas):
        marca = _MARCA_DE_LINEA.search(linea)
        if not (marca and marca.group(1).strip()):
            continue
        numero = indice + 1
        eximidas.add(numero)
        siguiente = indice + 1
        while siguiente < len(lineas) and lineas[siguiente].lstrip().startswith("#"):
            eximidas.add(siguiente + 1)
            siguiente += 1
        if siguiente < len(lineas):
            eximidas.add(siguiente + 1)
    return eximidas


def faltas_en(relativa: str, fuente: str) -> list[tuple[int, str, str]]:
    """Devuelve (linea, palabra escrita, palabra correcta) de cada falta."""
    if relativa.endswith(".py"):
        trozos = prosa_de_python(fuente)
    elif relativa.endswith((".ts", ".tsx")):
        trozos = prosa_de_typescript(fuente)
    else:
        # Markdown y YAML se tratan igual: en ambos el texto legible esta en
        # el cuerpo, y lo que no es prosa lo quitan los filtros de _limpiar.
        trozos = prosa_de_markdown(fuente)

    eximidas = _lineas_eximidas(fuente)
    trozos = [(n, t) for n, t in trozos if n not in eximidas]

    faltas: list[tuple[int, str, str]] = []
    vistas: set[tuple[int, str]] = set()
    for numero, texto in trozos:
        for patron, sin, con in _PATRONES:
            if sin == con:
                continue
            for hallazgo in patron.finditer(texto):
                escrita = hallazgo.group(0)
                if (numero, escrita.lower()) in vistas:
                    continue
                vistas.add((numero, escrita.lower()))
                faltas.append((numero, escrita, con))
    return faltas


def _candidatos(raiz: Path) -> list[str]:
    encontrados: list[str] = []
    for ruta in raiz.rglob("*"):
        if not ruta.is_file() or ruta.suffix not in EXTENSIONES:
            continue
        # Se mira la ruta RELATIVA, no la absoluta. Con la absoluta, un
        # arbol de trabajo bajo `.claude/worktrees/` llevaba `.claude` en su
        # propia raíz, así que TODO fichero quedaba ignorado y la herramienta
        # respondia «conforme» sin haber inspeccionado nada.
        relativa = ruta.relative_to(raiz)
        if any(parte in CARPETAS_IGNORADAS for parte in relativa.parts):
            continue
        encontrados.append(ruta.relative_to(raiz).as_posix())
    return sorted(encontrados)


def verificar_r8(raiz: Path, ficheros: list[str]) -> list[Infraccion]:
    """Busca palabras castellanas sin su tilde en la prosa del repositorio."""
    objetivos = [f.replace("\\", "/") for f in ficheros] or _candidatos(raiz)
    infracciones: list[Infraccion] = []

    for relativa in objetivos:
        if Path(relativa).suffix not in EXTENSIONES or _esta_exento(relativa):
            continue
        ruta = raiz / relativa
        if not ruta.is_file():
            continue
        try:
            fuente = ruta.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if fichero_eximido(fuente):
            continue

        for numero, escrita, correcta in faltas_en(relativa, fuente):
            infracciones.append(
                Infraccion(
                    regla="R8",
                    fichero=relativa,
                    detalle=(
                        f"Linea {numero}: «{escrita}» va con tilde: «{correcta}». "
                        "Este sistema produce texto que leen un profesor y sus "
                        "alumnos. Si es un identificador y no prosa, sacalo de "
                        "la cadena o renombralo."
                    ),
                )
            )
    return infracciones
