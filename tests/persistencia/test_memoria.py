"""El almacén en memoria, que es también el contrato del puerto."""

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva


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
