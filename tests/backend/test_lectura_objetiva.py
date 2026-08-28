"""El servicio que une medición, criterios y comparación."""

from pathlib import Path

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.servicios.lectura_objetiva import leer, localizar

# `criterios_de_formato` y los PDF vienen de tests/conftest.py.


@pytest.fixture
def entregas(tmp_path: Path) -> Path:
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    return carpeta


def _registrar(almacen, carpeta: Path, origen: Path, fase: str, version: int = 1):
    """Copia el PDF a la carpeta de entregas con nombre de convención.

    Se añade un comentario después del `%%EOF` que no cambia ni una página
    ni un carácter de lo que se lee -pymupdf lo ignora, es basura tras el
    final del archivo-, pero sí cambia la huella. Sin esto, dos fases
    registradas a partir del mismo `pdf_con_indice` comparten huella, y el
    almacén las rechaza por R-persistencia: una huella repetida con otra
    fase declarada es el error de atribución que `registrar` existe para
    detectar, no dos versiones legítimas del mismo trabajo.
    """
    destino = carpeta / f"AF023_DAM_{fase}_20260115_v{version}.pdf"
    marca = f"\n% entrega de prueba {fase} v{version}\n".encode()
    destino.write_bytes(origen.read_bytes() + marca)
    from backend.extraccion import medir

    return almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase=fase, version=version,
        nombre_archivo=destino.name, huella=medir(destino).huella,
        version_criterios="v2026-2027",
    ))


def test_la_ficha_trae_las_medidas(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.medidas is not None
    assert ficha.medidas.total_paginas == 7


def test_la_ficha_trae_las_comprobaciones(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert len(ficha.comprobaciones) == 9


def test_sin_entrega_anterior_no_hay_comparacion(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "TEMA")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is None
    assert ficha.comparada_con is None
    assert ficha.aviso == ""


def test_con_entrega_anterior_se_compara(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    _registrar(almacen, entregas, pdf_con_indice, "E1")
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is not None
    assert ficha.comparada_con == "AF023_DAM_E1_20260115_v1.pdf"


def test_si_el_archivo_anterior_ya_no_esta_se_dice(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    """§18.2: sin el material anterior no se compara, y se avisa."""
    almacen = AlmacenEnMemoria()
    anterior = _registrar(almacen, entregas, pdf_con_indice, "E1")
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    (entregas / anterior.nombre_archivo).unlink()

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is None
    assert "ya no está en la carpeta" in ficha.aviso


def test_un_archivo_que_desaparecio_bloquea_la_entrega(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    (entregas / entrega.nombre_archivo).unlink()

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.medidas is None
    assert ficha.entrega.estado == "BLOQUEADO"
    assert ficha.entrega.motivo_bloqueo is not None


def test_un_pdf_ilegible_bloquea_la_entrega(criterios_de_formato: Path, entregas: Path) -> None:
    almacen = AlmacenEnMemoria()
    roto = entregas / "AF023_DAM_E2_20260115_v1.pdf"
    roto.write_text("esto no es un PDF", encoding="utf-8")
    entrega = almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo=roto.name, huella="a" * 64, version_criterios="v2026-2027",
    ))

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.entrega.estado == "BLOQUEADO"
    assert "no se ha podido abrir" in ficha.entrega.motivo_bloqueo.lower()
    assert ficha.comprobaciones == []


def test_leer_no_modifica_el_archivo(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    ruta = entregas / entrega.nombre_archivo
    antes = ruta.read_bytes()

    leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ruta.read_bytes() == antes


def test_localizar_encuentra_el_archivo_por_su_ruta_relativa(entregas: Path, pdf_con_indice: Path) -> None:
    """Caso normal: `mirar` ya da la ruta relativa, unir carpeta y ruta basta."""
    subcarpeta = entregas / "AF023"
    subcarpeta.mkdir()
    destino = subcarpeta / "AF023_DAM_E2_20260115_v1.pdf"
    destino.write_bytes(pdf_con_indice.read_bytes())

    encontrado = localizar(entregas, "AF023/AF023_DAM_E2_20260115_v1.pdf")

    assert encontrado == destino


def test_localizar_recurre_al_respaldo_si_el_archivo_se_ha_movido_de_subcarpeta(
    entregas: Path, pdf_con_indice: Path,
) -> None:
    """El docente mueve el archivo de una subcarpeta a otra después de
    registrarlo: la ruta relativa guardada («AF023/trabajo.pdf») ya no
    apunta a él -ahora vive en «OTROS/trabajo.pdf»-, así que se busca por
    su nombre de archivo en todo el árbol.

    Esta es la prueba deliberada de que el respaldo busca por
    `Path(nombre).name` y no por `nombre` entero: con `carpeta / nombre`
    la ruta directa ya no existe (la subcarpeta cambió), y si el respaldo
    también usara la ruta relativa completa -`carpeta.rglob(nombre)`-
    tampoco la encontraría, porque «AF023/trabajo.pdf» no existe en
    ninguna parte del árbol tras el movimiento. Solo buscando por el
    nombre suelto se le encuentra en su nueva subcarpeta.
    """
    origen = entregas / "AF023"
    origen.mkdir()
    destino_final = entregas / "OTROS" / "trabajo.pdf"
    destino_final.parent.mkdir()
    (origen / "trabajo.pdf").write_bytes(pdf_con_indice.read_bytes())
    (origen / "trabajo.pdf").rename(destino_final)

    encontrado = localizar(entregas, "AF023/trabajo.pdf")

    assert encontrado == destino_final

    # Verificación de que la prueba de arriba de verdad ejercita el
    # respaldo por nombre: con la ruta relativa completa, rglob no
    # encuentra nada, porque «AF023/trabajo.pdf» ya no existe en ningún
    # sitio del árbol tras el movimiento.
    assert not any(entregas.rglob("AF023/trabajo.pdf"))
    assert list(entregas.rglob("trabajo.pdf")) == [destino_final]


def test_localizar_devuelve_none_si_no_esta_en_ningun_sitio(entregas: Path) -> None:
    assert localizar(entregas, "fantasma.pdf") is None
