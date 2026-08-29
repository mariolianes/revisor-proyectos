"""Endpoints del análisis y de la revisión.

Ninguno aprueba, califica ni comunica. El §13 reserva eso al profesor y la
forma de respetarlo sigue siendo que las operaciones no existan.

El análisis se guarda al hacerse y se devuelve tal cual después. Pedir la
ficha no puede volver a llamar al motor: cuesta dinero y, sobre todo, daría
otra cosa, y el docente vería cambiar bajo sus pies un juicio que estaba
revisando.

Un intento de análisis puede acabar de tres formas distintas, y las tres
tienen que llegar al docente sin una traza de Python por en medio:

- Completo: el informe y el borrador, los dos. 200, con `devolucion` puesta.
- Parcial (`InformeSinBorrador`): el análisis salió bien -el informe es
  válido y ya está guardado; la entrega ya ha pasado a ANALIZADO- y solo
  falló la redacción del borrador. No es un fallo del análisis, así que no
  se traduce como un error: se devuelve 200 igual, con `devolucion` a
  `None` y un `aviso` que explica qué falta y por qué. Tratarlo como
  cualquier otro fallo tiraría a la papelera un informe que sí es
  correcto, y es exactamente lo que este endpoint no puede permitirse.
- Fallo del proveedor (`ErrorDelProveedor`): sin red, sin clave, cuota
  agotada, una respuesta que no encaja ni al reintento. No se guarda nada,
  la entrega sigue en el estado en que estaba, y el mensaje del adaptador
  -ya redactado en castellano y ya limpio de cualquier fragmento de la
  clave, ver `backend/analisis/openai.py`- llega tal cual en un 503.

Un archivo que ha dejado de estar donde estaba (`PdfIlegible`) tampoco es un
fallo del servidor: es la parada del §18.2, y llega como 400 con el motivo.

Sobre pulsar el botón dos veces: un análisis habla con un servicio externo y
tarda; un segundo clic sobre la misma entrega mientras el primero sigue en
marcha no debe lanzar una segunda llamada -cuesta dinero otra vez, y el
proveedor simulado de las pruebas ni siquiera tiene una segunda respuesta
programada para darle-. Un candado por entrega, guardado en `app.state`,
basta para rechazar el segundo intento con 409 mientras dura el primero: no
hace falta ni una cola ni un trabajo en segundo plano para eso, y montar
cualquiera de las dos habría sido alcance nuevo que no pedía esta tarea.
"""

from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from backend.analisis.proveedor import ErrorDelProveedor
from backend.extraccion.lectura import PdfIlegible
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe
from backend.servicios.analisis_de_entrega import InformeSinBorrador, analizar_entrega

router = APIRouter(prefix="/api")

_DECISIONES = ("ACEPTADA", "EDITADA", "DESCARTADA")


class ResultadoAnalisis(BaseModel):
    """La corrección completa, o el informe solo cuando el borrador no se
    ha podido completar.

    Es un tipo propio de esta API y no el `Correccion` que devuelve
    `analizar_entrega`: `Correccion` exige una `Devolucion`, y no hay forma
    honesta de rellenarla cuando `InformeSinBorrador` dice justamente que
    no la hay. Forzar aquí una `Devolucion` vacía confundiría ese caso con
    el otro que ya produce una vacía a propósito -`componer()`, cuando no
    hay ni fortalezas ni prioridades de las que redactar nada-, y son dos
    situaciones distintas: una es que no había nada que decirle al alumno,
    la otra es que el motor no llegó a decirlo. `devolucion=None` más
    `aviso` con el motivo es la única forma de no mezclarlas.
    """

    model_config = ConfigDict(extra="forbid")

    entrega: EntregaRegistrada
    informe: Informe
    devolucion: Devolucion | None
    motor: str
    aviso: str | None = None


class Decision(BaseModel):
    dimension: str
    decision: str
    texto: str | None = None


class Revision(BaseModel):
    decisiones: list[Decision]


class EstadoDelMotor(BaseModel):
    nombre: str
    es_simulado: bool
    avisos: list[str]


def _candado(peticion: Request) -> Lock:
    return peticion.app.state.candado_analisis


def _en_curso(peticion: Request) -> set[str]:
    return peticion.app.state.analisis_en_curso


@router.get("/motor")
def obtener_motor(peticion: Request) -> EstadoDelMotor:
    """Con qué motor se analiza ahora mismo. El frontend lo enseña siempre.

    Un análisis hecho con el proveedor simulado no es un análisis: son
    respuestas de prueba, y el docente tiene que saberlo antes de apoyarse
    en cualquiera de las dos salidas.
    """
    proveedor = peticion.app.state.proveedor
    simulado = proveedor.nombre == "simulado"
    return EstadoDelMotor(
        nombre=proveedor.nombre,
        es_simulado=simulado,
        avisos=(
            ["No hay motor de análisis configurado. Lo que veas no es un "
             "análisis: son respuestas de prueba. Indica la clave y el "
             "modelo en OPENAI_API_KEY y REVISOR_MODELO_ANALISIS, dentro "
             "del fichero .env."]
            if simulado else []
        ),
    )


@router.post("/entregas/{identificador}/analisis")
def analizar(identificador: str, peticion: Request) -> ResultadoAnalisis:
    """Analiza la entrega y guarda el resultado para que `GET` lo recupere.

    Ver el docstring del módulo para las tres formas en que puede acabar y
    por qué se traducen así.
    """
    raiz = peticion.app.state.raiz
    configuracion = peticion.app.state.configuracion
    almacen = peticion.app.state.almacen
    proveedor = peticion.app.state.proveedor

    entrega = almacen.por_id(identificador)
    if entrega is None:
        raise HTTPException(status_code=404, detail="No existe esa entrega.")
    if configuracion.carpeta_entregas is None:
        raise HTTPException(
            status_code=409, detail="No hay carpeta de entregas configurada."
        )

    candado = _candado(peticion)
    en_curso = _en_curso(peticion)
    with candado:
        if identificador in en_curso:
            raise HTTPException(status_code=409, detail=(
                "Ya hay un análisis en curso para esta entrega. Espera a "
                "que termine antes de pedir otro: cada intento vuelve a "
                "llamar al motor y a costar dinero."
            ))
        en_curso.add(identificador)

    try:
        try:
            correccion = analizar_entrega(
                raiz, configuracion.carpeta_entregas,
                configuracion.version_criterios, almacen, proveedor, entrega,
            )
        except InformeSinBorrador as fallo:
            resultado = ResultadoAnalisis(
                entrega=fallo.entrega, informe=fallo.informe, devolucion=None,
                motor=proveedor.nombre, aviso=str(fallo),
            )
            peticion.app.state.correcciones[identificador] = resultado
            return resultado
        except ErrorDelProveedor as fallo:
            raise HTTPException(status_code=503, detail=str(fallo)) from fallo
        except PdfIlegible as fallo:
            raise HTTPException(status_code=400, detail=str(fallo)) from fallo
    finally:
        with candado:
            en_curso.discard(identificador)

    resultado = ResultadoAnalisis(
        entrega=correccion.entrega, informe=correccion.informe,
        devolucion=correccion.devolucion, motor=correccion.motor, aviso=None,
    )
    peticion.app.state.correcciones[identificador] = resultado
    return resultado


@router.get("/entregas/{identificador}/analisis")
def obtener_analisis(identificador: str, peticion: Request) -> ResultadoAnalisis:
    resultado = peticion.app.state.correcciones.get(identificador)
    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Esta entrega no se ha analizado todavía.",
        )
    return resultado


@router.post("/entregas/{identificador}/revision")
def revisar(
    identificador: str, cuerpo: Revision, peticion: Request
) -> ResultadoAnalisis:
    """Aplica lo que el docente ha decidido observación por observación.

    Solo lo aprobado se conserva. Es lo que el §13 llama revisión docente, y
    es la única vía por la que una observación llega a considerarse válida.
    """
    resultado = peticion.app.state.correcciones.get(identificador)
    if resultado is None:
        raise HTTPException(
            status_code=404, detail="Esta entrega no se ha analizado todavía."
        )

    por_dimension = {d.dimension: d for d in cuerpo.decisiones}
    for d in cuerpo.decisiones:
        if d.decision not in _DECISIONES:
            raise HTTPException(
                status_code=400,
                detail=f"«{d.decision}» no es una decisión válida. Son: "
                       + ", ".join(_DECISIONES) + ".",
            )

    conservadas = []
    for v in resultado.informe.valoraciones:
        decision = por_dimension.get(v.dimension)
        if decision is None or decision.decision == "ACEPTADA":
            conservadas.append(v)
        elif decision.decision == "EDITADA":
            conservadas.append(v.model_copy(
                update={"observacion": decision.texto or v.observacion}
            ))
        # DESCARTADA: no se conserva.

    informe = resultado.informe.model_copy(update={
        "valoraciones": conservadas,
        "prioridades": [p for p in resultado.informe.prioridades
                        if any(c.dimension == p.dimension for c in conservadas)],
    })
    revisado = resultado.model_copy(update={"informe": informe})
    peticion.app.state.correcciones[identificador] = revisado
    return revisado
