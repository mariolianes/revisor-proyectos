import subprocess
from datetime import date
from pathlib import Path

from backend.servicios.dependencias import criterios_de
from backend.servicios.repositorio import leer_seccion
from backend.servicios.transaccion import CambioDeValor, _asunto, guardar

# Copiadas de tests/backend/conftest.py: ni tests/ ni tests/backend/ tienen
# __init__.py -y no deben tenerlo, colisionaria con el paquete backend real-,
# así que "from tests.backend.conftest import ..." no resuelve como modulo.
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


def _revisiones_del_resto(repo: Path, ancla: str,
                          cambios: list[CambioDeValor]) -> list[CambioDeValor]:
    """Declara «revisado, no cambia» los criterios que el test no menciona.

    Es lo que hace el docente en el diálogo antes de guardar: decidir sobre
    cada criterio que deriva de la sección, uno por uno. Sin esas
    declaraciones el ancla no se sella, R2 protesta y el guardado se
    revierte entero -que es justo lo que comprueba
    'test_un_criterio_sin_revisar_hace_saltar_r2_y_no_guarda_nada'-.
    """
    decididos = {(c.fichero, c.identificador, c.clave) for c in cambios}
    return [
        CambioDeValor(
            fichero=criterio.fichero,
            identificador=criterio.identificador,
            clave=clave,
            valor_nuevo=None,
        )
        for criterio in criterios_de(repo, ancla)
        for clave in criterio.valores
        if (criterio.fichero, criterio.identificador, clave) not in decididos
    ]


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
    argumentos["cambios"] = argumentos["cambios"] + _revisiones_del_resto(
        repo, argumentos["ancla"], argumentos["cambios"]
    )
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
    resultado = _guardar_valido(repo)
    # Sin esta comprobación el test pasaría también cuando el guardado se
    # revierte: sobre un árbol restaurado R2 tampoco tiene nada que decir.
    assert resultado.exito, resultado.mensaje
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
    test- que ese escenario no disparaba ninguna de las seis reglas: la
    marca de ancla la conserva siempre '_sustituir_seccion', y el sello de
    R2 se regeneraba entero justo antes de verificar, así que R2 no podía
    fallar contra su propio sello recién escrito. Ese agujero está cerrado
    -ahora solo se sella lo revisado, y lo comprueba
    'test_un_criterio_sin_revisar_hace_saltar_r2_y_no_guarda_nada'-, pero
    este test se queda como está: cubre otro camino, el de un 'cambio' que
    deja la 'fuente' de un criterio apuntando a un ancla que no existe y
    hace saltar R1. El resto -que se revierte todo, byte a byte y sin
    commit- es idéntico en espíritu.
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
        "  excluye:  # lo que no cuenta para el mínimo\n"
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


# --- Fix round 4: la sustitución pasa a hacerse sobre el árbol del YAML --


def test_una_clave_repetida_mas_adentro_no_se_confunde_con_la_del_criterio(repo: Path):
    """Una clave del mismo nombre anidada dentro del bloque no es la del criterio.

    Es el quinto agujero de la misma familia, y el que cerró el cambio de
    mecanismo. Con una expresión regular acotada al bloque, pedir cambiar
    'extension_extra.fuente' reescribía la 'fuente' de 'notas' -anidada más
    adentro, pero antes en el texto-, dejaba intacta la de verdad y respondía
    'exito=True'. Un patrón de línea sabe encontrar 'fuente:' en un texto,
    pero no distingue una clave propia del criterio de otra con el mismo
    nombre en su subárbol: eso es estructura, no texto.
    """
    extra = repo / "criteria" / "v2026-2027" / "extra.yaml"
    contenido_original = (
        "extension_extra:\n"
        "  notas:\n"
        "    fuente: nota interna del docente, sin valor normativo\n"
        "  fuente: maestro#6-estandar-academico\n"
    )
    extra.write_text(contenido_original, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "criterio con clave repetida dentro"],
                   cwd=repo, check=True)

    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/extra.yaml",
        identificador="extension_extra",
        clave="fuente",
        valor_nuevo="maestro#8-dimensiones",
    )])
    assert resultado.exito, resultado.mensaje

    texto = extra.read_text(encoding="utf-8")
    # La anidada, intacta.
    assert "    fuente: nota interna del docente, sin valor normativo\n" in texto
    # La del criterio, cambiada.
    assert "  fuente: maestro#8-dimensiones\n" in texto
    # Y nada más ha cambiado en el fichero.
    assert texto == contenido_original.replace(
        "  fuente: maestro#6-estandar-academico",
        "  fuente: maestro#8-dimensiones",
    )


def test_los_comentarios_del_fichero_de_criterios_sobreviven_al_guardado(repo: Path):
    """Los comentarios de 'criteria/' son normativos y no se pueden perder.

    Las cabeceras del tipo «NO EDITAR sin cambiar antes la prosa» y las notas
    que explican de dónde sale cada valor forman parte de la gobernanza:
    guardar un cambio no puede borrarlas. Se comprueba además que el fichero
    queda igual salvo el valor pedido, líneas en blanco y sangría incluidas.
    """
    extra = repo / "criteria" / "v2026-2027" / "extra.yaml"
    contenido_original = (
        "# Requisitos extra de formato. Derivado de docs/maestro/.\n"
        "# NO EDITAR sin cambiar antes la prosa. Ver GOVERNANCE.md.\n"
        "\n"
        "extension_extra:\n"
        "  # El mínimo sale del apartado 4.2 de la programacion didactica.\n"
        "  minimo_paginas_contenido: 20  # sin portada, indice ni anexos\n"
        "\n"
        "  fuente: maestro#6-estandar-academico\n"
    )
    extra.write_text(contenido_original, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "criterio con comentarios normativos"],
                   cwd=repo, check=True)

    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/extra.yaml",
        identificador="extension_extra",
        clave="minimo_paginas_contenido",
        valor_nuevo="25",
    )])
    assert resultado.exito, resultado.mensaje

    texto = extra.read_text(encoding="utf-8")
    for comentario in (
        "# Requisitos extra de formato. Derivado de docs/maestro/.",
        "# NO EDITAR sin cambiar antes la prosa. Ver GOVERNANCE.md.",
        "  # El mínimo sale del apartado 4.2 de la programacion didactica.",
        "# sin portada, indice ni anexos",
    ):
        assert comentario in texto, f"se ha perdido el comentario: {comentario}"

    assert texto == contenido_original.replace(
        "minimo_paginas_contenido: 20",
        "minimo_paginas_contenido: 25",
    )


# --- Fix round 5: el sello ya no se genera del arbol que va a verificar --


def test_un_criterio_sin_revisar_hace_saltar_r2_y_no_guarda_nada(repo: Path):
    """El caso que este arreglo existe para impedir que vuelva.

    Se reescribe la sección entera -de «20 páginas / Arial 11» a «35 páginas
    / Times New Roman 12»- y se guarda sin decidir nada sobre los criterios
    que derivan de ella. Antes, el guardado sellaba el registro de R2 a
    partir de esa misma prosa y luego «verificaba» contra ese sello: salía
    'exito=True', el commit se hacía, y el verificador daba el repositorio
    por conforme para siempre, con la norma diciendo una cosa y los
    criterios otra.

    Ahora el ancla no se sella -no hay nada revisado que sellar-, R2 ve la
    prosa nueva contra el hash viejo, protesta, y el guardado se revierte
    entero.
    """
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = guardar(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=(
            "## 6. Estándar académico\n\n"
            "El contenido principal tendrá un mínimo de 35 páginas, excluidas\n"
            "portada, índice y anexos. La tipografía será Times New Roman 12.\n"
        ),
        cambios=[],
        motivo="Prueba: cambiar la prosa sin revisar los criterios",
        fuente="Prueba",
        hash_esperado=leer_seccion(repo, "maestro#6-estandar-academico").hash,
    )
    assert not resultado.exito
    assert any(i["regla"] == "R2" for i in resultado.infracciones), resultado.mensaje
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_el_sello_solo_avanza_en_las_anclas_revisadas(repo: Path):
    """El mecanismo, visto de cerca y sin transacción por medio.

    Con la prosa ya cambiada: si no se sella nada, R2 protesta; si se sella
    esa ancla -que es lo que el guardado hace cuando el docente ha decidido
    sobre todos sus criterios-, deja de protestar. Es la diferencia entre un
    sello que registra lo revisado y uno que se calca del árbol que va a
    verificar.
    """
    from backend.servicios.transaccion import _sellar
    from tools.gobernanza.sincronia import verificar_r2

    documento = repo / "docs/maestro/01-documento-maestro.md"
    documento.write_text(
        documento.read_text(encoding="utf-8").replace(
            "mínimo de 20 páginas", "mínimo de 35 páginas"
        ),
        encoding="utf-8",
    )

    _sellar(repo, set())
    infracciones = verificar_r2(repo)
    assert [i.regla for i in infracciones] == ["R2"]
    assert "maestro#6-estandar-academico" in infracciones[0].detalle

    _sellar(repo, {"maestro#6-estandar-academico"})
    assert verificar_r2(repo) == []


def test_lo_revisado_sin_cambio_no_toca_el_fichero_pero_sella(repo: Path):
    """«Lo he revisado y no cambia» es una decisión, y se comporta como tal.

    No escribe nada en 'criteria/' -el fichero queda byte a byte igual- pero
    cuenta como revisado: es lo único que permite volver a sellar el ancla
    cuando la prosa cambia y ningún criterio tiene que cambiar con ella.
    """
    formato = repo / "criteria/v2026-2027/formato.yaml"
    antes = formato.read_bytes()

    resultado = _guardar_valido(repo, cambios=[])
    assert resultado.exito, resultado.mensaje
    assert formato.read_bytes() == antes

    documento = next((repo / "docs/changes").glob("*-*.md")).read_text(encoding="utf-8")
    assert "revisado, sigue igual" in documento

    from tools.verificar_gobernanza import ejecutar
    assert ejecutar(repo, [], False) == []


def test_un_criterio_de_otra_seccion_no_se_decide_desde_aqui(repo: Path):
    """Un par descuadrado escribiría un documento de cambio que miente."""
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo, cambios=[CambioDeValor(
        fichero="criteria/v2026-2027/dimensiones.yaml",
        identificador="D05",
        clave="nombre",
        valor_nuevo="Otra cosa",
    )])
    assert not resultado.exito
    assert "no deriva de la sección" in resultado.mensaje
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_una_infraccion_previa_se_dice_como_previa_y_no_se_escribe_nada(repo: Path):
    """Si el repositorio ya venía torcido, no se culpa al docente.

    Se comitea a mano una prosa cambiada sin sellar: R2 queda protestando
    desde HEAD. Al guardar, el editor lo dice con esas palabras -que no
    estaba conforme antes de empezar- y no escribe nada, en vez de escribirlo
    todo, tropezar con la infracción al verificar y contarla como si la
    hubiera provocado este cambio.
    """
    documento = repo / "docs/maestro/01-documento-maestro.md"
    documento.write_text(
        documento.read_text(encoding="utf-8").replace(
            "mínimo de 20 páginas", "mínimo de 30 páginas"
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "prosa cambiada sin sellar"],
                   cwd=repo, check=True)

    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = _guardar_valido(repo)
    assert not resultado.exito
    assert "no estaba conforme antes de empezar" in resultado.mensaje
    assert any(i["regla"] == "R2" for i in resultado.infracciones)
    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_dos_guardados_a_la_vez_no_se_pisan(repo: Path, monkeypatch):
    """Dos peticiones solapadas: una guarda, la otra se va de vacío.

    El endpoint es una función normal y Starlette la ejecuta en un hilo del
    pool, así que dos peticiones corren de verdad a la vez. Sin cerrojo, el
    segundo guardado comiteaba y el primero, al fallar, restauraba los bytes
    que había capturado antes de ese commit: deshacía en disco un cambio ya
    registrado, borraba su documento de cambio y contestaba «no se ha
    guardado nada», que era falso.

    Se ensancha la ventana ralentizando la verificación -que es donde más
    tiempo pasa el guardado real- para que el solape sea seguro y no
    dependa de la máquina.
    """
    import threading
    import time

    import backend.servicios.transaccion as transaccion

    verificar = transaccion.ejecutar

    def verificar_despacio(raiz, ficheros, solo_staged):
        time.sleep(0.4)
        return verificar(raiz, ficheros, solo_staged)

    monkeypatch.setattr(transaccion, "ejecutar", verificar_despacio)

    commits = commits_de(repo)
    resultados: list = []

    def guardar_en_hilo():
        resultados.append(_guardar_valido(repo))

    primero = threading.Thread(target=guardar_en_hilo)
    primero.start()
    time.sleep(0.2)
    segundo = _guardar_valido(repo)
    primero.join(timeout=30)

    assert len(resultados) == 1
    assert resultados[0].exito, resultados[0].mensaje
    assert not segundo.exito
    assert "guardado en curso" in segundo.mensaje

    # Un solo commit nuevo, el árbol limpio y el repositorio conforme.
    assert len(commits_de(repo)) == len(commits) + 1
    estado = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                            capture_output=True, text=True, check=True)
    assert estado.stdout.strip() == ""
    assert verificar(repo, [], False) == []
    assert len(list((repo / "docs/changes").glob("*-*.md"))) == 1
    maestro = (repo / "docs/maestro/01-documento-maestro.md").read_text(encoding="utf-8")
    assert "mínimo de 25 páginas" in maestro



# --- Fix round 6: el rechazo no recomienda el atajo que la regla prohibe ---


def test_lo_sin_decidir_se_dice_con_palabras_del_editor_y_no_nombra_ningun_comando(
    repo: Path,
):
    """El rechazo por criterios sin decidir no puede recomendar '--sellar'.

    Ese comando sella todas las anclas sin revisar ninguna: si el docente lo
    ejecutara aquí, el repositorio quedaría conforme con la norma diciendo
    una cosa y los criterios otra, y para siempre. Pasarle crudo el texto de
    R2 -escrito para la consola, y que termina en ese comando- era
    recomendárselo justo en el momento en que no debe usarlo.

    Lo que ve es cuántos criterios le faltan y que vuelva al diálogo.
    """
    antes, commits = contenido_de(repo), commits_de(repo)
    resultado = guardar(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=(
            "## 6. Estándar académico\n\n"
            "El contenido principal tendrá un mínimo de 35 páginas, excluidas\n"
            "portada, índice y anexos. La tipografía será Times New Roman 12.\n"
        ),
        cambios=[],
        motivo="Prueba: cambiar la prosa sin decidir sobre los criterios",
        fuente="Prueba",
        hash_esperado=leer_seccion(repo, "maestro#6-estandar-academico").hash,
    )

    assert not resultado.exito
    assert "sin decidir" in resultado.mensaje
    assert "3 criterios" in resultado.mensaje
    assert "diálogo" in resultado.mensaje

    # Ni en el mensaje ni en ninguna infracción aparece el comando.
    todo = resultado.mensaje + " ".join(i["detalle"] for i in resultado.infracciones)
    assert "--sellar" not in todo
    assert "verificar_gobernanza" not in todo

    # La infracción sigue siendo de R2 y sigue estando: lo que cambia es lo
    # que dice, no que se oculte que la regla ha saltado.
    assert any(i["regla"] == "R2" for i in resultado.infracciones)

    assert contenido_de(repo) == antes
    assert commits_de(repo) == commits


def test_solo_se_reescribe_la_infraccion_de_la_seccion_que_se_esta_editando():
    """Lo que se sustituye es el detalle de ESTA sección, no el de R2 entera.

    Una infracción de R2 sobre otra sección -o de cualquier otra regla- no la
    ha provocado este guardado, así que sigue enseñándose con el texto que
    escribe el verificador. Y el reconocimiento se hace sobre el ancla entre
    comillas: si se buscara suelto, 'maestro#6-estandar' se daría por dueño
    de la infracción de 'maestro#6-estandar-academico', que es otra sección.
    """
    from backend.servicios.transaccion import _es_del_ancla
    from tools.gobernanza.resultado import Infraccion

    propia = Infraccion(
        regla="R2",
        fichero="criteria/.sincronia.json",
        detalle="La sección 'maestro#6-estandar-academico' ha cambiado.",
    )
    otra_ancla = Infraccion(
        regla="R2",
        fichero="criteria/.sincronia.json",
        detalle="La sección 'maestro#8-dimensiones' ha cambiado.",
    )
    otra_regla = Infraccion(
        regla="R1",
        fichero="criteria/v2026-2027/formato.yaml",
        detalle="La sección 'maestro#6-estandar-academico' no existe.",
    )

    assert _es_del_ancla(propia, "maestro#6-estandar-academico")
    assert not _es_del_ancla(otra_ancla, "maestro#6-estandar-academico")
    assert not _es_del_ancla(otra_regla, "maestro#6-estandar-academico")
    # El prefijo de otra ancla no se apropia de la infracción ajena.
    assert not _es_del_ancla(propia, "maestro#6-estandar")
