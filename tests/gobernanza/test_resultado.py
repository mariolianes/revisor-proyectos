from tools.gobernanza.resultado import Infraccion, formatear


def test_infraccion_es_inmutable():
    inf = Infraccion(regla="R1", fichero="criteria/x.yaml", detalle="falta fuente")
    try:
        inf.regla = "R2"
    except AttributeError:
        return
    raise AssertionError("Infraccion debería ser inmutable")


def test_formatear_sin_infracciones_confirma_conformidad():
    assert formatear([]) == "Gobernanza conforme: 0 infracciones."


def test_formatear_agrupa_por_regla_y_cuenta():
    infracciones = [
        Infraccion(regla="R1", fichero="criteria/a.yaml", detalle="falta fuente en D05"),
        Infraccion(regla="R1", fichero="criteria/b.yaml", detalle="falta fuente en D07"),
        Infraccion(regla="R6", fichero="docs/x.md", detalle="posible DNI"),
    ]
    salida = formatear(infracciones)
    assert "3 infracciones" in salida
    assert "R1 (2)" in salida
    assert "R6 (1)" in salida
    assert "falta fuente en D05" in salida
