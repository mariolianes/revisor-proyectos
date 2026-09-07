"""La portada como evidencia auxiliar (`decisiones#4-portada`).

Todos los nombres son inventados. Los PDF se construyen aquí mismo: ninguno
procede de un trabajo real.
"""

from pathlib import Path

import pymupdf
import pytest

from backend.extraccion.lectura import PdfIlegible
from backend.identificacion.determinista import CandidatoLocal, identificar
from backend.identificacion.portada import (
    PAGINAS_DE_PORTADA,
    aparece_en,
    candidatos_nombrados_en,
    nombre_confirmado_por_la_portada,
    texto_de_la_portada,
)

ANA = CandidatoLocal(student_id="ALU-260001", nombre="Ana Ficticia Inventada")
BEA = CandidatoLocal(student_id="ALU-260002", nombre="Beatriz Supuesta Imaginaria")


def _pdf(tmp_path: Path, *paginas: str) -> Path:
    documento = pymupdf.open()
    for texto in paginas:
        pagina = documento.new_page()
        pagina.insert_text((72, 100), texto, fontsize=12)
    ruta = tmp_path / "trabajo.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


# --- Encontrar un nombre conocido ------------------------------------------


def test_el_nombre_aparece_tal_cual() -> None:
    assert aparece_en("Ana Ficticia Inventada", "Autora: Ana Ficticia Inventada")


def test_el_orden_apellidos_nombre_encuentra_igual() -> None:
    """El listado puede traer «Apellidos, Nombre» y la portada lo contrario.
    Él pide expresamente ignorar ese orden."""
    assert aparece_en("Ficticia Inventada, Ana", "Ana Ficticia Inventada")


def test_las_tildes_y_las_mayusculas_no_impiden_encontrarlo() -> None:
    assert aparece_en("Mario Jesús Rodríguez Peña", "MARIO JESUS RODRIGUEZ PENA")


def test_las_palabras_desperdigadas_no_cuentan() -> None:
    """Lo que impide que esto se convierta en una heurística. Encontrar las
    tres palabras repartidas por la página no dice que ese sea el autor."""
    texto = (
        "Ana es un nombre comun. Este trabajo es una obra ficticia. "
        "La empresa fue inventada para el ejemplo."
    )

    assert not aparece_en("Ana Ficticia Inventada", texto)


def test_un_nombre_que_no_esta_no_aparece() -> None:
    assert not aparece_en("Ana Ficticia Inventada", "Autora: Beatriz Supuesta")


def test_un_nombre_vacio_nunca_aparece() -> None:
    assert not aparece_en("", "cualquier texto")


# --- Cuál de los candidatos confirma la portada ----------------------------


def test_la_portada_confirma_a_un_candidato() -> None:
    texto = "Proyecto Intermodular\nAutora: Ana Ficticia Inventada\nCurso 2026-2027"

    assert nombre_confirmado_por_la_portada(texto, [ANA, BEA]) == ANA.nombre


def test_una_portada_con_dos_nombres_no_confirma_a_ninguno() -> None:
    """Un trabajo en grupo, o una plantilla reutilizada sin borrar el nombre
    anterior. Elegir uno de los dos sería adivinar."""
    texto = "Ana Ficticia Inventada y Beatriz Supuesta Imaginaria"

    assert candidatos_nombrados_en(texto, [ANA, BEA]) == [ANA, BEA]
    assert nombre_confirmado_por_la_portada(texto, [ANA, BEA]) is None


def test_una_portada_sin_ningun_nombre_conocido_no_confirma() -> None:
    assert nombre_confirmado_por_la_portada("Proyecto Intermodular", [ANA, BEA]) is None


# --- Leer el PDF -----------------------------------------------------------


def test_se_lee_el_texto_de_las_primeras_paginas(tmp_path: Path) -> None:
    ruta = _pdf(tmp_path, "Ana Ficticia Inventada", "Texto de la segunda hoja")

    texto = texto_de_la_portada(ruta)

    assert "Ana Ficticia Inventada" in texto
    assert "Texto de la segunda hoja" in texto


def test_no_se_lee_mas_alla_de_las_paginas_de_portada(tmp_path: Path) -> None:
    """Encontrar el nombre en el cuerpo del trabajo dice poco sobre quién lo
    entrega, y leer el documento entero para buscar nombres es justo lo que
    la capa de privacidad no quiere que se haga por costumbre."""
    paginas = ["Portada"] + [f"Hoja numero {i}" for i in range(1, 6)]
    paginas[PAGINAS_DE_PORTADA] = "Ana Ficticia Inventada"
    ruta = _pdf(tmp_path, *paginas)

    texto = texto_de_la_portada(ruta)

    assert "Ana Ficticia Inventada" not in texto


def test_un_pdf_ilegible_lo_dice_en_castellano(tmp_path: Path) -> None:
    roto = tmp_path / "roto.pdf"
    roto.write_bytes(b"esto no es un pdf")

    with pytest.raises(PdfIlegible):
        texto_de_la_portada(roto)


def test_un_pdf_con_menos_paginas_que_el_limite_se_lee_entero(tmp_path: Path) -> None:
    ruta = _pdf(tmp_path, "Sola, con Ana Ficticia Inventada")

    assert "Ana Ficticia Inventada" in texto_de_la_portada(ruta)


# --- Enganchada a la escalera de decisión ----------------------------------


def test_la_portada_completa_la_prioridad_tres(tmp_path: Path) -> None:
    """El circuito entero: nombre de archivo incompleto, candidato único, y
    la portada lo confirma."""
    ruta = _pdf(tmp_path, "Autora: Ana Ficticia Inventada")
    texto = texto_de_la_portada(ruta)

    resultado = identificar(
        candidatos=[ANA, BEA],
        nombre_del_archivo="Ana Ficticia",
        nombre_de_portada=nombre_confirmado_por_la_portada(texto, [ANA, BEA]),
    )

    assert resultado.student_id == "ALU-260001"


def test_una_portada_que_nombra_a_otro_detiene_la_asignacion(tmp_path: Path) -> None:
    """La prioridad 5 del docente, con un PDF de verdad por medio."""
    ruta = _pdf(tmp_path, "Autora: Beatriz Supuesta Imaginaria")
    texto = texto_de_la_portada(ruta)
    con_plataforma = ANA.model_copy(update={"platform_id": "cesur-1"})

    resultado = identificar(
        candidatos=[con_plataforma, BEA],
        platform_id="cesur-1",
        nombre_de_portada=nombre_confirmado_por_la_portada(
            texto, [con_plataforma, BEA]
        ),
    )

    assert resultado.student_id is None
    assert resultado.a_incidencias
