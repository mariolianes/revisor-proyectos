"""Que ninguna regla se caiga de la pantalla de estado sin que un test lo note.

R8 existía en `tools/gobernanza/ortografia.py` y en GOVERNANCE.md, y llevaba
generando infracciones reales, pero `backend/api/estado.py` la olvidó al
describir las reglas en pantalla: el diccionario que agrupaba infracciones
por código solo conocía los siete primeros, así que las de R8 desaparecían
en silencio y el docente leía «conforme» y «0 infracciones» sobre un
repositorio que no lo era. Este fichero comprueba dos cosas para que ese
fallo concreto no pueda repetirse con una R9:

1. Que todo código de regla que de verdad usa el verificador -los
   `regla="Rn"` de `tools/gobernanza/*.py`- tiene su `Descripcion` en
   `REGLAS`.
2. Que `REGLAS` describe exactamente los mismos códigos que GOVERNANCE.md
   declara, ni uno de más ni uno de menos.

Y un tercero, en tiempo de ejecución en vez de estático: que si, aun así,
llega una infracción con un código sin describir, `construir_reglas` no la
descarta -es la red que queda cuando el test estático no basta, por
ejemplo porque a alguien se le olvidó correrlo-.
"""

import re
from pathlib import Path

from backend.api.estado import REGLAS, construir_reglas

RAIZ = Path(__file__).resolve().parents[2]

PATRON_REGLA_EN_CODIGO = re.compile(r'regla\s*=\s*"(R\d+)"')
PATRON_REGLA_EN_GOVERNANCE = re.compile(r"^\*\*R(\d+) ·", re.M)


def _codigos_que_usa_el_verificador() -> set[str]:
    """Todo código de regla que aparece en una `Infraccion(regla=...)` real,
    dentro de `tools/gobernanza/`. Es un escaneo de texto, no una ejecución
    -no todas las reglas infringen sobre el repositorio de pruebas-, pero
    basta para saber qué códigos puede llegar a emitir el verificador.
    """
    codigos = set()
    for ruta in (RAIZ / "tools" / "gobernanza").glob("*.py"):
        codigos |= set(PATRON_REGLA_EN_CODIGO.findall(ruta.read_text(encoding="utf-8")))
    return codigos


def _codigos_de_governance_md() -> set[str]:
    texto = (RAIZ / "GOVERNANCE.md").read_text(encoding="utf-8")
    return {f"R{n}" for n in PATRON_REGLA_EN_GOVERNANCE.findall(texto)}


def test_toda_regla_que_usa_el_verificador_esta_descrita_en_la_pantalla():
    """El fallo exacto que dejó caer R8: un código real sin su Descripcion.

    Si mañana una R9 empieza a levantar infracciones y nadie le añade una
    entrada a REGLAS, este test falla aquí, antes de que un profesor vea la
    pantalla de estado.
    """
    codigos_usados = _codigos_que_usa_el_verificador()
    codigos_descritos = {regla.codigo for regla in REGLAS}
    faltan = codigos_usados - codigos_descritos
    assert not faltan, (
        f"Estas reglas generan infracciones pero backend/api/estado.py no las "
        f"describe: {sorted(faltan)}. Añade su Descripcion en REGLAS."
    )


def test_las_reglas_de_la_pantalla_coinciden_con_governance_md():
    """GOVERNANCE.md es la fuente; REGLAS es su reflejo en pantalla.

    Un código de más en REGLAS describiría una regla que no existe. Uno de
    menos es exactamente el fallo de R8. Las dos direcciones importan.
    """
    codigos_governance = _codigos_de_governance_md()
    codigos_pantalla = {regla.codigo for regla in REGLAS}
    assert codigos_governance == codigos_pantalla, (
        f"GOVERNANCE.md declara {sorted(codigos_governance)}, pero "
        f"REGLAS describe {sorted(codigos_pantalla)}."
    )


def test_una_infraccion_de_codigo_desconocido_no_desaparece():
    """La red que queda si, pese a todo, se cuela una regla sin describir.

    Antes, `por_regla` era un diccionario que solo conocía los códigos de
    REGLAS, y `if infraccion.regla in por_regla` descartaba lo que no
    encajaba. Aquí se simula justo ese caso -un código «R99» que ninguna
    Descripcion nombra- y se comprueba que sigue saliendo en la lista, no
    que se pierde.
    """
    class InfraccionDeMentira:
        def __init__(self, regla, fichero, detalle):
            self.regla = regla
            self.fichero = fichero
            self.detalle = detalle

    infracciones = [InfraccionDeMentira("R99", "un/fichero.py", "algo que contar")]
    reglas = construir_reglas(infracciones)

    codigos = [regla.codigo for regla in reglas]
    assert "R99" in codigos, "una infracción de un código sin describir se ha perdido"

    r99 = next(regla for regla in reglas if regla.codigo == "R99")
    assert r99.infracciones == 1
    assert r99.detalles[0].fichero == "un/fichero.py"
    assert r99.detalles[0].detalle == "algo que contar"


def test_las_reglas_conocidas_no_se_duplican_ni_se_pierden():
    """`construir_reglas` sin infracciones devuelve exactamente REGLAS."""
    reglas = construir_reglas([])
    assert [r.codigo for r in reglas] == [regla.codigo for regla in REGLAS]
    assert all(r.infracciones == 0 for r in reglas)
