"""El alta de alumnos desde los Excel del docente, sin salir del programa.

Hasta el 2026-09-07 el importador solo existía como orden de consola, en
`tools/`, que no viaja dentro del ejecutable. Para la beta eso significaba
que el docente no podía dar de alta a sus propios alumnos sin que alguien le
ejecutara un comando: y sin alumnos dados de alta no hay a quién asignar un
trabajo, ni nombre que tachar antes de mandar el texto al motor.

**Los Excel no se suben: se eligen.** El docente los deja en
`00_LISTADOS_ALUMNOS`, dentro de su propia estructura, y aquí se enumeran y
se importa el que él diga. Es el mismo trato que ya reciben los trabajos de
los alumnos -una carpeta suya que el programa mira, no un fichero que viaja
por una petición-, y tiene la misma razón: un listado con los nombres de
250 alumnos no tiene por qué atravesar nada, ni siquiera dentro de su propio
equipo.

**Lo que devuelve esta API no lleva ningún nombre.** El recuento de altas,
las actualizaciones y las filas pendientes de revisión se identifican por
número de fila del Excel -que el docente puede localizar abriendo su
fichero- y por `student_id`. La correspondencia nombre-identificador se
queda en `backend/privacidad/listado_local.py`, en su equipo.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from backend.empaquetado import config
from backend.persistencia.alumnos import CCAA_CODES, validar_curso
from backend.servicios.importacion_alumnos import (
    ColumnasNoMapeadas,
    cargar_centros_conocidos,
    importar,
    leer_excel,
)

router = APIRouter(prefix="/api")

EXTENSIONES_DE_LISTADO = (".xlsx", ".xlsm")


class ListadoDisponible(BaseModel):
    """Un Excel que espera en la carpeta de listados."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    tamano_kb: int


class PeticionDeImportacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_archivo: str
    ccaa_code: str
    curso: str


class FilaPendienteExpuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fila: int
    motivo: str
    detalle: str


class ResultadoDeImportacion(BaseModel):
    """Sin un solo nombre: filas y códigos."""

    model_config = ConfigDict(extra="forbid")

    nuevas: int
    actualizadas: int
    pendientes: list[FilaPendienteExpuesta]


def _carpeta_de_listados(peticion: Request) -> Path:
    configuracion = peticion.app.state.configuracion
    raiz = getattr(configuracion, "raiz_expedientes", None)
    if raiz is None:
        raise HTTPException(status_code=409, detail=(
            "No hay ninguna arquitectura de expedientes configurada, así que "
            "no se sabe dónde buscar los listados. Indícala en "
            "REVISOR_RAIZ_EXPEDIENTES, en el fichero .env."
        ))
    carpeta = Path(raiz) / "00_LISTADOS_ALUMNOS"
    if not carpeta.is_dir():
        raise HTTPException(status_code=409, detail=(
            f"No existe la carpeta «{carpeta}». Es donde van los Excel de "
            "matrícula de cada comunidad."
        ))
    return carpeta


@router.get("/alumnos/listados")
def listados_disponibles(peticion: Request) -> list[ListadoDisponible]:
    """Los Excel que esperan en `00_LISTADOS_ALUMNOS`."""
    carpeta = _carpeta_de_listados(peticion)
    return [
        ListadoDisponible(
            nombre=ruta.name, tamano_kb=max(1, ruta.stat().st_size // 1024)
        )
        for ruta in sorted(carpeta.iterdir())
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_DE_LISTADO
    ]


@router.post("/alumnos/importacion")
def importar_listado(
    cuerpo: PeticionDeImportacion, peticion: Request
) -> ResultadoDeImportacion:
    """Da de alta a los alumnos de un Excel de la carpeta de listados.

    Ninguna fila dudosa se registra: van a `pendientes`, con su número de
    fila y el motivo, para que el docente las mire a mano. Es el principio
    que él mismo fijó -la automatización puede detenerse; lo que no puede es
    asignar un trabajo al alumno equivocado- aplicado al alta.
    """
    ccaa_code = cuerpo.ccaa_code.strip().upper()
    if ccaa_code not in CCAA_CODES:
        raise HTTPException(status_code=400, detail=(
            f"«{cuerpo.ccaa_code}» no es una comunidad autónoma reconocida. "
            "Las comunidades son: " + ", ".join(CCAA_CODES) + "."
        ))
    try:
        validar_curso(cuerpo.curso)
    except ValueError as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo

    # Solo el nombre del fichero, nunca una ruta: sin esto, un
    # `../../algo.xlsx` leería un Excel de cualquier parte del disco.
    nombre = Path(cuerpo.nombre_archivo).name
    ruta = _carpeta_de_listados(peticion) / nombre
    if not ruta.is_file() or ruta.suffix.lower() not in EXTENSIONES_DE_LISTADO:
        raise HTTPException(status_code=404, detail=(
            f"No se encuentra el listado «{nombre}» en la carpeta de listados."
        ))

    configuracion = peticion.app.state.configuracion
    listado_local = getattr(peticion.app.state, "listado_local", None)
    if listado_local is None:
        raise HTTPException(status_code=409, detail=(
            "No hay carpeta de datos locales configurada, y sin ella no se "
            "puede guardar la correspondencia entre el nombre de cada alumno "
            "y su identificador. Esa correspondencia no va a la base de "
            "datos: vive solo en este equipo. Indícala en "
            "REVISOR_DATOS_LOCALES, en el fichero .env."
        ))

    try:
        filas, cabecera = leer_excel(ruta)
    except Exception as fallo:
        raise HTTPException(status_code=400, detail=(
            f"No se ha podido leer «{nombre}»: {fallo}"
        )) from fallo
    if not filas:
        raise HTTPException(status_code=400, detail=(
            f"El Excel «{nombre}» no tiene filas de datos. Nada que importar."
        ))

    try:
        resultado = importar(
            filas, cabecera, ccaa_code=ccaa_code, curso=cuerpo.curso,
            almacen=peticion.app.state.almacen,
            listado_local=listado_local,
            # `config()` y no la raíz: el catálogo de centros es del docente
            # -cambia cuando abre uno nuevo- y tiene que poder editarlo sin
            # esperar a una versión nueva del programa. Ver
            # `backend/empaquetado.py`.
            centros_conocidos=cargar_centros_conocidos(
                config("centros.yaml", peticion.app.state.raiz), ccaa_code
            ),
        )
    except ColumnasNoMapeadas as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo

    return ResultadoDeImportacion(
        nuevas=resultado.nuevas,
        actualizadas=resultado.actualizadas,
        pendientes=[
            FilaPendienteExpuesta(
                fila=p.fila, motivo=p.motivo, detalle=p.detalle
            )
            for p in resultado.pendientes
        ],
    )
