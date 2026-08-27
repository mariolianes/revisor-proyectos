import subprocess
from datetime import date
from pathlib import Path

from backend.servicios.repositorio import leer_seccion
from backend.servicios.transaccion import CambioDeValor, _asunto, guardar

# Copiadas de tests/backend/conftest.py: ni tests/ ni tests/backend/ tienen
# __init__.py -y no deben tenerlo, colisionaria con el paquete backend real-,
# asi que "from tests.backend.conftest import ..." no resuelve como modulo.
# Son ocho lineas y no las usa nadie mas.


def contenido_de(raiz: Path) -> dict[str, bytes]:
    """Instantánea byte a byte del árbol, para comprobar que un fallo no deja rastro."""
    instantanea = {}
    for ruta in sorted(raiz.rglob("*")):
        if ruta.is_file() and ".git" not in ruta.parts:
            instantanea[ruta.relative_to(raiz).as_posix()] = ruta.read_bytes()
    return instantanea


def commits_de(raiz: Path) -> list[str]:
    salida = subprocess.run(
        ["git", "log", "--format=%H"], cwd=raiz, capture_output=True, text=True, check=True
    )
    return salida.stdout.split()


TEXTO_NUEVO = (
    "## 6. Estándar académico\n\n"
    "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
    "índice y anexos. La tipografía será Arial 11.\n"
)


def _guardar_valido(repo: Path, **extra):
    seccion = leer_seccion(repo, "maestro#6-estandar-academico")
    argumentos = dict(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=TEXTO_NUEVO,
        cambios=[CambioDeValor(
            fichero="criteria/v2026-2027/formato.yaml",
            identificador="extension",
            clave="minimo_paginas_contenido",
            valor_nuevo="25",
        )],
        motivo="La programación didáctica sube el mínimo a 25 páginas.",
        fuente="Programación didáctica 2026-2027, apartado 4.2",
        hash_esperado=seccion.hash,
    )
    argumentos.update(extra)
    return guardar(**argumentos)


def test_el_caso_feliz_deja_prosa_yaml_cambio_y_commit(repo: Path):
    resultado = _guardar_valido(repo)
    assert resultado.exito, resultado.mensaje
    assert resultado.commit

    maestro = (repo / "docs/maestro/01-documento-maestro.md").read_text(encoding="utf-8")
    assert "mínimo de 25 páginas" in maestro

    formato = (repo / "criteria/v2026-2027/formato.yaml").read_text(encoding="utf-8")
    assert "minimo_paginas_contenido: 25" in formato

    cambios = list((repo / "docs/changes").glob("*-*.md"))
    assert len(cambios) == 1
    documento = cambios[0].read_text(encoding="utf-8")
    assert "La programación didáctica sube el mínimo" in documento
    assert "Programación didáctica 2026-2027" in documento


def test_el_documento_de_cambio_lleva_las_cinco_secciones(repo: Path):
    _guardar_valido(repo)
    documento = next((repo / "docs/changes").glob("*-*.md")).read_text(encoding="utf-8")
    from tools.gobernanza.cambios import SECCIONES_OBLIGATORIAS
    for seccion in SECCIONES_OBLIGATORIAS:
        assert f"## {seccion}" in documento


def test_el_registro_de_sincronia_queda_sellado(repo: Path):
    _guardar_valido(repo)
    from tools.verificar_gobernanza import ejecutar
    assert [i for i in ejecutar(repo, [], False) if i.regla == "R2"] == []


def test_sin_motivo_no_se_guarda_nada(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, motivo="   ")
    assert not resultado.exito
    assert "motivo" in resultado.mensaje
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_sin_fuente_no_se_guarda_nada(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, fuente="")
    assert not resultado.exito
    assert "fuente" in resultado.mensaje
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_si_la_seccion_cambio_por_fuera_se_aborta(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, hash_esperado="0000000000000000")
    assert not resultado.exito
    assert "ha cambiado" in resultado.mensaje
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_si_el_arbol_esta_sucio_se_aborta(repo: Path):
    (repo / "suelto.txt").write_text("algo sin comitear\n", encoding="utf-8")
    commits = commits_de(repo)
    resultado = _guardar_valido(repo)
    assert not resultado.exito
    assert "sin comitear" in resultado.mensaje
    assert commits_de(repo) == commits


def test_si_una_regla_salta_se_revierte_todo(repo: Path):
    """Un cambio que deja un criterio apuntando a un ancla inexistente.

    NOTA: el brief proponía disparar esto sustituyendo el cuerpo de la
    sección sin tocar su marca de ancla. Se comprobó -en rojo, ejecutando el
    test- que ese escenario nunca dispara ninguna de las seis reglas: la
    marca de ancla la conserva siempre '_sustituir_seccion', y
    'escribir_sincronia' se llama justo antes de verificar, así que R2 nunca
    puede fallar contra su propio sello recién escrito. Se sustituye por un
    escenario que sí viola R1 de verdad: un 'cambio' que deja la 'fuente' de
    un criterio apuntando a un ancla que no existe. El resto del test -que
    se revierte todo, byte a byte y sin commit- es idéntico en espíritu.
    """
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = guardar(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=TEXTO_NUEVO,
        cambios=[CambioDeValor(
            fichero="criteria/v2026-2027/formato.yaml",
            identificador="extension",
            clave="fuente",
            valor_nuevo="maestro#no-existe",
        )],
        motivo="Prueba de reversión",
        fuente="Prueba",
        hash_esperado=leer_seccion(repo, "maestro#6-estandar-academico").hash,
    )
    assert not resultado.exito
    assert resultado.infracciones
    assert any(i["regla"] == "R1" for i in resultado.infracciones)
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_un_ancla_inexistente_se_rechaza(repo: Path):
    antes = contenido_de(repo)
    resultado = guardar(
        raiz=repo, ancla="maestro#no-existe", texto_nuevo="x",
        cambios=[], motivo="m", fuente="f", hash_esperado="x",
    )
    assert not resultado.exito
    assert contenido_de(repo) == antes


def test_un_cambio_sobre_un_fichero_fuera_de_criteria_se_rechaza(repo: Path):
    antes = contenido_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="../fuera.yaml", identificador="x", clave="y", valor_nuevo="1",
    )])
    assert not resultado.exito
    assert "no es un fichero de criterios" in resultado.mensaje
    assert contenido_de(repo) == antes


# --- Fix round 1: seis agujeros de atomicidad encontrados en revisión -----


def test_un_cambio_no_toca_otro_bloque_del_mismo_fichero(repo: Path):
    """El bloque 'extension' no se toca al cambiar 'fuente' en 'tipografia'.

    'criteria/v2026-2027/formato.yaml' tiene la clave 'fuente' repetida en
    dos bloques. Antes de este arreglo, la sustitución no acotaba al bloque
    del 'identificador' y se empalmaba contra el fichero entero con
    'count=1': un cambio dirigido a 'tipografia' reescribía en silencio la
    'fuente' de 'extension', el primer bloque del fichero.
    """
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/formato.yaml",
        identificador="tipografia",
        clave="fuente",
        valor_nuevo="maestro#8-dimensiones",
    )])
    assert resultado.exito, resultado.mensaje

    formato = (repo / "criteria/v2026-2027/formato.yaml").read_text(encoding="utf-8")
    assert "extension:\n  minimo_paginas_contenido: 20\n  fuente: maestro#6-estandar-academico" in formato
    assert "tipografia:\n  familia: Arial\n  cuerpo: 11\n  fuente: maestro#8-dimensiones" in formato


def test_una_clave_inexistente_no_se_guarda(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/formato.yaml",
        identificador="extension",
        clave="clave_que_no_existe",
        valor_nuevo="25",
    )])
    assert not resultado.exito
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_un_identificador_inexistente_no_se_guarda(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/formato.yaml",
        identificador="bloque_que_no_existe",
        clave="fuente",
        valor_nuevo="maestro#8-dimensiones",
    )])
    assert not resultado.exito
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_un_valor_con_salto_de_linea_no_deja_el_arbol_a_medias(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/formato.yaml",
        identificador="extension",
        clave="minimo_paginas_contenido",
        valor_nuevo="25\nfuente: maestro#no-existe",
    )])
    assert not resultado.exito
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_un_valor_con_metacaracter_no_deja_el_arbol_a_medias(repo: Path):
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/formato.yaml",
        identificador="extension",
        clave="minimo_paginas_contenido",
        valor_nuevo="25: inyectado",
    )])
    assert not resultado.exito
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_un_documento_de_cambio_preexistente_sobrevive_a_un_fallo(repo: Path):
    """Dos guardados el mismo día con el mismo asunto no se pisan.

    El nombre del documento de cambio es determinista: fecha más primeras
    palabras del motivo. Si ya existe uno con ese nombre -de un guardado
    anterior, ya comiteado- y el guardado actual falla, 'revertir()' no debe
    borrarlo: antes de este arreglo lo borraba siempre, perdiendo un
    registro de gobernanza ya comiteado.
    """
    motivo = "Prueba de reversión"
    nombre_cambio = f"{date.today().isoformat()}-{_asunto(motivo)}.md"
    ruta_cambio = repo / "docs" / "changes" / nombre_cambio
    contenido_previo = "# Documento de cambio ya existente\n\nNo debe perderse.\n"
    ruta_cambio.write_text(contenido_previo, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "cambio previo"], cwd=repo, check=True)

    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = guardar(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=TEXTO_NUEVO,
        cambios=[CambioDeValor(
            fichero="criteria/v2026-2027/formato.yaml",
            identificador="extension",
            clave="fuente",
            valor_nuevo="maestro#no-existe",
        )],
        motivo=motivo,
        fuente="Prueba",
        hash_esperado=leer_seccion(repo, "maestro#6-estandar-academico").hash,
    )
    assert not resultado.exito
    assert ruta_cambio.read_text(encoding="utf-8") == contenido_previo
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_si_el_registro_de_sincronia_no_existia_se_borra_al_revertir(repo: Path):
    """La rama de revertir() cuando el sello de R2 no existía antes."""
    from tools.gobernanza.sincronia import FICHERO_SINCRONIA
    ruta_sincronia = repo / FICHERO_SINCRONIA
    ruta_sincronia.unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "sin registro de sincronia"], cwd=repo, check=True)

    antes, commits = contenido_de(repo), commits_de(repo)
    assert "criteria/.sincronia.json" not in antes

    resultado = guardar(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=TEXTO_NUEVO,
        cambios=[CambioDeValor(
            fichero="criteria/v2026-2027/formato.yaml",
            identificador="extension",
            clave="fuente",
            valor_nuevo="maestro#no-existe",
        )],
        motivo="Prueba sin registro previo",
        fuente="Prueba",
        hash_esperado=leer_seccion(repo, "maestro#6-estandar-academico").hash,
    )
    assert not resultado.exito
    assert not ruta_sincronia.is_file()
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


# --- Fix round 2: el '\s*' del regex cruzaba el salto de línea -----------


def test_un_valor_con_lista_debajo_no_se_guarda(repo: Path):
    """Una clave cuyo valor vive en las líneas siguientes -una lista de
    bloque, que es como YAML escribe casi cualquier lista- no se puede
    sustituir con este mecanismo: se rechaza entero, sin tocar el fichero.

    Antes de esta guarda, '^(\\s*{clave}:\\s*).*$' con re.M dejaba que el
    '\\s*' de después de los dos puntos cruzara el salto de línea: sobre
        excluye:
          - portada
          - indice
    el grupo capturado se tragaba el salto y la indentación, y '.*$' se
    comía '- portada' entero. El resultado era 'excluye: <nuevo> - indice',
    que YAML interpreta como una cadena suelta -una lista de dos elementos
    convertida en frase-, y 'guardar' respondía 'exito=True'.
    """
    extra = repo / "criteria" / "v2026-2027" / "extra.yaml"
    contenido_original = (
        "extra:\n"
        "  fuente: maestro#6-estandar-academico\n"
        "  excluye:\n"
        "    - portada\n"
        "    - indice\n"
    )
    extra.write_text(contenido_original, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "criterio con lista de bloque"],
                    cwd=repo, check=True)

    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/extra.yaml",
        identificador="extra",
        clave="excluye",
        valor_nuevo="nada",
    )])
    assert not resultado.exito
    assert "varias líneas" in resultado.mensaje
    assert extra.read_text(encoding="utf-8") == contenido_original
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


# --- Fix round 3: comentario sin espacio delante, y lista en una línea ---


def test_una_clave_con_solo_un_comentario_no_se_guarda(repo: Path):
    """'clave:  # comentario' no tiene valor en su línea, aunque el
    comentario en sí sea un texto no vacío.

    Antes de esta guarda, '_valor_de_clave_en_linea' partía por " #" -con
    espacio delante-, pero el hueco tras los dos puntos ya se había comido
    ese espacio: el propio texto del comentario se colaba como si fuera el
    valor, y se aceptaba el cambio, corrompiendo la lista de debajo exactamente
    como en 'test_un_valor_con_lista_debajo_no_se_guarda'.
    """
    extra = repo / "criteria" / "v2026-2027" / "extra.yaml"
    contenido_original = (
        "extra:\n"
        "  fuente: maestro#6-estandar-academico\n"
        "  excluye:  # lo que no cuenta para el minimo\n"
        "    - portada\n"
        "    - indice\n"
        "    - anexos\n"
    )
    extra.write_text(contenido_original, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "criterio con lista comentada"],
                    cwd=repo, check=True)

    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/extra.yaml",
        identificador="extra",
        clave="excluye",
        valor_nuevo="nada",
    )])
    assert not resultado.exito
    assert "varias líneas" in resultado.mensaje
    assert extra.read_text(encoding="utf-8") == contenido_original
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_una_lista_en_una_sola_linea_no_se_guarda(repo: Path):
    """'excluye: [portada, indice, anexos]' es una lista en estilo de flujo:
    sustituirla la convertiría en un escalar sin que nadie lo pidiera.
    """
    extra = repo / "criteria" / "v2026-2027" / "extra.yaml"
    contenido_original = (
        "extra:\n"
        "  fuente: maestro#6-estandar-academico\n"
        "  excluye: [portada, indice, anexos]\n"
    )
    extra.write_text(contenido_original, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "criterio con lista en linea"],
                    cwd=repo, check=True)

    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/extra.yaml",
        identificador="extra",
        clave="excluye",
        valor_nuevo="nada",
    )])
    assert not resultado.exito
    assert "una sola línea" in resultado.mensaje
    assert extra.read_text(encoding="utf-8") == contenido_original
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits
