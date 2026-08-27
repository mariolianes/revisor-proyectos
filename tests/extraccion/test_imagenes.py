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
