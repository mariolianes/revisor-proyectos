import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PATRON_ANCLA = re.compile(r"^<!-- ancla: (maestro|indice|guia)#([a-z0-9-]+) -->$", re.M)

DOCUMENTOS = {
    "maestro": RAIZ / "docs" / "maestro" / "01-documento-maestro.md",
    "indice": RAIZ / "docs" / "maestro" / "02-indice-comentado.md",
    "guia": RAIZ / "docs" / "maestro" / "03-guia-desarrollo.md",
}

# Anclas que el destilado en YAML va a referenciar. Si una desaparece,
# los criterios se quedan sin origen y R1 falla.
ANCLAS_EXIGIDAS = {
    "maestro": [
        "1-principios",
        "5-ciclo-de-vida",
        "6-estandar-academico",
        "7-principios-correccion",
        "8-dimensiones",
        "9-matriz-entregas",
        "10-evaluacion-continua",
        "12-errores-y-semaforo",
        "13-reservas-del-profesor",
        "14-fuentes-y-criterios",
        "16-flujo-y-estados",
        "18-reglas-y-paradas",
        "19-privacidad",
    ],
    "indice": ["2-indice-comun", "6-formato-y-control"],
    "guia": ["4-las-cuatro-entregas", "5-documento-unico", "6-evaluacion-continua"],
}


def test_los_tres_documentos_existen():
    for nombre, ruta in DOCUMENTOS.items():
        assert ruta.exists(), f"falta {nombre}: {ruta}"


def test_cada_documento_declara_sus_anclas_exigidas():
    for nombre, ruta in DOCUMENTOS.items():
        texto = ruta.read_text(encoding="utf-8")
        encontradas = {m.group(2) for m in PATRON_ANCLA.finditer(texto)}
        faltan = set(ANCLAS_EXIGIDAS[nombre]) - encontradas
        assert not faltan, f"{nombre}: faltan anclas {sorted(faltan)}"


def test_no_hay_anclas_duplicadas():
    for nombre, ruta in DOCUMENTOS.items():
        texto = ruta.read_text(encoding="utf-8")
        todas = [m.group(2) for m in PATRON_ANCLA.finditer(texto)]
        duplicadas = {a for a in todas if todas.count(a) > 1}
        assert not duplicadas, f"{nombre}: anclas duplicadas {sorted(duplicadas)}"


def test_el_prefijo_del_ancla_coincide_con_su_documento():
    for nombre, ruta in DOCUMENTOS.items():
        texto = ruta.read_text(encoding="utf-8")
        for m in PATRON_ANCLA.finditer(texto):
            assert m.group(1) == nombre, (
                f"{ruta.name}: ancla '{m.group(2)}' declara documento "
                f"'{m.group(1)}' pero vive en '{nombre}'"
            )
