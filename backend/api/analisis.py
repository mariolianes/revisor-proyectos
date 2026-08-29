"""Endpoints del análisis y de la revisión.

Ninguno aprueba, califica ni comunica. El §13 reserva eso al profesor y la
forma de respetarlo sigue siendo que las operaciones no existan.

El análisis se guarda al hacerse -en el almacén, `Almacen.guardar_correccion`
de `backend/persistencia/modelos.py`- y se devuelve tal cual después. Pedir
la ficha no puede volver a llamar al motor: cuesta dinero y, sobre todo,
daría otra cosa, y el docente vería cambiar bajo sus pies un juicio que
estaba revisando.

Guardar una revisión del docente (`POST .../revision`) usa el mismo método
que guardar un análisis: una entrega tiene una corrección -`unique
(entrega_id)` en la migración-, y aplicar una revisión sustituye la
corrección entera por la que resulta de aplicarla, igual que reanalizar
sustituye la de un intento anterior. No hay un tercer método para «editar
en el sitio»: sería otra forma de decir lo mismo con más superficie que
mantener.

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

Antes de tocar nada de lo anterior, `analizar()` comprueba
`proteccion_datos_pendiente()` -la misma función de `tools/calibrar.py`, no
una copia-: mientras `proteccion_datos` siga PENDIENTE_OFICIAL en
`docs/PENDIENTE_OFICIAL.md`, este endpoint es la vía por la que el trabajo
real de un alumno saldría hacia un proveedor externo, y esa decisión tiene
que ser del docente, consciente, no del sistema por omisión. La guarda no
es un bloqueo permanente: exige `confirmo_datos_reales: true` en el cuerpo
de la petición, una confirmación explícita por cada análisis -no se
recuerda entre peticiones, con el mismo criterio que `--confirmo` en el
arnés de calibración no se recuerda entre ejecuciones-, y sin ella
responde 428 con el aviso completo (`AVISO_PROTECCION_DATOS`). Quien
integre esto en la pantalla decide cómo pedir esa confirmación; este
endpoint solo garantiza que, sin ella, no se envía nada.

Y solo se comprueba cuando de verdad hay algo que salga: la guarda también
exige `proveedor.nombre != "simulado"`. `AVISO_PROTECCION_DATOS` dice que
«el texto íntegro del documento se envía a un proveedor de análisis
externo», y con el motor simulado eso no ocurre -`ProveedorSimulado` no
habla con ningún servicio, devuelve lo que la prueba le programó-. Pedir
una confirmación consciente para un envío que no va a pasar no protege
nada: enseña al docente a aceptar el aviso sin leerlo, que es justo lo
contrario de lo que esta guarda busca para cuando el motor sí sea el real.

`revisar()` puede fallar por un motivo que no tenía manejador: el docente
edita una observación y el texto que escribe supera un límite. Ese límite
no es el mismo que el del motor: `LIMITE_DE_OBSERVACION` (800,
`backend/persistencia/correccion.py`) existe por D-001 -un motor verboso
podría reconstruir el trabajo del alumno por el campo de la observación,
sin tocar el límite de la cita-, y el docente no tiene ese riesgo -no va a
pegar el trabajo de su propio alumno dentro de su propia observación sobre
ese trabajo-, así que su edición se guarda con `LIMITE_DE_OBSERVACION_DOCENTE`
(2400), más holgado: un límite que solo evita un campo sin fondo, no que
defiende D-001. `guardar_correccion` valida antes de escribir y
levanta `TextoFueraDeLimite` si aun así se pasa -no se guarda ni esa
edición ni ninguna otra decisión de la misma petición-, y aquí se captura y
se traduce a 400 con un mensaje compuesto para el docente, no con
`str(fallo)`: ese texto asume que lo largo lo escribió el motor, y aquí lo
ha escrito él a mano. Ver `_mensaje_de_edicion_demasiado_larga`.

`analizar()` puede toparse con la misma excepción por el motivo contrario:
el motor devuelve una observación que supera su propio límite,
`LIMITE_DE_OBSERVACION`. Aquí `str(fallo)` sí describe lo que ha pasado
-el texto largo es del motor-, pero no basta con dejarlo subir sin
capturar: `analizar_entrega` ya ha marcado la entrega ANALIZADO antes de
que este endpoint intente guardar la corrección, así que un
`guardar_correccion` que falla aquí sin capturar dejaría la entrega marcada
como analizada sin ninguna corrección detrás -el docente la vería como
«analizada» y no habría nada que revisar-, además del «Internal Server
Error» crudo de siempre. Por eso se captura, se revierte la entrega a
RECIBIDO -el estado no miente- y se traduce a 503 con un mensaje que dice
que no ha sido un fallo suyo ni del alumno, y que nada se ha guardado. Ver
`_guardar_o_fallar` y `_mensaje_de_desbordamiento_del_motor`.

`guardar_correccion` puede fallar por un tercer motivo, ajeno al texto por
completo: `ErrorDeAlmacen` (`backend/persistencia/supabase.py`) -la red
caída, la clave caducada, cualquier 4xx de PostgREST que no sea el choque
de una restricción `unique`-. El mismo punto ciego que dejaba pasar el
`TextoFueraDeLimite` sin capturar lo dejaba pasar también a este: la
entrega ya está ANALIZADO cuando `guardar_correccion` se llama, así que un
`ErrorDeAlmacen` sin capturar aquí dejaba la entrega marcada como analizada
sin corrección detrás, con el profesor habiendo pagado la llamada al motor
y sin llevarse nada. El manejador global de `ErrorDeAlmacen`
(`backend/app.py`) ya traduce el mensaje a un 503 legible -por eso
`_guardar_o_fallar` no compone uno nuevo para este caso, solo revierte el
estado y deja subir la misma excepción-, pero ese manejador no sabe nada
del estado de la entrega: revertirlo es cosa de esta capa. Ver
`_guardar_o_fallar`.
"""

from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from backend.analisis.proveedor import ErrorDelProveedor
from backend.extraccion.lectura import PdfIlegible
from backend.persistencia.correccion import (
    LIMITE_DE_OBSERVACION_DOCENTE,
    TextoFueraDeLimite,
)
from backend.persistencia.modelos import EntregaRegistrada
from backend.persistencia.supabase import ErrorDeAlmacen
from backend.salidas.borrador import BorradorNoValido, Devolucion
from backend.salidas.informe import Informe, componer_resumen
from backend.salidas.seleccion import SeleccionDePrioridades
from backend.servicios.analisis_de_entrega import InformeSinBorrador, analizar_entrega
from tools.calibrar import proteccion_datos_pendiente

router = APIRouter(prefix="/api")

_DECISIONES = ("ACEPTADA", "EDITADA", "DESCARTADA")

# El mismo aviso que ya usa `tools/calibrar.py` para su banco de nueve casos
# históricos, adaptado a que aquí quien lo lee es el docente en el momento
# de analizar una entrega, no un desarrollador leyendo la salida de una CLI.
# `proteccion_datos_pendiente()` es la misma función en los dos sitios: no
# se duplica el criterio de cuándo avisar, solo el texto de cómo se avisa,
# porque el lector y el gesto disponible para seguir no son los mismos.
AVISO_PROTECCION_DATOS = (
    "Analizar esta entrega envía el texto íntegro del documento a un "
    "proveedor de análisis externo. Las condiciones de protección de "
    "datos para tratar documentos reales de alumnos con esa herramienta "
    "todavía no están cerradas (proteccion_datos, pendiente en "
    "docs/PENDIENTE_OFICIAL.md). Si esto es una prueba con un documento "
    "tuyo, puedes seguir sin problema. Pero si es el trabajo real de un "
    "alumno, la decisión de mandarlo fuera es tuya, y tiene que ser "
    "consciente: no se envía nada hasta que confirmes explícitamente que "
    "lo sabes y lo aceptas."
)


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


class ConfirmacionDeAnalisis(BaseModel):
    """La confirmación consciente del docente para enviar esta entrega a un
    proveedor externo mientras `proteccion_datos` siga PENDIENTE_OFICIAL.

    Por omisión es `False`: un `POST` sin cuerpo -como hace hoy el
    frontend, y como hace casi toda la batería de pruebas- no puede leerse
    como una confirmación que nadie ha dado. Solo cuenta cuando alguien la
    pone a `true` a propósito.
    """

    model_config = ConfigDict(extra="forbid")

    confirmo_datos_reales: bool = False


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


def _mensaje_de_edicion_demasiado_larga(fallo: TextoFueraDeLimite) -> str:
    """El aviso que ve el docente cuando su propia edición no cabe en el
    límite de longitud del campo.

    `str(fallo)` no sirve aquí: `TextoFueraDeLimite` lo compone asumiendo
    que el texto largo lo escribió el motor -«esto indica un fallo del
    motor, no un dato del alumno que recortar»-, y en este canal lo ha
    escrito el docente a mano, al editar una observación en `revisar()`. Se
    construye un mensaje propio a partir de los atributos de la excepción
    (`etiqueta`, `longitud`, `limite`), con el mismo criterio que
    `_aviso_de_borrador_incompleto` usa con `ErrorDelProveedor`: no
    reenviar un texto de dominio escrito para otro lector.
    """
    de_mas = fallo.longitud - fallo.limite
    return (
        f"{fallo.etiqueta} tiene {fallo.longitud} caracteres: se pasa por "
        f"{de_mas} del límite de {fallo.limite} caracteres. No se ha "
        "guardado ningún cambio de esta revisión -ni este texto ni "
        "cualquier otra decisión que vinieras a aplicar a la vez-. Acorta "
        "el texto y vuelve a guardar la revisión."
    )


def _mensaje_de_desbordamiento_del_motor(fallo: TextoFueraDeLimite) -> str:
    """El aviso que ve el docente cuando es el propio motor -no él- quien ha
    devuelto un texto que no cabe en su límite.

    Al contrario que en `_mensaje_de_edicion_demasiado_larga`, aquí
    `str(fallo)` sí describe lo que ha pasado -el texto largo es del motor,
    y eso es justo lo que dice-, pero no se reenvía tal cual: no dice que no
    se ha guardado nada, y ese es el dato que de verdad le hace falta al
    docente para saber que puede volver a intentarlo sin que nada se haya
    quedado a medias.
    """
    return (
        "El motor de análisis ha devuelto un texto que no cabe en su "
        f"límite: {fallo.etiqueta} tiene {fallo.longitud} caracteres, y el "
        f"límite es {fallo.limite}. No es un fallo tuyo ni del trabajo del "
        "alumno: es del motor. No se ha guardado nada de este análisis; la "
        "entrega sigue disponible para volver a analizarla, y la respuesta "
        "del motor puede ser distinta la próxima vez."
    )


def _guardar_o_fallar(
    almacen, identificador: str, informe: Informe, devolucion: Devolucion | None,
    motor: str, aviso: str | None = None,
) -> None:
    """Guarda la corrección; si `guardar_correccion` no llega a escribirla,
    deja la entrega tal como estaba antes de este intento.

    `analizar_entrega` marca la entrega ANALIZADO -en las dos ramas que
    llaman a esta función- antes de que el resultado se intente guardar
    aquí, porque hasta ese punto el informe es válido. Pero si
    `guardar_correccion` no consigue escribirlo, no queda ninguna
    corrección detrás de ese estado: `GET /analisis` respondería 404 -«no
    se ha analizado todavía»- sobre una entrega que dice ANALIZADO, una
    entrega que miente. Por eso se revierte a RECIBIDO antes de devolver el
    error: el estado no miente (ver el docstring de
    `backend/servicios/analisis_de_entrega.py`), y RECIBIDO es honesto aquí
    -nada de este intento ha quedado guardado, así que nada distingue esta
    entrega de una que todavía no se ha analizado-.

    Hay dos formas de que `guardar_correccion` falle, y las dos revierten
    igual:

    - `TextoFueraDeLimite`: un texto del motor por encima de
      `LIMITE_DE_OBSERVACION`. Se traduce a un mensaje propio -ver
      `_mensaje_de_desbordamiento_del_motor`-, porque `str(fallo)` no basta
      por sí solo (ver ese docstring).
    - `ErrorDeAlmacen` (`backend/persistencia/supabase.py`): la escritura en
      sí no llega -red caída, clave caducada, cualquier fallo de
      PostgREST-. Antes solo se capturaba `TextoFueraDeLimite` aquí, y
      `ErrorDeAlmacen` se escapaba directa hacia el manejador global de
      `backend/app.py` -que sí la traduce a un 503 legible-, pero sin pasar
      por este revertido antes: el profesor pagaba la llamada al motor, no
      se llevaba nada, y la entrega se quedaba ANALIZADO sin corrección
      detrás, el mismo callejón sin salida que el bloqueante original. Aquí
      no se compone un mensaje nuevo -el que ya trae `ErrorDeAlmacen` está
      escrito para el docente-: se revierte el estado y se deja subir la
      misma excepción, para que el manejador global la traduzca como ya
      hace en cualquier otro endpoint.
    """
    try:
        almacen.guardar_correccion(identificador, informe, devolucion, motor, aviso)
    except TextoFueraDeLimite as fallo:
        almacen.cambiar_estado(identificador, "RECIBIDO", None)
        raise HTTPException(
            status_code=503,
            detail=_mensaje_de_desbordamiento_del_motor(fallo),
        ) from fallo
    except ErrorDeAlmacen:
        almacen.cambiar_estado(identificador, "RECIBIDO", None)
        raise


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
def analizar(
    identificador: str, peticion: Request,
    cuerpo: ConfirmacionDeAnalisis = ConfirmacionDeAnalisis(),
) -> ResultadoAnalisis:
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

    # La misma guarda que ya protege al desarrollador en
    # `tools/calibrar.py` -reutilizando la misma función,
    # `proteccion_datos_pendiente()`, no un criterio duplicado-, puesta
    # donde de verdad hace falta: esta es la vía por la que un trabajo real
    # de un alumno sale hacia el proveedor de análisis. No es un bloqueo sin
    # salida -no impide seguir usando el sistema, incluso con documentos
    # reales, si el docente ya lo ha decidido-: es una confirmación
    # explícita por petición, igual que `--confirmo` en el arnés no se
    # recuerda de una pasada a la siguiente. Va antes de tocar el candado y
    # antes de llamar al motor: es una decisión de si se puede seguir en
    # absoluto, no un paso más de la validación técnica.
    #
    # `proveedor.nombre != "simulado"` es la condición que faltaba: el
    # aviso dice, literalmente, que «el texto íntegro del documento se
    # envía a un proveedor de análisis externo», y con el motor simulado
    # eso es falso -`ProveedorSimulado` no manda nada a ningún sitio, solo
    # devuelve lo que ya se le programó en la prueba-. Pedir una
    # confirmación consciente para algo que no ocurre no es prudencia, es
    # ruido: es justo así como un aviso se convierte en un clic automático,
    # y cuando de verdad haga falta -con el motor real- el docente ya
    # tendrá el hábito de descartarlo sin leerlo. `obtener_motor` usa el
    # mismo criterio (`proveedor.nombre == "simulado"`) para decidir si
    # avisa de que lo que se ve no es un análisis real; aquí se comprueba
    # lo mismo, para la pregunta contraria: si de verdad va a salir algo.
    if (
        proteccion_datos_pendiente(raiz)
        and proveedor.nombre != "simulado"
        and not cuerpo.confirmo_datos_reales
    ):
        raise HTTPException(status_code=428, detail=AVISO_PROTECCION_DATOS)

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
            aviso = _aviso_de_borrador_incompleto(fallo)
            resultado = ResultadoAnalisis(
                entrega=fallo.entrega, informe=fallo.informe, devolucion=None,
                motor=proveedor.nombre, aviso=aviso,
            )
            _guardar_o_fallar(
                almacen, identificador, resultado.informe, None,
                resultado.motor, aviso,
            )
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
    _guardar_o_fallar(
        almacen, identificador, resultado.informe, resultado.devolucion,
        resultado.motor,
    )
    return resultado


def _correccion_guardada(almacen, identificador: str):
    """La corrección guardada de esta entrega, o `None` si no hay ninguna.

    `obtener_analisis` y `revisar` la necesitan igual: la primera para
    devolverla tal cual, la segunda para partir de ella antes de aplicar las
    decisiones del docente.
    """
    return almacen.correccion_de(identificador)


@router.get("/entregas/{identificador}/analisis")
def obtener_analisis(identificador: str, peticion: Request) -> ResultadoAnalisis:
    almacen = peticion.app.state.almacen
    guardada = _correccion_guardada(almacen, identificador)
    if guardada is None:
        raise HTTPException(
            status_code=404,
            detail="Esta entrega no se ha analizado todavía.",
        )
    entrega = almacen.por_id(identificador)
    if entrega is None:
        # No debería pasar -toda corrección cuelga de una entrega real-,
        # pero si la entrega hubiera desaparecido, un 404 explícito dice más
        # que un 500 con el campo `entrega` vacío.
        raise HTTPException(status_code=404, detail="No existe esa entrega.")
    return ResultadoAnalisis(
        entrega=entrega, informe=guardada.informe, devolucion=guardada.devolucion,
        motor=guardada.motor, aviso=guardada.aviso,
    )


@router.post("/entregas/{identificador}/revision")
def revisar(
    identificador: str, cuerpo: Revision, peticion: Request
) -> ResultadoAnalisis:
    """Aplica lo que el docente ha decidido observación por observación.

    Solo lo aprobado se conserva. Es lo que el §13 llama revisión docente, y
    es la única vía por la que una observación llega a considerarse válida.
    """
    almacen = peticion.app.state.almacen
    guardada = _correccion_guardada(almacen, identificador)
    if guardada is None:
        raise HTTPException(
            status_code=404, detail="Esta entrega no se ha analizado todavía."
        )
    entrega = almacen.por_id(identificador)
    if entrega is None:
        raise HTTPException(status_code=404, detail="No existe esa entrega.")

    por_dimension = {d.dimension: d for d in cuerpo.decisiones}
    for d in cuerpo.decisiones:
        if d.decision not in _DECISIONES:
            raise HTTPException(
                status_code=400,
                detail=f"«{d.decision}» no es una decisión válida. Son: "
                       + ", ".join(_DECISIONES) + ".",
            )

    # La decisión del docente se resuelve una sola vez por dimensión, a
    # partir de `valoraciones` -la lista completa, la única que las trae
    # todas-, y el mismo resultado se reutiliza en las tres listas de abajo.
    # Antes se recalculaba `prioridades` filtrando los objetos ORIGINALES de
    # `guardada.informe.prioridades`: una edición quedaba aplicada en
    # `valoraciones` y perdida en `prioridades` -el Anexo C, lo que de
    # verdad se traslada al alumno-, y `prioridades_descartadas` ni
    # siquiera se tocaba. Resolver aquí y aplicar el mismo resultado en las
    # tres es lo que hace imposible, por construcción, que la edición
    # sobreviva en una lista y no en otra.
    def _decision_resuelta(v):
        decision = por_dimension.get(v.dimension)
        if decision is None or decision.decision == "ACEPTADA":
            return v
        if decision.decision == "EDITADA":
            return v.model_copy(
                update={"observacion": decision.texto or v.observacion}
            )
        return None  # DESCARTADA: no se conserva en ninguna lista.

    resueltas = {
        v.dimension: _decision_resuelta(v) for v in guardada.informe.valoraciones
    }

    def _aplicar(lista):
        aplicada = []
        for v in lista:
            resuelta = resueltas.get(v.dimension, v)
            if resuelta is not None:
                aplicada.append(resuelta)
        return aplicada

    nuevas_prioridades = _aplicar(guardada.informe.prioridades)
    nuevas_descartadas = _aplicar(guardada.informe.prioridades_descartadas)
    informe = guardada.informe.model_copy(update={
        "valoraciones": _aplicar(guardada.informe.valoraciones),
        "prioridades": nuevas_prioridades,
        "prioridades_descartadas": nuevas_descartadas,
        # El resumen es un recuento de estas mismas piezas -ver
        # `componer_resumen`, en `backend/salidas/informe.py`-, y antes esta
        # llamada no existía: `revisar()` recomponía `valoraciones`,
        # `prioridades` y `prioridades_descartadas`, pero dejaba el
        # `resumen` guardado tal cual, con las cifras de ANTES de aplicar la
        # revisión. El docente volvía a la ficha y leía, por ejemplo, «2
        # prioridades verificadas (1 P1, 1 P2)» encima de una lista de
        # prioridades con una sola entrada y ningún P1 -justo lo que
        # `prioridades` decía tras el `_aplicar` de arriba-. Recomponerlo
        # aquí no cuesta una llamada al motor: `componer_resumen` es una
        # función pura sobre piezas que esta petición ya tiene en la mano.
        # El semáforo no se recalcula -no es una de las piezas que el
        # docente edita aquí, sigue siendo el de `guardada.informe.semaforo`
        # tras el `model_copy`- y por eso se pasa tal cual, para que la
        # primera frase del resumen («Semáforo propuesto: …») siga diciendo
        # lo mismo que el campo `semaforo` del informe.
        "resumen": componer_resumen(
            guardada.informe.semaforo,
            SeleccionDePrioridades(
                elegidas=nuevas_prioridades, descartadas=nuevas_descartadas,
            ),
            guardada.informe.dimensiones_ausentes,
            guardada.informe.reparos,
        ),
    })
    # Sustituye la corrección entera: mismo método que guarda un análisis,
    # mismo criterio de «la segunda sustituye a la primera». La devolución y
    # el aviso no cambian con la revisión -el docente decide sobre el
    # informe, no vuelve a pedir la redacción-, así que se conservan tal
    # cual estaban.
    try:
        # `LIMITE_DE_OBSERVACION_DOCENTE`, no el del motor: el texto que
        # esta llamada guarda puede llevar una observación que ha escrito
        # el docente a mano (ver el docstring del módulo).
        almacen.guardar_correccion(
            identificador, informe, guardada.devolucion, guardada.motor,
            guardada.aviso, limite_de_observacion=LIMITE_DE_OBSERVACION_DOCENTE,
        )
    except TextoFueraDeLimite as fallo:
        # `TextoFueraDeLimite.__str__()` no sirve aquí: asume que el texto
        # largo lo escribió el motor, y en este canal lo ha escrito el
        # docente a mano al editar una observación. Se compone un mensaje
        # propio a partir de los atributos de la excepción, no de
        # `str(fallo)` -mismo criterio que `_aviso_de_borrador_incompleto`
        # con `ErrorDelProveedor`-, y nada de esta revisión queda guardado:
        # `guardar_correccion` valida antes de escribir, así que un texto
        # fuera de límite no deja ni esta edición ni ninguna otra decisión
        # de la misma petición a medias.
        raise HTTPException(
            status_code=400,
            detail=_mensaje_de_edicion_demasiado_larga(fallo),
        ) from fallo
    return ResultadoAnalisis(
        entrega=entrega, informe=informe, devolucion=guardada.devolucion,
        motor=guardada.motor, aviso=guardada.aviso,
    )
