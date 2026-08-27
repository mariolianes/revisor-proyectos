"""Índice, contenido y anexos: dónde empieza y acaba lo que se cuenta."""

from pathlib import Path

from backend.extraccion.estructura import medir_estructura
from backend.extraccion.lectura import abrir


def test_localiza_la_pagina_del_indice(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.pagina_del_indice == 2


def test_el_contenido_empieza_tras_el_indice(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_contenido == 3


def test_localiza_el_comienzo_de_los_anexos(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_anexos == 7


def test_cuenta_las_paginas_de_contenido(pdf_con_indice: Path) -> None:
    """De la 3 a la 6: cuatro páginas. Portada, índice y anexo fuera."""
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.paginas_de_contenido == 4


def test_lee_las_entradas_del_indice(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    titulos = [entrada.titulo for entrada in estructura.entradas_de_indice]
    assert "1. Introduccion" in titulos
    assert "2. Objetivos" in titulos
    assert len(estructura.entradas_de_indice) == 4


def test_detecta_la_pagina_declarada_que_no_cuadra(pdf_con_indice: Path) -> None:
    """El índice dice que «3. Desarrollo» está en la 5, y está en la 6."""
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert any("Desarrollo" in aviso for aviso in estructura.paginas_declaradas_incorrectas)


def test_las_paginas_correctas_no_se_avisan(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert not any(
        "Introduccion" in aviso for aviso in estructura.paginas_declaradas_incorrectas
    )


def test_titulo_del_indice_que_no_aparece_en_el_documento(escribir_pdf, tmp_path: Path) -> None:
    ruta = escribir_pdf(
        tmp_path / "descuadrado.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3", "9. Conclusiones fantasma .... 4"],
            ["1. Introduccion", "Texto."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert any("fantasma" in titulo for titulo in estructura.titulos_no_encontrados)


def test_sin_indice_no_se_deduce_nada(pdf_simple: Path) -> None:
    """No hay índice: no se adivina dónde empieza el contenido."""
    with abrir(pdf_simple) as documento:
        estructura = medir_estructura(documento)

    assert estructura.pagina_del_indice is None
    assert estructura.primera_pagina_de_contenido is None
    assert estructura.paginas_de_contenido is None
    assert estructura.entradas_de_indice == []


def test_sin_anexos_el_contenido_llega_al_final(escribir_pdf, tmp_path: Path) -> None:
    ruta = escribir_pdf(
        tmp_path / "sin-anexos.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3"],
            ["1. Introduccion", "Texto."],
            ["Mas texto del trabajo."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_anexos is None
    assert estructura.paginas_de_contenido == 2
