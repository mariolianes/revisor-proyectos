from pathlib import Path

from backend.servicios.propuesta import proponer


def test_propone_el_valor_nuevo_cuando_el_numero_cambia_en_el_texto(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_actual == "20"
    assert extension.valor_propuesto == "25"


def test_no_propone_nada_para_un_valor_que_sigue_igual(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert cuerpo.valor_propuesto is None
    assert "sigue apareciendo" in cuerpo.motivo


def test_marca_para_revisar_a_mano_un_valor_que_no_aparece_en_el_texto(repo: Path):
    texto = "## 8. Dimensiones de evaluación\n\nTrece dimensiones, con peso variable.\n"
    propuestas = proponer(repo, "maestro#8-dimensiones", texto)
    activa = next(p for p in propuestas if p.clave == "activa_en")
    assert activa.valor_propuesto is None
    assert "no aparece literalmente" in activa.motivo


def test_no_propone_cuando_el_valor_desaparece_sin_sustituto_claro(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "La extensión se fijará según la programación didáctica.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None
    assert "ha desaparecido" in extension.motivo


def test_no_propone_cuando_hay_mas_de_un_candidato(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "Un mínimo de 25 páginas, o de 30 si el proyecto es de investigación.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None
    assert "más de un" in extension.motivo


def test_una_seccion_sin_criterios_no_produce_propuestas(repo: Path):
    assert proponer(repo, "maestro#19-privacidad", "texto nuevo") == []
