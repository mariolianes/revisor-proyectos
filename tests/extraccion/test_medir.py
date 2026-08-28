"""La medición completa de un archivo."""

from pathlib import Path

from backend.extraccion import medir


def test_recoge_el_nombre_del_archivo(pdf_con_indice: Path) -> None:
    medidas = medir(pdf_con_indice)

    assert medidas.nombre_archivo == "con-indice.pdf"


def test_la_huella_es_estable(pdf_con_indice: Path) -> None:
    """Dos lecturas del mismo archivo dan la misma huella."""
    assert medir(pdf_con_indice).huella == medir(pdf_con_indice).huella


def test_la_huella_distingue_dos_archivos(pdf_con_indice: Path, pdf_simple: Path) -> None:
    assert medir(pdf_con_indice).huella != medir(pdf_simple).huella


def test_junta_las_cuatro_mediciones(pdf_con_indice: Path) -> None:
    medidas = medir(pdf_con_indice)

    assert medidas.total_paginas == 7
    assert medidas.texto.cuerpo_dominante == 11.0
    assert medidas.estructura.paginas_de_contenido == 4
    assert medidas.imagenes == []


def test_lista_las_paginas_en_blanco(pdf_con_pagina_en_blanco: Path) -> None:
    medidas = medir(pdf_con_pagina_en_blanco)

    assert medidas.paginas_en_blanco == [2]


def test_marca_el_escaneado(pdf_escaneado: Path) -> None:
    medidas = medir(pdf_escaneado)

    assert medidas.escaneado is True
    assert medir(pdf_escaneado).texto.familia_dominante == ""


def test_conserva_el_texto_plano(pdf_con_indice: Path) -> None:
    """Lo necesita la comparación evolutiva. No se guarda en Supabase."""
    medidas = medir(pdf_con_indice)

    assert "Introduccion" in medidas.texto_plano


def test_no_toca_el_archivo(pdf_con_indice: Path) -> None:
    """El §18.1 lo exige: se lee y nada más."""
    antes = pdf_con_indice.read_bytes()
    momento = pdf_con_indice.stat().st_mtime

    medir(pdf_con_indice)

    assert pdf_con_indice.read_bytes() == antes
    assert pdf_con_indice.stat().st_mtime == momento
