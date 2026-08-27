from pathlib import Path

from backend.servicios.repositorio import (
    leer_seccion,
    listar_documentos,
    ruta_de_documento,
)


def test_listar_documentos_devuelve_los_presentes(repo: Path):
    documentos = listar_documentos(repo)
    assert [d.clave for d in documentos] == ["maestro"]
    assert documentos[0].titulo == "Documento Maestro"


def test_listar_documentos_enumera_sus_secciones_en_orden(repo: Path):
    secciones = listar_documentos(repo)[0].secciones
    assert [s.ancla for s in secciones] == [
        "maestro#6-estandar-academico",
        "maestro#8-dimensiones",
        "maestro#19-privacidad",
    ]
    assert secciones[0].titulo == "6. Estándar académico"


def test_leer_seccion_devuelve_solo_su_texto(repo: Path):
    seccion = leer_seccion(repo, "maestro#6-estandar-academico")
    assert seccion is not None
    assert "mínimo de 20 páginas" in seccion.texto
    assert "Doce dimensiones" not in seccion.texto


def test_leer_seccion_incluye_su_hash(repo: Path):
    seccion = leer_seccion(repo, "maestro#6-estandar-academico")
    assert seccion.hash and len(seccion.hash) == 16


def test_leer_una_ancla_inexistente_devuelve_none(repo: Path):
    assert leer_seccion(repo, "maestro#no-existe") is None


def test_ruta_de_documento_rechaza_una_clave_desconocida(repo: Path):
    assert ruta_de_documento(repo, "maestro") is not None
    assert ruta_de_documento(repo, "../../etc/passwd") is None
    assert ruta_de_documento(repo, "inventado") is None


def test_cada_seccion_sabe_cuantos_criterios_la_citan(repo: Path):
    secciones = {s.ancla: s for s in listar_documentos(repo)[0].secciones}
    assert secciones["maestro#6-estandar-academico"].criterios_que_la_citan == 2
    assert secciones["maestro#8-dimensiones"].criterios_que_la_citan == 1
    assert secciones["maestro#19-privacidad"].criterios_que_la_citan == 0
