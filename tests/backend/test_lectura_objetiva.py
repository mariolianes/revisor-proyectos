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


def _sin_tildes(texto: str) -> str:
    """Para afirmar sobre el texto de un aviso sin pelearse con los acentos."""
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )


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


def test_si_la_anterior_no_tiene_texto_no_se_inventa_una_comparacion(
    criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path,
    pdf_escaneado: Path,
) -> None:
    """Un escaneado no da ni una palabra: no hay nada que comparar.

    Antes se comparaba igual, porque el PDF anterior se abria sin error, y
    la ficha salia con proporcion_conservada 0.0 y proporcion_nueva 0.0
    -los valores por omision de Evolucion, no una medida-, que la pantalla
    lee como "se conserva el 0 % de lo anterior".
    """
    almacen = AlmacenEnMemoria()
    _registrar(almacen, entregas, pdf_escaneado, "E1")
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is None
    assert ficha.comparada_con is None
    assert "no parece incluir el trabajo anterior" not in ficha.aviso
    assert "no se ha comparado el progreso" in ficha.aviso.lower()
    # Dice cual de los dos documentos es el que no tiene texto.
    assert "AF023_DAM_E1_20260115_v1.pdf" in ficha.aviso
    assert "texto extraible" in _sin_tildes(ficha.aviso)


def test_si_la_nueva_no_tiene_texto_no_se_acusa_al_alumno(
    criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path,
    pdf_escaneado: Path,
) -> None:
    """El caso peor: sin este arreglo saltaba el aviso mas severo del 5.1.

    Que la entrega nueva sea un escaneado es un hecho técnico, no una
    entrega incompleta, y ya lo reporta por su cuenta el criterio "archivo"
    de formato. Acusar además de no incluir el trabajo anterior seria un
    aviso falso, y los avisos falsos llegan al alumno.
    """
    almacen = AlmacenEnMemoria()
    _registrar(almacen, entregas, pdf_con_indice, "E1")
    entrega = _registrar(almacen, entregas, pdf_escaneado, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is None
    assert ficha.comparada_con is None
    assert "no parece incluir el trabajo anterior" not in ficha.aviso
    assert "esta entrega no tiene texto" in _sin_tildes(ficha.aviso)
    # Lo que si se dice del escaneado lo dice el criterio de formato.
    archivo = next(c for c in ficha.comprobaciones if c.criterio == "archivo")
    assert archivo.veredicto == "NO_CUMPLE"


def test_un_archivo_que_desaparecio_bloquea_la_entrega(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    (entregas / entrega.nombre_archivo).unlink()

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.medidas is None
    assert ficha.entrega.estado == "BLOQUEADO"
    assert ficha.entrega.motivo_bloqueo is not None


def test_devolver_el_archivo_levanta_el_bloqueo(
    criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path
) -> None:
    """Una entrega bloqueada no se quedaba bloqueada para siempre.

    Si el archivo desaparecía, la entrega quedaba en BLOQUEADO. Al volver a
    dejarlo en la carpeta seguía bloqueada, y la ficha enseñaba las medidas
    completas junto al motivo falso «El archivo ya no está en la carpeta de
    entregas», en tinta de señal.
    """
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    ruta = entregas / entrega.nombre_archivo
    guardado = ruta.read_bytes()
    ruta.unlink()

    bloqueada = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)
    assert bloqueada.entrega.estado == "BLOQUEADO"
    assert bloqueada.entrega.motivo_bloqueo is not None

    ruta.write_bytes(guardado)
    ficha = leer(
        criterios_de_formato, entregas, "v2026-2027", almacen,
        almacen.por_id(entrega.id),
    )

    assert ficha.entrega.estado == "RECIBIDO"
    assert ficha.entrega.motivo_bloqueo is None
    assert ficha.medidas is not None
    # Y ha quedado guardado, no solo en la ficha que se devuelve.
    assert almacen.por_id(entrega.id).estado == "RECIBIDO"
    assert almacen.por_id(entrega.id).motivo_bloqueo is None


def test_una_lectura_correcta_no_toca_el_estado_que_puso_el_docente(
    criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path
) -> None:
    """Solo se levanta el bloqueo. ANALIZADO es del docente y ahí se queda."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    almacen.cambiar_estado(entrega.id, "ANALIZADO", None)

    ficha = leer(
        criterios_de_formato, entregas, "v2026-2027", almacen,
        almacen.por_id(entrega.id),
    )

    assert ficha.entrega.estado == "ANALIZADO"


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
