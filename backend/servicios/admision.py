"""La admisión: de un archivo en la bandeja a un expediente, o a Incidencias.

Es la columna vertebral que faltaba. Hasta ahora había piezas sueltas -la
estructura de carpetas, el registro de alumnos, la identificación
determinista, la lectura de la portada- y ninguna se llamaba entre sí. Aquí
se cosen, en el orden que fija el docente en `decisiones#4-portada`:

1. leer el nombre del archivo y los metadatos disponibles,
2. consultar la correspondencia nombre-ID **en local**,
3. leer la portada cuando haga falta,
4. confirmar el `student_id` o mandar el caso a Incidencias,
5. enmascarar el nombre antes de cualquier llamada externa.

Los cuatro primeros pasos son de este módulo. **El quinto no**, y es
deliberado: la minimización ocurre después, al analizar
(`backend/servicios/analisis_de_entrega.py`). Aquí no se llama a ningún
proveedor externo ni sale nada del equipo.

**Nada se mueve y nada se borra.** El archivo original se copia al
expediente con su nombre normalizado y se deja donde estaba, intacto. El
docente no ha dicho qué hacer con el original una vez copiado, y adivinarlo
puede costarle el trabajo de un alumno; mientras no lo diga, la bandeja se
queda como está. Volver a admitir el mismo archivo no duplica nada: la huella
lo reconoce y sale como `DUPLICATE_EXACT`, que es exactamente lo que él pide
para ese caso -«registrar, no analizar, no generar coste API»-.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from backend.expedientes.creacion import crear_expediente
from backend.expedientes.estructura import (
    ConfiguracionExpedientes,
    ruta_entrada_incidencias,
    ruta_expediente,
)
from backend.extraccion import _huella
from backend.identificacion.determinista import (
    CandidatoLocal,
    Identificacion,
    identificar,
)
from backend.persistencia.modelos import EntregaNueva
from backend.identificacion.portada import (
    nombre_confirmado_por_la_portada,
    texto_de_la_portada,
)

# Las marcas del §7 del docente, con su vocabulario.
DUPLICADO_EXACTO = "DUPLICATE_EXACT"
CONFLICTO_DE_VERSION = "VERSION_CONFLICT"

# Por qué un archivo no entra. En castellano, como el resto del sistema.
EXTENSION_NO_ADMITIDA = "EXTENSION_NO_ADMITIDA"
DEMASIADO_GRANDE = "DEMASIADO_GRANDE"
DOC_ANTIGUO = "DOC_ANTIGUO"
SIN_IDENTIFICAR = "SIN_IDENTIFICAR"

UN_MEGABYTE = 1024 * 1024


class EntregaAdmitida(BaseModel):
    """Lo que ya está admitido, para poder reconocer un duplicado.

    Sin nombres: se identifica por `student_id`, como todo lo que cruza esta
    frontera.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: str
    fase: str
    version: int
    huella: str


class Admision(BaseModel):
    """Qué ha pasado con un archivo. Sin ningún nombre de persona."""

    model_config = ConfigDict(extra="forbid")

    archivo: str
    huella: str | None = None
    student_id: str | None = None
    fase: str | None = None
    version: int | None = None
    # Dónde ha quedado la copia, relativa a la raíz de expedientes. `None`
    # cuando el archivo no ha llegado a copiarse a ningún sitio.
    destino: str | None = None
    marca: str | None = None
    a_incidencias: bool = False
    motivo: str = ""

    @property
    def admitido(self) -> bool:
        return self.destino is not None and not self.a_incidencias


def nombre_normalizado(student_id: str, fase: str, version: int, extension: str) -> str:
    """`ALU-260001_E02_v01.pdf`, la forma que fija el docente.

    Él lo cerró en `decisiones#2-identificador`: el alumno entrega con el
    nombre que quiera y es el sistema el que renombra después, nunca antes.
    """
    return f"{student_id}_{fase}_v{version:02d}{extension.lower()}"


def _nombre_de_persona_del_archivo(archivo: Path) -> str:
    """El nombre que trae el archivo, para poder compararlo con el listado.

    No se adivina nada: se sustituyen por espacios los separadores que usan
    las plataformas -guiones bajos, guiones, puntos- y se deja que la
    normalización de `backend/identificacion/nombres.py` haga el resto. Si lo
    que sale no es un nombre de persona, no encajará con ningún alumno y el
    caso irá a Incidencias, que es lo correcto.
    """
    return archivo.stem.replace("_", " ").replace("-", " ").replace(".", " ")


def _problema_del_archivo(
    archivo: Path, cfg: ConfiguracionExpedientes, es_defensa: bool
) -> tuple[str, str] | None:
    """Motivo y explicación si el archivo no puede entrar, o `None`."""
    extension = archivo.suffix.lower().lstrip(".")
    admitidas = (
        cfg.archivos.extensiones_de_defensa if es_defensa
        else cfg.archivos.extensiones_del_proyecto
    )
    if extension == "doc":
        return DOC_ANTIGUO, (
            "es un documento de Word antiguo (.doc). El docente lo dejó como "
            "incidencia técnica: no se analiza directamente. Conviértelo a "
            "PDF o DOCX y vuelve a dejarlo en la bandeja."
        )
    if extension not in admitidas:
        return EXTENSION_NO_ADMITIDA, (
            f"su extensión «.{extension}» no está admitida. Se admiten: "
            + ", ".join(f".{e}" for e in admitidas) + "."
        )
    limite = cfg.archivos.tamano_maximo_mb
    tamano = archivo.stat().st_size
    if tamano > limite * UN_MEGABYTE:
        return DEMASIADO_GRANDE, (
            f"ocupa {tamano / UN_MEGABYTE:.1f} MB y el límite es {limite} MB."
        )
    return None


def _carpeta_de_la_fase(cfg: ConfiguracionExpedientes, codigo_fase: str):
    """La carpeta del expediente donde va una entrega de esa fase, o `None`.

    Devuelve la carpeta entera y no solo su nombre porque quien llama
    necesita saber también si lleva las cinco subcarpetas: una entrega
    evaluable va a `00_ORIGINAL`, y la presentación de la defensa va a la
    carpeta a secas, porque `06_DEFENSA` no tiene esa subestructura.
    """
    # Se busca en las carpetas del expediente, no en las fases de la
    # bandeja: no son la misma lista. La bandeja tiene cuatro carpetas -las
    # cuatro entregas evaluables-, y el expediente ocho, porque TEMA y
    # DEFENSA también reciben documento aunque no lleguen por una carpeta
    # vigilada propia. Una presentación de defensa entra por la bandeja FINAL
    # y se separa por tipo, como pide decisiones#9-carpetas.
    return next(
        (c for c in cfg.expediente_alumno.carpetas if c.fase == codigo_fase),
        None,
    )


def admitir(
    *,
    archivo: Path,
    codigo_comunidad: str,
    codigo_fase: str,
    cfg: ConfiguracionExpedientes,
    raiz_repositorio: Path,
    raiz_expedientes: Path,
    candidatos: list[CandidatoLocal],
    ya_admitidas: list[EntregaAdmitida],
    platform_id: str | None = None,
) -> Admision:
    """Admite un archivo de la bandeja, o dice por qué no.

    `candidatos` son los alumnos del curso y la comunidad esperados, con su
    nombre: vienen del listado local del docente y **no salen de aquí**.
    `Admision` no lleva ninguno.
    """
    resultado = Admision(archivo=archivo.name)

    es_defensa = codigo_fase == "DEFENSA"
    problema = _problema_del_archivo(archivo, cfg, es_defensa)
    if problema is not None:
        motivo, explicacion = problema
        resultado.a_incidencias = True
        resultado.marca = motivo
        resultado.motivo = f"«{archivo.name}» no entra: {explicacion}"
        resultado.destino = _a_incidencias(archivo, cfg, codigo_comunidad, raiz_expedientes)
        return resultado

    resultado.huella = _huella(archivo)

    # La portada solo se lee cuando el archivo es un PDF y hace falta: es la
    # evidencia auxiliar del docente, no una lectura por costumbre.
    nombre_de_portada = None
    if archivo.suffix.lower() == ".pdf":
        try:
            nombre_de_portada = nombre_confirmado_por_la_portada(
                texto_de_la_portada(archivo), candidatos
            )
        except Exception:
            # Un PDF ilegible no impide identificar por las otras dos vías.
            # Si tampoco bastan, el caso irá a Incidencias con su motivo.
            nombre_de_portada = None

    identificacion: Identificacion = identificar(
        candidatos=candidatos,
        platform_id=platform_id,
        nombre_del_archivo=_nombre_de_persona_del_archivo(archivo),
        nombre_de_portada=nombre_de_portada,
    )
    if identificacion.student_id is None:
        resultado.a_incidencias = True
        resultado.marca = SIN_IDENTIFICAR
        resultado.motivo = (
            f"«{archivo.name}» no se ha podido asignar a ningún alumno: "
            f"{identificacion.motivo}."
        )
        resultado.destino = _a_incidencias(archivo, cfg, codigo_comunidad, raiz_expedientes)
        return resultado

    resultado.student_id = identificacion.student_id
    resultado.fase = codigo_fase

    # El §7 del docente: mismo archivo y misma huella es un duplicado exacto;
    # un archivo distinto para la misma fase es un conflicto de versión.
    de_esta_fase = [
        e for e in ya_admitidas
        if e.student_id == identificacion.student_id and e.fase == codigo_fase
    ]
    duplicado = next((e for e in de_esta_fase if e.huella == resultado.huella), None)
    if duplicado is not None:
        resultado.marca = DUPLICADO_EXACTO
        resultado.version = duplicado.version
        resultado.motivo = (
            "Ya estaba admitido, con el mismo contenido. No se analiza otra "
            "vez ni se sobrescribe el original."
        )
        return resultado

    resultado.version = max((e.version for e in de_esta_fase), default=0) + 1
    if de_esta_fase:
        resultado.marca = CONFLICTO_DE_VERSION
        resultado.motivo = (
            f"Es un archivo distinto para una fase que ya tenía entrega. Se "
            f"conserva como versión {resultado.version} y el análisis espera "
            "a que elijas cuál vale."
        )

    carpeta = _carpeta_de_la_fase(cfg, codigo_fase)
    if carpeta is None:
        resultado.a_incidencias = True
        resultado.motivo = (
            f"La fase «{codigo_fase}» no tiene carpeta en el expediente."
        )
        return resultado

    # Creación diferida: el expediente nace ahora, con la primera entrega, y
    # no al importar el listado. Es lo que evita doscientas carpetas vacías
    # sin perder de vista quién no ha entregado. Es idempotente.
    crear_expediente(
        raiz_repositorio, raiz_expedientes, cfg, identificacion.student_id
    )

    dentro = ruta_expediente(cfg, identificacion.student_id) / carpeta.carpeta
    if carpeta.tiene_entregas:
        # `00_ORIGINAL`: el archivo tal como lo entregó el alumno, solo
        # renombrado. Las otras cuatro subcarpetas las llenan pasos
        # posteriores -procesado, informe, feedback, evidencias-.
        dentro = dentro / cfg.expediente_alumno.subcarpetas_de_entrega[0]
    destino = dentro / nombre_normalizado(
        identificacion.student_id, codigo_fase, resultado.version,
        archivo.suffix,
    )
    completa = raiz_expedientes / destino
    completa.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archivo, completa)
    # `as_posix` y no `str`: una ruta guardada con las barras invertidas de
    # Windows es ilegible desde cualquier otro sitio y se rompe al partirla
    # por el separador. Lo que va a la base es una ruta de texto, no una ruta
    # de este sistema operativo. Se vio guardando la primera de verdad.
    resultado.destino = destino.as_posix()
    if not resultado.motivo:
        resultado.motivo = "Admitida."
    return resultado


def _a_incidencias(
    archivo: Path, cfg: ConfiguracionExpedientes, codigo_comunidad: str,
    raiz_expedientes: Path,
) -> str | None:
    """Copia el archivo a la carpeta de incidencias de su comunidad.

    Con su nombre original y sin normalizar: un archivo que no se ha podido
    asignar a nadie no tiene un ID con el que renombrarlo, y ponerle uno
    inventado sería justamente el error que todo esto evita.
    """
    try:
        relativa = ruta_entrada_incidencias(cfg, codigo_comunidad)
    except ValueError:
        return None
    destino = raiz_expedientes / relativa / archivo.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archivo, destino)
    return (relativa / archivo.name).as_posix()


def entrega_desde(
    admision: Admision, *, ciclo: str, version_criterios: str,
    modalidad: str | None = None,
) -> EntregaNueva:
    """La entrega que corresponde a una admisión, lista para registrarse.

    Es el puente entre lo que la admisión decide y lo que la base guarda:
    hasta que existió, `marca_admision`, `estado_version` y `ruta_expediente`
    se calculaban y se perdían.

    `ciclo` y `version_criterios` no salen de aquí porque la admisión no los
    conoce: el ciclo es del alumno -lo tiene el registro maestro- y la
    versión de criterios es del curso. Pedirlos explícitamente evita que este
    módulo se invente ninguno de los dos.

    Levanta `ValueError` si la admisión no llegó a admitir nada: un duplicado
    exacto o un caso mandado a Incidencias no produce una entrega nueva, y
    construir una a partir de ellos sería registrar dos veces el mismo
    trabajo o dar por bueno uno que no se pudo asignar.
    """
    if not admision.admitido:
        raise ValueError(
            f"«{admision.archivo}» no se admitió, así que no hay entrega que "
            f"registrar: {admision.motivo}"
        )
    return EntregaNueva(
        codigo_alumno=admision.student_id or "",
        ciclo=ciclo,
        fase=admision.fase or "",
        version=admision.version or 1,
        nombre_archivo=admision.archivo,
        huella=admision.huella or "",
        version_criterios=version_criterios,
        modalidad=modalidad,
        marca_admision=admision.marca,
        # Un conflicto de versión entra igual como vigente: el docente
        # todavía no ha elegido cuál vale, y marcarla ya como sustituida
        # sería decidir por él. Lo que hace el conflicto es detener el
        # análisis, no degradar la entrega.
        ruta_expediente=admision.destino,
    )
