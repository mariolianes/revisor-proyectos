"""Lo medido contra lo exigido."""

from pathlib import Path

import pytest

from backend.extraccion import medir
from backend.formato.comprobacion import (
    CUMPLE,
    NO_CUMPLE,
    NO_VERIFICABLE,
    comprobar,
)

# Los criterios y los PDF vienen de tests/conftest.py: `criterios_de_formato`
# es una raíz con criteria/v2026-2027/formato.yaml dentro.


def _de(comprobaciones: list, criterio: str):
    return next(c for c in comprobaciones if c.criterio == criterio)



def test_extension_suficiente_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """Cuatro páginas de contenido contra un mínimo de cuatro."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "extension").veredicto == CUMPLE


def test_extension_insuficiente_no_cumple(criterios_alterados, pdf_con_indice: Path) -> None:
    raiz = criterios_alterados(
        "minimo_paginas_contenido: 4", "minimo_paginas_contenido: 30"
    )

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "extension")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "30" in comprobacion.esperado
    assert "4" in comprobacion.medido


def test_sin_indice_la_extension_no_es_verificable(criterios_de_formato: Path, pdf_simple: Path) -> None:
    """Sin saber dónde empieza el contenido no se cuenta. No se estima."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_simple))

    comprobacion = _de(resultado, "extension")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "índice" in comprobacion.nota


def test_tipografia_correcta_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "tipografia").veredicto == CUMPLE


def test_familia_distinta_no_cumple(criterios_alterados, pdf_con_indice: Path) -> None:
    raiz = criterios_alterados("familia: Helvetica", "familia: Arial")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "tipografia")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "Helvetica" in comprobacion.medido


def test_el_interlineado_nunca_se_juzga(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """El punto importante: el ratio se enseña, no se traduce."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "interlineado")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "1.73" in comprobacion.medido or "1,73" in comprobacion.medido
    assert "equivalencia" in comprobacion.nota


def test_las_imagenes_esperan_a_la_segunda_parte(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "imagenes")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "leer" in comprobacion.nota


def test_escaneado_no_cumple(criterios_de_formato: Path, pdf_escaneado: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_escaneado))

    assert _de(resultado, "archivo").veredicto == NO_CUMPLE


def test_pagina_en_blanco_no_cumple(criterios_de_formato: Path, pdf_con_pagina_en_blanco: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_pagina_en_blanco))

    comprobacion = _de(resultado, "paginas_en_blanco")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "2" in comprobacion.medido


def test_sin_paginas_en_blanco_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "paginas_en_blanco").veredicto == CUMPLE


def test_indice_descuadrado_no_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """El fixture declara «3. Desarrollo» en la 5 y está en la 6."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "indice_paginado")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "Desarrollo" in comprobacion.medido


def test_alineacion_ambigua_no_es_verificable(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """Entre las dos bandas no se decide: se enseña la proporción."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "alineacion").veredicto in (NO_CUMPLE, NO_VERIFICABLE)


def test_cada_comprobacion_lleva_su_fuente(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """R1 en la salida: ningún veredicto sin la sección que lo respalda."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert resultado
    assert all("#" in comprobacion.fuente for comprobacion in resultado)


def test_sin_fichero_de_criterios_no_hay_comprobaciones(tmp_path: Path, pdf_simple: Path) -> None:
    assert comprobar(tmp_path, "v2026-2027", medir(pdf_simple)) == []
