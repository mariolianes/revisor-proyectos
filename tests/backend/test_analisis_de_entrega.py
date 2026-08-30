"""El servicio que une la lectura con el análisis."""

from pathlib import Path

import pytest

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Fortaleza, Valoracion
from backend.analisis.proveedor import (
    ErrorDelProveedor,
    ProveedorSimulado,
    RespuestaNoValida,
)
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.salidas.borrador import Devolucion
from backend.servicios.analisis_de_entrega import (
    Correccion,
    InformeSinBorrador,
    analizar_entrega,
)


def _analisis_bueno(cita, dimension="D05"):
    """Un `AnalisisDelMotor` válido cuyas citas existen en el PDF de prueba.

    El brief traía `fortalezas=["La estructura del documento es clara."]`,
    una lista de cadenas sueltas: `AnalisisDelMotor.fortalezas` exige
    `list[Fortaleza]`, con su propia evidencia -el mismo requisito que ya
    cierra la puerta a una fortaleza inventada-, y una cadena suelta no
    valida contra ese tipo. Se corrige aquí construyendo la `Fortaleza` con
    evidencia real, tomada del mismo fragmento que ya se sabe localizable
    porque `cita` lo es.

    `dimension` es D05 por omisión -la fase de todos los usos históricos de
    este ayudante es E2, donde D05 está activa (`criteria/v2026-2027/
    dimensiones.yaml`)-, pero D05 no está activa en E1: las pruebas de
    continuidad de más abajo, que analizan una E1 primero, tienen que pasar
    una dimensión que sí lo esté (D01, por ejemplo), o `verificar()` la
    descarta entera -no por la cita, sino por la fase- y no queda ninguna
    prioridad de la que continuar nada.
    """
    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension=dimension, nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita=cita, apartado="5"),
            observacion="Faltan fuentes que respalden las cifras.",
        )],
        fortalezas=[Fortaleza(
            descripcion="La estructura del documento es clara.",
            evidencia=Evidencia(cita=cita, apartado="5"),
        )],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )


def _devolucion():
    return Devolucion(
        apertura="Has avanzado.", fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con fuentes."], cierre="Sigue así.",
    )


def _devolucion_con_nota():
    """Un borrador que viola una regla dura: menciona una nota numerica.

    `componer` (Task 8) rechaza esto con `BorradorNoValido` después de
    pedirlo al motor, así que sirve para probar que un informe ya válido no
    se pierde cuando el borrador sí falla.
    """
    return Devolucion(
        apertura="Tu nota final es un 8 sobre 10.",
        fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con fuentes."],
        cierre="Sigue así.",
    )


@pytest.fixture
def entregas_con_pdf(tmp_path: Path, escribir_pdf):
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    escribir_pdf(carpeta / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion",
        "El presente proyecto describe la implantacion de un sistema.",
        "5. Presupuesto",
        "El presupuesto inicial asciende a 4.500 euros en total.",
    ]])
    return carpeta


def _registrar(almacen, carpeta):
    from backend.extraccion import medir
    ruta = carpeta / "AF023_DAM_E2_20260115_v1.pdf"
    return almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo=ruta.name, huella=medir(ruta).huella,
        version_criterios="v2026-2027",
    ))


def test_una_correccion_completa(criterios_de_analisis, entregas_con_pdf) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert c.informe.valoraciones[0].dimension == "D05"
    assert c.devolucion.acciones == ["Justifica las cifras con fuentes."]
    assert c.motor == "simulado"


def test_la_entrega_pasa_a_analizada(criterios_de_analisis, entregas_con_pdf) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                     almacen, proveedor, entrega)

    assert almacen.por_id(entrega.id).estado == "ANALIZADO"


def test_si_el_motor_falla_la_entrega_no_cambia_de_estado(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """Ni media corrección ni un estado que miente."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(fallos=[ErrorDelProveedor("sin red")])

    with pytest.raises(ErrorDelProveedor):
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert almacen.por_id(entrega.id).estado == "RECIBIDO"


def test_una_respuesta_mal_formada_se_reintenta_una_vez(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """El fallo mas comun y el mas barato de resolver."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(
        fallos=[RespuestaNoValida("no encaja")],
        respuestas=[_analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
                    _devolucion()],
    )

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert c.informe.valoraciones
    assert len(proveedor.llamadas) == 3


def test_no_se_reintenta_dos_veces(criterios_de_analisis, entregas_con_pdf) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(
        fallos=[RespuestaNoValida("uno"), RespuestaNoValida("dos")]
    )

    with pytest.raises(RespuestaNoValida):
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert len(proveedor.llamadas) == 2


def test_un_pdf_que_no_se_puede_leer_no_llega_al_motor(
    criterios_de_analisis, tmp_path
) -> None:
    """Sin texto no hay nada que analizar, y no se gasta una llamada."""
    from backend.extraccion.lectura import PdfIlegible

    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    (carpeta / "AF023_DAM_E2_20260115_v1.pdf").write_text("no soy un pdf")
    almacen = AlmacenEnMemoria()
    entrega = almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        version_criterios="v2026-2027",
    ))
    proveedor = ProveedorSimulado(respuestas=[])

    with pytest.raises(PdfIlegible):
        analizar_entrega(criterios_de_analisis, carpeta, "v2026-2027",
                         almacen, proveedor, entrega)

    assert proveedor.llamadas == []


def test_al_motor_se_le_envia_el_texto_del_trabajo(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                     almacen, proveedor, entrega)

    _, texto_enviado = proveedor.llamadas[0]
    assert "El presupuesto inicial asciende a 4.500 euros" in texto_enviado


def test_si_el_borrador_no_es_valido_el_informe_no_se_pierde(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """El informe es lo que le permite al profesor decidir, y no depende del
    borrador: si `componer` levanta `BorradorNoValido`, la entrega pasa a
    ANALIZADO igual y el informe viaja en la excepcion, no se tira.
    """
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion_con_nota(),
    ])

    with pytest.raises(InformeSinBorrador) as excepcion:
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert excepcion.value.informe.valoraciones[0].dimension == "D05"
    assert excepcion.value.entrega.estado == "ANALIZADO"
    assert almacen.por_id(entrega.id).estado == "ANALIZADO"


class _ProveedorQueFallaEnLaDevolucion:
    """El análisis sale bien a la primera. La segunda llamada -la de la
    devolución- falla con `fallo`; si se da `respuesta_final`, el reintento
    -la tercera llamada- la devuelve; si no, el reintento vuelve a fallar
    con el mismo `fallo` y ahí se detiene.

    Sirve para las dos formas en que puede fallar la devolución: un fallo
    persistente que no se reintenta (`ErrorDelProveedor`, sin
    `respuesta_final`: la segunda y la tercera llamada fallan igual) o un
    único tropiezo que el reintento resuelve (`RespuestaNoValida`, con
    `respuesta_final`). No se puede montar ninguno de los dos con
    `ProveedorSimulado`: esa clase consume siempre antes la cola de fallos,
    y aquí hace falta lo contrario, que la primera llamada tenga éxito.
    """

    def __init__(self, primera_respuesta, fallo, respuesta_final=None) -> None:
        self._primera_respuesta = primera_respuesta
        self._fallo = fallo
        self._respuesta_final = respuesta_final
        self.llamadas: list[tuple[str, str]] = []

    @property
    def nombre(self) -> str:
        return "simulado"

    def analizar(self, instruccion, texto, formato):
        self.llamadas.append((instruccion, texto))
        if len(self.llamadas) == 1:
            return self._primera_respuesta
        if len(self.llamadas) >= 3 and self._respuesta_final is not None:
            return self._respuesta_final
        raise self._fallo


def test_si_el_motor_falla_en_el_borrador_el_informe_no_se_pierde(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """Lo mismo, pero cuando el fallo en el borrador es del proveedor -sin
    red, por ejemplo- y no una regla dura violada.
    """
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = _ProveedorQueFallaEnLaDevolucion(
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        ErrorDelProveedor("sin red"),
    )

    with pytest.raises(InformeSinBorrador) as excepcion:
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert excepcion.value.informe.valoraciones[0].dimension == "D05"
    assert almacen.por_id(entrega.id).estado == "ANALIZADO"
    # Dos llamadas: el análisis, y el intento de la devolución que falla.
    # `ErrorDelProveedor` -sin red- no es `RespuestaNoValida`, así que no se
    # reintenta: solo el formulario mal rellenado merece un segundo intento.
    assert len(proveedor.llamadas) == 2


def test_la_devolucion_tambien_se_reintenta_una_vez(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """El reintento único no protege solo la llamada del análisis: la
    llamada que pide la redacción del borrador -dentro de `componer()`,
    Task 8- también puede volver un formulario que no encaja, y también
    merece un reintento.

    Sin esta prueba, quitar el envoltorio de reintento alrededor de esa
    segunda llamada no lo detecta ningún test: el que prueba la retentiva
    programa el `RespuestaNoValida` en la primera llamada -la del
    análisis-, y los que tocan el borrador usan `ErrorDelProveedor` y
    `BorradorNoValido`, que precisamente no son reintentables.
    """
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = _ProveedorQueFallaEnLaDevolucion(
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        RespuestaNoValida("no encaja"),
        respuesta_final=_devolucion(),
    )

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert c.devolucion.acciones == ["Justifica las cifras con fuentes."]
    # Tres llamadas: el análisis, la devolución que falla, y su reintento,
    # que sale bien.
    assert len(proveedor.llamadas) == 3


def test_el_texto_del_alumno_no_viaja_en_la_correccion(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """Nada de lo que se sirve al docente puede llevar el texto entero del
    trabajo: ni `Correccion` como tipo, ni su volcado a JSON.

    Una cita literal breve -la evidencia de una valoración- sí aparece, y es
    lo esperado: es la garantía del §7, no una fuga del texto entero. Lo que
    no puede aparecer es el documento completo tal cual lo devuelve `medir`.
    """
    from backend.extraccion import medir

    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    texto_completo = medir(entregas_con_pdf / entrega.nombre_archivo).texto_plano
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert "texto_plano" not in Correccion.model_fields
    assert texto_completo not in c.model_dump_json()


# --- cabecera: modalidad y fecha (§17.1) ------------------------------------


def test_la_cabecera_lleva_modalidad_y_fecha(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    # `_registrar` no declara modalidad: sin pantalla de validación de tema
    # todavía, es el caso más frecuente, y el informe lo dice en vez de
    # dejar la clave vacía o ausente.
    assert c.informe.identificacion["modalidad"] == "No registrada"
    assert c.informe.identificacion["fecha"]


def test_la_cabecera_lleva_la_modalidad_declarada_al_confirmar(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    from backend.extraccion import medir
    from backend.persistencia.modelos import EntregaNueva

    almacen = AlmacenEnMemoria()
    ruta = entregas_con_pdf / "AF023_DAM_E2_20260115_v1.pdf"
    entrega = almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo=ruta.name, huella=medir(ruta).huella,
        version_criterios="v2026-2027", modalidad="profesional",
    ))
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert c.informe.identificacion["modalidad"] == "PROFESIONAL"


# --- continuidad (§17.1, D-012) ---------------------------------------------
#
# El bloque «Continuidad» compara el último feedback guardado -las
# prioridades de la corrección anterior- con el texto de esta entrega. Estas
# pruebas ejercitan el recorrido entero, con PDFs reales, no con un
# `Informe` montado a mano: es la única forma de comprobar que
# `analizar_entrega` de verdad recupera la entrega y la corrección
# anteriores y se las pasa a `componer_informe`.


@pytest.fixture
def carpeta_dos_fases(tmp_path: Path, escribir_pdf):
    """E1 y E2 del mismo alumno, con el mismo párrafo de presupuesto: sirve
    de base tanto para «sigue igual» (PENDIENTE) como, modificando solo la
    segunda entrega, para «ha cambiado» (NO_VERIFICABLE)."""
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    escribir_pdf(carpeta / "AF023_DAM_E1_20260101_v1.pdf", [[
        "1. Introduccion",
        "El presente proyecto describe la implantacion de un sistema.",
        "5. Presupuesto",
        "El presupuesto inicial asciende a 4.500 euros en total.",
    ]])
    return carpeta


def _registrar_fase(almacen, carpeta, nombre_archivo, fase):
    from backend.extraccion import medir
    ruta = carpeta / nombre_archivo
    return almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase=fase, version=1,
        nombre_archivo=ruta.name, huella=medir(ruta).huella,
        version_criterios="v2026-2027",
    ))


def _analizar_e1(criterios_de_analisis, carpeta_dos_fases, almacen):
    """Analiza la E1 y, a diferencia de lo que hace `analizar_entrega` por
    sí sola, GUARDA la corrección en el almacén -es lo que hace
    `backend/api/analisis.py` (`_guardar_o_fallar`), no este servicio-, para
    que `anterior_de`/`correccion_de` puedan encontrarla al analizar la E2.
    Sin este guardado explícito, `almacen.correccion_de(entrega_e1.id)`
    devolvería `None` y todas las pruebas de continuidad de aquí abajo
    estarían comparando contra un antecedente que en realidad nunca se
    guardó.
    """
    entrega_e1 = _registrar_fase(
        almacen, carpeta_dos_fases, "AF023_DAM_E1_20260101_v1.pdf", "E1",
    )
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros", dimension="D01"),
        _devolucion(),
    ])
    c = analizar_entrega(
        criterios_de_analisis, carpeta_dos_fases, "v2026-2027",
        almacen, proveedor, entrega_e1,
    )
    almacen.guardar_correccion(entrega_e1.id, c.informe, c.devolucion, c.motor)
    return c


def test_la_primera_entrega_no_tiene_continuidad(
    criterios_de_analisis, carpeta_dos_fases
) -> None:
    almacen = AlmacenEnMemoria()

    c = _analizar_e1(criterios_de_analisis, carpeta_dos_fases, almacen)

    assert c.informe.continuidad == []
    assert "primera entrega" in c.informe.continuidad_nota.lower()


def test_el_feedback_que_sigue_igual_en_la_entrega_nueva_es_pendiente(
    criterios_de_analisis, carpeta_dos_fases, escribir_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    _analizar_e1(criterios_de_analisis, carpeta_dos_fases, almacen)

    # La E2 conserva, literal, el párrafo del presupuesto que motivó la
    # prioridad de la E1: el alumno no lo ha tocado.
    escribir_pdf(carpeta_dos_fases / "AF023_DAM_E2_20260201_v1.pdf", [[
        "1. Introduccion",
        "El presente proyecto describe la implantacion de un sistema.",
        "3. Arquitectura",
        "El sistema se organiza en tres capas bien diferenciadas.",
        "5. Presupuesto",
        "El presupuesto inicial asciende a 4.500 euros en total.",
    ]])
    entrega_e2 = _registrar_fase(
        almacen, carpeta_dos_fases, "AF023_DAM_E2_20260201_v1.pdf", "E2",
    )
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El sistema se organiza en tres capas"),
        _devolucion(),
    ])

    c = analizar_entrega(
        criterios_de_analisis, carpeta_dos_fases, "v2026-2027",
        almacen, proveedor, entrega_e2,
    )

    assert c.informe.continuidad_nota is None
    por_dimension = {item.dimension: item.estado for item in c.informe.continuidad}
    assert por_dimension == {"D01": "PENDIENTE"}


def test_el_feedback_que_ya_no_aparece_es_no_verificable(
    criterios_de_analisis, carpeta_dos_fases, escribir_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    _analizar_e1(criterios_de_analisis, carpeta_dos_fases, almacen)

    # La E2 conserva la introducción, pero reescribe el presupuesto entero:
    # el fragmento que motivó la prioridad de la E1 ya no está.
    escribir_pdf(carpeta_dos_fases / "AF023_DAM_E2_20260201_v1.pdf", [[
        "1. Introduccion",
        "El presente proyecto describe la implantacion de un sistema.",
        "3. Arquitectura",
        "El sistema se organiza en tres capas bien diferenciadas.",
        "5. Presupuesto",
        "Se ha revisado el coste total del proyecto con el nuevo proveedor.",
    ]])
    entrega_e2 = _registrar_fase(
        almacen, carpeta_dos_fases, "AF023_DAM_E2_20260201_v1.pdf", "E2",
    )
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El sistema se organiza en tres capas"),
        _devolucion(),
    ])

    c = analizar_entrega(
        criterios_de_analisis, carpeta_dos_fases, "v2026-2027",
        almacen, proveedor, entrega_e2,
    )

    assert c.informe.continuidad_nota is None
    por_dimension = {item.dimension: item.estado for item in c.informe.continuidad}
    assert por_dimension == {"D01": "NO_VERIFICABLE"}


def test_sin_prioridades_en_la_entrega_anterior_la_nota_lo_dice(
    criterios_de_analisis, carpeta_dos_fases, escribir_pdf
) -> None:
    """La E1 se analiza con un motor que no encuentra nada que priorizar
    -`AnalisisDelMotor` con `valoraciones=[]`-, así que no hay ningún
    feedback que continuar en la E2, y no es lo mismo que no tener
    antecedente en absoluto."""
    almacen = AlmacenEnMemoria()
    entrega_e1 = _registrar_fase(
        almacen, carpeta_dos_fases, "AF023_DAM_E1_20260101_v1.pdf", "E1",
    )
    c1 = analizar_entrega(
        criterios_de_analisis, carpeta_dos_fases, "v2026-2027", almacen,
        ProveedorSimulado(respuestas=[
            AnalisisDelMotor(
                valoraciones=[], fortalezas=[], patrones=[],
                dudas_para_el_docente=[], indicios_de_autoria=[],
            ),
            _devolucion(),
        ]),
        entrega_e1,
    )
    # Sin este guardado explícito no habría corrección que recuperar al
    # analizar la E2: ver el docstring de `_analizar_e1`.
    almacen.guardar_correccion(entrega_e1.id, c1.informe, c1.devolucion, c1.motor)

    escribir_pdf(carpeta_dos_fases / "AF023_DAM_E2_20260201_v1.pdf", [[
        "1. Introduccion",
        "El presente proyecto describe la implantacion de un sistema.",
    ]])
    entrega_e2 = _registrar_fase(
        almacen, carpeta_dos_fases, "AF023_DAM_E2_20260201_v1.pdf", "E2",
    )

    c = analizar_entrega(
        criterios_de_analisis, carpeta_dos_fases, "v2026-2027", almacen,
        ProveedorSimulado(respuestas=[
            AnalisisDelMotor(
                valoraciones=[], fortalezas=[], patrones=[],
                dudas_para_el_docente=[], indicios_de_autoria=[],
            ),
            _devolucion(),
        ]),
        entrega_e2,
    )

    assert c.informe.continuidad == []
    assert "no tenia prioridades" in c.informe.continuidad_nota.lower() \
        or "no tenía prioridades" in c.informe.continuidad_nota.lower()
