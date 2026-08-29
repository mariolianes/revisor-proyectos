"""R8: la prosa en castellano lleva sus tildes; el código no es prosa."""

from pathlib import Path

from tools.gobernanza.ortografia import (
    faltas_en,
    fichero_eximido,
    prosa_de_markdown,
    prosa_de_python,
    verificar_r8,
)


def _palabras(faltas: list[tuple[int, str, str]]) -> set[str]:
    return {escrita.lower() for _, escrita, _ in faltas}


def test_una_falta_en_un_comentario_se_denuncia() -> None:
    fuente = "# el analisis se hace despues de leer el trabajo\nx = 1\n"
    assert _palabras(faltas_en("m.py", fuente)) == {"analisis", "despues"}


def test_una_falta_en_un_docstring_se_denuncia_en_su_linea() -> None:
    """Un docstring ocupa varias líneas: la falta se señala donde está.

    Sin esto, quien lea el aviso iría a la primera línea del bloque y no
    encontraría la palabra allí.
    """
    fuente = '"""Primera linea correcta.\n\nAqui va el analisis del trabajo entregado.\n"""\n'
    faltas = faltas_en("m.py", fuente)
    assert {numero for numero, _, _ in faltas} == {3}
    assert _palabras(faltas) == {"analisis", "aqui"}


def test_un_identificador_no_es_prosa() -> None:
    """`analisis` como nombre es una convención del proyecto, no un descuido."""
    fuente = "analisis = 1\nfrom backend.analisis import contrato\n"
    assert faltas_en("m.py", fuente) == []


def test_una_clave_de_diccionario_no_es_prosa() -> None:
    fuente = 'datos = {"version": 1, "codigo_alumno": "AF023", "dimension": "D05"}\n'
    assert faltas_en("m.py", fuente) == []


def test_una_ruta_de_fichero_no_es_prosa() -> None:
    fuente = '# se lee de criteria/<version>/formato.yaml y de backend/analisis/x.py\n'
    assert faltas_en("m.py", fuente) == []


def test_un_nombre_de_clase_en_mitad_de_una_frase_no_es_prosa() -> None:
    """`Evolucion` en «los valores de Evolucion» es un tipo, no una falta."""
    fuente = "# se devuelven los valores de Evolucion cuando no hay medida\n"
    assert faltas_en("m.py", fuente) == []


def test_una_palabra_capitalizada_al_empezar_la_frase_si_es_prosa() -> None:
    """Distinta de la anterior: aquí la mayúscula es ortografía normal."""
    fuente = "# Despues de leer, se compara. Tambien se mide.\n"
    assert _palabras(faltas_en("m.py", fuente)) == {"despues", "tambien"}


def test_una_constante_en_mayusculas_no_es_prosa() -> None:
    fuente = "# el cruce va al reves que en SELECCION, y por eso no lleva inner\n"
    assert faltas_en("m.py", fuente) == []


def test_las_palabras_ambiguas_no_estan_en_el_vocabulario() -> None:
    """«mas», «solo», «el» y «seria» son válidas sin tilde.

    Denunciarlas daría falsos positivos, y una regla con falsos positivos
    acaba desactivada, que es el peor final para un verificador.
    """
    fuente = "# no es mas que un limite, y solo el profesor decide si seria util\n"
    assert faltas_en("m.py", fuente) == []


def test_un_bloque_de_codigo_de_markdown_no_es_prosa() -> None:
    fuente = "El analisis se guarda.\n\n```python\nanalisis = leer()\n```\n\nY despues se muestra.\n"
    faltas = faltas_en("d.md", fuente)
    assert [numero for numero, _, _ in faltas] == [1, 7]


def test_el_codigo_en_linea_de_markdown_no_es_prosa() -> None:
    fuente = "El campo `version` se compara con `codigo` antes de nada mas.\n"
    assert faltas_en("d.md", fuente) == []


def test_una_marca_con_motivo_exime_su_linea_y_el_codigo_que_sigue() -> None:
    fuente = (
        "x = (\n"
        "    # sin-tilde: es la salida normalizada, que las quita a proposito\n"
        "    # y escribirla con tildes diria lo contrario de lo que hace\n"
        '    "un analisis coste-beneficio detallado"\n'
        ")\n"
    )
    assert faltas_en("m.py", fuente) == []


def test_una_marca_sin_motivo_no_exime_nada() -> None:
    """La válvula tiene que ser una decisión escrita, no un silenciador."""
    fuente = "# sin-tilde:\nx = 1  # aqui va el analisis\n"
    assert _palabras(faltas_en("m.py", fuente)) == {"aqui", "analisis"}


def test_la_marca_no_exime_mas_alla_del_codigo_que_acompana() -> None:
    fuente = (
        "# sin-tilde: solo para la linea de abajo\n"
        '"un analisis"\n'
        "# aqui ya no vale la marca, y este despues es una falta\n"
    )
    assert _palabras(faltas_en("m.py", fuente)) == {"aqui", "despues"}


def test_una_marca_de_fichero_con_motivo_exime_el_fichero() -> None:
    assert fichero_eximido("# sin-tilde-fichero: son PDF de prueba comparados literalmente\n")


def test_una_marca_de_fichero_sin_motivo_no_exime() -> None:
    assert not fichero_eximido("# sin-tilde-fichero:\n")


def test_un_fichero_sin_marca_no_esta_eximido() -> None:
    assert not fichero_eximido("# un comentario cualquiera\n")


def test_la_marca_de_fichero_vale_en_cualquier_linea() -> None:
    """Se busca en el fuente entero, no solo al principio."""
    fuente = "import os\n\n# sin-tilde-fichero: datos de prueba comparados literalmente\n"
    assert fichero_eximido(fuente)


def test_un_fichero_que_no_compila_no_inventa_faltas() -> None:
    """Ya lo denuncian los tests; R8 no se suma al ruido."""
    assert prosa_de_python("def roto(:\n") == []


def test_solo_se_miran_cadenas_y_comentarios() -> None:
    piezas = prosa_de_python('x = 1  # el analisis va aqui\ny = "una frase con analisis"\n')
    assert len(piezas) == 2


def test_markdown_devuelve_el_numero_de_linea_real() -> None:
    piezas = prosa_de_markdown("uno dos tres\n\ncuatro cinco seis\n")
    assert [numero for numero, _ in piezas] == [1, 3]


def test_el_repositorio_esta_conforme() -> None:
    """La regla se cumple hoy: si alguien introduce una falta, este test cae."""
    raiz = Path(__file__).resolve().parents[2]
    assert verificar_r8(raiz, []) == []


def test_las_carpetas_se_ignoran_por_ruta_relativa(tmp_path: Path) -> None:
    """Un repositorio que vive dentro de una carpeta ignorada sigue mirándose.

    Los árboles de trabajo de los agentes cuelgan de `.claude/worktrees/`. Si
    el filtro se aplicara a la ruta absoluta, `.claude` aparecería en la raíz
    misma del repositorio y **ningún** fichero se inspeccionaría: la
    herramienta respondería «conforme» sin haber mirado nada, que es la peor
    forma de fallar que puede tener un verificador.
    """
    raiz = tmp_path / ".claude" / "worktrees" / "agente"
    (raiz / "backend").mkdir(parents=True)
    (raiz / "backend" / "modulo.py").write_text(
        "# el analisis va aqui\n", encoding="utf-8"
    )
    infracciones = verificar_r8(raiz, [])
    assert [i.fichero for i in infracciones] == [
        "backend/modulo.py",
        "backend/modulo.py",
    ]


def test_dentro_del_repositorio_las_carpetas_ignoradas_siguen_ignorandose(
    tmp_path: Path,
) -> None:
    """Lo de arriba no debe romper el filtro para lo que sí cuelga dentro."""
    (tmp_path / ".claude" / "worktrees").mkdir(parents=True)
    (tmp_path / ".claude" / "worktrees" / "copia.py").write_text(
        "# el analisis va aqui\n", encoding="utf-8"
    )
    assert verificar_r8(tmp_path, []) == []
