"""Lo que se sabe de un PDF sin interpretarlo."""

from pathlib import Path

import pytest

from backend.extraccion.lectura import (
    PdfIlegible,
    abrir,
    leer_paginas,
    procede_de_escaner,
)


def test_cuenta_las_paginas(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        paginas = leer_paginas(documento)

    assert len(paginas) == 2
    assert [pagina.numero for pagina in paginas] == [1, 2]


def test_detecta_la_pagina_en_blanco(pdf_con_pagina_en_blanco: Path) -> None:
    with abrir(pdf_con_pagina_en_blanco) as documento:
        paginas = leer_paginas(documento)

    assert [pagina.en_blanco for pagina in paginas] == [False, True, False]


def test_cuenta_los_caracteres_de_cada_pagina(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        paginas = leer_paginas(documento)

    assert paginas[0].caracteres > paginas[1].caracteres > 0


def test_mide_el_tamano_de_la_pagina(pdf_simple: Path) -> None:
    """A4 son 595 x 842 puntos; se admite el redondeo del propio PDF."""
    with abrir(pdf_simple) as documento:
        paginas = leer_paginas(documento)

    assert paginas[0].ancho_pt == pytest.approx(595, abs=1)
    assert paginas[0].alto_pt == pytest.approx(842, abs=1)


def test_un_pdf_con_texto_no_es_escaneado(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        assert procede_de_escaner(documento) is False


def test_un_pdf_de_imagenes_sin_texto_es_escaneado(pdf_escaneado: Path) -> None:
    with abrir(pdf_escaneado) as documento:
        assert procede_de_escaner(documento) is True


def test_un_fichero_que_no_es_pdf_da_error_legible(tmp_path: Path) -> None:
    falso = tmp_path / "no-es.pdf"
    falso.write_text("esto no es un PDF", encoding="utf-8")

    with pytest.raises(PdfIlegible) as fallo:
        with abrir(falso):
            pass

    assert "no se ha podido abrir" in str(fallo.value).lower()


def test_un_fichero_que_no_existe_da_error_legible(tmp_path: Path) -> None:
    with pytest.raises(PdfIlegible) as fallo:
        with abrir(tmp_path / "fantasma.pdf"):
            pass

    assert "no existe" in str(fallo.value).lower()


def test_un_pdf_sin_paginas_da_error_legible(tmp_path: Path) -> None:
    """PyMuPDF se niega a guardar un PDF de cero páginas, así que se escribe
    a mano. Un PDF así llega cuando una exportación se queda a medias."""
    vacio = tmp_path / "vacio.pdf"
    vacio.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R /Size 3 >>\n%%EOF\n"
    )

    with pytest.raises(PdfIlegible) as fallo:
        with abrir(vacio):
            pass

    assert "ninguna página" in str(fallo.value)
