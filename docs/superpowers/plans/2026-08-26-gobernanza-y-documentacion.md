# Gobernanza y documentación maestra — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la capa de gobernanza que impide que los criterios de corrección deriven de lo que el docente realmente decidió, y dejar los tres documentos maestros convertidos a Markdown versionado con su destilado ejecutable en YAML.

**Architecture:** Dos capas. La prosa normativa vive en `docs/maestro/*.md` con secciones ancladas y su hash registrado. De ella se destila `criteria/v2026-2027/*.yaml`, que es lo único que el futuro backend leerá. Un verificador en Python comprueba las seis reglas mecanizables (R1–R6) y se ejecuta como hook de pre-commit, de modo que una infracción impide el commit en lugar de descubrirse meses después.

**Tech Stack:** Python 3.13, PyYAML, pytest. Sin dependencias de red ni de base de datos en esta fase.

**Spec:** `docs/superpowers/specs/2026-08-26-revisor-proyectos-design.md`

## Global Constraints

- Idioma de código, identificadores, mensajes y documentación: **castellano**.
- Python **3.13** (`C:\Users\conta\AppData\Local\Programs\Python\Python313\python`).
- Todo verificador devuelve `list[Infraccion]`. Ninguno lanza excepción por una infracción: una infracción es un resultado, no un error.
- Ningún fichero de este plan contiene datos de alumnos reales. Los tests usan datos inventados.
- Versión de criterios vigente: `v2026-2027`.
- Formato de referencia a fuente: `documento#ancla`, donde `documento` ∈ {`maestro`, `indice`, `guia`}.
- Los tres documentos maestros originales en PDF están en `C:\Users\conta\Desktop\RECAMBIFY\`. Su texto ya extraído en UTF-8 está en el scratchpad de la sesión; si no estuviera, se regenera con `pdftotext -layout -enc UTF-8`.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `tools/verificar_gobernanza.py` | CLI: orquesta los verificadores e imprime el informe |
| `tools/gobernanza/resultado.py` | `Infraccion` y utilidades de formato compartidas |
| `tools/gobernanza/criterios.py` | R1 (fuente obligatoria) y R3 (pendiente oficial) |
| `tools/gobernanza/sincronia.py` | R2 (hash prosa ↔ YAML) |
| `tools/gobernanza/versiones.py` | R4 (congelación de versiones) |
| `tools/gobernanza/cambios.py` | R5 (registro de cambios) |
| `tools/gobernanza/privacidad.py` | R6 (datos personales) |
| `docs/maestro/*.md` | La prosa normativa, con anclas estables |
| `criteria/v2026-2027/*.yaml` | El destilado ejecutable |

Un fichero por regla. Cada uno se entiende y se prueba solo.

---

### Task 1: Base del repositorio y arnés de pruebas

**Files:**
- Create: `.gitignore`
- Create: `.gitattributes`
- Create: `README.md`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `tools/gobernanza/__init__.py`
- Create: `tools/gobernanza/resultado.py`
- Test: `tests/gobernanza/test_resultado.py`

**Interfaces:**
- Consumes: nada.
- Produces: `Infraccion(regla: str, fichero: str, detalle: str)` — dataclass congelada que todos los verificadores devuelven. `formatear(infracciones: list[Infraccion]) -> str` para el informe de la CLI.

- [ ] **Step 1: Crear `.gitattributes`**

Windows y Git pelean por los finales de línea y ya han avisado en los dos primeros commits. Esto lo zanja.

```
* text=auto eol=lf
*.png binary
*.pdf binary
```

- [ ] **Step 2: Crear `.gitignore`**

```
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
.env
.env.*
!.env.example
node_modules/
dist/
*.pdf
*.docx
*.doc
!docs/plantillas/*.pdf
```

La exclusión de `*.pdf` y `*.docx` es la primera línea de defensa de R6: aunque alguien arrastre una entrega al repo por error, Git la ignora.

- [ ] **Step 3: Crear `requirements-dev.txt`**

```
pyyaml==6.0.2
pytest==8.3.4
```

- [ ] **Step 4: Crear `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v
```

- [ ] **Step 5: Escribir el test que falla**

Crear `tests/gobernanza/test_resultado.py`:

```python
from tools.gobernanza.resultado import Infraccion, formatear


def test_infraccion_es_inmutable():
    inf = Infraccion(regla="R1", fichero="criteria/x.yaml", detalle="falta fuente")
    try:
        inf.regla = "R2"
    except AttributeError:
        return
    raise AssertionError("Infraccion deberia ser inmutable")


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
```

- [ ] **Step 6: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_resultado.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 7: Crear `tools/gobernanza/__init__.py` vacío y `tools/__init__.py` vacío**

Ambos ficheros vacíos, para que `tools.gobernanza` sea importable desde la raíz.

- [ ] **Step 8: Escribir la implementación mínima**

Crear `tools/gobernanza/resultado.py`:

```python
"""Tipo comun de resultado de los verificadores de gobernanza."""

from dataclasses import dataclass
from collections import Counter


@dataclass(frozen=True)
class Infraccion:
    """Una infraccion concreta de una regla de gobernanza.

    regla: identificador corto, "R1" a "R7".
    fichero: ruta relativa a la raiz del repositorio.
    detalle: explicacion accionable, en castellano, sin jerga.
    """

    regla: str
    fichero: str
    detalle: str


def formatear(infracciones: list[Infraccion]) -> str:
    """Devuelve el informe legible que imprime la CLI."""
    if not infracciones:
        return "Gobernanza conforme: 0 infracciones."

    conteo = Counter(inf.regla for inf in infracciones)
    resumen = ", ".join(f"{regla} ({conteo[regla]})" for regla in sorted(conteo))
    lineas = [f"{len(infracciones)} infracciones -> {resumen}", ""]
    for inf in sorted(infracciones, key=lambda i: (i.regla, i.fichero)):
        lineas.append(f"  [{inf.regla}] {inf.fichero}")
        lineas.append(f"        {inf.detalle}")
    return "\n".join(lineas)
```

- [ ] **Step 9: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_resultado.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 10: Escribir `README.md`**

```markdown
# Revisor de Proyectos Intermodulares

Asistente interno de correccion y seguimiento de Proyectos Intermodulares de
Formacion Profesional.

El sistema no califica ni comunica. Propone, evidencia y se detiene. La
valoracion definitiva, la calificacion y cualquier comunicacion al alumno
pertenecen siempre al profesor.

## Documentacion

- `GOVERNANCE.md` — las reglas del repositorio. Leelo antes de tocar criterios.
- `docs/maestro/` — la prosa normativa. Es la fuente de verdad.
- `criteria/` — el destilado ejecutable, derivado de la prosa.
- `docs/decisions.md` — por que el sistema es como es.
- `docs/PENDIENTE_OFICIAL.md` — lo que aun no se sabe y no se inventa.

## Puesta en marcha

    python -m pip install -r requirements-dev.txt
    python -m pytest
    python tools/verificar_gobernanza.py
```

- [ ] **Step 11: Commit**

```bash
git add .gitignore .gitattributes README.md requirements-dev.txt pytest.ini tools/ tests/
git commit -m "chore: base del repositorio y tipo comun de infraccion"
```

---

### Task 2: Los tres documentos maestros en Markdown con anclas estables

**Files:**
- Create: `docs/maestro/01-documento-maestro.md`
- Create: `docs/maestro/02-indice-comentado.md`
- Create: `docs/maestro/03-guia-desarrollo.md`
- Create: `docs/maestro/README.md`
- Test: `tests/gobernanza/test_anclas.py`

**Interfaces:**
- Consumes: nada.
- Produces: las anclas que R1 usará como destino de `fuente`. Formato de ancla, una línea inmediatamente antes de cada encabezado de sección:
  `<!-- ancla: maestro#8-dimensiones -->`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_anclas.py`:

```python
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
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_anclas.py -v`
Expected: FAIL en `test_los_tres_documentos_existen`, los ficheros no existen.

- [ ] **Step 3: Convertir el Documento Maestro a Markdown**

Transcribir el contenido íntegro del PDF `Documento_Maestro_Sistema_Correccion_Proyectos_Intermodulares_2026-2027.pdf` a `docs/maestro/01-documento-maestro.md`.

Reglas de conversión, sin excepciones:

- **No se reescribe el contenido.** Se conserva la redacción del docente palabra por palabra. Esto es un documento normativo, no un borrador a mejorar.
- Las tablas del PDF salen descuadradas de `pdftotext` porque las columnas se entrelazan. Hay que **recomponerlas** como tablas Markdown legibles, respetando qué celda pertenece a qué fila. Es la parte más delicada de esta tarea: una fila mal asignada cambia un criterio.
- Cada sección numerada lleva su ancla en la línea anterior al encabezado.
- Los recuadros destacados del PDF ("Decisión central:", "Regla obligatoria:", "Regla de conflicto:") se convierten en citas Markdown `>` conservando el rótulo en negrita.
- Se añade al inicio una cabecera de procedencia.

Estructura de la cabecera y las primeras secciones:

```markdown
# Documento Maestro del Sistema de Corrección y Seguimiento

> **Curso 2026-2027 · Proyecto Intermodular**
> Documento interno. No dirigido al alumnado.
> Origen: `Documento_Maestro_Sistema_Correccion_Proyectos_Intermodulares_2026-2027.pdf`
> Convertido a Markdown el 2026-08-26. Desde esta fecha, **este fichero es la
> fuente de verdad** y el PDF pasa a ser una copia histórica.

<!-- ancla: maestro#1-principios -->
## 1. Finalidad, alcance y principios del Documento Maestro

Este documento reúne en una única fuente el modelo académico del Proyecto
Intermodular, el método de corrección y seguimiento y los requisitos
funcionales del futuro sistema local. Su función es evitar que la guía del
alumnado, el criterio del docente y el comportamiento del asistente
evolucionen por caminos distintos.

> **Decisión central:** El sistema asistirá en la lectura, la comparación, la
> preevaluación y la redacción de borradores. La valoración definitiva, la
> calificación y cualquier comunicación al alumno pertenecerán siempre al
> profesor.

### 1.1 Usuarios y usos

| Usuario | Uso principal | Límite |
|---|---|---|
| Marcos / docente | Corregir, seguir la evolución, registrar notas y preparar feedback | Aprueba o modifica toda salida |
| Colaborador técnico | Construir, probar y mantener la solución | No redefine criterios académicos |
| Asistente local | Aplicar criterios, localizar evidencias y generar borradores | No decide ni publica |
| Alumno | Recibe únicamente el feedback validado por el docente | No accede al informe interno |

### 1.2 Principios no negociables

- **Nivel propio de Formación Profesional:** riguroso, claro, aplicado y proporcionado.
- **Carácter profesional e intermodular:** el proyecto debe integrar aprendizajes de varios módulos y aplicarlos a una situación significativa del sector.
- **Evaluación progresiva:** cada fase se valora por lo que debe existir en ese momento, no por exigencias de fases posteriores.
- **Documento acumulativo:** cada entrega contiene lo anterior corregido más el nuevo desarrollo.
- **Trazabilidad:** toda observación debe vincularse a una evidencia del documento, una ausencia verificable o un criterio vigente.
- **Prudencia:** el sistema distingue entre hecho, inferencia, duda y decisión reservada al profesor.
- **Humanidad del feedback:** claridad y firmeza sin perder cercanía, contexto ni capacidad de motivar.
- **No automatización del alumno:** ninguna salida se envía ni publica sin revisión docente.
```

Nótese la tabla 1.1: en el PDF las columnas están desplazadas y "Corregir, seguir la evolución..." aparece bajo "Colaborador técnico" cuando corresponde a "Marcos / docente". Recomponer así todas las tablas del documento.

Continuar hasta cubrir las 22 secciones y los anexos A–H, colocando las anclas de `ANCLAS_EXIGIDAS["maestro"]` en sus secciones correspondientes:

| Ancla | Sección del PDF |
|---|---|
| `1-principios` | 1. Finalidad, alcance y principios |
| `5-ciclo-de-vida` | 5. Ciclo de vida: tema, entregas y defensa |
| `6-estandar-academico` | 6. Estándar académico y condiciones transversales |
| `7-principios-correccion` | 7. Principios del modelo de corrección |
| `8-dimensiones` | 8. Dimensiones de evaluación |
| `9-matriz-entregas` | 9. Matriz de revisión por entregas |
| `10-evaluacion-continua` | 10. Evaluación continua, nota interna y ficha |
| `12-errores-y-semaforo` | 12. Errores recurrentes, alertas y semáforo |
| `13-reservas-del-profesor` | 13. Decisiones reservadas al profesor |
| `14-fuentes-y-criterios` | 14. Fuentes de verdad y criterios configurables |
| `16-flujo-y-estados` | 16. Flujo propuesto de corrección |
| `18-reglas-y-paradas` | 18. Reglas funcionales y condiciones de parada |
| `19-privacidad` | 19. Privacidad, seguridad y trazabilidad |

- [ ] **Step 4: Convertir el Índice comentado a Markdown**

A `docs/maestro/02-indice-comentado.md`, con las mismas reglas. Anclas exigidas:

| Ancla | Sección del PDF |
|---|---|
| `2-indice-comun` | 2. El índice común del proyecto |
| `6-formato-y-control` | 6. Presentación y control final |

La sección 6 es la que más peso tiene para el sistema: contiene las reglas de formato, distribución del contenido, imágenes, redacción, autoría e IA, preparación del archivo y la lista de control final. Transcribir esa sección con especial cuidado, sin resumir ninguna viñeta.

- [ ] **Step 5: Convertir la Guía de desarrollo a Markdown**

A `docs/maestro/03-guia-desarrollo.md`. Anclas exigidas:

| Ancla | Sección del PDF |
|---|---|
| `4-las-cuatro-entregas` | 4. Las cuatro entregas del proyecto |
| `5-documento-unico` | 5. La regla fundamental: siempre el mismo documento |
| `6-evaluacion-continua` | 6. Evaluación continua y responsabilidad del estudiante |

Incluir íntegro el apartado de preguntas habituales: contiene reglas duras que el sistema aplicará (0 puntos por entrega fuera de plazo, mínimo de 20 páginas de contenido sin portada ni índice ni anexos, prohibición de entregar apartados en archivos separados).

- [ ] **Step 6: Escribir `docs/maestro/README.md`**

```markdown
# Documentos maestros

Estos tres ficheros son la fuente de verdad del sistema. El PDF del que
proceden es, desde el 2026-08-26, una copia histórica.

| Fichero | Qué responde | Destinatario |
|---|---|---|
| `01-documento-maestro.md` | Cómo se corrige | Interno |
| `02-indice-comentado.md` | Qué debe contener cada apartado | Alumnado |
| `03-guia-desarrollo.md` | Cómo se trabaja el curso | Alumnado |

## Anclas

Cada sección referenciable lleva, en la línea anterior a su encabezado, un
ancla con esta forma:

    <!-- ancla: maestro#8-dimensiones -->

Los criterios de `criteria/` apuntan a estas anclas mediante su campo
`fuente`. **Borrar o renombrar un ancla deja criterios huérfanos y el
verificador lo rechaza.** Si necesitas reorganizar un documento, cambia
primero el ancla en el YAML que la usa.

## Cómo se cambia un criterio

Se edita aquí, nunca en el YAML. Consulta `GOVERNANCE.md`.
```

- [ ] **Step 7: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_anclas.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 8: Commit**

```bash
git add docs/maestro/ tests/gobernanza/test_anclas.py
git commit -m "docs: los tres documentos maestros en Markdown con anclas estables"
```

---

### Task 3: R1 — ningún criterio sin origen

**Files:**
- Create: `criteria/v2026-2027/dimensiones.yaml`
- Create: `criteria/v2026-2027/formato.yaml`
- Create: `tools/gobernanza/criterios.py`
- Test: `tests/gobernanza/test_criterios.py`

**Interfaces:**
- Consumes: `Infraccion` de `tools.gobernanza.resultado`; las anclas de la Task 2.
- Produces:
  - `cargar_anclas(raiz: Path) -> set[str]` → conjunto de anclas existentes, en formato `documento#ancla`.
  - `entradas_de(ruta_yaml: Path) -> list[dict]` → lista plana de entradas con campo `fuente`, sea cual sea la forma del YAML.
  - `verificar_r1(raiz: Path) -> list[Infraccion]`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_criterios.py`:

```python
from pathlib import Path

import pytest

from tools.gobernanza.criterios import cargar_anclas, entradas_de, verificar_r1


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repositorio minimo con un documento maestro y una carpeta de criterios."""
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(
        "<!-- ancla: maestro#8-dimensiones -->\n"
        "## 8. Dimensiones de evaluacion\n\n"
        "Texto.\n",
        encoding="utf-8",
    )
    (tmp_path / "criteria" / "v2026-2027").mkdir(parents=True)
    return tmp_path


def test_cargar_anclas_encuentra_las_declaradas(repo: Path):
    assert cargar_anclas(repo) == {"maestro#8-dimensiones"}


def test_entradas_de_aplana_una_lista(tmp_path: Path):
    ruta = tmp_path / "d.yaml"
    ruta.write_text(
        "- codigo: D05\n"
        "  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    entradas = entradas_de(ruta)
    assert len(entradas) == 1
    assert entradas[0]["codigo"] == "D05"


def test_entradas_de_aplana_un_mapa_con_listas_anidadas(tmp_path: Path):
    ruta = tmp_path / "f.yaml"
    ruta.write_text(
        "extension:\n"
        "  minimo_paginas: 20\n"
        "  fuente: guia#6-evaluacion-continua\n"
        "tipografia:\n"
        "  familia: Arial\n"
        "  fuente: maestro#6-estandar-academico\n",
        encoding="utf-8",
    )
    entradas = entradas_de(ruta)
    assert len(entradas) == 2
    assert {e["fuente"] for e in entradas} == {
        "guia#6-evaluacion-continua",
        "maestro#6-estandar-academico",
    }


def test_r1_acepta_un_criterio_con_fuente_existente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  nombre: Fundamentacion y fuentes\n"
        "  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    assert verificar_r1(repo) == []


def test_r1_rechaza_un_criterio_sin_campo_fuente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  nombre: Fundamentacion y fuentes\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R1"
    assert "D05" in infracciones[0].detalle
    assert "sin campo 'fuente'" in infracciones[0].detalle


def test_r1_rechaza_una_fuente_que_apunta_a_un_ancla_inexistente(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  fuente: maestro#seccion-que-no-existe\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R1"
    assert "maestro#seccion-que-no-existe" in infracciones[0].detalle


def test_r1_rechaza_una_fuente_con_formato_invalido(repo: Path):
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n"
        "  fuente: el documento maestro, seccion 8\n",
        encoding="utf-8",
    )
    infracciones = verificar_r1(repo)
    assert len(infracciones) == 1
    assert "formato" in infracciones[0].detalle
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_criterios.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.gobernanza.criterios'`

- [ ] **Step 3: Escribir la implementación mínima**

Crear `tools/gobernanza/criterios.py`:

```python
"""R1: ningun criterio sin origen. R3: lo pendiente se marca, no se inventa."""

import re
from pathlib import Path

import yaml

from tools.gobernanza.resultado import Infraccion

PATRON_ANCLA = re.compile(r"^<!-- ancla: ((?:maestro|indice|guia)#[a-z0-9-]+) -->$", re.M)
PATRON_FUENTE = re.compile(r"^(?:maestro|indice|guia)#[a-z0-9-]+$")


def cargar_anclas(raiz: Path) -> set[str]:
    """Devuelve todas las anclas declaradas en los documentos maestros."""
    anclas: set[str] = set()
    carpeta = raiz / "docs" / "maestro"
    if not carpeta.is_dir():
        return anclas
    for ruta in sorted(carpeta.glob("*.md")):
        texto = ruta.read_text(encoding="utf-8")
        anclas.update(m.group(1) for m in PATRON_ANCLA.finditer(texto))
    return anclas


def entradas_de(ruta_yaml: Path) -> list[dict]:
    """Aplana un YAML de criterios a la lista de sus entradas con criterio.

    Un fichero de criterios puede ser una lista de entradas o un mapa cuyos
    valores son entradas. Se considera entrada todo diccionario que declare
    'fuente' o 'codigo': son los que R1 debe examinar.
    """
    datos = yaml.safe_load(ruta_yaml.read_text(encoding="utf-8"))
    entradas: list[dict] = []

    def recorrer(nodo, clave_padre: str | None) -> None:
        if isinstance(nodo, dict):
            if "fuente" in nodo or "codigo" in nodo:
                entrada = dict(nodo)
                entrada.setdefault("_clave", clave_padre)
                entradas.append(entrada)
                return
            for clave, valor in nodo.items():
                recorrer(valor, clave)
        elif isinstance(nodo, list):
            for elemento in nodo:
                recorrer(elemento, clave_padre)

    recorrer(datos, None)
    return entradas


def _identificar(entrada: dict) -> str:
    """Nombre con el que referirse a una entrada en el mensaje de error."""
    return str(entrada.get("codigo") or entrada.get("_clave") or "entrada sin codigo")


def verificar_r1(raiz: Path) -> list[Infraccion]:
    """Comprueba que todo criterio declara una fuente valida y existente."""
    anclas = cargar_anclas(raiz)
    infracciones: list[Infraccion] = []
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return infracciones

    for ruta in sorted(carpeta.rglob("*.yaml")):
        relativa = ruta.relative_to(raiz).as_posix()
        for entrada in entradas_de(ruta):
            nombre = _identificar(entrada)
            fuente = entrada.get("fuente")

            if fuente is None:
                infracciones.append(Infraccion(
                    regla="R1",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' no declara de donde sale: sin campo 'fuente'. "
                        f"Anade 'fuente: documento#ancla' apuntando a la seccion "
                        f"de docs/maestro/ que lo respalda."
                    ),
                ))
                continue

            if not PATRON_FUENTE.match(str(fuente)):
                infracciones.append(Infraccion(
                    regla="R1",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' tiene una fuente con formato invalido: "
                        f"'{fuente}'. Se espera 'documento#ancla', donde documento "
                        f"es maestro, indice o guia."
                    ),
                ))
                continue

            if fuente not in anclas:
                infracciones.append(Infraccion(
                    regla="R1",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' apunta a '{fuente}', que no existe en "
                        f"docs/maestro/. O el ancla se ha renombrado, o el criterio "
                        f"no tiene respaldo en la prosa."
                    ),
                ))

    return infracciones
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_criterios.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Escribir `criteria/v2026-2027/dimensiones.yaml`**

Las doce dimensiones del §8, con su actividad por fase según la matriz del §9. `activa_en` usa las fases `TEMA`, `E1`, `E2`, `E3`, `FINAL`, `DEFENSA`. Una dimensión ausente de `activa_en` en una fase no penaliza (nivel "No aplicable" de la escala del §8.1).

```yaml
# Dimensiones de evaluacion. Derivado de docs/maestro/01-documento-maestro.md
# NO EDITAR sin cambiar antes la prosa. Ver GOVERNANCE.md.

- codigo: D01
  nombre: Adecuacion al ciclo e intermodularidad
  observa: Relacion profesional e integracion de aprendizajes
  fuente: maestro#8-dimensiones
  activa_en: [TEMA, E1, E2, E3, FINAL]

- codigo: D02
  nombre: Tema, necesidad y justificacion
  observa: Concrecion, relevancia y evidencia de partida
  fuente: maestro#8-dimensiones
  activa_en: [TEMA, E1, E2, E3, FINAL]

- codigo: D03
  nombre: Objetivos
  observa: Claridad, coherencia y posibilidad de respuesta
  fuente: maestro#8-dimensiones
  activa_en: [E1, E2, E3, FINAL]

- codigo: D04
  nombre: Estructura y coherencia global
  observa: Orden, equilibrio y ausencia de contradicciones
  fuente: maestro#8-dimensiones
  activa_en: [E1, E2, E3, FINAL]

- codigo: D05
  nombre: Fundamentacion y fuentes
  observa: Seleccion, calidad, citas y uso real
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]

- codigo: D06
  nombre: Metodologia o procedimiento
  observa: Trazabilidad del trabajo y adecuacion al enfoque
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]

- codigo: D07
  nombre: Desarrollo aplicado
  observa: Profundidad, decisiones, viabilidad y uso de competencias
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]

- codigo: D08
  nombre: Resultados e interpretacion
  observa: Evidencias, significado y relacion con objetivos
  fuente: maestro#8-dimensiones
  activa_en: [E3, FINAL]

- codigo: D09
  nombre: Conclusiones
  observa: Respuesta, limites, aportacion y mejora
  fuente: maestro#8-dimensiones
  activa_en: [E3, FINAL]

- codigo: D10
  nombre: Evolucion y feedback
  observa: Correcciones incorporadas y progreso entre versiones
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]

- codigo: D11
  nombre: Redaccion y presentacion
  observa: Claridad, rigor, formato, tablas e imagenes
  fuente: maestro#8-dimensiones
  activa_en: [E1, E2, E3, FINAL]

- codigo: D12
  nombre: Autoria y defendibilidad
  observa: Comprension, decisiones propias y ausencia de indicios criticos
  fuente: maestro#8-dimensiones
  activa_en: [E1, E2, E3, FINAL, DEFENSA]
```

Nota sobre D05: el §9.2 dice que en la primera entrega no corresponde exigir bibliografía completa, pero sí "primeras fuentes o datos que permitan investigar". Se resuelve activando D05 desde E2 y dejando la comprobación de E1 a D02, que ya observa la "evidencia de partida". Registrar esta interpretación en `docs/changes/` al commitear.

- [ ] **Step 6: Escribir `criteria/v2026-2027/formato.yaml`**

```yaml
# Requisitos de formato verificables sobre el PDF.
# Derivado de docs/maestro/. NO EDITAR sin cambiar antes la prosa.

extension:
  minimo_paginas_contenido: 20
  excluye: [portada, indice, anexos]
  fuente: guia#6-evaluacion-continua

tipografia:
  familia: Arial
  cuerpo: 11
  tolerancia_cuerpo: 0.5
  fuente: maestro#6-estandar-academico

interlineado:
  valor: 1.5
  tolerancia: 0.1
  fuente: maestro#6-estandar-academico

alineacion:
  valor: justificado
  fuente: maestro#6-estandar-academico

margenes:
  centimetros: 2.5
  tolerancia: 0.5
  fuente: maestro#6-estandar-academico

archivo:
  formato: PDF
  generado_desde_original: true
  admite_escaneado: false
  fuente: indice#6-formato-y-control

paginas_en_blanco:
  permitidas: false
  fuente: indice#6-formato-y-control

imagenes:
  requiere_numeracion: true
  requiere_titulo: true
  requiere_fuente_si_ajena: true
  requiere_mencion_en_texto: true
  fuente: indice#6-formato-y-control

indice_paginado:
  titulos_coinciden_con_documento: true
  paginas_actualizadas: true
  fuente: indice#6-formato-y-control
```

- [ ] **Step 7: Escribir `criteria/v2026-2027/matriz-fases.yaml`**

Qué debe existir en cada fase, según el §9. Es lo que permite la evaluación progresiva: no exigir en E1 lo que corresponde a E3.

```yaml
# Que debe existir en cada fase. Derivado del §9 del Documento Maestro.
# NO EDITAR sin cambiar antes la prosa.

TEMA:
  evaluable: false
  debe_existir:
    - titulo_o_frase_provisional
    - problema_necesidad_u_oportunidad
    - relacion_con_el_ciclo
    - intencion_del_alumno
    - acceso_probable_a_informacion
  fuente: maestro#9-matriz-entregas

E1:
  evaluable: true
  finalidad: Comprobar que el proyecto tiene una direccion viable
  debe_existir:
    - portada_y_titulo_provisional
    - presentacion_del_tema
    - justificacion_vinculada_al_ciclo
    - objetivo_general_y_especificos
    - modalidad_e_indice_provisional
    - primeras_fuentes_o_datos
  no_corresponde_aun:
    - resultados_definitivos
    - conclusiones_cerradas
    - bibliografia_completa
    - desarrollo_exhaustivo
  fuente: maestro#9-matriz-entregas

E2:
  evaluable: true
  finalidad: Convertir la idea en un proyecto con contenido sustancial
  debe_existir:
    - entrega_anterior_corregida_e_integrada
    - introduccion_justificacion_objetivos_revisados
    - contexto_y_marco_teorico_util
    - metodologia_o_procedimiento
    - desarrollo_aplicado_inicial
    - datos_ejemplos_o_evidencias
    - bibliografia_actualizada
  alerta_caracteristica: Subir solo los capitulos nuevos o repetir la version anterior sin progreso real
  fuente: maestro#9-matriz-entregas

E3:
  evaluable: true
  finalidad: Proyecto practicamente completo, detectar los ultimos problemas
  debe_existir:
    - todo_lo_anterior_corregido
    - desarrollo_completo
    - resultados_interpretacion_o_viabilidad
    - conclusiones_provisionales
    - bibliografia_casi_completa
    - presentacion_formal_cercana_a_definitiva
  regla_clave: No es la entrega final; debe estar casi terminada para que el ultimo feedback cierre, no construya
  fuente: maestro#9-matriz-entregas

FINAL:
  evaluable: true
  finalidad: Depositar el documento definitivo, completo y defendible
  debe_existir:
    - todos_los_apartados_completos
    - conclusiones_definitivas
    - citas_y_bibliografia_revisadas
    - tablas_graficos_e_imagenes_identificados
    - indice_y_paginas_actualizados
    - formato_uniforme_y_pdf_correcto
    - presentacion_depositada
  fuente: maestro#9-matriz-entregas

DEFENSA:
  evaluable: true
  valoracion: manual
  observa:
    - comprension
    - seleccion_de_ideas
    - claridad
    - capacidad_para_justificar_decisiones
    - respuestas_a_preguntas
  fuente: maestro#9-matriz-entregas
```

- [ ] **Step 8: Escribir `criteria/v2026-2027/semaforo.yaml`**

```yaml
# Semaforo pedagogico. Derivado del §12.1 del Documento Maestro.
# El semaforo resume el estado; no sustituye la rubrica, la nota ni la
# explicacion. Un mismo color puede responder a causas diferentes.

- codigo: VERDE
  significado: Cumple la fase y puede avanzar
  accion: Mantener fortalezas y aplicar ajustes menores
  fuente: maestro#12-errores-y-semaforo

- codigo: AMBAR
  significado: Avanza, pero existen correcciones prioritarias
  accion: Aplicar cambios antes de cerrar la siguiente fase
  fuente: maestro#12-errores-y-semaforo

- codigo: ROJO
  significado: Carencia estructural o academica que exige reconduccion
  accion: Revision docente y plan de correccion
  fuente: maestro#12-errores-y-semaforo

- codigo: GRIS
  significado: No evaluable por falta, fuera de plazo, archivo ilegible o criterio bloqueado
  accion: Resolver incidencia; no emitir juicio academico automatico
  fuente: maestro#12-errores-y-semaforo
```

- [ ] **Step 9: Escribir `criteria/v2026-2027/reglas-parada.yaml`**

Las condiciones del §18.2. Son las que convierten `BLOQUEADO` en una salida legítima del sistema y no en un fallo.

```yaml
# Condiciones de parada. Derivado del §18.2 del Documento Maestro.
# 'alcance: total' detiene la correccion entera. 'alcance: juicio' detiene
# solo el juicio afectado y permite continuar con el resto.

- codigo: pdf_ilegible
  condicion: PDF ilegible, vacio o protegido
  respuesta: Bloquear y solicitar archivo valido
  alcance: total
  fuente: maestro#18-reglas-y-paradas

- codigo: identidad_no_coincide
  condicion: Alumno o fase no coinciden con la ficha
  respuesta: Bloquear y pedir seleccion correcta
  alcance: total
  fuente: maestro#18-reglas-y-paradas

- codigo: fuera_de_plazo
  condicion: Entrega presentada fuera de plazo
  respuesta: Marcar GRIS y 0; no corregir salvo instruccion docente
  alcance: total
  fuente: maestro#18-reglas-y-paradas

- codigo: criterios_contradictorios
  condicion: Dos criterios vigentes se contradicen
  respuesta: Crear alerta de resolucion y detener el juicio afectado
  alcance: juicio
  fuente: maestro#18-reglas-y-paradas

- codigo: falta_feedback_anterior
  condicion: No existe el feedback anterior cuando es necesario compararlo
  respuesta: Continuar sin comparacion solo con autorizacion expresa
  alcance: juicio
  fuente: maestro#18-reglas-y-paradas

- codigo: indicio_de_autoria
  condicion: Indicio critico sobre autoria o uso indebido de IA
  respuesta: Generar nota interna prudente y escalar al profesor
  alcance: juicio
  fuente: maestro#18-reglas-y-paradas

- codigo: error_tecnico
  condicion: Error tecnico durante la generacion de salidas
  respuesta: Conservar la entrada, registrar el error y no crear salida aprobable
  alcance: total
  fuente: maestro#18-reglas-y-paradas
```

- [ ] **Step 10: Escribir el test de integración sobre los criterios reales**

Añadir al final de `tests/gobernanza/test_criterios.py`:

```python
def test_r1_pasa_sobre_los_criterios_reales_del_repositorio():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r1(raiz)
    assert infracciones == [], "\n".join(i.detalle for i in infracciones)
```

- [ ] **Step 11: Ejecutar toda la batería**

Run: `python -m pytest tests/ -v`
Expected: PASS. Si el test de integración falla, es porque un ancla de la Task 2 no coincide con las usadas aquí: corregir el ancla en el Markdown, nunca el YAML.

- [ ] **Step 12: Commit**

```bash
git add criteria/ tools/gobernanza/criterios.py tests/gobernanza/test_criterios.py
git commit -m "feat: R1, ningun criterio sin origen trazable a la prosa"
```

---

### Task 4: R3 — lo pendiente se marca, no se inventa

**Files:**
- Create: `docs/PENDIENTE_OFICIAL.md`
- Create: `criteria/v2026-2027/ponderaciones.yaml`
- Create: `criteria/v2026-2027/calendario.yaml`
- Modify: `tools/gobernanza/criterios.py`
- Test: `tests/gobernanza/test_pendiente_oficial.py`

**Interfaces:**
- Consumes: `entradas_de`, `Infraccion`.
- Produces: `verificar_r3(raiz: Path) -> list[Infraccion]`. Toda entrada con `estado: PENDIENTE_OFICIAL` debe declarar `bloquea` (lista de fases o `[]`) y tener una entrada homónima en `docs/PENDIENTE_OFICIAL.md` con la forma `- **<clave>** —`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_pendiente_oficial.py`:

```python
from pathlib import Path

import pytest

from tools.gobernanza.criterios import verificar_r3


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "criteria" / "v2026-2027").mkdir(parents=True)
    (tmp_path / "docs" / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente oficial\n\n"
        "- **ponderaciones** — a la espera de la programacion didactica.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_r3_acepta_un_pendiente_bien_declarado(repo: Path):
    (repo / "criteria" / "v2026-2027" / "ponderaciones.yaml").write_text(
        "ponderaciones:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  bloquea: [nota_final]\n"
        "  fuente: maestro#10-evaluacion-continua\n",
        encoding="utf-8",
    )
    assert verificar_r3(repo) == []


def test_r3_rechaza_un_pendiente_sin_campo_bloquea(repo: Path):
    (repo / "criteria" / "v2026-2027" / "ponderaciones.yaml").write_text(
        "ponderaciones:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  fuente: maestro#10-evaluacion-continua\n",
        encoding="utf-8",
    )
    infracciones = verificar_r3(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R3"
    assert "bloquea" in infracciones[0].detalle


def test_r3_rechaza_un_pendiente_no_documentado(repo: Path):
    (repo / "criteria" / "v2026-2027" / "calendario.yaml").write_text(
        "calendario:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  bloquea: [plazo]\n"
        "  fuente: maestro#14-fuentes-y-criterios\n",
        encoding="utf-8",
    )
    infracciones = verificar_r3(repo)
    assert len(infracciones) == 1
    assert "PENDIENTE_OFICIAL.md" in infracciones[0].detalle


def test_r3_rechaza_un_pendiente_que_ya_trae_valor_inventado(repo: Path):
    (repo / "criteria" / "v2026-2027" / "ponderaciones.yaml").write_text(
        "ponderaciones:\n"
        "  estado: PENDIENTE_OFICIAL\n"
        "  bloquea: [nota_final]\n"
        "  valor: 20\n"
        "  fuente: maestro#10-evaluacion-continua\n",
        encoding="utf-8",
    )
    infracciones = verificar_r3(repo)
    assert len(infracciones) == 1
    assert "valor" in infracciones[0].detalle


def test_r3_pasa_sobre_el_repositorio_real():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r3(raiz)
    assert infracciones == [], "\n".join(i.detalle for i in infracciones)
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_pendiente_oficial.py -v`
Expected: FAIL con `ImportError: cannot import name 'verificar_r3'`

- [ ] **Step 3: Añadir `verificar_r3` a `tools/gobernanza/criterios.py`**

```python
CLAVES_DE_VALOR_PROHIBIDAS = ("valor", "valores", "fechas", "porcentajes")


def _pendientes_documentados(raiz: Path) -> set[str]:
    """Claves listadas en docs/PENDIENTE_OFICIAL.md como '- **clave** —'."""
    ruta = raiz / "docs" / "PENDIENTE_OFICIAL.md"
    if not ruta.is_file():
        return set()
    texto = ruta.read_text(encoding="utf-8")
    return set(re.findall(r"^- \*\*([a-z0-9_]+)\*\* —", texto, re.M))


def verificar_r3(raiz: Path) -> list[Infraccion]:
    """Comprueba que lo pendiente esta marcado, acotado y documentado."""
    documentados = _pendientes_documentados(raiz)
    infracciones: list[Infraccion] = []
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return infracciones

    for ruta in sorted(carpeta.rglob("*.yaml")):
        relativa = ruta.relative_to(raiz).as_posix()
        for entrada in entradas_de(ruta):
            if entrada.get("estado") != "PENDIENTE_OFICIAL":
                continue

            nombre = _identificar(entrada)

            if "bloquea" not in entrada:
                infracciones.append(Infraccion(
                    regla="R3",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' esta PENDIENTE_OFICIAL pero no declara "
                        f"'bloquea'. Indica que juicios no pueden emitirse sin "
                        f"este dato, o '[]' si no bloquea ninguno."
                    ),
                ))

            inventados = [c for c in CLAVES_DE_VALOR_PROHIBIDAS if c in entrada]
            if inventados:
                infracciones.append(Infraccion(
                    regla="R3",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' esta PENDIENTE_OFICIAL pero ya trae "
                        f"{inventados}. Un criterio pendiente no lleva valor: "
                        f"eso es inventarlo. Retira el valor o retira el estado."
                    ),
                ))

            if nombre not in documentados:
                infracciones.append(Infraccion(
                    regla="R3",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' esta PENDIENTE_OFICIAL pero no aparece en "
                        f"docs/PENDIENTE_OFICIAL.md. Anadelo alli con la forma "
                        f"'- **{nombre}** — que falta y de quien se espera.'"
                    ),
                ))

    return infracciones
```

- [ ] **Step 4: Escribir `docs/PENDIENTE_OFICIAL.md`**

Recoge el Anexo H del Maestro. Formato obligatorio de cada entrada: `- **clave** — explicación.`

```markdown
# Pendiente de cierre oficial

Lo que este sistema **no sabe** y **no va a inventar**. Recoge el Anexo H del
Documento Maestro.

Cada entrada de esta lista se corresponde con una clave marcada
`estado: PENDIENTE_OFICIAL` en `criteria/`. Mientras siga aquí, el sistema se
detiene ante cualquier juicio que la necesite, conforme al §18.2 del Maestro.

## Pendientes

- **ponderaciones** — reparto definitivo entre las cuatro entregas y la presentación. El Maestro §10 propone 20 % cada componente como modelo provisional, expresamente configurable hasta validarlo con la programación oficial. Se espera de la programación didáctica.
- **calendario** — fechas de validación del tema, de las cuatro entregas, de recuperación y de defensa. Se espera de la programación didáctica y del centro.
- **rubrica** — criterios oficiales, niveles, mínimos y causas de no superación. Se espera de la programación didáctica.
- **resultados_aprendizaje** — resultados y criterios de evaluación oficiales vinculados al Proyecto Intermodular. Se espera de la normativa del ciclo.
- **defensa** — duración, soporte, composición del tribunal y procedimiento de evaluación de la exposición. Se espera del centro.
- **politica_ia** — política institucional sobre autoría, uso de IA y evidencias admitidas. La Guía y el Índice comentado ya fijan la norma para el alumnado; falta la posición institucional que la respalde.
- **proteccion_datos** — condiciones de tratamiento aplicables y régimen de uso de herramientas externas. Bloquea el piloto con entregas reales.
- **tutorias** — procedimiento de tutorías, correcciones y plazos de respuesta. Se espera del centro.
- **casos_especiales** — reglas para retrasos, cambios de tema y recuperación. Se espera del centro.
- **canal_devolucion** — cómo llega el feedback aprobado al alumno y qué marca exactamente el estado COMUNICADO. Decisión D-004, pendiente del docente.

## Qué hacer cuando llegue uno

1. Se incorpora el dato a la prosa de `docs/maestro/`.
2. Se retira `estado: PENDIENTE_OFICIAL` del YAML y se pone el valor real.
3. Se borra la entrada de esta lista.
4. Se registra en `docs/changes/` y, si cambia una decisión, en `docs/decisions.md`.

El orden importa: primero la prosa, después el YAML.
```

- [ ] **Step 5: Escribir `criteria/v2026-2027/ponderaciones.yaml`**

```yaml
# Reparto de la calificacion. PENDIENTE de la programacion didactica oficial.
# El Maestro propone 20% por componente como modelo provisional; ese numero
# NO se escribe aqui hasta que sea oficial. Ver docs/PENDIENTE_OFICIAL.md.

ponderaciones:
  estado: PENDIENTE_OFICIAL
  bloquea: [nota_final, nota_propuesta]
  componentes: [E1, E2, E3, FINAL, DEFENSA]
  fuente: maestro#10-evaluacion-continua
```

- [ ] **Step 6: Escribir `criteria/v2026-2027/calendario.yaml`**

```yaml
# Fechas del curso. PENDIENTE de la programacion didactica oficial.

calendario:
  estado: PENDIENTE_OFICIAL
  bloquea: [control_de_plazo, entrega_fuera_de_plazo]
  hitos: [TEMA, E1, E2, E3, FINAL, DEFENSA]
  fuente: maestro#14-fuentes-y-criterios
```

- [ ] **Step 7: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/ -v`
Expected: PASS. Atención: `verificar_r1` también se ejecuta sobre los dos YAML nuevos, así que sus anclas deben existir en el Markdown de la Task 2.

- [ ] **Step 8: Commit**

```bash
git add docs/PENDIENTE_OFICIAL.md criteria/ tools/ tests/
git commit -m "feat: R3, lo pendiente se marca, se acota y no se inventa"
```

---

### Task 5: R2 — la prosa manda, y se nota cuando cambia

**Files:**
- Create: `tools/gobernanza/sincronia.py`
- Create: `criteria/v2026-2027/.sincronia.json`
- Test: `tests/gobernanza/test_sincronia.py`

**Interfaces:**
- Consumes: `cargar_anclas`, `entradas_de`, `Infraccion`.
- Produces:
  - `hash_de_seccion(raiz: Path, ancla: str) -> str | None` → SHA-256 (16 primeros caracteres) del texto de la sección, normalizado.
  - `calcular_sincronia(raiz: Path) -> dict[str, str]` → hash de cada ancla referenciada por algún criterio.
  - `verificar_r2(raiz: Path) -> list[Infraccion]`
  - `escribir_sincronia(raiz: Path) -> None` → regenera el fichero tras revisar el derivado.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_sincronia.py`:

```python
import json
from pathlib import Path

import pytest

from tools.gobernanza.sincronia import (
    calcular_sincronia,
    escribir_sincronia,
    hash_de_seccion,
    verificar_r2,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(
        "<!-- ancla: maestro#8-dimensiones -->\n"
        "## 8. Dimensiones\n\n"
        "Doce dimensiones comunes.\n\n"
        "<!-- ancla: maestro#19-privacidad -->\n"
        "## 19. Privacidad\n\n"
        "Codigos anonimos.\n",
        encoding="utf-8",
    )
    criterios = tmp_path / "criteria" / "v2026-2027"
    criterios.mkdir(parents=True)
    (criterios / "dimensiones.yaml").write_text(
        "- codigo: D05\n  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    return tmp_path


def test_hash_de_seccion_solo_cubre_su_propia_seccion(repo: Path):
    h1 = hash_de_seccion(repo, "maestro#8-dimensiones")
    h2 = hash_de_seccion(repo, "maestro#19-privacidad")
    assert h1 and h2 and h1 != h2


def test_hash_ignora_cambios_de_espaciado(repo: Path):
    antes = hash_de_seccion(repo, "maestro#8-dimensiones")
    ruta = repo / "docs" / "maestro" / "01-documento-maestro.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Doce dimensiones comunes.", "Doce   dimensiones   comunes.  "
        ),
        encoding="utf-8",
    )
    assert hash_de_seccion(repo, "maestro#8-dimensiones") == antes


def test_hash_cambia_si_cambia_el_contenido(repo: Path):
    antes = hash_de_seccion(repo, "maestro#8-dimensiones")
    ruta = repo / "docs" / "maestro" / "01-documento-maestro.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Doce dimensiones comunes.", "Trece dimensiones comunes."
        ),
        encoding="utf-8",
    )
    assert hash_de_seccion(repo, "maestro#8-dimensiones") != antes


def test_calcular_sincronia_solo_incluye_anclas_referenciadas(repo: Path):
    calculada = calcular_sincronia(repo)
    assert set(calculada) == {"maestro#8-dimensiones"}


def test_r2_pasa_cuando_el_registro_esta_al_dia(repo: Path):
    escribir_sincronia(repo)
    assert verificar_r2(repo) == []


def test_r2_detecta_que_la_prosa_cambio_sin_revisar_el_derivado(repo: Path):
    escribir_sincronia(repo)
    ruta = repo / "docs" / "maestro" / "01-documento-maestro.md"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace(
            "Doce dimensiones comunes.", "Trece dimensiones comunes."
        ),
        encoding="utf-8",
    )
    infracciones = verificar_r2(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R2"
    assert "maestro#8-dimensiones" in infracciones[0].detalle


def test_r2_avisa_si_falta_el_registro_de_sincronia(repo: Path):
    infracciones = verificar_r2(repo)
    assert len(infracciones) == 1
    assert ".sincronia.json" in infracciones[0].detalle
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_sincronia.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.gobernanza.sincronia'`

- [ ] **Step 3: Escribir la implementación**

Crear `tools/gobernanza/sincronia.py`:

```python
"""R2: la prosa manda. Detecta que una seccion cambio sin revisar su derivado.

El mecanismo es deliberadamente tosco: se guarda el hash del texto de cada
seccion referenciada por algun criterio. Si la prosa cambia, el hash deja de
coincidir y el verificador obliga a mirar el YAML derivado antes de seguir.
No decide si el YAML esta bien: obliga a que alguien lo mire.
"""

import hashlib
import json
import re
from pathlib import Path

from tools.gobernanza.criterios import entradas_de
from tools.gobernanza.resultado import Infraccion

FICHERO_SINCRONIA = "criteria/v2026-2027/.sincronia.json"
PATRON_CUALQUIER_ANCLA = re.compile(r"^<!-- ancla: (?:maestro|indice|guia)#[a-z0-9-]+ -->$", re.M)

_DOCUMENTOS = {
    "maestro": "01-documento-maestro.md",
    "indice": "02-indice-comentado.md",
    "guia": "03-guia-desarrollo.md",
}


def _normalizar(texto: str) -> str:
    """Colapsa espacios para que reformatear no cuente como cambio de criterio."""
    return " ".join(texto.split())


def hash_de_seccion(raiz: Path, ancla: str) -> str | None:
    """SHA-256 abreviado del texto de una seccion, de su ancla a la siguiente."""
    documento, _, _ = ancla.partition("#")
    nombre = _DOCUMENTOS.get(documento)
    if nombre is None:
        return None
    ruta = raiz / "docs" / "maestro" / nombre
    if not ruta.is_file():
        return None

    texto = ruta.read_text(encoding="utf-8")
    marca = f"<!-- ancla: {ancla} -->"
    inicio = texto.find(marca)
    if inicio == -1:
        return None

    resto = texto[inicio + len(marca):]
    siguiente = PATRON_CUALQUIER_ANCLA.search(resto)
    cuerpo = resto[:siguiente.start()] if siguiente else resto

    return hashlib.sha256(_normalizar(cuerpo).encode("utf-8")).hexdigest()[:16]


def _anclas_referenciadas(raiz: Path) -> set[str]:
    """Anclas que algun criterio usa como fuente."""
    referenciadas: set[str] = set()
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return referenciadas
    for ruta in sorted(carpeta.rglob("*.yaml")):
        for entrada in entradas_de(ruta):
            fuente = entrada.get("fuente")
            if isinstance(fuente, str):
                referenciadas.add(fuente)
    return referenciadas


def calcular_sincronia(raiz: Path) -> dict[str, str]:
    """Hash actual de cada ancla referenciada por algun criterio."""
    resultado: dict[str, str] = {}
    for ancla in sorted(_anclas_referenciadas(raiz)):
        h = hash_de_seccion(raiz, ancla)
        if h is not None:
            resultado[ancla] = h
    return resultado


def escribir_sincronia(raiz: Path) -> None:
    """Regenera el registro. Ejecutar solo tras revisar el YAML derivado."""
    ruta = raiz / FICHERO_SINCRONIA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(calcular_sincronia(raiz), indent=2, ensure_ascii=False)
    ruta.write_text(contenido + "\n", encoding="utf-8")


def verificar_r2(raiz: Path) -> list[Infraccion]:
    """Comprueba que ninguna seccion cambio sin revisarse su derivado."""
    ruta = raiz / FICHERO_SINCRONIA
    actual = calcular_sincronia(raiz)

    if not ruta.is_file():
        if not actual:
            return []
        return [Infraccion(
            regla="R2",
            fichero=FICHERO_SINCRONIA,
            detalle=(
                "No existe el registro de sincronia. Generalo con "
                "'python tools/verificar_gobernanza.py --sellar' despues de "
                "comprobar que los criterios reflejan la prosa."
            ),
        )]

    registrado = json.loads(ruta.read_text(encoding="utf-8"))
    infracciones: list[Infraccion] = []

    for ancla, h in sorted(actual.items()):
        anterior = registrado.get(ancla)
        if anterior is None:
            infracciones.append(Infraccion(
                regla="R2",
                fichero=FICHERO_SINCRONIA,
                detalle=(
                    f"'{ancla}' se referencia desde criteria/ pero no esta en el "
                    f"registro. Sella tras revisar el derivado."
                ),
            ))
        elif anterior != h:
            infracciones.append(Infraccion(
                regla="R2",
                fichero=FICHERO_SINCRONIA,
                detalle=(
                    f"La seccion '{ancla}' ha cambiado en docs/maestro/ y su "
                    f"derivado en criteria/ no se ha revisado. Comprueba si el "
                    f"cambio afecta a los criterios que la citan, ajustalos si "
                    f"procede, y sella con '--sellar'."
                ),
            ))

    for ancla in sorted(set(registrado) - set(actual)):
        infracciones.append(Infraccion(
            regla="R2",
            fichero=FICHERO_SINCRONIA,
            detalle=(
                f"'{ancla}' esta en el registro pero ya no la referencia ningun "
                f"criterio. Si era intencionado, sella para limpiarlo."
            ),
        ))

    return infracciones
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_sincronia.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Sellar el registro real**

Run: `python -c "from pathlib import Path; from tools.gobernanza.sincronia import escribir_sincronia; escribir_sincronia(Path('.'))"`
Expected: se crea `criteria/v2026-2027/.sincronia.json` con una entrada por ancla referenciada.

- [ ] **Step 6: Commit**

```bash
git add tools/gobernanza/sincronia.py tests/gobernanza/test_sincronia.py criteria/v2026-2027/.sincronia.json
git commit -m "feat: R2, la prosa manda y su cambio obliga a revisar el derivado"
```

---

### Task 6: R4 — los criterios se versionan y se congelan

**Files:**
- Create: `tools/gobernanza/versiones.py`
- Test: `tests/gobernanza/test_versiones.py`

**Interfaces:**
- Consumes: `Infraccion`.
- Produces:
  - `congelar(raiz: Path, version: str) -> None` → escribe `criteria/<version>/.congelada` con el hash de cada YAML.
  - `verificar_r4(raiz: Path) -> list[Infraccion]`

Una versión se congela cuando se usa por primera vez en una corrección aprobada. A partir de ahí no se modifica: se crea la siguiente.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_versiones.py`:

```python
from pathlib import Path

import pytest

from tools.gobernanza.versiones import congelar, verificar_r4


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    carpeta = tmp_path / "criteria" / "v2026-2027"
    carpeta.mkdir(parents=True)
    (carpeta / "dimensiones.yaml").write_text(
        "- codigo: D05\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    return tmp_path


def test_una_version_sin_congelar_se_puede_cambiar(repo: Path):
    assert verificar_r4(repo) == []
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D06\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    assert verificar_r4(repo) == []


def test_congelar_crea_el_sello(repo: Path):
    congelar(repo, "v2026-2027")
    assert (repo / "criteria" / "v2026-2027" / ".congelada").is_file()


def test_una_version_congelada_intacta_pasa(repo: Path):
    congelar(repo, "v2026-2027")
    assert verificar_r4(repo) == []


def test_r4_rechaza_modificar_una_version_congelada(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").write_text(
        "- codigo: D05\n  nombre: cambiado\n  fuente: maestro#8-dimensiones\n",
        encoding="utf-8",
    )
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R4"
    assert "dimensiones.yaml" in infracciones[0].detalle
    assert "nueva version" in infracciones[0].detalle


def test_r4_rechaza_borrar_un_fichero_de_una_version_congelada(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "dimensiones.yaml").unlink()
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert "ha desaparecido" in infracciones[0].detalle


def test_r4_rechaza_anadir_un_fichero_a_una_version_congelada(repo: Path):
    congelar(repo, "v2026-2027")
    (repo / "criteria" / "v2026-2027" / "nuevo.yaml").write_text(
        "clave:\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    infracciones = verificar_r4(repo)
    assert len(infracciones) == 1
    assert "nuevo.yaml" in infracciones[0].detalle
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_versiones.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.gobernanza.versiones'`

- [ ] **Step 3: Escribir la implementación**

Crear `tools/gobernanza/versiones.py`:

```python
"""R4: los criterios se versionan y se congelan.

Una version que ya se uso en una correccion aprobada no se toca nunca mas.
Esto es lo que permite reconstruir, un ano despues, con que criterio exacto
se corrigio a un alumno concreto. Si hay que cambiar algo, se crea la
version siguiente.
"""

import hashlib
import json
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

SELLO = ".congelada"


def _hash_fichero(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]


def _yaml_de(carpeta: Path) -> dict[str, str]:
    return {r.name: _hash_fichero(r) for r in sorted(carpeta.glob("*.yaml"))}


def congelar(raiz: Path, version: str) -> None:
    """Sella una version de criterios. Operacion deliberadamente irreversible."""
    carpeta = raiz / "criteria" / version
    if not carpeta.is_dir():
        raise FileNotFoundError(f"No existe la version de criterios: {carpeta}")
    contenido = json.dumps(_yaml_de(carpeta), indent=2, ensure_ascii=False)
    (carpeta / SELLO).write_text(contenido + "\n", encoding="utf-8")


def verificar_r4(raiz: Path) -> list[Infraccion]:
    """Comprueba que ninguna version congelada ha sido alterada."""
    infracciones: list[Infraccion] = []
    carpeta_criterios = raiz / "criteria"
    if not carpeta_criterios.is_dir():
        return infracciones

    for carpeta in sorted(p for p in carpeta_criterios.iterdir() if p.is_dir()):
        sello = carpeta / SELLO
        if not sello.is_file():
            continue

        version = carpeta.name
        registrado: dict[str, str] = json.loads(sello.read_text(encoding="utf-8"))
        actual = _yaml_de(carpeta)

        for nombre, h in sorted(registrado.items()):
            relativa = (carpeta / nombre).relative_to(raiz).as_posix()
            if nombre not in actual:
                infracciones.append(Infraccion(
                    regla="R4",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' ha desaparecido de la version congelada "
                        f"{version}. Una version usada en correcciones aprobadas "
                        f"no se altera. Restaura el fichero y crea una nueva "
                        f"version si necesitas cambiar algo."
                    ),
                ))
            elif actual[nombre] != h:
                infracciones.append(Infraccion(
                    regla="R4",
                    fichero=relativa,
                    detalle=(
                        f"'{nombre}' ha cambiado, pero la version {version} esta "
                        f"congelada. Deshaz el cambio y crea una nueva version: "
                        f"copia criteria/{version}/ a la siguiente, modifica alli "
                        f"y registra el cambio en docs/changes/."
                    ),
                ))

        for nombre in sorted(set(actual) - set(registrado)):
            relativa = (carpeta / nombre).relative_to(raiz).as_posix()
            infracciones.append(Infraccion(
                regla="R4",
                fichero=relativa,
                detalle=(
                    f"'{nombre}' se ha anadido a la version congelada {version}. "
                    f"Un criterio nuevo va en una version nueva, no en una "
                    f"cerrada."
                ),
            ))

    return infracciones
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_versiones.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

No se congela `v2026-2027` todavía: aún no se ha usado en ninguna corrección y quedan criterios pendientes por incorporar.

```bash
git add tools/gobernanza/versiones.py tests/gobernanza/test_versiones.py
git commit -m "feat: R4, congelacion de versiones de criterios ya utilizadas"
```

---

### Task 7: R5 — un fichero por cambio

**Files:**
- Create: `tools/gobernanza/cambios.py`
- Create: `docs/changes/PLANTILLA.md`
- Create: `docs/changes/2026-08-26-fundacion-repo.md`
- Test: `tests/gobernanza/test_cambios.py`

**Interfaces:**
- Consumes: `Infraccion`.
- Produces:
  - `verificar_formato_cambios(raiz: Path) -> list[Infraccion]` → todo fichero de `docs/changes/` cumple nombre y secciones.
  - `verificar_cambio_acompanado(raiz: Path, ficheros_tocados: list[str]) -> list[Infraccion]` → si se tocan criterios, hay un documento de cambio nuevo. La usa el hook con la salida de `git diff --cached --name-only`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_cambios.py`:

```python
from pathlib import Path

import pytest

from tools.gobernanza.cambios import (
    verificar_cambio_acompanado,
    verificar_formato_cambios,
)

CAMBIO_VALIDO = """# Minimo de paginas de 20 a 25

**Fecha:** 2026-09-15
**Autor:** Marcos

## Que cambia

El minimo de contenido pasa de 20 a 25 paginas.

## Por que

## Fuente que lo respalda

Programacion didactica 2026-2027, apartado 4.2.

## Que arrastra

- `docs/maestro/03-guia-desarrollo.md`
- `criteria/v2026-2027/formato.yaml`

## Correcciones cerradas afectadas

Ninguna.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "changes").mkdir(parents=True)
    (tmp_path / "criteria" / "v2026-2027").mkdir(parents=True)
    return tmp_path


def test_acepta_un_documento_de_cambio_completo(repo: Path):
    (repo / "docs" / "changes" / "2026-09-15-minimo-paginas.md").write_text(
        CAMBIO_VALIDO, encoding="utf-8"
    )
    assert verificar_formato_cambios(repo) == []


def test_rechaza_un_nombre_de_fichero_sin_fecha(repo: Path):
    (repo / "docs" / "changes" / "minimo-paginas.md").write_text(
        CAMBIO_VALIDO, encoding="utf-8"
    )
    infracciones = verificar_formato_cambios(repo)
    assert len(infracciones) == 1
    assert "AAAA-MM-DD" in infracciones[0].detalle


def test_rechaza_un_documento_al_que_le_falta_una_seccion(repo: Path):
    incompleto = CAMBIO_VALIDO.replace("## Fuente que lo respalda", "## Otra cosa")
    (repo / "docs" / "changes" / "2026-09-15-minimo-paginas.md").write_text(
        incompleto, encoding="utf-8"
    )
    infracciones = verificar_formato_cambios(repo)
    assert len(infracciones) == 1
    assert "Fuente que lo respalda" in infracciones[0].detalle


def test_la_plantilla_no_se_valida_como_cambio(repo: Path):
    (repo / "docs" / "changes" / "PLANTILLA.md").write_text("# Plantilla\n", encoding="utf-8")
    assert verificar_formato_cambios(repo) == []


def test_tocar_criterios_sin_documentar_el_cambio_es_infraccion(repo: Path):
    tocados = ["criteria/v2026-2027/formato.yaml"]
    infracciones = verificar_cambio_acompanado(repo, tocados)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R5"
    assert "docs/changes/" in infracciones[0].detalle


def test_tocar_criterios_con_su_documento_de_cambio_pasa(repo: Path):
    tocados = [
        "criteria/v2026-2027/formato.yaml",
        "docs/changes/2026-09-15-minimo-paginas.md",
    ]
    assert verificar_cambio_acompanado(repo, tocados) == []


def test_tocar_solo_codigo_no_exige_documento_de_cambio(repo: Path):
    tocados = ["tools/gobernanza/criterios.py", "tests/gobernanza/test_criterios.py"]
    assert verificar_cambio_acompanado(repo, tocados) == []


def test_tocar_la_prosa_maestra_tambien_exige_documento_de_cambio(repo: Path):
    tocados = ["docs/maestro/01-documento-maestro.md"]
    infracciones = verificar_cambio_acompanado(repo, tocados)
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R5"
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_cambios.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.gobernanza.cambios'`

- [ ] **Step 3: Escribir la implementación**

Crear `tools/gobernanza/cambios.py`:

```python
"""R5: un fichero por cambio.

Todo cambio de criterio deja constancia de que cambia, por que, con que
respaldo y a que afecta. No es burocracia: es lo que permite defender una
nota meses despues de haberla puesto.
"""

import re
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

CARPETA = "docs/changes"
PLANTILLA = "PLANTILLA.md"
PATRON_NOMBRE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")

SECCIONES_OBLIGATORIAS = (
    "Que cambia",
    "Por que",
    "Fuente que lo respalda",
    "Que arrastra",
    "Correcciones cerradas afectadas",
)

# Tocar cualquiera de estos exige documentar el cambio.
PREFIJOS_VIGILADOS = ("criteria/", "docs/maestro/")


def verificar_formato_cambios(raiz: Path) -> list[Infraccion]:
    """Comprueba nombre y secciones de cada documento de cambio."""
    infracciones: list[Infraccion] = []
    carpeta = raiz / CARPETA
    if not carpeta.is_dir():
        return infracciones

    for ruta in sorted(carpeta.glob("*.md")):
        if ruta.name == PLANTILLA:
            continue
        relativa = ruta.relative_to(raiz).as_posix()

        if not PATRON_NOMBRE.match(ruta.name):
            infracciones.append(Infraccion(
                regla="R5",
                fichero=relativa,
                detalle=(
                    f"'{ruta.name}' no sigue el formato AAAA-MM-DD-asunto.md. "
                    f"La fecha en el nombre permite ordenar los cambios sin "
                    f"abrirlos."
                ),
            ))
            continue

        texto = ruta.read_text(encoding="utf-8")
        for seccion in SECCIONES_OBLIGATORIAS:
            if f"## {seccion}" not in texto:
                infracciones.append(Infraccion(
                    regla="R5",
                    fichero=relativa,
                    detalle=(
                        f"Falta la seccion '## {seccion}'. Copia "
                        f"{CARPETA}/{PLANTILLA} y rellenala entera."
                    ),
                ))

    return infracciones


def verificar_cambio_acompanado(raiz: Path, ficheros_tocados: list[str]) -> list[Infraccion]:
    """Si el commit toca criterios o prosa maestra, exige documento de cambio."""
    tocados = [f.replace("\\", "/") for f in ficheros_tocados]

    vigilados = [f for f in tocados if f.startswith(PREFIJOS_VIGILADOS)]
    if not vigilados:
        return []

    hay_documento = any(
        f.startswith(f"{CARPETA}/") and not f.endswith(PLANTILLA) for f in tocados
    )
    if hay_documento:
        return []

    return [Infraccion(
        regla="R5",
        fichero=vigilados[0],
        detalle=(
            f"Este commit toca {len(vigilados)} fichero(s) de criterios o de "
            f"prosa maestra sin documentar el cambio. Crea "
            f"{CARPETA}/AAAA-MM-DD-asunto.md a partir de la plantilla."
        ),
    )]
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_cambios.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Escribir `docs/changes/PLANTILLA.md`**

```markdown
# [Título del cambio en una línea]

**Fecha:** AAAA-MM-DD
**Autor:**

## Que cambia

Qué era antes y qué es ahora. Concreto y verificable.

## Por que

Qué problema resuelve o qué instrucción lo obliga.

## Fuente que lo respalda

La fuente de la jerarquía del §14.1 que lo autoriza: programación didáctica,
instrucción del centro, acuerdo interno documentado. Si no hay ninguna, este
cambio no debería hacerse.

## Que arrastra

Ficheros que se tocan. Prosa primero, YAML después.

## Correcciones cerradas afectadas

Correcciones ya aprobadas que se hicieron con el criterio anterior. Si hay
alguna, indicar si se revisan o si se mantienen tal cual y por qué.
```

- [ ] **Step 6: Escribir `docs/changes/2026-08-26-fundacion-repo.md`**

```markdown
# Fundación del repositorio y de la capa de gobernanza

**Fecha:** 2026-08-26
**Autor:** Marcos / colaborador técnico

## Que cambia

El sistema pasa de existir como tres documentos PDF sueltos a tener un
repositorio con la prosa normativa en Markdown, su destilado ejecutable en
YAML y un verificador que comprueba las reglas R1 a R6.

Desde hoy, `docs/maestro/` es la fuente de verdad. Los PDF originales pasan a
ser copia histórica.

## Por que

Los tres documentos se solapan a propósito y ninguno era la fuente de verdad
de los otros. Un criterio podía cambiar en la Guía y no en el Maestro, y el
sistema habría acabado corrigiendo con un criterio que ya no era el del
docente. El §1 del Maestro plantea exactamente ese riesgo.

## Fuente que lo respalda

Documento Maestro §14.1, jerarquía de fuentes y regla de conflicto.

## Que arrastra

- `docs/maestro/01-documento-maestro.md`
- `docs/maestro/02-indice-comentado.md`
- `docs/maestro/03-guia-desarrollo.md`
- `criteria/v2026-2027/` completo
- `docs/PENDIENTE_OFICIAL.md`
- `docs/decisions.md`
- `tools/gobernanza/`

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema.

## Interpretación registrada

La dimensión D05 (fundamentación y fuentes) se activa desde la segunda
entrega, no desde la primera. El §9.2 no exige bibliografía completa en E1,
solo "primeras fuentes o datos que permitan investigar", y esa comprobación la
cubre D02, que observa la evidencia de partida. Si el criterio del docente es
otro, se corrige en `criteria/v2026-2027/dimensiones.yaml` con su documento de
cambio.
```

- [ ] **Step 7: Ejecutar toda la batería**

Run: `python -m pytest tests/ -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/gobernanza/cambios.py tests/gobernanza/test_cambios.py docs/changes/
git commit -m "feat: R5, todo cambio de criterio deja constancia"
```

---

### Task 8: R6 — nada personal entra en el repositorio

**Files:**
- Create: `tools/gobernanza/privacidad.py`
- Test: `tests/gobernanza/test_privacidad.py`

**Interfaces:**
- Consumes: `Infraccion`.
- Produces: `verificar_r6(raiz: Path, ficheros: list[str]) -> list[Infraccion]`. Si `ficheros` viene vacío, recorre el árbol de trabajo; el hook le pasa los ficheros en staging.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_privacidad.py`:

```python
from pathlib import Path

import pytest

from tools.gobernanza.privacidad import verificar_r6


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    return tmp_path


def test_un_repositorio_limpio_pasa(repo: Path):
    (repo / "docs" / "notas.md").write_text("Sin datos personales.\n", encoding="utf-8")
    assert verificar_r6(repo, ["docs/notas.md"]) == []


def test_rechaza_un_pdf(repo: Path):
    (repo / "entrega.pdf").write_bytes(b"%PDF-1.7\n")
    infracciones = verificar_r6(repo, ["entrega.pdf"])
    assert len(infracciones) == 1
    assert infracciones[0].regla == "R6"
    assert "entrega.pdf" in infracciones[0].fichero


def test_rechaza_un_documento_de_word(repo: Path):
    (repo / "trabajo.docx").write_bytes(b"PK\x03\x04")
    infracciones = verificar_r6(repo, ["trabajo.docx"])
    assert len(infracciones) == 1


def test_detecta_un_dni_espanol(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Alumno con DNI 12345678Z matriculado.\n", encoding="utf-8"
    )
    infracciones = verificar_r6(repo, ["docs/ficha.md"])
    assert len(infracciones) == 1
    assert "DNI" in infracciones[0].detalle


def test_detecta_un_correo_electronico(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Contacto: alumno.ejemplo@centro.es\n", encoding="utf-8"
    )
    infracciones = verificar_r6(repo, ["docs/ficha.md"])
    assert len(infracciones) == 1
    assert "correo" in infracciones[0].detalle


def test_detecta_un_telefono_espanol(repo: Path):
    (repo / "docs" / "ficha.md").write_text("Telefono 612345678\n", encoding="utf-8")
    infracciones = verificar_r6(repo, ["docs/ficha.md"])
    assert len(infracciones) == 1
    assert "telefono" in infracciones[0].detalle


def test_no_confunde_un_codigo_anonimo_con_un_dato_personal(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Codigo de alumno AF023, ciclo Marketing, fase E2.\n", encoding="utf-8"
    )
    assert verificar_r6(repo, ["docs/ficha.md"]) == []


def test_no_confunde_una_fecha_con_un_telefono(repo: Path):
    (repo / "docs" / "ficha.md").write_text(
        "Version 2026-08-26, hash 16 caracteres.\n", encoding="utf-8"
    )
    assert verificar_r6(repo, ["docs/ficha.md"]) == []


def test_los_planes_y_specs_estan_exentos(repo: Path):
    ruta = repo / "docs" / "superpowers" / "plans"
    ruta.mkdir(parents=True)
    (ruta / "plan.md").write_text(
        "Ejemplo de deteccion: DNI 12345678Z y correo alumno@centro.es\n",
        encoding="utf-8",
    )
    assert verificar_r6(repo, ["docs/superpowers/plans/plan.md"]) == []


def test_el_repositorio_real_esta_limpio():
    raiz = Path(__file__).resolve().parents[2]
    infracciones = verificar_r6(raiz, [])
    assert infracciones == [], "\n".join(
        f"{i.fichero}: {i.detalle}" for i in infracciones
    )
```

La exención de `docs/superpowers/` no es una concesión: planes y specs contienen ejemplos de DNI y correo precisamente para documentar qué se detecta. Sin la exención, el verificador se denunciaría a sí mismo.

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_privacidad.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.gobernanza.privacidad'`

- [ ] **Step 3: Escribir la implementación**

Crear `tools/gobernanza/privacidad.py`:

```python
"""R6: nada personal entra en el repositorio.

Es un cedazo, no una garantia. Atrapa el descuido tipico -arrastrar una
entrega, pegar una ficha con datos- y no pretende sustituir el criterio de
quien commitea.
"""

import re
from pathlib import Path

from tools.gobernanza.resultado import Infraccion

EXTENSIONES_PROHIBIDAS = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".pptx"}

CARPETAS_IGNORADAS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "dist",
}

# Solo se inspecciona el contenido de texto plano.
EXTENSIONES_DE_TEXTO = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".ts", ".tsx", ".sql"}

# El DNI espanol lleva 8 digitos y una letra de control; se exige limite de
# palabra a ambos lados para no capturar hashes ni identificadores largos.
PATRON_DNI = re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b")
PATRON_CORREO = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
# Movil o fijo espanol: empieza por 6, 7, 8 o 9 y tiene nueve digitos.
PATRON_TELEFONO = re.compile(r"(?<![\d-])[6789]\d{8}(?![\d-])")

# Ficheros y arboles que hablan de estos patrones sin contener datos reales:
# el propio verificador, sus tests, y los planes y specs, que incluyen
# ejemplos de DNI y correo precisamente para explicar que se detecta.
EXENTOS = {
    "tools/gobernanza/privacidad.py",
    "tests/gobernanza/test_privacidad.py",
}
PREFIJOS_EXENTOS = ("docs/superpowers/",)


def _esta_exento(relativa: str) -> bool:
    return relativa in EXENTOS or relativa.startswith(PREFIJOS_EXENTOS)


def _candidatos(raiz: Path) -> list[str]:
    """Todos los ficheros del arbol, ignorando carpetas de trabajo."""
    encontrados: list[str] = []
    for ruta in raiz.rglob("*"):
        if not ruta.is_file():
            continue
        if any(parte in CARPETAS_IGNORADAS for parte in ruta.parts):
            continue
        encontrados.append(ruta.relative_to(raiz).as_posix())
    return sorted(encontrados)


def verificar_r6(raiz: Path, ficheros: list[str]) -> list[Infraccion]:
    """Busca documentos ofimaticos y datos identificativos en los ficheros dados."""
    objetivos = [f.replace("\\", "/") for f in ficheros] or _candidatos(raiz)
    infracciones: list[Infraccion] = []

    for relativa in objetivos:
        if _esta_exento(relativa):
            continue
        ruta = raiz / relativa
        if not ruta.is_file():
            continue

        sufijo = ruta.suffix.lower()

        if sufijo in EXTENSIONES_PROHIBIDAS:
            infracciones.append(Infraccion(
                regla="R6",
                fichero=relativa,
                detalle=(
                    f"Documento ofimatico en el repositorio. Las entregas de "
                    f"alumnos no se versionan. Sacalo del repositorio y, si "
                    f"llego a commitearse, limpia el historial."
                ),
            ))
            continue

        if sufijo not in EXTENSIONES_DE_TEXTO:
            continue

        try:
            texto = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for patron, etiqueta in (
            (PATRON_DNI, "un DNI"),
            (PATRON_CORREO, "un correo electronico"),
            (PATRON_TELEFONO, "un telefono"),
        ):
            encontrado = patron.search(texto)
            if encontrado:
                linea = texto[:encontrado.start()].count("\n") + 1
                infracciones.append(Infraccion(
                    regla="R6",
                    fichero=relativa,
                    detalle=(
                        f"Linea {linea}: parece {etiqueta}. El sistema trabaja "
                        f"con codigos anonimos de alumno. Si es un dato real, "
                        f"retiralo; si es un ejemplo, usa un codigo tipo AF023."
                    ),
                ))

    return infracciones
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_privacidad.py -v`
Expected: PASS, 10 tests.

Si `test_el_repositorio_real_esta_limpio` falla por un correo en algún fichero de configuración, añadir ese fichero a `EXENTOS` **solo** si el correo es el del propio docente o del colaborador, nunca el de un alumno.

- [ ] **Step 5: Commit**

```bash
git add tools/gobernanza/privacidad.py tests/gobernanza/test_privacidad.py
git commit -m "feat: R6, cedazo de datos personales y documentos ofimaticos"
```

---

### Task 9: La CLI, el hook y los documentos de gobernanza

**Files:**
- Create: `tools/verificar_gobernanza.py`
- Create: `tools/instalar_hooks.py`
- Create: `GOVERNANCE.md`
- Create: `CLAUDE.md`
- Create: `docs/decisions.md`
- Test: `tests/gobernanza/test_cli.py`

**Interfaces:**
- Consumes: `verificar_r1`, `verificar_r3`, `verificar_r2`, `verificar_r4`, `verificar_formato_cambios`, `verificar_cambio_acompanado`, `verificar_r6`, `formatear`, `escribir_sincronia`.
- Produces: `ejecutar(raiz: Path, ficheros: list[str], solo_staged: bool) -> list[Infraccion]` y un `main()` con códigos de salida 0 (conforme) y 1 (infracciones).

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/gobernanza/test_cli.py`:

```python
from pathlib import Path

import pytest

from tools.verificar_gobernanza import ejecutar


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(
        "<!-- ancla: maestro#8-dimensiones -->\n## 8. Dimensiones\n\nTexto.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "changes").mkdir()
    (tmp_path / "docs" / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente\n", encoding="utf-8"
    )
    criterios = tmp_path / "criteria" / "v2026-2027"
    criterios.mkdir(parents=True)
    (criterios / "dimensiones.yaml").write_text(
        "- codigo: D05\n  fuente: maestro#8-dimensiones\n", encoding="utf-8"
    )
    from tools.gobernanza.sincronia import escribir_sincronia
    escribir_sincronia(tmp_path)
    return tmp_path


def test_un_repositorio_conforme_no_devuelve_infracciones(repo: Path):
    assert ejecutar(repo, ficheros=[], solo_staged=False) == []


def test_agrega_infracciones_de_varias_reglas(repo: Path):
    # R1: criterio sin fuente.
    (repo / "criteria" / "v2026-2027" / "roto.yaml").write_text(
        "- codigo: D99\n  nombre: sin fuente\n", encoding="utf-8"
    )
    # R6: dato personal.
    (repo / "docs" / "ficha.md").write_text("DNI 12345678Z\n", encoding="utf-8")

    infracciones = ejecutar(repo, ficheros=[], solo_staged=False)
    reglas = {i.regla for i in infracciones}
    assert "R1" in reglas
    assert "R6" in reglas


def test_r5_solo_se_evalua_sobre_los_ficheros_indicados(repo: Path):
    # Sin lista de ficheros, R5 no puede saber que se esta commiteando.
    assert not [i for i in ejecutar(repo, [], False) if i.regla == "R5"]
    # Con lista, si.
    infracciones = ejecutar(
        repo, ficheros=["criteria/v2026-2027/dimensiones.yaml"], solo_staged=False
    )
    assert [i for i in infracciones if i.regla == "R5"]
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/gobernanza/test_cli.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.verificar_gobernanza'`

- [ ] **Step 3: Escribir la CLI**

Crear `tools/verificar_gobernanza.py`:

```python
"""Verificador de gobernanza del repositorio.

    python tools/verificar_gobernanza.py              todo el arbol
    python tools/verificar_gobernanza.py --staged     solo lo que se va a commitear
    python tools/verificar_gobernanza.py --sellar     regenera el registro de R2

Codigos de salida: 0 conforme, 1 hay infracciones.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from tools.gobernanza.cambios import (
    verificar_cambio_acompanado,
    verificar_formato_cambios,
)
from tools.gobernanza.criterios import verificar_r1, verificar_r3
from tools.gobernanza.privacidad import verificar_r6
from tools.gobernanza.resultado import Infraccion, formatear
from tools.gobernanza.sincronia import escribir_sincronia, verificar_r2
from tools.gobernanza.versiones import verificar_r4


def ficheros_en_staging(raiz: Path) -> list[str]:
    """Ficheros que el proximo commit incluira."""
    salida = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=True,
    )
    return [linea for linea in salida.stdout.splitlines() if linea.strip()]


def ejecutar(raiz: Path, ficheros: list[str], solo_staged: bool) -> list[Infraccion]:
    """Ejecuta las seis reglas mecanizables y devuelve todas las infracciones."""
    objetivos = ficheros_en_staging(raiz) if solo_staged else list(ficheros)

    infracciones: list[Infraccion] = []
    infracciones += verificar_r1(raiz)
    infracciones += verificar_r2(raiz)
    infracciones += verificar_r3(raiz)
    infracciones += verificar_r4(raiz)
    infracciones += verificar_formato_cambios(raiz)
    infracciones += verificar_r6(raiz, objetivos)

    # R5 solo tiene sentido sobre un conjunto concreto de ficheros: sin saber
    # que se esta commiteando, no se puede exigir que lo acompane un cambio.
    if objetivos:
        infracciones += verificar_cambio_acompanado(raiz, objetivos)

    return infracciones


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de gobernanza.")
    parser.add_argument("--staged", action="store_true",
                        help="verificar solo los ficheros en staging")
    parser.add_argument("--sellar", action="store_true",
                        help="regenerar el registro de sincronia de R2")
    args = parser.parse_args()

    raiz = Path(__file__).resolve().parents[1]

    if args.sellar:
        escribir_sincronia(raiz)
        print("Registro de sincronia regenerado.")
        print("Hazlo solo despues de comprobar que los criterios reflejan la prosa.")
        return 0

    infracciones = ejecutar(raiz, ficheros=[], solo_staged=args.staged)
    print(formatear(infracciones))
    return 1 if infracciones else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/gobernanza/test_cli.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Escribir el instalador del hook**

Crear `tools/instalar_hooks.py`:

```python
"""Instala el hook de pre-commit que ejecuta el verificador de gobernanza."""

import stat
import sys
from pathlib import Path

HOOK = """#!/bin/sh
# Verificador de gobernanza. Instalado por tools/instalar_hooks.py
python tools/verificar_gobernanza.py --staged
estado=$?
if [ $estado -ne 0 ]; then
    echo ""
    echo "Commit detenido: hay infracciones de gobernanza."
    echo "Corrigelas, o usa 'git commit --no-verify' si sabes lo que haces."
    exit 1
fi
exit 0
"""


def main() -> int:
    raiz = Path(__file__).resolve().parents[1]
    carpeta = raiz / ".git" / "hooks"
    if not carpeta.is_dir():
        print(f"No encuentro {carpeta}. ¿Estas en un repositorio git?")
        return 1

    ruta = carpeta / "pre-commit"
    ruta.write_text(HOOK, encoding="utf-8", newline="\n")
    ruta.chmod(ruta.stat().st_mode | stat.S_IEXEC)
    print(f"Hook instalado en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Instalar el hook y comprobar que funciona**

Run: `python tools/instalar_hooks.py`
Expected: `Hook instalado en ...`

Comprobación real de que muerde:

```bash
echo "DNI 12345678Z" > docs/prueba-hook.md
git add docs/prueba-hook.md
git commit -m "prueba"    # debe FALLAR con una infraccion R6
git reset HEAD docs/prueba-hook.md
rm docs/prueba-hook.md
```

Expected: el commit se rechaza citando R6 y `docs/prueba-hook.md`.

- [ ] **Step 7: Escribir `docs/decisions.md`**

```markdown
# Registro de decisiones

Por qué el sistema es como es. Formato del Anexo G del Documento Maestro.

Una decisión entra aquí cuando condiciona la arquitectura, contradice una
fuente superior o no puede deducirse leyendo el código. Los ajustes ordinarios
de criterio van a `docs/changes/`, no aquí.

**Estados:** `Provisional` (adoptada, revisable) · `Validada` (confirmada por el
docente) · `Pendiente` (identificada, sin resolver) · `Revertida`.

---

## D-001 · Supabase como persistencia, en lugar de sistema estrictamente local

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

El Documento Maestro §19 y §21.1 especifican un sistema estrictamente local.
Se adopta Supabase para persistencia, historial y trazabilidad.

**La contradicción es consciente y obliga a corregir el §19 y el §21.1**, no a
ignorarlos. Motivo: una aplicación puramente local no da historial consultable
ni acceso desde varios equipos, y el docente ya trabaja con este stack.

Alcance acotado:

- **Se almacena:** fichas, criterios versionados, correcciones por dimensión,
  evidencias citadas, semáforo, nota interna, feedback aprobado y auditoría.
- **No se almacena:** el PDF de la entrega ni el texto completo del trabajo.
- Evidencia citada: referencia a apartado y página más un fragmento de 1.500
  caracteres como máximo, verificado en el backend.

**Arrastra:** corrección pendiente del §19 y §21.1 del Documento Maestro.

## D-002 · OpenAI como proveedor de análisis, tras adaptador intercambiable

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

El análisis académico lo realiza la API de OpenAI. El backend define un puerto
`ProveedorAnalisis` con implementaciones sustituibles.

Circuito de datos, a efectos de arquitectura: el texto de la entrega, ya
anonimizado, se transmite al proveedor durante el procesamiento. No se
almacena allí ni en Supabase. Quien mantenga el sistema debe conocerlo para no
alterar el circuito por descuido.

La clave de la API reside únicamente en el backend local, nunca en el frontend.

## D-003 · PyMuPDF para la extracción

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

Es la herramienta más capaz para las comprobaciones objetivas del §6.2 y de la
lista de control del Índice comentado: tipografía y cuerpo por fragmento,
interlineado real, páginas en blanco, correspondencia del índice, resolución y
superficie de las imágenes, origen del PDF.

**Limitación:** licencia AGPL. Sin restricción para uso interno. Una eventual
distribución exigiría licencia comercial o migrar a pdfplumber.

## D-004 · Canal de devolución del feedback

**Fecha:** 2026-08-26 · **Estado:** Pendiente · **Responsable:** Marcos

No está definido cómo llega el feedback aprobado al alumno ni qué marca
exactamente el estado `COMUNICADO`. Hasta cerrarla, ese estado se modela pero
no se activa.

**Bloquea:** la transición a `COMUNICADO`.

## D-005 · La prosa manda sobre el destilado

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

Los criterios ejecutables de `criteria/` se derivan de `docs/maestro/`, nunca
al revés. Un criterio sin fuente trazable no existe.

Se descartó que el motor leyera la prosa directamente: impedía validar la
existencia de un criterio, versionar ponderaciones y medir la calibración
del §20.

**Arrastra:** reglas R1 y R2 de `GOVERNANCE.md`.
```

- [ ] **Step 8: Escribir `GOVERNANCE.md`**

```markdown
# Gobernanza del repositorio

Este sistema decide sobre el trabajo de personas. Estas reglas existen para
que, dentro de un año, se pueda reconstruir con qué criterio exacto se corrigió
a un alumno y de dónde salía ese criterio.

La regla madre está en el §14.1 del Documento Maestro: **una fuente inferior no
puede contradecir a una superior.** Todo lo demás es maquinaria para que se
cumpla sin depender de la memoria de nadie.

## Jerarquía de fuentes

1. Programación didáctica y rúbrica oficial vigente
2. Instrucciones formales de CESUR, centro o coordinación
3. Acuerdos internos documentados y fechados
4. Documento Maestro, guía de desarrollo e índice comentado
5. Manual docente, banco de feedback y casos calibrados
6. Precedentes del curso anterior

Si dos criterios vigentes chocan, el sistema **detiene ese juicio** y crea una
alerta. No elige.

## Las siete reglas

**R1 · Ningún criterio sin origen.** Toda entrada de `criteria/` declara
`fuente: documento#ancla` apuntando a una sección real de `docs/maestro/`.
*Verificada.*

**R2 · La prosa manda.** El YAML se deriva del Markdown, nunca al revés. Si una
sección cambia, hay que revisar su derivado y sellar con `--sellar`.
*Verificada.*

**R3 · Lo pendiente se marca, no se inventa.** `estado: PENDIENTE_OFICIAL`, con
`bloquea` y entrada en `docs/PENDIENTE_OFICIAL.md`. Un criterio pendiente no
lleva valor. *Verificada.*

**R4 · Los criterios se versionan y se congelan.** Una versión usada en una
corrección aprobada no se modifica: se crea la siguiente. *Verificada.*

**R5 · Un fichero por cambio.** Tocar `criteria/` o `docs/maestro/` exige un
documento en `docs/changes/`. *Verificada.*

**R6 · Nada personal entra en el repositorio.** Ni entregas, ni nombres, ni
datos identificativos. *Verificada.*

**R7 · Las reservas del profesor son bloqueos reales.** Las nueve decisiones
del §13 del Maestro se implementan como estados que el backend no atraviesa
solo. *Pendiente: se implementa con el backend.*

## Cómo se cambia un criterio

```
1. Editar   docs/maestro/<documento>.md          la prosa
2. Ajustar  criteria/vAAAA-AAAA/<fichero>.yaml   el derivado
3. Escribir docs/changes/AAAA-MM-DD-<asunto>.md
4. Anotar   docs/decisions.md                    si es decisión, no ajuste
5. Ejecutar python tools/verificar_gobernanza.py --sellar
6. Commit
```

El orden importa. Editar el YAML primero es exactamente lo que R2 impide.

## Puesta en marcha

```
python -m pip install -r requirements-dev.txt
python tools/instalar_hooks.py
python -m pytest
python tools/verificar_gobernanza.py
```

El hook se salta con `git commit --no-verify`. Existe para emergencias reales.
Saltárselo por prisa deja el repositorio en un estado que nadie sabrá
interpretar después.
```

- [ ] **Step 9: Escribir `CLAUDE.md`**

```markdown
# Instrucciones para el agente

Sistema de corrección de Proyectos Intermodulares. Antes de tocar nada, lee
`GOVERNANCE.md`.

## Lo que no se hace nunca

- **No inventes un criterio.** Si un dato no está en `docs/maestro/` ni en una
  fuente oficial, va a `docs/PENDIENTE_OFICIAL.md` con `estado:
  PENDIENTE_OFICIAL`. Nunca se rellena con un valor razonable.
- **No edites `criteria/` sin editar antes `docs/maestro/`.** El YAML es un
  derivado. Al revés rompe R2.
- **No toques una versión de criterios congelada.** Se crea la siguiente.
- **No metas datos de alumnos.** Ni PDFs, ni nombres, ni ejemplos con datos
  reales. Los ejemplos usan códigos tipo `AF023`.
- **No reescribas la prosa del docente.** Los documentos de `docs/maestro/` son
  normativos. Se corrigen cuando él lo pide, con su documento de cambio; no se
  "mejoran" de oficio.
- **No implementes que el sistema decida algo del §13.** Aprobar nota, valorar
  autoría, autorizar cambio de tema, dar por apto un documento, comunicar
  feedback: el sistema propone y se detiene.

## Antes de dar por terminado un cambio

```
python -m pytest
python tools/verificar_gobernanza.py
```

Ambos en verde, o el trabajo no está terminado. No anuncies que algo funciona
sin haber visto la salida.

## Idioma

Todo en castellano: identificadores, comentarios, mensajes de error,
documentación y commits. Los mensajes de infracción los lee el docente, no un
programador: han de decir qué pasa y qué hacer, sin jerga.

## Estructura

| Ruta | Qué es |
|---|---|
| `docs/maestro/` | La fuente de verdad. Prosa normativa. |
| `criteria/` | Destilado ejecutable. Derivado, nunca original. |
| `docs/decisions.md` | Por qué el sistema es como es. |
| `docs/PENDIENTE_OFICIAL.md` | Lo que no se sabe y no se inventa. |
| `docs/changes/` | Un fichero por cambio de criterio. |
| `tools/gobernanza/` | Un módulo por regla. |
```

- [ ] **Step 10: Ejecutar la verificación completa**

Run: `python -m pytest && python tools/verificar_gobernanza.py`
Expected: todos los tests en verde y `Gobernanza conforme: 0 infracciones.`

- [ ] **Step 11: Commit**

```bash
git add tools/verificar_gobernanza.py tools/instalar_hooks.py tests/gobernanza/test_cli.py GOVERNANCE.md CLAUDE.md docs/decisions.md
git commit -m "feat: CLI de gobernanza, hook de pre-commit y documentos de reglas"
```

- [ ] **Step 12: Corregir el Documento Maestro conforme a D-001**

D-001 obliga a que el §19 y el §21.1 dejen de decir "sistema local". Editar
`docs/maestro/01-documento-maestro.md`:

En el §19, sustituir la viñeta que remite a un sistema estrictamente local y
añadir el circuito real. Texto a insertar al principio del §19, tras el
encabezado:

```markdown
> **Modificado por D-001 el 2026-08-26.** La versión original de este apartado
> presuponía un sistema estrictamente local. La arquitectura acordada es otra y
> se describe aquí.

Circuito de datos del sistema:

- La ficha del alumno, los criterios versionados, la corrección por
  dimensiones, las evidencias citadas, el semáforo, la nota interna, el
  feedback aprobado y el registro de auditoría se almacenan en Supabase.
- El PDF de la entrega y el texto completo del trabajo **no se almacenan**: ni
  en Supabase, ni en el repositorio.
- Una evidencia citada es la referencia al apartado y la página más un
  fragmento literal de 1.500 caracteres como máximo. El límite lo verifica el
  backend e impide que la suma de evidencias reconstruya el trabajo.
- Durante el análisis, el texto de la entrega, ya anonimizado, se transmite al
  proveedor de análisis. No se almacena allí.
- Las credenciales técnicas residen en el backend local, nunca en el frontend.
```

En el §21.1, sustituir la línea `Aplicación mínima local` por:

```markdown
- Aplicación con interfaz web local, backend en el equipo del docente y
  persistencia en Supabase (D-001).
```

El resto del §19 —códigos anónimos, supresión de datos identificativos,
separación de las observaciones personales, registro mínimo y copias de
seguridad— se conserva intacto: sigue siendo aplicable.

Después:

```bash
python tools/verificar_gobernanza.py    # R2 debe protestar: la prosa cambio
```

Revisar si el cambio afecta a algún criterio de `criteria/`, escribir
`docs/changes/2026-08-26-supabase-corrige-maestro.md` a partir de la plantilla,
sellar y commitear:

```bash
python tools/verificar_gobernanza.py --sellar
git add docs/ criteria/
git commit -m "docs: el Maestro recoge el circuito de datos real (D-001)"
```

Este paso cierra el bucle: la primera decisión que contradijo al Maestro acaba
corrigiéndolo, que es exactamente lo que la gobernanza promete.

---

## Verificación final del plan

Al terminar las nueve tareas, comprobar:

- [ ] `python -m pytest` — todos en verde
- [ ] `python tools/verificar_gobernanza.py` — `Gobernanza conforme: 0 infracciones.`
- [ ] El hook rechaza un commit con un DNI de prueba
- [ ] `docs/PENDIENTE_OFICIAL.md` lista las diez pendientes y ninguna tiene valor en el YAML
- [ ] El §19 y el §21.1 del Maestro ya no dicen "sistema local"
- [ ] No hay ningún `.pdf` ni `.docx` versionado
