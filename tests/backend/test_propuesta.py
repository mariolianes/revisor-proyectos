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


# --- Fix round 6: no se pide decisión sobre lo que no ha cambiado ---


def test_un_valor_que_sigue_en_el_texto_llega_ya_revisado_sin_cambio(repo: Path):
    """Corregir una errata en la sección no obliga a redecidir lo demás.

    El cuerpo de letra sigue diciendo 11 en el texto nuevo: la prosa que lo
    respalda no lo ha tocado, así que no hay nada que decidir sobre él y
    llega al diálogo ya marcado. El docente puede desmarcarlo si no está de
    acuerdo, pero no tiene que tocarlo.
    """
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert cuerpo.revisado_sin_cambio
    assert "sigue apareciendo igual" in cuerpo.motivo

    # Lo que sí ha cambiado se sigue preguntando: se propone, no se marca.
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert not extension.revisado_sin_cambio
    assert extension.valor_propuesto == "25"


def test_un_valor_que_no_es_numero_pero_sigue_en_el_texto_tambien_llega_marcado(
    repo: Path,
):
    """La marca no es cosa de números: es que el valor siga estando.

    «Arial» no es un número y nunca se podrá proponer un sustituto para él,
    pero sigue escrito palabra por palabra en el texto nuevo. Preguntar por
    él era el grueso de las treinta y seis decisiones del §8.
    """
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    familia = next(p for p in propuestas if p.clave == "familia")
    assert familia.valor_actual == "Arial"
    assert familia.revisado_sin_cambio


def test_un_valor_que_no_aparece_literalmente_nunca_llega_marcado(repo: Path):
    """Que no se pueda comprobar no es que no haya cambiado.

    'activa_en' vale una lista que no está escrita literalmente en la prosa,
    ni antes ni después. Darlo por «no ha cambiado» sería declarar revisado
    algo que nadie ha mirado, que es justo lo que R1 impide. Se pregunta.
    """
    texto = "## 8. Dimensiones de evaluación\n\nTrece dimensiones, con peso variable.\n"
    propuestas = proponer(repo, "maestro#8-dimensiones", texto)
    activa = next(p for p in propuestas if p.clave == "activa_en")
    assert not activa.revisado_sin_cambio
    assert "no aparece literalmente" in activa.motivo


def test_un_valor_que_desaparece_del_texto_no_llega_marcado(repo: Path):
    """Si el valor ya no está, hay algo que decidir."""
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas.\n"
        "La tipografía será Times New Roman 12.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    for clave in ("familia", "cuerpo"):
        propuesta = next(p for p in propuestas if p.clave == clave)
        assert not propuesta.revisado_sin_cambio, clave


# --- Fix round 7: no basta con que el valor este; tiene que ser el mismo ---


def test_no_se_marca_apoyandose_en_otra_aparicion_del_mismo_valor(repo: Path):
    """El caso que demuestra por qué «sigue estando» no era suficiente.

    La prosa dice «mínimo de 11 páginas ... Arial 11» y el criterio 'cuerpo'
    vale 11. Se cambia SOLO la tipografía, a Arial 12. El 11 sigue en el
    texto -el de la extensión-, así que una comprobación que solo mire si el
    valor aparece daría 'cuerpo' por revisado sin cambio: la norma diría
    Arial 12, el criterio seguiría diciendo 11, y el ancla quedaría sellada
    sin que nadie lo hubiera mirado. Se pregunta.
    """
    documento = repo / "docs/maestro/01-documento-maestro.md"
    documento.write_text(
        documento.read_text(encoding="utf-8").replace(
            "mínimo de 20 páginas", "mínimo de 11 páginas"
        ),
        encoding="utf-8",
    )
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 11 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 12.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert cuerpo.valor_actual == "11"
    assert not cuerpo.revisado_sin_cambio


def test_no_se_marca_si_el_valor_reaparece_en_otra_frase(repo: Path):
    """El valor sigue en el texto, pero hablando de otra cosa.

    «Arial 11» pasa a «Arial 12. Los márgenes serán de 11 mm»: el 11 sigue
    escrito, pero ya no es el cuerpo de letra. Marcarlo sellaría un criterio
    obsoleto apoyado en un número de otra oración.
    """
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 20 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 12. Los márgenes serán de 11 mm.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert not cuerpo.revisado_sin_cambio
    # Y además se propone el sustituto correcto: el que está en su sitio.
    assert cuerpo.valor_propuesto == "12"


def test_repartir_el_parrafo_en_otras_lineas_no_mueve_el_valor(repo: Path):
    """Lo que se compara es la prosa, no su maquetado.

    Reescribir los saltos de línea de la sección no toca ningún valor, así
    que no puede obligar a redecidirlos todos.
    """
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 20 páginas,\n"
        "excluidas portada, índice y anexos. La tipografía\n"
        "será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    for clave in ("familia", "cuerpo", "minimo_paginas_contenido"):
        propuesta = next(p for p in propuestas if p.clave == clave)
        assert propuesta.revisado_sin_cambio, clave
