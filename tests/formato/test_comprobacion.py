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


# --- Revisión: hallazgos sobre el brief original --------------------------
#
# Los catorce tests de arriba son los del brief, intactos. Lo que sigue
# cubre los cinco defectos que encontró la revisión de esa primera versión.


def test_alineacion_izquierda_no_sale_no_cumple(
    criterios_alterados, pdf_alineado_izquierda: Path
) -> None:
    """Crítico: el documento cumple justo lo que pide el criterio.

    Con `valor: alineado_izquierda` y un documento alineado a la izquierda
    de verdad, la proporción de líneas al margen derecho es baja -es lo
    esperado-. Juzgar eso como si el criterio pidiera "justificado" daría
    NO_CUMPLE a un documento que está haciendo exactamente lo que se le
    pide, y ese veredicto lo lee el alumno.
    """
    raiz = criterios_alterados("valor: justificado", "valor: alineado_izquierda")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_alineado_izquierda))

    comprobacion = _de(resultado, "alineacion")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert comprobacion.veredicto != NO_CUMPLE


def test_alineacion_justificado_conserva_las_tres_bandas(
    criterios_de_formato: Path,
    pdf_justificado: Path,
    pdf_alineado_izquierda: Path,
    pdf_con_indice: Path,
) -> None:
    """Con `valor: justificado` -el único que se juzga- nada cambia."""
    alta = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_justificado))
    baja = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_alineado_izquierda))
    media = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(alta, "alineacion").veredicto == CUMPLE
    assert _de(baja, "alineacion").veredicto == NO_CUMPLE
    assert _de(media, "alineacion").veredicto == NO_VERIFICABLE


def test_tipografia_sin_cuerpo_no_tumba_los_demas(
    criterios_alterados, pdf_con_indice: Path
) -> None:
    """Crítico: un `KeyError` en un bloque no debe tirar abajo el resto."""
    raiz = criterios_alterados("  cuerpo: 11\n", "")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "tipografia")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "tipografia" in comprobacion.nota
    assert "KeyError" in comprobacion.nota
    assert _de(resultado, "extension").veredicto == CUMPLE


def test_cuerpo_no_numerico_no_tumba_los_demas(
    criterios_alterados, pdf_con_indice: Path
) -> None:
    """Crítico: `cuerpo: once` no convierte a número y no debe tumbar nada."""
    raiz = criterios_alterados("cuerpo: 11", "cuerpo: once")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "tipografia")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "ValueError" in comprobacion.nota
    assert _de(resultado, "extension").veredicto == CUMPLE


def test_cuerpo_con_coma_decimal_no_tumba_los_demas(
    criterios_alterados, pdf_con_indice: Path
) -> None:
    """Crítico: la coma decimal es la errata más probable de las cuatro.

    `11,5` es la notación española natural para un cuerpo de letra; en YAML
    no es un número, es una cadena, y `float()` la rechaza.
    """
    raiz = criterios_alterados("cuerpo: 11", "cuerpo: 11,5")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "tipografia")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "ValueError" in comprobacion.nota
    assert _de(resultado, "extension").veredicto == CUMPLE


def test_yaml_mal_indentado_no_revienta(
    criterios_alterados, pdf_con_indice: Path
) -> None:
    """Crítico: si el fichero entero no se puede interpretar, no hay YAML
    del que sacar "los demás criterios" -la comprobación entera se declara
    NO_VERIFICABLE en un único resultado en vez de lanzar la excepción."""
    raiz = criterios_alterados("  familia: Helvetica", "\tfamilia: Helvetica")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    assert len(resultado) == 1
    comprobacion = resultado[0]
    assert comprobacion.criterio == "fichero_de_criterios"
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "YAML" in comprobacion.nota


def test_criterio_desconocido_no_desaparece_en_silencio(
    criterios_alterados, pdf_con_indice: Path
) -> None:
    """Importante: una errata en el nombre del criterio, o uno nuevo que
    todavía no se sabe comprobar, debe quedar a la vista y no en silencio."""
    raiz = criterios_alterados("tipografia:", "tipogtafia:")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "tipogtafia")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "tipogtafia" in comprobacion.nota
    # el resto del fichero, que sí se conoce, sigue comprobándose
    assert _de(resultado, "extension").veredicto == CUMPLE


def test_margenes_senalan_el_lado_que_falla(
    criterios_de_formato: Path, pdf_con_indice: Path
) -> None:
    """Importante: `medido` debe decir cuál de los cuatro lados incumple,
    no dejar que el docente reste cada uno contra la tolerancia a mano."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "margenes")
    assert comprobacion.veredicto == NO_CUMPLE

    partes = {parte.split()[0]: parte for parte in comprobacion.medido.split(", ")}
    # el derecho se sale del criterio real (2,5 cm ± 0,5) con líneas cortas
    assert "incumple" in partes["derecho"]
    # el izquierdo, en cambio, cae dentro de la tolerancia
    assert "incumple" not in partes["izquierdo"]


def test_fuente_vacia_no_pasa_el_filtro(
    criterios_alterados, pdf_con_indice: Path
) -> None:
    """Menor: una `fuente` presente pero vacía debe tratarse como ausente."""
    raiz = criterios_alterados(
        "admite_escaneado: false\n  fuente: indice#6-formato-y-control",
        'admite_escaneado: false\n  fuente: ""',
    )

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    assert all(comprobacion.criterio != "archivo" for comprobacion in resultado)
    # el resto del fichero no se ve afectado
    assert _de(resultado, "extension").veredicto == CUMPLE
