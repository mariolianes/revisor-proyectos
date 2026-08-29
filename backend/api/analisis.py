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
  Ese `aviso` se compone aquí, no se reenvía `str(fallo)` tal cual: el
  texto de dominio -de `BorradorNoValido`, en `salidas/borrador.py`- puede
  terminar en «pide de nuevo la redacción», y eso da a entender que existe
  una operación que repite solo el borrador. No existe -esta tarea no la
  construye a propósito-, y la única vía real es `POST /analisis` entero,
  que repite el análisis completo. Prometer un atajo que no hay es peor
  que no decir nada. Ver `_aviso_de_borrador_incompleto`.
- Fallo del proveedor (`ErrorDelProveedor`): sin red, sin clave, cuota
  agotada, una respuesta que no encaja ni al reintento. No se guarda nada,
  la entrega sigue en el estado en que estaba, y lo que llega en el 503 es
  `fallo.mensaje_para_el_profesor` -el contrato explícito de
  `ErrorDelProveedor` (`backend/analisis/proveedor.py`), no `str(fallo)`
  directo-. Hoy coinciden: el adaptador de OpenAI ya redacta ese mensaje
  en castellano y limpio de cualquier fragmento de la clave (ver
  `backend/analisis/openai.py`), y por omisión la propiedad devuelve
  justo ese texto. Pero esta capa no confía en esa coincidencia sin
  nombrarla: pasar por la propiedad, no por `str()`, es lo que obliga a
  cualquier proveedor futuro a decidir qué le enseña al docente.

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
from backend.salidas.borrador import BorradorNoValido, Devolucion
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


def _aviso_de_borrador_incompleto(fallo: InformeSinBorrador) -> str:
    """El aviso que ve el profesor cuando el informe salió bien pero el
    borrador no. Se compone en esta capa, no se reenvía el texto de dominio.

    `InformeSinBorrador` guarda la causa original en `__cause__` -así la
    levanta `analizar_entrega`, con `raise ... from fallo`-, y esa causa
    puede ser `BorradorNoValido` o `ErrorDelProveedor`. El texto de
    `BorradorNoValido` combina el motivo con una sugerencia -«Corrígelo a
    mano o pide de nuevo la redacción»- que aquí no se sostiene: no hay
    ninguna operación que repita solo la redacción, así que ese fragmento
    no se reenvía. El de `ErrorDelProveedor` se toma de
    `mensaje_para_el_profesor` -el contrato explícito de ese tipo, no
    `str(fallo)`-, y ese sí se cita tal cual: ya está escrito para el
    docente y no trae esa promesa concreta.

    La acción de verdad disponible -volver a pedir el análisis entero por
    `POST /analisis`- se dice siempre, la ponga o no la causa original.
    """
    causa = fallo.__cause__
    if isinstance(causa, BorradorNoValido):
        motivo = (
            "el texto que ha propuesto el motor incumplía una de las "
            "reglas que no se negocian sobre lo que puede decirle a un "
            "alumno."
        )
    elif isinstance(causa, ErrorDelProveedor):
        motivo = causa.mensaje_para_el_profesor
    elif causa is not None:  # pragma: no cover - `analizar_entrega` no
        # levanta InformeSinBorrador con ninguna otra causa; se cubre por
        # si acaso, sin asumir que eso vaya a seguir siendo cierto siempre.
        motivo = str(causa)
    else:  # pragma: no cover - siempre llega con `from fallo`.
        motivo = "no se ha podido completar."
    return (
        "El análisis se ha completado: el informe es válido y ya se puede "
        "usar para decidir. El borrador de devolución para el alumno no se "
        f"ha podido generar. Motivo: {motivo} No hay una forma de pedir "
        "solo el borrador otra vez: para reintentarlo hay que volver a "
        "pedir el análisis completo, que se repite entero. Mientras tanto, "
        "el borrador se puede redactar a mano."
    )


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
                motor=proveedor.nombre,
                aviso=_aviso_de_borrador_incompleto(fallo),
            )
            peticion.app.state.correcciones[identificador] = resultado
            return resultado
        except ErrorDelProveedor as fallo:
            raise HTTPException(
                status_code=503, detail=fallo.mensaje_para_el_profesor
            ) from fallo
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
