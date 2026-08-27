from pathlib import Path

from backend.servicios.dependencias import contar_por_ancla, criterios_de


def test_criterios_de_una_seccion_citada_por_dos_bloques(repo: Path):
    criterios = criterios_de(repo, "maestro#6-estandar-academico")
    identificadores = sorted(c.identificador for c in criterios)
    assert identificadores == ["extension", "tipografia"]


def test_cada_criterio_trae_su_fichero_y_sus_valores(repo: Path):
    criterios = criterios_de(repo, "maestro#6-estandar-academico")
    extension = next(c for c in criterios if c.identificador == "extension")
    assert extension.fichero == "criteria/v2026-2027/formato.yaml"
    assert extension.valores["minimo_paginas_contenido"] == "20"
    assert "fuente" not in extension.valores


def test_criterios_de_una_entrada_de_lista_usa_su_codigo(repo: Path):
    criterios = criterios_de(repo, "maestro#8-dimensiones")
    assert [c.identificador for c in criterios] == ["D05"]


def test_una_seccion_que_nadie_cita_no_tiene_criterios(repo: Path):
    assert criterios_de(repo, "maestro#19-privacidad") == []


def test_contar_por_ancla_cubre_todas_las_anclas_del_repositorio(repo: Path):
    conteo = contar_por_ancla(repo)
    assert conteo["maestro#6-estandar-academico"] == 2
    assert conteo["maestro#8-dimensiones"] == 1
    assert conteo["maestro#19-privacidad"] == 0
