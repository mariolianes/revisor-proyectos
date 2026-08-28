"""El almacén en memoria, que es también el contrato del puerto."""

from datetime import datetime

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva, EntregaRegistrada


def _entrega(**cambios) -> EntregaNueva:
    datos = dict(
        codigo_alumno="AF023",
        ciclo="DAM",
        fase="E2",
        version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf",
        huella="a" * 64,
        version_criterios="v2026-2027",
    )
    datos.update(cambios)
    return EntregaNueva(**datos)


def test_una_entrega_registrada_se_recupera() -> None:
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega())

    assert almacen.por_id(guardada.id) == guardada
    assert guardada.codigo_alumno == "AF023"


def test_una_entrega_nueva_nace_recibida() -> None:
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega())

    assert guardada.estado == "RECIBIDO"
    assert guardada.motivo_bloqueo is None


def test_listar_devuelve_lo_registrado() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega())
    almacen.registrar(_entrega(codigo_alumno="AF024", huella="b" * 64))

    assert len(almacen.listar()) == 2


def test_se_encuentra_por_huella() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega())

    assert almacen.por_huella("a" * 64) is not None
    assert almacen.por_huella("z" * 64) is None


def test_el_mismo_archivo_dos_veces_no_se_duplica() -> None:
    """Misma huella es el mismo archivo: se devuelve el registro existente."""
    almacen = AlmacenEnMemoria()
    primera = almacen.registrar(_entrega())

    segunda = almacen.registrar(_entrega(nombre_archivo="copia.pdf"))

    assert segunda.id == primera.id
    assert len(almacen.listar()) == 1


def test_la_anterior_es_la_de_la_fase_previa() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="E1", huella="1" * 64))
    almacen.registrar(_entrega(fase="E2", huella="2" * 64))

    anterior = almacen.anterior_de("AF023", "E2")

    assert anterior is not None
    assert anterior.fase == "E1"


def test_la_anterior_puede_ser_una_version_previa_de_la_misma_fase() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="E2", version=1, huella="1" * 64))

    anterior = almacen.anterior_de("AF023", "E2", version=2)

    assert anterior is not None
    assert anterior.version == 1


def test_sin_entrega_previa_no_hay_anterior() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="TEMA"))

    assert almacen.anterior_de("AF023", "TEMA") is None


def test_la_anterior_es_de_ese_alumno_y_no_de_otro() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(codigo_alumno="AF024", fase="E1", huella="1" * 64))

    assert almacen.anterior_de("AF023", "E2") is None


def test_cambiar_de_estado() -> None:
    almacen = AlmacenEnMemoria()
    guardada = almacen.registrar(_entrega())

    cambiada = almacen.cambiar_estado(guardada.id, "BLOQUEADO", "PDF ilegible.")

    assert cambiada is not None
    assert cambiada.estado == "BLOQUEADO"
    assert cambiada.motivo_bloqueo == "PDF ilegible."
    assert almacen.por_id(guardada.id).estado == "BLOQUEADO"


def test_un_estado_desconocido_se_rechaza() -> None:
    almacen = AlmacenEnMemoria()
    guardada = almacen.registrar(_entrega())

    with pytest.raises(ValueError, match="no es un estado"):
        almacen.cambiar_estado(guardada.id, "TERMINADO", None)


def test_bloquear_sin_motivo_se_rechaza() -> None:
    """La tabla lo impone con una restricción; aquí se falla antes y mejor."""
    almacen = AlmacenEnMemoria()
    guardada = almacen.registrar(_entrega())

    with pytest.raises(ValueError, match="motivo"):
        almacen.cambiar_estado(guardada.id, "BLOQUEADO", None)


def test_cambiar_el_estado_de_algo_que_no_existe_da_none() -> None:
    almacen = AlmacenEnMemoria()

    assert almacen.cambiar_estado("no-existe", "ANALIZADO", None) is None


def test_una_fase_desconocida_se_rechaza() -> None:
    almacen = AlmacenEnMemoria()

    with pytest.raises(ValueError, match="no es una fase"):
        almacen.registrar(_entrega(fase="E9"))


def test_el_almacen_en_memoria_dice_que_no_es_duradero() -> None:
    """Lo lee el frontend para avisar al docente. No se finge lo contrario."""
    assert AlmacenEnMemoria().es_duradero is False


def test_una_fase_desconocida_en_anterior_de_se_rechaza_en_castellano() -> None:
    """`anterior_de` no debe reventar con el mensaje en inglés de tuple.index."""
    almacen = AlmacenEnMemoria()

    with pytest.raises(ValueError, match="no es una fase"):
        almacen.anterior_de("AF023", "E9")


def test_el_codigo_con_espacios_se_normaliza_al_guardar() -> None:
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega(codigo_alumno="  AF023  "))

    assert guardada.codigo_alumno == "AF023"


def test_la_fase_en_minusculas_se_acepta_y_queda_en_mayusculas() -> None:
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega(fase="e2"))

    assert guardada.fase == "E2"


def test_anterior_de_encuentra_al_alumno_aunque_se_registrara_con_espacios() -> None:
    """Sin normalizar, esto devolvía None: el alumno quedaba bajo otra clave."""
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(codigo_alumno="  AF023  ", fase="E2", huella="s" * 64))
    almacen.registrar(_entrega(codigo_alumno="  AF023  ", fase="E3", huella="t" * 64))

    anterior = almacen.anterior_de("AF023", "E3")

    assert anterior is not None
    assert anterior.fase == "E2"


def test_la_misma_huella_con_los_mismos_datos_declarados_devuelve_la_existente() -> None:
    """El mismo trabajo confirmado dos veces, aunque haya cambiado de ruta."""
    almacen = AlmacenEnMemoria()
    primera = almacen.registrar(_entrega(huella="x" * 64))

    segunda = almacen.registrar(
        _entrega(huella="x" * 64, nombre_archivo="otra_carpeta/copia.pdf")
    )

    assert segunda.id == primera.id
    assert len(almacen.listar()) == 1


def test_la_misma_huella_con_datos_declarados_distintos_se_rechaza() -> None:
    """Error de atribución: no se resuelve en silencio a favor del primero."""
    almacen = AlmacenEnMemoria()
    existente = almacen.registrar(_entrega(codigo_alumno="AF023", huella="x" * 64))

    with pytest.raises(ValueError, match="AF023") as excepcion:
        almacen.registrar(_entrega(codigo_alumno="AF999", huella="x" * 64))

    assert existente.id in str(excepcion.value)
    assert "AF999" in str(excepcion.value)


def test_la_anterior_es_la_inmediatamente_previa_entre_varias_candidatas() -> None:
    """Con varias entregas previas fuera de orden, se elige la más cercana.

    Blinda `max(candidatas, key=...)`: con `candidatas[0]` este test falla,
    porque la primera insertada (TEMA) no es la inmediatamente anterior a
    E3 (que es E2).
    """
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="TEMA", huella="1" * 64))
    almacen.registrar(_entrega(fase="E2", huella="2" * 64))
    almacen.registrar(_entrega(fase="E1", huella="3" * 64))

    anterior = almacen.anterior_de("AF023", "E3")

    assert anterior is not None
    assert anterior.fase == "E2"


@pytest.mark.parametrize(
    "codigo_sucio",
    [
        "AF 023",  # espacio normal en medio
        "AF\t023",  # tabulador en medio
        "AF\xa0023",  # espacio de no separación (NBSP) en medio
    ],
)
def test_un_espacio_en_medio_del_codigo_tambien_se_quita(codigo_sucio: str) -> None:
    """No solo los extremos: strip() los deja pasar, esto no."""
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega(codigo_alumno=codigo_sucio))

    assert guardada.codigo_alumno == "AF023"


def test_entrega_registrada_normaliza_igual_que_entrega_nueva() -> None:
    """La Task 11 construye EntregaRegistrada directo desde una fila de
    Supabase que puede ser anterior a esta regla: tiene que normalizar por
    su cuenta, no solo confiar en que ya llegó limpia."""
    registrada = EntregaRegistrada(
        id="cualquier-id",
        codigo_alumno="AF\xa0023",
        ciclo=" dam ",
        fase="e2",
        version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf",
        huella="a" * 64,
        recibida_en=datetime.now(),
        estado="RECIBIDO",
        motivo_bloqueo=None,
        version_criterios="v2026-2027",
    )

    assert registrada.codigo_alumno == "AF023"
    assert registrada.ciclo == "DAM"
    assert registrada.fase == "E2"
