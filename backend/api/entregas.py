"""Endpoints del flujo de entregas.

Todo lo que devuelven es interno y provisional. Ningún endpoint aprueba
nada, califica nada ni comunica nada al alumno: el §13 reserva eso al
profesor, y la forma de respetarlo es que las operaciones no existan.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.configuracion import Configuracion
from backend.extraccion import medir
from backend.extraccion.lectura import PdfIlegible
from backend.persistencia.modelos import (
    ESTADOS,
    Almacen,
    EntregaNueva,
    EntregaRegistrada,
)
from backend.servicios.lectura_objetiva import FichaDeLectura, leer, localizar
from backend.vigilancia.carpeta import ArchivoVisto, mirar

router = APIRouter(prefix="/api")

# Los únicos estados que esta API sabe fijar. Los siete del §16.1 están en
# `persistencia.modelos.ESTADOS` y en el enum de la tabla: no se quitan de
# ahí, porque la segunda parte del flujo los necesitará. Lo que no puede
# existir es la operación que los fije desde aquí -APROBADO y COMUNICADO
# son dos de las nueve decisiones que el §13 reserva al profesor-, y una
# lista corta y explícita es más difícil de ampliar por descuido que un
# `if estado in (...)` escondido en el cuerpo.
ESTADOS_DE_ESTA_API: tuple[str, ...] = ("RECIBIDO", "BLOQUEADO", "ANALIZADO")


class Confirmacion(BaseModel):
    """Lo que el docente confirma de un archivo pendiente.

    `modalidad` puede faltar: el nombre del archivo no la codifica (§15.3) y
    todavía no existe una pantalla propia de validación de tema (§3.2) desde
    la que fijarla antes de la primera entrega. Cuando se declara, es del
    proyecto, no de esta entrega -el mismo caso que `ciclo`- y `registrar`
    decide qué hacer si ya estaba fijada por una entrega anterior.
    """

    nombre_archivo: str
    codigo_alumno: str
    ciclo: str
    fase: str
    version: int = 1
    modalidad: str | None = None


class CambioDeEstado(BaseModel):
    estado: str
    motivo: str | None = None


class Entorno(BaseModel):
    """Lo que el frontend necesita saber para avisar al docente."""

    hay_carpeta: bool
    carpeta: str | None
    persistencia_duradera: bool
    version_criterios: str
    # Qué motor va a analizar, tal como lo nombra el propio proveedor
    # («openai:gpt-5.6-luna», o «simulado»). Se expone antes de analizar y no
    # solo después, para que el docente sepa con qué va a gastar antes de
    # pulsar: hasta ahora el nombre del motor solo aparecía cuando el
    # análisis ya se había hecho y ya se había pagado.
    motor: str
    avisos: list[str]


def _raiz(peticion: Request) -> Path:
    return peticion.app.state.raiz


def _configuracion(peticion: Request) -> Configuracion:
    return peticion.app.state.configuracion


def _almacen(peticion: Request) -> Almacen:
    return peticion.app.state.almacen


@router.get("/entorno")
def obtener_entorno(peticion: Request) -> Entorno:
    configuracion = _configuracion(peticion)
    almacen = _almacen(peticion)

    avisos = []
    if configuracion.carpeta_entregas is None:
        # El motivo concreto manda sobre el genérico. `revisar_carpeta`
        # redacta tres -no existe, no es una carpeta, está dentro del
        # repositorio- y cada uno dice qué corregir; el genérico solo vale
        # cuando de verdad no se ha indicado ninguna, porque a quien sí la
        # indicó le estaría diciendo algo que no es cierto.
        avisos.append(configuracion.problema_carpeta or (
            "No hay carpeta de entregas configurada, así que no se vigila "
            "ninguna. Indícala en REVISOR_CARPETA_ENTREGAS, en el fichero .env, "
            "y tiene que estar fuera de este repositorio."
        ))
    if not almacen.es_duradero:
        avisos.append(
            "No hay credenciales de Supabase: lo que registres vive solo "
            "mientras el programa esté abierto y se pierde al cerrarlo."
        )

    return Entorno(
        hay_carpeta=configuracion.carpeta_entregas is not None,
        carpeta=str(configuracion.carpeta_entregas)
                if configuracion.carpeta_entregas else None,
        persistencia_duradera=almacen.es_duradero,
        version_criterios=configuracion.version_criterios,
        motor=peticion.app.state.proveedor.nombre,
        avisos=avisos,
    )


@router.get("/entregas/pendientes")
def obtener_pendientes(peticion: Request) -> list[ArchivoVisto]:
    """Los archivos de la carpeta que aún no se han confirmado."""
    carpeta = _configuracion(peticion).carpeta_entregas
    if carpeta is None:
        return []
    registrados = {
        entrega.nombre_archivo for entrega in _almacen(peticion).listar()
    }
    return mirar(carpeta, registrados)


@router.get("/entregas")
def obtener_entregas(peticion: Request) -> list[EntregaRegistrada]:
    return _almacen(peticion).listar()


@router.post("/entregas")
def confirmar(cuerpo: Confirmacion, peticion: Request) -> FichaDeLectura:
    """El docente confirma de quién y de qué fase es el archivo.

    Esta es la decisión que D-009 le reserva. El sistema propuso; aquí se
    registra lo que él dice, no lo que se dedujo.
    """
    configuracion = _configuracion(peticion)
    if configuracion.carpeta_entregas is None:
        raise HTTPException(
            status_code=409,
            detail="No hay carpeta de entregas configurada.",
        )

    ruta = localizar(configuracion.carpeta_entregas, cuerpo.nombre_archivo)
    if ruta is None:
        raise HTTPException(
            status_code=404,
            detail=f"«{cuerpo.nombre_archivo}» no está en la carpeta de entregas.",
        )

    try:
        huella = medir(ruta).huella
    except PdfIlegible as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo

    # La ruta relativa a la carpeta -no el nombre suelto del archivo- es lo
    # que `mirar` compara para decidir qué sigue pendiente (Task 9): dos
    # alumnos pueden dejar un archivo con el mismo nombre en subcarpetas
    # distintas, y guardar solo el nombre haría que uno tapase al otro para
    # siempre en la bandeja de pendientes.
    relativa = ruta.relative_to(configuracion.carpeta_entregas).as_posix()

    almacen = _almacen(peticion)
    # Se mira antes de registrar: si la huella ya estaba, `registrar` no
    # falla ni crea una segunda ficha -devuelve la que ya había-, y aquí es
    # donde se distingue ese caso legítimo (mismos datos declarados; ver
    # `_choca_con_lo_declarado` en persistencia) del alta nueva, para
    # poder avisar de que no ha pasado nada nuevo.
    ya_registrada = almacen.por_huella(huella)
    try:
        # La declaración se guarda aparte para poder compararla luego con lo
        # que el almacén ha guardado de verdad: `EntregaNueva` normaliza los
        # tres campos de identidad, así que comparar contra ella es comparar
        # lo mismo con lo mismo, y no un texto crudo del formulario contra
        # un valor ya normalizado.
        declarada = EntregaNueva(
            codigo_alumno=cuerpo.codigo_alumno.strip().upper(),
            ciclo=cuerpo.ciclo.strip().upper(),
            fase=cuerpo.fase.strip().upper(),
            version=cuerpo.version,
            nombre_archivo=relativa,
            huella=huella,
            version_criterios=configuracion.version_criterios,
            modalidad=cuerpo.modalidad.strip().upper() if cuerpo.modalidad else None,
        )
        entrega = almacen.registrar(declarada)
    except ValueError as fallo:
        # La huella ya estaba registrada, pero con otro alumno, ciclo, fase
        # o versión declarados: es un error de atribución (persistencia.py),
        # no un fallo del servidor. El profesor tiene que leer el motivo,
        # no un 500 genérico.
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo

    ficha = leer(
        _raiz(peticion), configuracion.carpeta_entregas,
        configuracion.version_criterios, almacen, entrega,
    )

    avisos: list[str] = []

    if ya_registrada is not None and ya_registrada.id == entrega.id:
        avisos.append(
            f"Este archivo ya estaba registrado como entrega desde el "
            f"{ya_registrada.recibida_en:%d/%m/%Y %H:%M} (ficha "
            f"{entrega.id}). No se ha creado una ficha nueva; si lo has "
            "movido de carpeta, es lo esperado."
        )

    if declarada.ciclo != entrega.ciclo:
        # El ciclo es del alumno, no de la entrega: en la base de datos lo
        # tiene la tabla `alumno` y la tabla `entrega` no. Así que el ciclo
        # con el que el alumno está dado de alta manda sobre el que se
        # declara ahora, y los dos almacenes hacen lo mismo.
        #
        # Eso normaliza en silencio lo que casi siempre es un error del
        # profesor -una errata en el ciclo, o un código de alumno
        # reutilizado-, y callarlo sería lo contrario de lo que hace el
        # resto del sistema. Es un aviso, no un error: la entrega es
        # legítima y el trabajo de un alumno no puede quedarse fuera por un
        # dato administrativo. Quien decide qué hacer es el profesor.
        avisos.append(
            f"Has declarado el ciclo {declarada.ciclo}, pero "
            f"{entrega.codigo_alumno} está registrado con el ciclo "
            f"{entrega.ciclo}, y es el que se ha usado: el ciclo es del "
            "alumno, no de cada entrega. Si es una errata, ya sabes cuál de "
            "los dos está mal; si el alumno ha cambiado de ciclo de verdad, "
            "hay que corregirlo en su ficha de alumno, y eso no se hace "
            "desde aquí. La entrega ha quedado registrada igual."
        )

    if declarada.modalidad is not None and declarada.modalidad != entrega.modalidad:
        # La modalidad es del proyecto, no de la entrega -igual que el
        # ciclo es del alumno-, así que la primera que se fijó manda sobre
        # la que se declara ahora. Aquí no se normaliza en silencio: el §3.2
        # exige decisión expresa del profesor para un cambio de modalidad, y
        # el §13 se la reserva. El sistema no la cambia por su cuenta ni
        # aunque el docente la declare distinta al confirmar una entrega
        # posterior; si de verdad ha cambiado, hace falta una vía que la
        # actualice a propósito, que hoy no existe. La entrega queda
        # registrada con la modalidad que ya tenía el proyecto.
        avisos.append(
            f"Has declarado la modalidad {declarada.modalidad}, pero el "
            f"proyecto de {entrega.codigo_alumno} ya está fijado en "
            f"{entrega.modalidad}, y es la que se ha usado: la modalidad es "
            "del proyecto, no de cada entrega, y cambiarla es una decisión "
            "expresa del profesor (§3.2), no algo que esta pantalla pueda "
            "decidir por sí sola. La entrega ha quedado registrada igual."
        )

    if ficha.aviso:
        avisos.append(ficha.aviso)
    ficha.aviso = " ".join(avisos)

    return ficha


@router.get("/entregas/{identificador}")
def obtener_ficha(identificador: str, peticion: Request) -> FichaDeLectura:
    """La ficha completa. Las medidas se recalculan, no se guardan."""
    almacen = _almacen(peticion)
    entrega = almacen.por_id(identificador)
    if entrega is None:
        raise HTTPException(
            status_code=404, detail="No existe esa entrega."
        )
    configuracion = _configuracion(peticion)
    if configuracion.carpeta_entregas is None:
        raise HTTPException(
            status_code=409, detail="No hay carpeta de entregas configurada."
        )
    return leer(
        _raiz(peticion), configuracion.carpeta_entregas,
        configuracion.version_criterios, almacen, entrega,
    )


@router.post("/entregas/{identificador}/estado")
def cambiar_estado(
    identificador: str, cuerpo: CambioDeEstado, peticion: Request
) -> EntregaRegistrada:
    """Solo los tres estados que esta parte del flujo usa.

    Los siete del §16.1 siguen existiendo en el modelo y en la base de
    datos; lo que se cierra es la puerta de esta API. Aprobar y comunicar
    son dos de las nueve decisiones que el §13 reserva al profesor, y la
    forma de respetarlo -lo dice el docstring de este módulo- es que las
    operaciones no existan.
    """
    # Un estado que no existe lo explica mejor el almacén -dice cuáles son
    # los siete-, así que aquí solo se cierra la puerta a los que existen y
    # no le tocan a esta API.
    if cuerpo.estado in ESTADOS and cuerpo.estado not in ESTADOS_DE_ESTA_API:
        raise HTTPException(status_code=400, detail=(
            f"«{cuerpo.estado}» no se puede fijar desde aquí. Esta parte del "
            "flujo solo mueve la entrega entre " +
            ", ".join(ESTADOS_DE_ESTA_API) + ". Aprobar y comunicar "
            "corresponden a la segunda parte del flujo y son decisiones del "
            "profesor (§13), no de esta API."
        ))
    try:
        cambiada = _almacen(peticion).cambiar_estado(
            identificador, cuerpo.estado, cuerpo.motivo
        )
    except ValueError as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo
    if cambiada is None:
        raise HTTPException(status_code=404, detail="No existe esa entrega.")
    return cambiada


@router.post("/entregas/{identificador}/version-elegida")
def elegir_version(identificador: str, peticion: Request) -> EntregaRegistrada:
    """El docente elige qué versión de una fase vale.

    Es una de las decisiones que el §13 le reserva, y por eso es una
    operación explícita suya y no algo que el sistema resuelva al detectar
    el conflicto: cuando llegan dos archivos para la misma fase, la
    admisión los conserva los dos, marca el conflicto y **detiene el
    análisis** hasta que él pulse aquí. Ver `decisiones#7-versiones`.

    Las otras versiones pasan a sustituidas. Ninguna se elimina: «nunca se
    eliminan», dice él, y por eso esta operación no borra nada.
    """
    elegida = _almacen(peticion).elegir_version(identificador)
    if elegida is None:
        raise HTTPException(status_code=404, detail="No existe esa entrega.")
    return elegida
