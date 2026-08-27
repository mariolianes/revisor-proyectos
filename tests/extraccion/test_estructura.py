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


def test_localiza_un_apartado_que_no_empieza_al_principio_de_pagina(
    escribir_pdf, tmp_path: Path
) -> None:
    """«2. Objetivos» empieza en la sexta línea de su página, no en la primera.

    Es lo normal cuando el apartado anterior es corto y no llena la página.
    """
    ruta = escribir_pdf(
        tmp_path / "apartado-a-media-pagina.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3", "2. Objetivos .... 3"],
            [
                "1. Introduccion", "linea 1 del texto", "linea 2 del texto",
                "linea 3 del texto", "linea 4 del texto",
                "2. Objetivos", "texto de objetivos",
            ],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.titulos_no_encontrados == []


def test_lee_las_entradas_de_un_indice_repartido_en_dos_paginas(
    escribir_pdf, tmp_path: Path
) -> None:
    """Un índice con muchos subapartados no siempre cabe en una página."""
    ruta = escribir_pdf(
        tmp_path / "indice-en-dos-paginas.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3", "2. Objetivos .... 4"],
            ["3. Desarrollo .... 5", "4. Conclusiones .... 6"],
            ["1. Introduccion", "Texto."],
            ["2. Objetivos", "Texto."],
            ["3. Desarrollo", "Texto."],
            ["4. Conclusiones", "Texto."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    titulos = [entrada.titulo for entrada in estructura.entradas_de_indice]
    assert "3. Desarrollo" in titulos
    assert "4. Conclusiones" in titulos
    assert len(estructura.entradas_de_indice) == 4
    assert estructura.primera_pagina_de_contenido == 4
    assert estructura.paginas_de_contenido == 4


def test_el_indice_declarado_de_anexos_gana_a_un_falso_positivo(
    escribir_pdf, tmp_path: Path
) -> None:
    """Un párrafo que empieza por «Anexos» no debe ganar a lo que declara el índice."""
    ruta = escribir_pdf(
        tmp_path / "anexos-declarados.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3", "ANEXOS .... 5"],
            [
                "1. Introduccion",
                "Anexos de estudios previos citados en la introduccion.",
            ],
            ["Mas texto."],
            ["ANEXOS", "Anexo I."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_anexos == 5


def test_sin_anexos_declarados_se_toma_la_ultima_aparicion(
    escribir_pdf, tmp_path: Path
) -> None:
    """Sin entrada de anexos en el índice, gana la última mención, no la primera."""
    ruta = escribir_pdf(
        tmp_path / "anexos-sin-declarar.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3"],
            [
                "1. Introduccion",
                "Anexos de calculo mencionados en el texto.",
            ],
            ["Mas contenido del trabajo."],
            ["ANEXOS", "Anexo I. Codigo fuente."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_anexos == 5
    assert estructura.paginas_de_contenido == 2


def test_no_busca_el_indice_mas_alla_del_limite_de_paginas(
    escribir_pdf, tmp_path: Path
) -> None:
    """Un índice que empieza en la página 7 queda fuera de la ventana de búsqueda."""
    ruta = escribir_pdf(
        tmp_path / "indice-tardio.pdf",
        [
            ["Pagina de relleno 1."],
            ["Pagina de relleno 2."],
            ["Pagina de relleno 3."],
            ["Pagina de relleno 4."],
            ["Pagina de relleno 5."],
            ["Pagina de relleno 6."],
            ["INDICE", "1. Introduccion .... 8"],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.pagina_del_indice is None
    assert estructura.primera_pagina_de_contenido is None
    assert estructura.paginas_de_contenido is None
    assert estructura.entradas_de_indice == []


def test_un_indice_de_figuras_no_se_confunde_con_continuacion_del_indice(
    escribir_pdf, tmp_path: Path
) -> None:
    """Un «Índice de figuras» detrás del índice tiene la misma forma, pero no es su continuación.

    Empieza con su propio título, no con una entrada: no debe absorberse
    como si fuera la segunda página del índice.
    """
    ruta = escribir_pdf(
        tmp_path / "indice-de-figuras.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 4"],
            ["INDICE DE FIGURAS", "Figura 1. Diagrama .... 4", "Figura 2. Esquema .... 5"],
            ["1. Introduccion", "Texto."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_contenido == 3
    titulos = [entrada.titulo for entrada in estructura.entradas_de_indice]
    assert titulos == ["1. Introduccion"]
    assert not any("Figura" in titulo for titulo in estructura.titulos_no_encontrados)


def test_una_tabla_de_presupuesto_no_se_confunde_con_continuacion_del_indice(
    escribir_pdf, tmp_path: Path
) -> None:
    """Una tabla de presupuesto detrás del índice tampoco es su continuación.

    Empieza con su propia cabecera, no con una entrada de índice.
    """
    ruta = escribir_pdf(
        tmp_path / "tabla-de-presupuesto.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 4"],
            ["PRESUPUESTO", "Materiales .... 120", "Mano de obra .... 300"],
            ["1. Introduccion", "Texto."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_contenido == 3
    titulos = [entrada.titulo for entrada in estructura.entradas_de_indice]
    assert titulos == ["1. Introduccion"]
    assert not any("Materiales" in titulo for titulo in estructura.titulos_no_encontrados)
