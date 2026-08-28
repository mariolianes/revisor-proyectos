"""Las imágenes: cuántas, dónde, a qué resolución y cuánto ocupan."""

from pathlib import Path

import pytest

from backend.extraccion.imagenes import leer_imagenes
from backend.extraccion.lectura import abrir


def test_cuenta_las_imagenes(pdf_con_imagenes: Path) -> None:
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    assert len(imagenes) == 2


def test_dice_en_que_pagina_esta_cada_una(pdf_con_imagenes: Path) -> None:
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    assert all(imagen.pagina == 1 for imagen in imagenes)


def test_calcula_la_resolucion_efectiva(pdf_con_imagenes: Path) -> None:
    """40 px repartidos en 200 pt son 14,4 ppp: 40 / (200/72)."""
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    borrosa = min(imagenes, key=lambda imagen: imagen.dpi_efectivo)
    assert borrosa.dpi_efectivo == pytest.approx(14.4, abs=0.1)
    assert borrosa.ancho_px == 40


def test_la_imagen_nitida_tiene_mas_resolucion(pdf_con_imagenes: Path) -> None:
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    nitida = max(imagenes, key=lambda imagen: imagen.dpi_efectivo)
    assert nitida.dpi_efectivo > 200


def test_calcula_la_proporcion_de_pagina(pdf_con_imagenes: Path) -> None:
    """200 x 150 pt sobre una A4 de 595 x 842: en torno al 6 %."""
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    assert all(
        imagen.proporcion_de_pagina == pytest.approx(0.06, abs=0.01)
        for imagen in imagenes
    )


def test_un_documento_sin_imagenes_da_lista_vacia(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        assert leer_imagenes(documento) == []


def test_el_dpi_no_cambia_con_la_rotacion_de_la_pagina(
    pdfs_con_imagen_en_cada_rotacion: dict[int, Path],
) -> None:
    """Una rotación de página es una isometría: mueve la imagen y su
    rectángulo juntos, sin estirar ninguno de los dos, así que no puede
    cambiar cuántos píxeles hay repartidos por punto.

    200x80 px en un rectángulo nativo de 150x50 pt da 96 ppp
    (200 / (150/72), el peor de los dos lados) sea cual sea la rotación de
    la página: 0°, 90°, 180° o 270° tienen que dar el mismo número.
    """
    dpis = {}
    for rotacion, ruta in pdfs_con_imagen_en_cada_rotacion.items():
        with abrir(ruta) as documento:
            imagenes = leer_imagenes(documento)
        assert len(imagenes) == 1
        dpis[rotacion] = imagenes[0].dpi_efectivo

    assert dpis[0] == pytest.approx(96.0, abs=0.1)
    assert dpis[90] == pytest.approx(dpis[0])
    assert dpis[180] == pytest.approx(dpis[0])
    assert dpis[270] == pytest.approx(dpis[0])


def test_dpi_efectivo_toma_el_lado_peor_mandado(
    pdf_con_imagen_estirada_de_forma_asimetrica: Path,
) -> None:
    """400x100 px en un rectángulo de 100x100 pt, sin conservar proporción:
    400/(100/72) = 288 ppp en horizontal, 100/(100/72) = 72 en vertical. El
    dpi efectivo tiene que quedarse con el peor de los dos, 72 -es el lado
    que se ve borroso-, no con el mejor: con `max` saldría 288 y la imagen
    pasaría por nítida.
    """
    dpi_horizontal_esperado = 400 / (100 / 72)
    dpi_vertical_esperado = 100 / (100 / 72)
    assert dpi_horizontal_esperado == pytest.approx(288.0)
    assert dpi_vertical_esperado == pytest.approx(72.0)

    with abrir(pdf_con_imagen_estirada_de_forma_asimetrica) as documento:
        imagenes = leer_imagenes(documento)

    assert len(imagenes) == 1
    assert imagenes[0].dpi_efectivo == pytest.approx(dpi_vertical_esperado, abs=0.1)


def test_imagen_sin_colocacion_localizable_no_aparece(
    pdf_con_imagen_sin_colocacion: Path,
) -> None:
    """Documentado en el módulo, no resuelto: un recurso sin colocación no
    se cuenta, sin error ni aviso.

    Deja constancia del límite tal como es hoy, no lo corrige: corregirlo
    exigiría reconstruir la colocación a partir del flujo de contenido, que
    es justo lo que falta cuando el operador que la dibuja no está.
    """
    with abrir(pdf_con_imagen_sin_colocacion) as documento:
        imagenes = leer_imagenes(documento)

    assert imagenes == []
