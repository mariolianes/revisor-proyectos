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


class _ProveedorQueFallaSoloEnLaDevolucion:
    """El análisis sale bien a la primera; cualquier llamada posterior -la
    de la devolución, y su reintento- falla sin red.

    No se puede montar con `ProveedorSimulado`: esa clase consume siempre
    primero la cola de fallos, y aquí hace falta lo contrario, que la
    primera llamada tenga éxito y las siguientes no.
    """

    def __init__(self, primera_respuesta) -> None:
        self._primera_respuesta = primera_respuesta
        self.llamadas: list[tuple[str, str]] = []

    @property
    def nombre(self) -> str:
        return "simulado"

    def analizar(self, instruccion, texto, formato):
        self.llamadas.append((instruccion, texto))
        if len(self.llamadas) == 1:
            return self._primera_respuesta
        raise ErrorDelProveedor("sin red")


def test_si_el_motor_falla_en_el_borrador_el_informe_no_se_pierde(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """Lo mismo, pero cuando el fallo en el borrador es del proveedor -sin
    red, por ejemplo- y no una regla dura violada.
    """
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = _ProveedorQueFallaSoloEnLaDevolucion(
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros")
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
