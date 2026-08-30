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


def _analisis_bueno(cita):
    """Un `AnalisisDelMotor` válido cuyas citas existen en el PDF de prueba.

    El brief traía `fortalezas=["La estructura del documento es clara."]`,
    una lista de cadenas sueltas: `AnalisisDelMotor.fortalezas` exige
    `list[Fortaleza]`, con su propia evidencia -el mismo requisito que ya
    cierra la puerta a una fortaleza inventada-, y una cadena suelta no
    valida contra ese tipo. Se corrige aquí construyendo la `Fortaleza` con
    evidencia real, tomada del mismo fragmento que ya se sabe localizable
    porque `cita` lo es.
    """
    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
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


@pytest.fixture
def entregas_con_pdf_y_nombre(tmp_path: Path, escribir_pdf):
    """Como `entregas_con_pdf`, pero con el nombre del alumno escrito en el
    trabajo -como aparecería en una portada real-, para probar la
    minimización antes de la llamada al motor."""
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    escribir_pdf(carpeta / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion",
        "Trabajo presentado por Nombre Apellido para el modulo de FCT.",
        "5. Presupuesto",
        "El presupuesto inicial asciende a 4.500 euros en total.",
    ]])
    return carpeta


class _ListadoFalso:
    """Un `ListadoLocal` de mentira, sin tocar disco."""

    def __init__(self, nombres: dict[str, str]) -> None:
        self._nombres = nombres

    def nombre_de(self, codigo: str) -> str | None:
        return self._nombres.get(codigo)


class _ProveedorRealDePrueba:
    """Como `ProveedorSimulado`, pero con un `nombre` que no es "simulado".

    El aviso de privacidad se calla a propósito cuando el proveedor es el
    simulado -no sale nada hacia ningún sitio, así que avisar sería ruido
    sobre un envío que no ocurre (ver `analizar_entrega`)-. Para probar que
    el aviso SÍ aparece cuando de verdad haría falta, hace falta un
    proveedor cuyo nombre no sea literalmente "simulado".
    """

    def __init__(self, respuestas) -> None:
        self._interno = ProveedorSimulado(respuestas=respuestas)

    @property
    def nombre(self) -> str:
        return "real-de-prueba"

    @property
    def llamadas(self):
        return self._interno.llamadas

    def analizar(self, instruccion: str, texto: str, formato):
        return self._interno.analizar(instruccion, texto, formato)


def test_el_nombre_del_alumno_no_llega_al_motor_si_el_listado_lo_conoce(
    criterios_de_analisis, entregas_con_pdf_y_nombre
) -> None:
    """El caso central que pide el docente: antes de la llamada externa, el
    nombre se sustituye por el marcador de minimización."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf_y_nombre)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])
    listado = _ListadoFalso({"AF023": "Nombre Apellido"})

    analizar_entrega(criterios_de_analisis, entregas_con_pdf_y_nombre, "v2026-2027",
                     almacen, proveedor, entrega, listado)

    for _, texto_enviado in proveedor.llamadas:
        assert "Nombre Apellido" not in texto_enviado
    _, primera_llamada = proveedor.llamadas[0]
    assert "[ALUMNO]" in primera_llamada


def test_sin_listado_el_nombre_llega_tal_cual_pero_el_aviso_lo_dice(
    criterios_de_analisis, entregas_con_pdf_y_nombre
) -> None:
    """Lo que hace el sistema cuando NO puede comprobar que el nombre se
    retiró: no lo esconde ni promete lo que no puede garantizar. Sigue
    analizando -son datos propios, en una prueba-, pero lo dice."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf_y_nombre)
    proveedor = _ProveedorRealDePrueba([
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf_y_nombre, "v2026-2027",
                         almacen, proveedor, entrega, None)

    _, texto_enviado = proveedor.llamadas[0]
    assert "Nombre Apellido" in texto_enviado
    assert "listado local" in c.aviso_privacidad


def test_el_proveedor_simulado_no_genera_aviso_de_privacidad(
    criterios_de_analisis, entregas_con_pdf_y_nombre
) -> None:
    """Con el proveedor simulado no sale nada hacia ningún sitio: avisar de
    que el nombre podría no haberse retirado sería ruido."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf_y_nombre)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf_y_nombre, "v2026-2027",
                         almacen, proveedor, entrega, None)

    assert c.aviso_privacidad == ""


class _ConsumoFalso:
    def __init__(self, tokens_entrada: int, tokens_salida: int,
                 tokens_entrada_cacheados: int = 0) -> None:
        self.tokens_entrada = tokens_entrada
        self.tokens_salida = tokens_salida
        self.tokens_entrada_cacheados = tokens_entrada_cacheados


class _ProveedorConConsumo:
    """Un proveedor de prueba que sí deja huella de consumo -`nombre` real,
    `numero_de_llamadas`, `ultimo_consumo`, `modelo`-, para probar el
    registro de consumo sin hablar con OpenAI de verdad."""

    def __init__(self, respuestas, consumos=None, fallos=None) -> None:
        self._interno = ProveedorSimulado(respuestas=respuestas, fallos=fallos)
        self._consumos = list(consumos or [])
        self.numero_de_llamadas = 0
        self.ultimo_consumo = None
        self.modelo = "modelo-de-prueba"

    @property
    def nombre(self) -> str:
        return "proveedor-de-prueba"

    @property
    def llamadas(self):
        return self._interno.llamadas

    def analizar(self, instruccion: str, texto: str, formato):
        self.numero_de_llamadas += 1
        self.ultimo_consumo = self._consumos.pop(0) if self._consumos else None
        return self._interno.analizar(instruccion, texto, formato)


def test_se_registra_el_consumo_de_una_ejecucion_completa(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = _ProveedorConConsumo(
        respuestas=[_analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
                    _devolucion()],
        consumos=[_ConsumoFalso(1000, 200), _ConsumoFalso(500, 100)],
    )

    analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                     almacen, proveedor, entrega)

    registros = almacen.consumos()
    assert len(registros) == 1
    registro = registros[0]
    assert registro.entrega_id == entrega.id
    assert registro.modelo == "proveedor-de-prueba"
    assert registro.estado == "OK"
    assert registro.intentos == 2
    assert registro.tokens_entrada == 1500
    assert registro.tokens_salida == 300
    assert registro.paginas is not None
    assert registro.caracteres_texto is not None
    # "modelo-de-prueba" no está en config/precios_openai.yaml: el coste no
    # se inventa, se deja como no calculable.
    assert registro.coste_estimado_usd is None
    assert registro.tarifa_aplicada is None


def test_se_registra_el_consumo_aunque_el_motor_falle(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = _ProveedorConConsumo(
        respuestas=[], fallos=[ErrorDelProveedor("la cuota se ha agotado")],
    )

    with pytest.raises(ErrorDelProveedor):
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    registros = almacen.consumos()
    assert len(registros) == 1
    assert registros[0].estado == "ERROR"
    assert "cuota" in registros[0].causa_error


def test_el_proveedor_simulado_no_deja_registro_de_consumo(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """No cuesta nada: no hay nada que registrar."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                     almacen, proveedor, entrega)

    assert almacen.consumos() == []
