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


def test_no_fabrica_un_valor_a_partir_de_la_numeracion_de_un_subapartado(repo: Path):
    """Añadir un ### 6.6 no debe ofrecerse jamás como el mínimo de páginas."""
    texto = (
        "## 6. Estándar académico\n\n"
        "### 6.6 Anexos digitales\n\n"
        "Los anexos digitales se entregarán en formato PDF.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None


def test_no_fabrica_un_valor_a_partir_de_un_numero_de_otro_asunto(repo: Path):
    """Un margen nuevo (2,5 -> 3 cm) no debe ofrecerse como el mínimo de páginas."""
    texto = (
        "## 6. Estándar académico\n\n"
        "La extensión se ajustará a la programación. Los márgenes serán de 3 cm.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None


def test_no_propone_nada_si_el_valor_queda_dos_veces_en_el_texto_nuevo(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 20 páginas, o 20 si se trata\n"
        "de un proyecto breve. La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None
    assert "ha desaparecido" not in extension.motivo


def test_localiza_el_valor_aunque_termine_en_punto_de_fin_de_frase(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 20 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 12.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert cuerpo.valor_actual == "11"
    assert cuerpo.valor_propuesto == "12"


def test_dos_criterios_numericos_cambian_a_la_vez_cada_uno_su_propuesta(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 12.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert extension.valor_propuesto == "25"
    assert cuerpo.valor_propuesto == "12"
