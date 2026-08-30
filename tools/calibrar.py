"""El arnés de calibración: compara el juicio del sistema con el del docente.

ADVERTENCIA: esto no es un test. Los nueve casos P01-P09 del párrafo 6 del
documento de calibración (docs/maestro/04-calibracion.md) son referencias de
comportamiento del docente, no un veredicto que el sistema tenga que
reproducir palabra por palabra. Que un caso no coincida puede significar
que el motor se ha equivocado, que la referencia del docente era discutible,
o que el caso está mal descrito en el banco -y esa lectura la hace el
docente, no este comando: ni `evaluar` ni `ejecutar` deciden "aprobado" ni
"reprobado", solo comparan y cuentan.

Vive aparte de `python -m pytest` porque cada caso es una llamada de pago a
un proveedor de análisis: la suite de tests y `verificar_gobernanza.py`
corren en cada commit y no pueden depender de la red ni del dinero, y este
arnés sí. Se invoca a mano::

    python tools/calibrar.py --carpeta <ruta-fuera-del-repositorio>

Los PDF de los nueve casos son trabajos reales de alumnos del curso pasado.
No entran en el repositorio ni como material de prueba: la carpeta que los
contiene se indica al ejecutar -por `--carpeta` o por
`REVISOR_CARPETA_CALIBRACION`-, nunca vive dentro del árbol versionado, y
este módulo lo comprueba antes de tocar nada, con el mismo criterio que ya
usa `backend.configuracion` para la carpeta de entregas. El informe que
compone tampoco se escribe en el repositorio: por omisión se guarda dentro
de esa misma carpeta externa, y si se pide una ruta de salida que cae
dentro del repositorio, este módulo se niega a escribirla -puede llevar
códigos de alumno y las observaciones del sistema sobre su trabajo, y eso es
justo lo que R6 prohíbe versionar, lo diga un PDF o un informe con las
mismas palabras-.

Y una guarda más, antes de gastar la primera llamada: si `proteccion_datos`
sigue `PENDIENTE_OFICIAL` en `docs/PENDIENTE_OFICIAL.md`, el comando avisa y
exige `--confirmo` antes de enviar nada. Los casos de calibración son
trabajos reales; que el piloto con entregas reales siga sin resolver no
impide -por sí solo- correr la calibración, pero el docente tiene que
decidirlo él, no que el comando lo dé por hecho.

Cada caso completado se escribe en disco, en la carpeta de calibración, en
cuanto se obtiene -no solo al final de la tanda-. Cada uno es una llamada
de pago, y un Ctrl+C o un corte a mitad de las nueve no debe borrar lo que
ya costó dinero y ya terminó. Esto no es una reanudación automática -una
pasada interrumpida se relanza entera, no retoma por donde se quedó-, es
solo que el trabajo pagado quede en disco, no únicamente en la memoria de
un proceso que puede morir antes del final.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

# Este fichero se invoca como script ("python tools/calibrar.py"), y en ese
# caso Python solo pone tools/ en la ruta de busqueda, no la raiz del
# repositorio: sin esta linea no encontraria el paquete backend y la
# herramienta no arranca. Mismo motivo y misma solucion que en
# tools/verificar_gobernanza.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.analisis.proveedor import (  # noqa: E402
    ErrorDelProveedor,
    ProveedorAnalisis,
)
from backend.analisis.verificacion import normalizar_para_buscar  # noqa: E402
from backend.configuracion import VERSION_CRITERIOS_POR_OMISION  # noqa: E402
from backend.extraccion import medir  # noqa: E402
from backend.extraccion.lectura import PdfIlegible  # noqa: E402
from backend.persistencia.memoria import AlmacenEnMemoria  # noqa: E402
from backend.persistencia.modelos import Almacen, EntregaNueva  # noqa: E402
from backend.salidas.informe import Informe  # noqa: E402
from backend.servicios.analisis_de_entrega import InformeSinBorrador, analizar_entrega  # noqa: E402
from backend.servicios.lectura_objetiva import localizar  # noqa: E402

ADVERTENCIA = (
    "ADVERTENCIA: esto no es un test. El resultado es un informe para el "
    "docente, no un veredicto en verde o en rojo. Un caso que no coincide "
    "puede significar que el motor se ha equivocado, que la referencia era "
    "discutible o que el caso está mal descrito; lo decide él."
)

# La variable de entorno de la carpeta de calibración. Distinta de
# REVISOR_CARPETA_ENTREGAS: una es donde llegan las entregas del curso en
# marcha, la otra es el banco fijo de nueve casos históricos.
CARPETA_CALIBRACION = "REVISOR_CARPETA_CALIBRACION"

# El alumno de calibración no tiene ciclo real -el banco de casos no lo
# recoge, y no hace falta para comparar semáforos-. No es un criterio
# académico que se esté inventando, es un dato administrativo que
# `EntregaNueva` exige para poder registrar algo con lo que `analizar_entrega`
# pueda trabajar.
CICLO_DE_CALIBRACION = "CALIBRACION"

# El §11.1 del documento de calibración, con su pregunta de control exacta.
PREGUNTAS_DEL_11_1: dict[str, str] = {
    "cobertura": "¿Detecta el problema principal?",
    "exactitud": "¿La observación está apoyada en el documento?",
    "prioridad": "¿Distingue P1-P4?",
    "proporcionalidad": "¿Exige un nivel razonable de FP?",
    "tono": "¿Suena docente, claro y humano?",
    "prudencia": "¿Evita afirmaciones no demostrables?",
    "ahorro": "¿Reduce carga sin trasladarla al alumno?",
}

# VERDE < AMBAR < ROJO en severidad. GRIS no entra: no es "más duro" ni "más
# blando" que un color, es "no evaluable", y forzarlo a un lado de la escala
# inventaría una lectura que la propia calibración del §9 no da.
_SEVERIDAD = {"VERDE": 0, "AMBAR": 1, "ROJO": 2}


class CasoDeCalibracion(BaseModel):
    """La ficha de un caso histórico del banco P01-P09.

    No lleva el PDF ni su texto: solo lo necesario para localizarlo
    (`archivo`, dentro de la carpeta que se indique al ejecutar) y para
    contrastar lo que el sistema proponga con lo que decidió el docente.
    """

    model_config = ConfigDict(extra="forbid")

    codigo: str
    archivo: str
    fase: str
    semaforo_esperado: str
    debe_encontrar: list[str] = []
    no_debe: list[str] = []
    notas: str = ""


class ResultadoDeCaso(BaseModel):
    """Lo que salió de comparar un caso con lo que propuso el sistema.

    `saltado` cubre tanto el archivo que no está en la carpeta como
    cualquier fallo del proveedor a mitad de la ejecución: en los dos casos
    el arnés sigue con el siguiente caso, y `motivo_salto` es lo único que
    el docente necesita para saber por qué este no cuenta.
    """

    model_config = ConfigDict(extra="forbid")

    codigo: str
    saltado: bool = False
    motivo_salto: str | None = None

    semaforo_esperado: str | None = None
    semaforo_obtenido: str | None = None
    acierta_semaforo: bool | None = None
    # COINCIDE, MAS_DURO, MAS_BLANDO o NO_COMPARABLE (por GRIS). None si el
    # caso se saltó.
    direccion: str | None = None

    debe_encontrar_hallado: list[str] = []
    debe_encontrar_ausente: list[str] = []
    no_debe_hallado: list[str] = []

    # Para el indicador de exactitud del §11.1: cuántas valoraciones del
    # informe llevan su evidencia localizada en el documento, sobre el
    # total. `Informe.valoraciones` ya trae ese dato por valoración -lo
    # calculó `verificar()`-; aquí solo se cuenta, no se recalcula.
    valoraciones_totales: int = 0
    valoraciones_con_evidencia: int = 0

    notas: str = ""


class IndicadorDeCalibracion(BaseModel):
    """Un indicador del §11.1: su pregunta de control y lo que el arnés
    puede decir de él sin fijar un umbral de éxito que nadie ha decidido.

    Tres indicadores son medibles con lo que ya calcula `evaluar`; los otros
    cuatro son juicios de lectura que exigen abrir el informe y el borrador
    de cada caso, y esta herramienta no los inventa. Un indicador no
    medible no se omite -eso se leería como "no aplica", y no es eso-: se
    deja marcado como tal, con su pregunta, para que el docente sepa que
    tiene que mirarlo él.
    """

    model_config = ConfigDict(extra="forbid")

    pregunta: str
    medible_automaticamente: bool
    lectura: str


class InformeDeCalibracion(BaseModel):
    """El resultado entero de una pasada del arnés por el banco de casos."""

    model_config = ConfigDict(extra="forbid")

    resultados: list[ResultadoDeCaso]
    total_casos: int
    evaluados: int
    saltados: int
    aciertos_semaforo: int
    mas_duro: int
    mas_blando: int
    no_comparable: int
    lectura_de_sesgo: str
    indicadores: dict[str, IndicadorDeCalibracion]


def cargar_casos(fichero: Path) -> list[CasoDeCalibracion]:
    """Los casos declarados en un fichero YAML como `casos.example.yaml`.

    No hay PDF aquí ni falta que hace: el fichero solo describe el
    comportamiento esperado. Los PDF de verdad viven en la carpeta que se
    indica al ejecutar, siempre fuera del repositorio.
    """
    bruto = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    if not isinstance(bruto, list):
        raise ValueError(
            f"«{fichero}» debería contener una lista de casos, y contiene "
            f"{type(bruto).__name__}."
        )
    return [CasoDeCalibracion(**item) for item in bruto]


def _texto_de_observaciones(informe: Informe) -> str:
    """Toda la prosa del informe interno donde puede aparecer un hallazgo.

    Reúne el resumen, las observaciones de cada valoración, las
    descripciones de las fortalezas y de los indicios, y las dudas para el
    docente. Deliberadamente no incluye `control_administrativo` -son
    medidas objetivas, no un juicio sobre el trabajo- ni `reparos` -son
    avisos sobre la propia verificación, no hallazgos del proyecto-.
    """
    partes = [informe.resumen]
    partes += [v.observacion for v in informe.valoraciones]
    partes += [f.descripcion for f in informe.fortalezas]
    partes += list(informe.dudas)
    partes += [i.descripcion for i in informe.indicios]
    return "\n".join(partes)


def _direccion(esperado: str, obtenido: str) -> str:
    """Si el sistema coincide con el docente, es más duro, más blando o no
    comparable.

    Que el sistema falle siempre hacia el mismo lado importa más que
    cuántas veces falla: un sesgo sistemático hacia la dureza se corrige
    bajando el listón; un error repartido al azar no se corrige con ningún
    ajuste, y confundir los dos leería una calibración sana donde hay un
    problema, o al revés.
    """
    if esperado == obtenido:
        return "COINCIDE"
    if esperado not in _SEVERIDAD or obtenido not in _SEVERIDAD:
        return "NO_COMPARABLE"
    return "MAS_DURO" if _SEVERIDAD[obtenido] > _SEVERIDAD[esperado] else "MAS_BLANDO"


def evaluar(caso: CasoDeCalibracion, informe: Informe) -> ResultadoDeCaso:
    """Compara lo que el sistema propuso con la referencia del docente.

    Recibe únicamente `informe`, nunca la `Devolucion`: `debe_encontrar` y
    `no_debe` se buscan en las observaciones internas -lo que el docente lee
    entero-, no en el texto que llegaría al alumno. Que esta función no
    reciba el borrador no es un descuido de la firma: es lo que hace
    imposible, por construcción, buscar en el sitio equivocado.

    La búsqueda es literal -normalizada como una cita: sin tildes, sin
    mayúsculas, con los espacios colapsados- y no semántica. Encuentra
    "bibliografía ausente" si el informe lo dice con esas palabras, no si lo
    dice de otra forma; y no puede juzgar un rasgo de comportamiento como
    "no enumerar cada defecto menor" -eso lo lee el docente en el informe
    completo, esta función solo confirma que la frase exacta no aparece.
    """
    corpus = normalizar_para_buscar(_texto_de_observaciones(informe))

    hallado = [t for t in caso.debe_encontrar if normalizar_para_buscar(t) in corpus]
    ausente = [t for t in caso.debe_encontrar if t not in hallado]
    no_debe_hallado = [t for t in caso.no_debe if normalizar_para_buscar(t) in corpus]

    return ResultadoDeCaso(
        codigo=caso.codigo,
        semaforo_esperado=caso.semaforo_esperado,
        semaforo_obtenido=informe.semaforo_propuesto,
        acierta_semaforo=(informe.semaforo_propuesto == caso.semaforo_esperado),
        direccion=_direccion(caso.semaforo_esperado, informe.semaforo_propuesto),
        debe_encontrar_hallado=hallado,
        debe_encontrar_ausente=ausente,
        no_debe_hallado=no_debe_hallado,
        valoraciones_totales=len(informe.valoraciones),
        valoraciones_con_evidencia=sum(
            1 for v in informe.valoraciones if v.evidencia_localizada
        ),
        notas=caso.notas,
    )


def _ejecutar_caso(
    raiz: Path,
    carpeta: Path,
    version: str,
    almacen: Almacen,
    proveedor: ProveedorAnalisis,
    caso: CasoDeCalibracion,
) -> ResultadoDeCaso:
    """Un caso, de principio a fin, sin dejar que su fallo se lleve a los
    demás.

    Cada caso es una llamada de pago que puede fallar a mitad de una tanda
    de nueve. Perder los ocho casos restantes por el tropiezo de uno solo
    desperdiciaría llamadas ya pagadas, así que cualquier fallo -archivo
    ausente, proveedor caído, una excepción que este módulo no había
    previsto- se convierte aquí en un resultado saltado con su motivo, no en
    una excepción que suba y tumbe la pasada entera.
    """

    def _saltado(motivo: str) -> ResultadoDeCaso:
        return ResultadoDeCaso(
            codigo=caso.codigo,
            saltado=True,
            motivo_salto=motivo,
            semaforo_esperado=caso.semaforo_esperado,
            notas=caso.notas,
        )

    ruta = localizar(carpeta, caso.archivo)
    if ruta is None:
        return _saltado(f"El archivo «{caso.archivo}» no está en «{carpeta}».")

    try:
        huella = medir(ruta).huella
    except PdfIlegible as fallo:
        return _saltado(f"El archivo no se ha podido leer: {fallo}")

    entrega = almacen.registrar(EntregaNueva(
        codigo_alumno=caso.codigo,
        ciclo=CICLO_DE_CALIBRACION,
        fase=caso.fase,
        version=1,
        nombre_archivo=caso.archivo,
        huella=huella,
        version_criterios=version,
    ))

    try:
        try:
            correccion = analizar_entrega(
                raiz, carpeta, version, almacen, proveedor, entrega
            )
            informe = correccion.informe
        except InformeSinBorrador as fallo:
            # El informe se completó; solo falló la redacción del borrador
            # para el alumno, y el arnés no compara borradores. Perder este
            # caso por eso tiraría un informe válido a la basura.
            informe = fallo.informe
    except (ErrorDelProveedor, PdfIlegible) as fallo:
        return _saltado(f"El proveedor de análisis ha fallado: {fallo}")
    except Exception as fallo:  # noqa: BLE001 - un caso no debe tirar a los demás
        return _saltado(f"Fallo inesperado: {type(fallo).__name__}: {fallo}")

    return evaluar(caso, informe)


def _lectura_de_sesgo(
    evaluados: list[ResultadoDeCaso], mas_duro: int, mas_blando: int, no_comparable: int
) -> str:
    """La frase que resume el sesgo, no el porcentaje de acierto.

    Un porcentaje suelto no dice si el sistema se equivoca al azar -no hay
    nada que corregir con un solo ajuste- o si falla siempre hacia el mismo
    lado -un sesgo que sí se corrige, bajando o subiendo el listón-. Esta
    función no decide si el sistema está calibrado: nadie ha fijado ese
    umbral todavía, y no se inventa aquí.
    """
    if not evaluados:
        return "Ningún caso se ha podido evaluar; no hay lectura de sesgo posible."
    if mas_duro == 0 and mas_blando == 0:
        return (
            f"De {len(evaluados)} casos evaluados, ninguna discrepancia de "
            f"semáforo cae hacia un lado fijo ({no_comparable} no "
            "comparables por GRIS). No hay indicio de sesgo sistemático en "
            "esta tanda."
        )
    if mas_duro == mas_blando:
        lado = "sin un lado dominante"
    else:
        lado = "hacia la dureza" if mas_duro > mas_blando else "hacia la indulgencia"
    return (
        f"De {len(evaluados)} casos evaluados: {mas_duro} el sistema fue más "
        f"duro que el docente y {mas_blando} más blando ({no_comparable} no "
        f"comparables por GRIS). Tendencia {lado}. No se fija aquí ningún "
        "umbral de calibración superada -nadie lo ha decidido todavía-: "
        "esto es una lectura para que el docente decida."
    )


def _indicadores(evaluados: list[ResultadoDeCaso]) -> dict[str, IndicadorDeCalibracion]:
    """Los siete indicadores del §11.1, con lo que el arnés puede medir de
    cada uno y sin fingir que mide los que no puede.
    """
    if not evaluados:
        vacio = "No hay ningún caso evaluado del que leer esto."
        return {
            clave: IndicadorDeCalibracion(
                pregunta=pregunta, medible_automaticamente=False, lectura=vacio
            )
            for clave, pregunta in PREGUNTAS_DEL_11_1.items()
        }

    total_debe_encontrar = sum(
        len(r.debe_encontrar_hallado) + len(r.debe_encontrar_ausente) for r in evaluados
    )
    total_hallado = sum(len(r.debe_encontrar_hallado) for r in evaluados)
    aciertos = sum(1 for r in evaluados if r.acierta_semaforo)
    total_valoraciones = sum(r.valoraciones_totales for r in evaluados)
    con_evidencia = sum(r.valoraciones_con_evidencia for r in evaluados)

    no_automatizable = (
        "No es automatizable: exige leer el informe y el borrador de cada "
        "caso. El arnés no lo juzga por el docente."
    )

    lectura_cobertura = (
        f"{total_hallado}/{total_debe_encontrar} términos de «debe_encontrar» "
        f"localizados en las observaciones, en {len(evaluados)} casos "
        "evaluados."
        if total_debe_encontrar
        else "Ningún caso evaluado declara «debe_encontrar»."
    )
    lectura_exactitud = (
        f"{con_evidencia}/{total_valoraciones} valoraciones del informe "
        "tienen su evidencia localizada en el documento."
        if total_valoraciones
        else "Ningún caso evaluado tiene valoraciones que contar."
    )
    lectura_prioridad = (
        f"{aciertos}/{len(evaluados)} semáforos coinciden con la referencia "
        "del docente."
    )

    return {
        "cobertura": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["cobertura"],
            medible_automaticamente=True,
            lectura=lectura_cobertura,
        ),
        "exactitud": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["exactitud"],
            medible_automaticamente=True,
            lectura=lectura_exactitud,
        ),
        "prioridad": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["prioridad"],
            medible_automaticamente=True,
            lectura=lectura_prioridad,
        ),
        "proporcionalidad": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["proporcionalidad"],
            medible_automaticamente=False,
            lectura=no_automatizable,
        ),
        "tono": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["tono"],
            medible_automaticamente=False,
            lectura=no_automatizable,
        ),
        "prudencia": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["prudencia"],
            medible_automaticamente=False,
            lectura=no_automatizable,
        ),
        "ahorro": IndicadorDeCalibracion(
            pregunta=PREGUNTAS_DEL_11_1["ahorro"],
            medible_automaticamente=False,
            lectura=no_automatizable,
        ),
    }


def _componer_informe(resultados: list[ResultadoDeCaso]) -> InformeDeCalibracion:
    evaluados = [r for r in resultados if not r.saltado]
    saltados = [r for r in resultados if r.saltado]
    mas_duro = [r for r in evaluados if r.direccion == "MAS_DURO"]
    mas_blando = [r for r in evaluados if r.direccion == "MAS_BLANDO"]
    no_comparable = [r for r in evaluados if r.direccion == "NO_COMPARABLE"]

    return InformeDeCalibracion(
        resultados=resultados,
        total_casos=len(resultados),
        evaluados=len(evaluados),
        saltados=len(saltados),
        aciertos_semaforo=sum(1 for r in evaluados if r.acierta_semaforo),
        mas_duro=len(mas_duro),
        mas_blando=len(mas_blando),
        no_comparable=len(no_comparable),
        lectura_de_sesgo=_lectura_de_sesgo(
            evaluados, len(mas_duro), len(mas_blando), len(no_comparable)
        ),
        indicadores=_indicadores(evaluados),
    )


def _progreso_por_omision(carpeta: Path) -> Path:
    """La ruta del fichero de progreso de esta pasada, junto al informe.

    Un nombre por ejecución -con su propia marca de tiempo-, no un fichero
    fijo: dos pasadas seguidas no se pisan la una a la otra, y cada una deja
    su propio rastro de lo que llegó a completarse.
    """
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    return carpeta / f"progreso-calibracion-{marca}.jsonl"


def _registrar_progreso(raiz: Path, fichero: Path, resultado: ResultadoDeCaso) -> None:
    """Añade `resultado` al fichero de progreso, en cuanto se obtiene.

    Cada caso es una llamada de pago, y un fallo del proceso entero -un
    Ctrl+C, un corte- no debe perder los que ya se han completado y pagado.
    Por eso esto se llama una vez por caso, dentro del bucle de `ejecutar`,
    y no una sola vez al final con la tanda entera: si el proceso muere en
    el caso cinco de nueve, quedan los cuatro anteriores escritos en disco,
    no solo en una lista en memoria que desaparece con el proceso.

    Una línea JSON por caso -no un documento que se reescribe entero cada
    vez-: el fichero se abre, se escribe y se cierra en cada llamada, así
    que un corte a mitad de un caso deja como mucho una línea a medias al
    final, nunca corrompe las que ya se cerraron antes.

    Usa la misma guarda que la ruta de salida final -`_dentro_del_repositorio`,
    la que ya protege que un informe con códigos de alumno no acabe en un
    commit-: si por lo que sea `fichero` cayera dentro del repositorio, aquí
    no se escribe nada. No es una segunda oportunidad para el mismo fallo:
    en el uso normal `carpeta` ya la valida `_problema_de_carpeta` antes de
    que `ejecutar` llegue a llamarse; esto es la misma comprobación, otra
    vez, en el sitio exacto donde se escribe.

    Un fallo de disco -sin espacio, sin permiso- no aborta la tanda: perder
    el progreso persistido de este caso es peor que no tenerlo, pero no es
    motivo para tirar los casos que aún quedan por evaluar.
    """
    if _dentro_del_repositorio(raiz, fichero):
        return
    try:
        with fichero.open("a", encoding="utf-8") as flujo:
            flujo.write(resultado.model_dump_json())
            flujo.write("\n")
            flujo.flush()
    except OSError:
        pass


def ejecutar(
    raiz: Path,
    casos: list[CasoDeCalibracion],
    carpeta: Path,
    proveedor: ProveedorAnalisis,
    espera: float = 0.0,
    dormir=time.sleep,
) -> InformeDeCalibracion:
    """Recorre los casos del banco contra `proveedor` y compara con el
    docente.

    Usa siempre `VERSION_CRITERIOS_POR_OMISION`: hoy solo existe una versión
    de criterios en `criteria/`, y esta firma -fijada por el diseño de esta
    tarea- no lleva un parámetro de versión. Si algún día conviene calibrar
    contra una versión congelada distinta de la vigente, esa es una amplia-
    ción real de esta función, no algo que se deba adivinar aquí leyendo el
    entorno por su cuenta -y menos en una función que los tests llaman
    directamente y esperan determinista, sin que una variable de entorno
    del equipo de quien la ejecuta le cambie el resultado.

    Cada resultado se persiste en `carpeta`, junto al informe final, tan
    pronto como se obtiene -ver `_registrar_progreso`-. Esto no es una
    reanudación: una pasada interrumpida no retoma los casos que ya se
    completaron, se vuelve a lanzar entera. Es, únicamente, que el trabajo
    ya pagado quede en disco y no solo en la memoria de un proceso que
    puede morir antes de llegar al final.

    `espera` son los segundos que se aguardan entre un caso y el siguiente.
    Existe porque la cuenta del docente tiene un límite de tokens por minuto,
    y un proyecto entero puede acercarse a ese límite él solo: en la primera
    calibración real -2026-08-29, límite de 30.000 tokens por minuto- los dos
    trabajos que fallaron fueron precisamente los dos más largos, 19.418 y
    13.116 tokens, que juntos lo superaban. No es un problema de saldo, y por
    eso no se arregla esperando a mañana: se arregla no mandándolos seguidos.
    El valor va en la línea de órdenes porque el límite depende de la cuenta y
    de la hora, y el arnés no tiene forma de conocerlo.

    `dormir` se inyecta para que los tests no esperen de verdad.
    """
    almacen = AlmacenEnMemoria()
    fichero_de_progreso = _progreso_por_omision(carpeta)
    resultados: list[ResultadoDeCaso] = []
    for numero, caso in enumerate(casos):
        # Antes del caso y no después: así el último no hace esperar de balde
        # a quien mira la pantalla.
        if numero and espera:
            dormir(espera)
        resultado = _ejecutar_caso(
            raiz, carpeta, VERSION_CRITERIOS_POR_OMISION, almacen, proveedor, caso
        )
        _registrar_progreso(raiz, fichero_de_progreso, resultado)
        resultados.append(resultado)
    return _componer_informe(resultados)


def proteccion_datos_pendiente(raiz: Path) -> bool:
    """Si `proteccion_datos` sigue constando en `docs/PENDIENTE_OFICIAL.md`.

    Sin el fichero no hay forma de comprobar que se haya resuelto, así que
    se trata igual que si siguiera pendiente: la duda no se resuelve a favor
    de enviar datos reales.
    """
    fichero = raiz / "docs" / "PENDIENTE_OFICIAL.md"
    if not fichero.is_file():
        return True
    texto = fichero.read_text(encoding="utf-8")
    # Solo cuenta lo que sigue en «Pendientes». El documento conserva las
    # entradas resueltas en su propia sección -saber que algo estuvo
    # pendiente, y por qué dejó de estarlo, es parte de la trazabilidad-, y
    # buscar el nombre en el fichero entero haría que una entrada archivada
    # siguiera bloqueando para siempre.
    pendientes = texto.split("## Pendientes", 1)[-1].split(chr(10) + "## ", 1)[0]
    return "**proteccion_datos**" in pendientes


def _dentro_del_repositorio(raiz: Path, ruta: Path) -> bool:
    raiz = raiz.resolve()
    objetivo = ruta.resolve()
    return objetivo == raiz or raiz in objetivo.parents


def _problema_de_carpeta(raiz: Path, carpeta: Path) -> str | None:
    """Por qué esa carpeta no sirve como carpeta de calibración, o `None`."""
    if _dentro_del_repositorio(raiz, carpeta):
        return (
            f"La carpeta de calibración «{carpeta}» está dentro del "
            "repositorio. Los trabajos de los alumnos no pueden vivir en el "
            f"árbol versionado. Indica en {CARPETA_CALIBRACION} una carpeta "
            "de fuera."
        )
    if not carpeta.exists():
        return f"La carpeta de calibración «{carpeta}» no existe."
    if not carpeta.is_dir():
        return f"«{carpeta}» no es una carpeta."
    return None


def _problema_de_ruta_de_salida(raiz: Path, salida: Path) -> str | None:
    if _dentro_del_repositorio(raiz, salida):
        return (
            f"La ruta de salida «{salida}» está dentro del repositorio, y el "
            "informe puede llevar códigos de alumno y observaciones sobre su "
            "trabajo. No se escribe ahí."
        )
    return None


def _valor_de_entorno(raiz: Path, clave: str) -> str | None:
    """El valor de una variable, con el mismo criterio que `cargar()`: el
    entorno del proceso manda sobre el fichero `.env`.
    """
    import os

    from backend.configuracion import _leer_env

    valores = _leer_env(raiz)
    valores.update(os.environ)
    return valores.get(clave) or None


def _salida_por_omision(carpeta: Path) -> Path:
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    return carpeta / f"informe-calibracion-{marca}.md"


def _formatear(informe: InformeDeCalibracion) -> str:
    """El informe legible que se imprime y se escribe en disco."""
    lineas = [
        ADVERTENCIA,
        "",
        f"{informe.evaluados}/{informe.total_casos} casos evaluados "
        f"({informe.saltados} saltados).",
        f"Semáforo: {informe.aciertos_semaforo} coinciden, {informe.mas_duro} "
        f"más duro, {informe.mas_blando} más blando, {informe.no_comparable} "
        "no comparables (GRIS).",
        "",
        informe.lectura_de_sesgo,
        "",
        "Indicadores del §11.1:",
    ]
    for clave, indicador in informe.indicadores.items():
        automatico = (
            "automático" if indicador.medible_automaticamente else "lectura humana"
        )
        lineas.append(f"  - {clave} ({automatico}): {indicador.pregunta}")
        lineas.append(f"      {indicador.lectura}")

    lineas.append("")
    lineas.append("Por caso:")
    for r in informe.resultados:
        if r.saltado:
            lineas.append(f"  - {r.codigo}: SALTADO. {r.motivo_salto}")
            continue
        lineas.append(
            f"  - {r.codigo}: esperado {r.semaforo_esperado}, obtenido "
            f"{r.semaforo_obtenido} ({r.direccion})."
        )
        if r.debe_encontrar_ausente:
            lineas.append(
                f"      No se localizó: {', '.join(r.debe_encontrar_ausente)}"
            )
        if r.no_debe_hallado:
            lineas.append(
                f"      Aparece lo que no debería: {', '.join(r.no_debe_hallado)}"
            )
        if r.notas:
            lineas.append(f"      Notas del banco: {r.notas}")

    lineas.append("")
    lineas.append(
        "Recuerda: esto no es un test. Un caso que no coincide puede "
        "significar que el motor se ha equivocado, que la referencia era "
        "discutible, o que el caso está mal descrito. Lo decide el docente."
    )
    return "\n".join(lineas)


AVISO_PROTECCION_DATOS = (
    "AVISO: proteccion_datos sigue PENDIENTE_OFICIAL en "
    "docs/PENDIENTE_OFICIAL.md. Los casos de calibración son trabajos "
    "reales de alumnos del curso pasado, y este comando va a enviar su "
    "contenido al proveedor de análisis configurado. Vuelve a ejecutar con "
    "--confirmo solo si el docente ya ha decidido que esto es aceptable; si "
    "no, no sigas."
)


def _configurar_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "El arnés de calibración. No es un test: compara el semáforo y "
            "las observaciones del sistema con lo que decidió el docente en "
            "los casos históricos del banco P01-P09."
        )
    )
    parser.add_argument(
        "--carpeta", type=Path, default=None,
        help=(
            "Carpeta con los PDF de los casos. Si se omite, se lee de "
            f"{CARPETA_CALIBRACION}, en el entorno o en .env. Tiene que "
            "estar fuera del repositorio."
        ),
    )
    parser.add_argument(
        "--casos", type=Path, default=None,
        help=(
            "Fichero YAML con la ficha de cada caso. Por omisión, "
            "docs/calibracion/casos.example.yaml."
        ),
    )
    parser.add_argument(
        "--salida", type=Path, default=None,
        help=(
            "Dónde escribir el informe. Por omisión, dentro de la carpeta "
            "de calibración, fuera del repositorio."
        ),
    )
    parser.add_argument(
        "--espera", type=float, default=0.0, metavar="SEGUNDOS",
        help=(
            "Segundos de espera entre un caso y el siguiente. Sirve para no "
            "chocar con el limite de tokens por minuto de la cuenta: un "
            "proyecto largo puede acercarse el solo a ese limite, y dos "
            "seguidos lo superan. No es un problema de saldo; no se arregla "
            "esperando a manana, se arregla no mandandolos seguidos."
        ),
    )
    parser.add_argument(
        "--confirmo", action="store_true",
        help=(
            "Confirma que se puede enviar el contenido de la carpeta de "
            "calibración al proveedor de análisis, aunque proteccion_datos "
            "siga PENDIENTE_OFICIAL."
        ),
    )
    return parser


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    """Punto de entrada de la CLI.

    0 informe generado (impreso, y escrito en disco si la ruta de salida es
    segura); 1 no se ha podido arrancar -falta la carpeta, falta la
    confirmación, el fichero de casos no es válido-; 2 fallo inesperado. El 2
    no es una condición de arranque: es que la comprobación no ha llegado a
    hacerse, y quien lo lea tiene que saberlo, no confundirlo con un aviso
    de los de arriba.
    """
    try:
        return _resolver(argv, raiz)
    except Exception as fallo:  # noqa: BLE001 - se traduce a código 2 a propósito
        print("No se ha podido ejecutar el arnés de calibración.")
        print(f"Motivo: {type(fallo).__name__}: {fallo}")
        return 2


def _resolver(argv: list[str] | None, raiz: Path | None) -> int:
    if raiz is None:
        raiz = Path(__file__).resolve().parents[1]
    args = _configurar_argumentos().parse_args(argv)

    print(ADVERTENCIA)
    print()

    carpeta = args.carpeta
    if carpeta is None:
        valor = _valor_de_entorno(raiz, CARPETA_CALIBRACION)
        carpeta = Path(valor) if valor else None
    if carpeta is None:
        print(
            "No hay carpeta de calibración. Indícala con --carpeta o en "
            f"{CARPETA_CALIBRACION}, en el entorno o en el fichero .env."
        )
        return 1
    problema = _problema_de_carpeta(raiz, carpeta)
    if problema:
        print(problema)
        return 1

    # La guarda de proteccion_datos va antes de tocar el fichero de casos o
    # de montar el proveedor: es una decisión de si se puede seguir en
    # absoluto, y se comprueba lo antes posible, no como un paso más de la
    # validación técnica.
    if proteccion_datos_pendiente(raiz) and not args.confirmo:
        print(AVISO_PROTECCION_DATOS)
        return 1

    fichero_de_casos = args.casos or (raiz / "docs" / "calibracion" / "casos.example.yaml")
    if not fichero_de_casos.is_file():
        print(f"No se encuentra el fichero de casos «{fichero_de_casos}».")
        return 1
    try:
        casos = cargar_casos(fichero_de_casos)
    except Exception as fallo:
        print(f"El fichero de casos no se ha podido leer: {fallo}")
        return 1

    from backend.analisis import crear_proveedor
    from backend.configuracion import cargar

    proveedor = crear_proveedor(cargar(raiz))
    if proveedor.nombre == "simulado":
        print(
            "AVISO: sin OPENAI_API_KEY ni REVISOR_MODELO_ANALISIS, el "
            "proveedor es el simulado. Esto no calibra nada real: solo "
            "comprueba que el arnés funciona."
        )

    informe = ejecutar(raiz, casos, carpeta, proveedor, args.espera)
    texto = _formatear(informe)
    print()
    print(texto)

    salida = args.salida or _salida_por_omision(carpeta)
    problema_salida = _problema_de_ruta_de_salida(raiz, salida)
    if problema_salida:
        print()
        print(problema_salida)
        print("El informe no se ha escrito en disco, solo se ha impreso arriba.")
        return 0

    salida.write_text(texto, encoding="utf-8")
    print(f"\nInforme escrito en «{salida}».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
