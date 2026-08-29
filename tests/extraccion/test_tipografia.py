"""Tipografía, interlineado, márgenes y alineación medidos sobre el PDF."""

from pathlib import Path

import pytest

from backend.extraccion.lectura import abrir
from backend.extraccion.tipografia import medir_texto, normalizar_familia


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("Arial", "Arial"),
        ("ABCDEF+Arial", "Arial"),
        ("ABCDEF+Arial-BoldMT", "Arial"),
        ("Arial,Bold", "Arial"),
        ("ArialMT", "Arial"),
        ("Helvetica", "Helvetica"),
        ("TimesNewRomanPSMT", "TimesNewRoman"),
        ("", ""),
        ("Times-Roman", "Times"),
        ("Helvetica-BoldOblique", "Helvetica"),
        ("Courier-BoldOblique", "Courier"),
        ("Courier-Oblique", "Courier"),
    ],
)
def test_normalizar_familia(crudo: str, esperado: str) -> None:
    assert normalizar_familia(crudo) == esperado


def test_familia_y_cuerpo_dominantes(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.familia_dominante == "Helvetica"
    assert medidas.cuerpo_dominante == 11.0


def test_el_titular_no_desplaza_al_cuerpo_dominante(pdf_cuerpo_mezclado: Path) -> None:
    """Domina lo que ocupa más caracteres, no lo que aparece primero."""
    with abrir(pdf_cuerpo_mezclado) as documento:
        medidas = medir_texto(documento)

    assert medidas.cuerpo_dominante == 11.0
    assert medidas.proporcion_cuerpo_dominante > 0.9


def test_ratio_de_interlineado(pdf_simple: Path) -> None:
    """El fixture separa las líneas base 19 pt con cuerpo 11: 19/11."""
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.ratio_interlineado == pytest.approx(19 / 11, abs=0.02)


def test_sin_dos_lineas_no_hay_interlineado(tmp_path: Path) -> None:
    """Una sola línea no define ningún salto. No se inventa uno."""
    import pymupdf

    documento = pymupdf.open()
    documento.new_page().insert_text((72.0, 100.0), "Sola.", fontname="helv", fontsize=11.0)
    ruta = tmp_path / "una-linea.pdf"
    documento.save(ruta)
    documento.close()

    with abrir(ruta) as abierto:
        medidas = medir_texto(abierto)

    assert medidas.ratio_interlineado is None


def test_margen_izquierdo_en_centimetros(pdf_simple: Path) -> None:
    """72 pt es exactamente una pulgada: 2,54 cm."""
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.margen_izquierdo_cm == pytest.approx(2.54, abs=0.05)


def test_los_cuatro_margenes_se_miden(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.margen_derecho_cm is not None
    assert medidas.margen_superior_cm is not None
    assert medidas.margen_inferior_cm is not None
    assert medidas.margen_superior_cm > 0


def test_texto_justificado_da_proporcion_alta(pdf_justificado: Path) -> None:
    with abrir(pdf_justificado) as documento:
        medidas = medir_texto(documento)

    assert medidas.proporcion_lineas_al_margen_derecho == pytest.approx(0.8, abs=0.01)


def test_texto_de_lineas_desiguales_da_proporcion_baja(
    pdf_alineado_izquierda: Path,
) -> None:
    """Cinco longitudes distintas: solo la más larga llega al borde."""
    with abrir(pdf_alineado_izquierda) as documento:
        medidas = medir_texto(documento)

    assert medidas.proporcion_lineas_al_margen_derecho == pytest.approx(0.2, abs=0.01)


def test_una_pagina_de_una_sola_linea_no_cuenta_para_la_alineacion(
    escribir_pdf, tmp_path: Path
) -> None:
    """Con una sola línea, el borde derecho no distingue nada.

    Esa línea es a la vez el máximo y el único candidato, así que daría el
    100 %. Una portada o una página de cierre bastarían para que un texto
    alineado a la izquierda pareciera justificado.
    """
    ruta = escribir_pdf(tmp_path / "mixto.pdf", [
        ["Una linea francamente larga que ocupa casi todo el ancho.",
         "Corta.", "Otra mediana de por medio.", "Fin."],
        ["Sola en su página."],
    ])

    with abrir(ruta) as documento:
        medidas = medir_texto(documento)

    assert medidas.proporcion_lineas_al_margen_derecho == pytest.approx(0.25, abs=0.01)


def test_un_pdf_sin_texto_no_inventa_medidas(pdf_escaneado: Path) -> None:
    """Un escaneado no tiene tipografía. Todo queda a None o vacío."""
    with abrir(pdf_escaneado) as documento:
        medidas = medir_texto(documento)

    assert medidas.familia_dominante == ""
    assert medidas.cuerpo_dominante is None
    assert medidas.ratio_interlineado is None
    assert medidas.margen_izquierdo_cm is None
    assert medidas.proporcion_lineas_al_margen_derecho is None


def test_la_portada_no_distorsiona_el_margen_izquierdo(tmp_path: Path) -> None:
    """Una portada centrada más una página de cuerpo a 72 pt de margen.

    Si el margen izquierdo se calculara con una mediana de un valor por
    página, la portada —centrada, y por tanto con un margen izquierdo mucho
    mayor que el del cuerpo— pesaría la mitad del resultado en un documento
    de solo dos páginas. Midiendo línea a línea sobre todo el documento, el
    cuerpo domina y el margen sale el real: 2,54 cm.
    """
    import pymupdf

    documento = pymupdf.open()

    portada = documento.new_page()
    texto_portada = "PROYECTO INTERMODULAR"
    ancho_portada = pymupdf.get_text_length(texto_portada, fontname="helv", fontsize=16.0)
    x_centrado = (portada.rect.width - ancho_portada) / 2
    portada.insert_text((x_centrado, 400.0), texto_portada, fontname="helv", fontsize=16.0)

    cuerpo = documento.new_page()
    cuerpo.insert_text((72.0, 100.0), "Primera linea del cuerpo.", fontname="helv", fontsize=11.0)
    cuerpo.insert_text((72.0, 119.0), "Segunda linea del cuerpo.", fontname="helv", fontsize=11.0)

    ruta = tmp_path / "portada-mas-cuerpo.pdf"
    documento.save(ruta)
    documento.close()

    with abrir(ruta) as abierto:
        medidas = medir_texto(abierto)

    assert medidas.margen_izquierdo_cm == pytest.approx(2.54, abs=0.05)


def test_saltos_de_parrafo_no_desplazan_el_interlineado(tmp_path: Path) -> None:
    """Un hueco de 60 pt entre bloques no debe arrastrar la mediana al alza.

    Dos bloques de dos líneas (salto interno de 19 pt) con un bloque de una
    sola línea de por medio, separados por huecos de 60 pt: dos saltos
    normales y dos saltos de párrafo, a partes iguales. Sin el filtro de
    `SALTO_MAXIMO_EN_CUERPOS` la mediana se iría hacia 60 pt; con él, solo
    cuentan los saltos normales y el ratio sigue en 19/11.
    """
    import pymupdf

    documento = pymupdf.open()
    pagina = documento.new_page()
    y = 100.0
    for salto in (19.0, 60.0, 60.0, 19.0):
        pagina.insert_text((72.0, y), "Linea del cuerpo del trabajo.", fontname="helv", fontsize=11.0)
        y += salto
    # La quinta y última línea, tras el último salto.
    pagina.insert_text((72.0, y), "Linea del cuerpo del trabajo.", fontname="helv", fontsize=11.0)

    ruta = tmp_path / "parrafos-con-huecos.pdf"
    documento.save(ruta)
    documento.close()

    with abrir(ruta) as abierto:
        medidas = medir_texto(abierto)

    assert medidas.ratio_interlineado == pytest.approx(19 / 11, abs=0.02)
