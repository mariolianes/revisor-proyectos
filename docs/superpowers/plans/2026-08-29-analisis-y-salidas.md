# El análisis y las dos salidas — Plan de implementación (Parte B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el sistema valore las doce dimensiones de una entrega con evidencia localizable, redacte el informe interno y el borrador de devolución, y se detenga para que el docente decida observación por observación.

**Architecture:** Dos módulos nuevos bajo `backend/`. `analisis/` pide el juicio a un modelo de lenguaje y lo somete a siete comprobaciones propias antes de darlo por bueno; no sabe qué es un informe. `salidas/` compone las dos salidas del Anexo C y del Anexo D a partir de un análisis ya verificado; no sabe qué es OpenAI. El motor no redacta: rellena un formulario cuya forma valida el proveedor, y cuyo contenido validamos nosotros.

**Tech Stack:** Python 3.13, `openai` 3.5.0 (Responses API con `text_format`), Pydantic 2, FastAPI, pytest, React 19, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-29-analisis-y-salidas-design.md`

## Global Constraints

Todo lo que sigue vincula a **todas** las tareas.

- **Idioma:** todo en castellano — identificadores, comentarios, mensajes de error, docstrings y commits. Los mensajes los lee un profesor, no un programador.
- **El sistema propone y se detiene.** Ningún endpoint aprueba, califica ni comunica nada al alumno. La forma de respetarlo es que esas operaciones no existan.
- **No hay nota. En ninguna parte.** Aunque el motor la sugiera, se descarta antes de guardarla. Las ponderaciones siguen en `PENDIENTE_OFICIAL` y R3 prohíbe sustituir un dato oficial ausente por una estimación.
- **Las siete defensas son código propio.** Ninguna delega en que el modelo se porte bien. Se prueban contra un motor hostil, no contra uno que colabora.
- **La suite normal no llama nunca al proveedor real.** Corre contra el adaptador simulado. El proveedor real solo se usa en el arnés de calibración, que es un comando aparte.
- **Ningún PDF ni texto de trabajo entra en el repositorio.** Los documentos de prueba se construyen en los fixtures.
- **Valores exactos de los criterios:** se leen de `criteria/v2026-2027/` en tiempo de ejecución. Ninguna tarea los copia al código.
- **El texto del trabajo se envía íntegro al proveedor**, por decisión del docente del 2026-08-29. No se anonimiza. Eso obliga a corregir el §19 del Maestro, que es la Task 16.
- **Antes de dar por cerrada cualquier tarea:** `python -m pytest`, `cd frontend && npm test` y `python tools/verificar_gobernanza.py`, los tres en verde.

---

### Task 1: El contrato — el formulario que el motor debe rellenar

Lo primero, porque todo lo demás lo consume. El motor no devuelve prosa: rellena una estructura fija que el proveedor valida antes de entregárnosla.

**Un detalle verificado que conviene entender:** en el modo estricto de OpenAI, **todos los campos son obligatorios**, y un campo opcional se traduce a «obligatorio que admite nulo». El motor no puede omitir la prioridad de un hallazgo: tiene que decidirla, aunque sea para decir que no la tiene. Eso nos conviene y por eso los opcionales se declaran así.

**Files:**
- Create: `backend/analisis/__init__.py`
- Create: `backend/analisis/contrato.py`
- Create: `tests/analisis/test_contrato.py`
- Modify: `requirements-dev.txt` (añadir `openai==3.5.0`)

**Interfaces:**
- Consumes: nada.
- Produces:
  - `NIVELES: tuple[str, ...]` y `PRIORIDADES: tuple[str, ...]`
  - `Evidencia(BaseModel)` con `cita: str`, `apartado: str`
  - `Valoracion(BaseModel)` con `dimension: str`, `nivel: str`, `prioridad: str | None`, `evidencia: Evidencia`, `observacion: str`
  - `Patron(BaseModel)` con `nombre: str`, `descripcion: str`, `evidencia: Evidencia`
  - `AnalisisDelMotor(BaseModel)` con `valoraciones: list[Valoracion]`, `fortalezas: list[str]`, `patrones: list[Patron]`, `dudas_para_el_docente: list[str]`, `indicios_de_autoria: list[str]`
  - `esquema_estricto() -> dict` — el JSON Schema que se le pasa al proveedor.

- [ ] **Step 1: Añadir la dependencia**

En `requirements-dev.txt`, tras la línea `pymupdf==1.28.2`, añadir:

```
openai==3.5.0
```

- [ ] **Step 2: Escribir los tests**

Crear `tests/analisis/test_contrato.py`:

```python
"""El formulario que el motor debe rellenar."""

import pytest
from pydantic import ValidationError

from backend.analisis.contrato import (
    NIVELES,
    PRIORIDADES,
    AnalisisDelMotor,
    Evidencia,
    Valoracion,
    esquema_estricto,
)


def _valoracion(**cambios) -> dict:
    datos = dict(
        dimension="D05",
        nivel="ADECUADO",
        prioridad="P2",
        evidencia={"cita": "El presupuesto asciende a 4.500 euros.",
                   "apartado": "5. Presupuesto"},
        observacion="Las cifras se presentan sin justificar su origen.",
    )
    datos.update(cambios)
    return datos


def test_una_valoracion_completa_se_acepta() -> None:
    v = Valoracion(**_valoracion())

    assert v.dimension == "D05"
    assert v.evidencia.cita.startswith("El presupuesto")


def test_un_nivel_inventado_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Valoracion(**_valoracion(nivel="REGULAR"))


def test_una_prioridad_inventada_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Valoracion(**_valoracion(prioridad="P9"))


def test_la_prioridad_puede_ser_nula() -> None:
    """Un hallazgo puede no tener prioridad, pero el motor ha de decirlo."""
    assert Valoracion(**_valoracion(prioridad=None)).prioridad is None


def test_una_dimension_fuera_del_catalogo_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Valoracion(**_valoracion(dimension="D99"))


def test_una_valoracion_sin_evidencia_se_rechaza() -> None:
    """Ningún juicio sin evidencia. Es la regla, no una preferencia."""
    datos = _valoracion()
    del datos["evidencia"]

    with pytest.raises(ValidationError):
        Valoracion(**datos)


def test_los_niveles_son_los_del_maestro() -> None:
    assert NIVELES == (
        "SOLIDO", "ADECUADO", "EN_DESARROLLO",
        "INSUFICIENTE", "NO_APLICABLE", "NO_VERIFICABLE",
    )


def test_las_prioridades_son_las_del_calibrador() -> None:
    assert PRIORIDADES == ("P1", "P2", "P3", "P4")


def test_un_analisis_completo_se_acepta() -> None:
    a = AnalisisDelMotor(
        valoraciones=[Valoracion(**_valoracion())],
        fortalezas=["La estructura del documento es clara."],
        patrones=[],
        dudas_para_el_docente=[],
        indicios_de_autoria=[],
    )

    assert len(a.valoraciones) == 1


def test_el_analisis_no_admite_campos_de_mas() -> None:
    """Si el motor devuelve una nota, la validación la rechaza aquí mismo."""
    with pytest.raises(ValidationError):
        AnalisisDelMotor(
            valoraciones=[], fortalezas=[], patrones=[],
            dudas_para_el_docente=[], indicios_de_autoria=[],
            nota_propuesta=7.5,
        )


def test_el_esquema_estricto_lo_acepta_el_proveedor() -> None:
    """Comprueba lo que exige el modo estricto: nada opcional, nada de más."""
    esquema = esquema_estricto()

    assert esquema["additionalProperties"] is False
    assert set(esquema["required"]) == {
        "valoraciones", "fortalezas", "patrones",
        "dudas_para_el_docente", "indicios_de_autoria",
    }


def test_el_esquema_obliga_a_decidir_la_prioridad() -> None:
    """En modo estricto un opcional es «obligatorio que admite nulo».

    El motor no puede callarse el campo: tiene que decir P1..P4 o null.
    """
    esquema = esquema_estricto()
    valoracion = esquema["$defs"]["Valoracion"]

    assert "prioridad" in valoracion["required"]
    tipos = valoracion["properties"]["prioridad"]["anyOf"]
    assert {"type": "null"} in tipos
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/analisis/test_contrato.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.analisis'`

- [ ] **Step 4: Escribir `backend/analisis/__init__.py`**

```python
"""Pide el juicio a un modelo de lenguaje y lo comprueba antes de creerlo."""
```

- [ ] **Step 5: Escribir `backend/analisis/contrato.py`**

```python
"""El formulario que el motor rellena.

El motor no redacta un informe: rellena esta estructura, y el proveedor la
valida antes de devolverla. Eso convierte «el modelo dijo algo» en «el modelo
rellenó estos campos», que es lo único que se puede comprobar.

Sobre el modo estricto del proveedor: exige que TODOS los campos sean
obligatorios y que ningún objeto admita propiedades de más. Un campo opcional
se traduce a «obligatorio que admite nulo», así que el motor no puede callarse
la prioridad de un hallazgo: tiene que decidirla, aunque sea para decir que no
tiene. Nos conviene, y por eso los opcionales se declaran de esta forma.

Que no se admitan propiedades de más tiene una consecuencia que importa: si el
motor decidiera devolver una nota, la validación la rechaza aquí, antes de que
nadie la vea. La regla R3 se cumple en el tipo, no en una comprobación que
alguien pueda olvidar.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

# Escala del §8.1 del Documento Maestro.
NIVELES: tuple[str, ...] = (
    "SOLIDO",
    "ADECUADO",
    "EN_DESARROLLO",
    "INSUFICIENTE",
    "NO_APLICABLE",
    "NO_VERIFICABLE",
)

# Niveles de prioridad del §7 del documento de calibración.
PRIORIDADES: tuple[str, ...] = ("P1", "P2", "P3", "P4")

# Las doce dimensiones del §8. El catálogo vive en criteria/dimensiones.yaml;
# aquí se enumeran para que el proveedor pueda validarlas, y la comprobación
# de cuáles están activas en cada fase la hace backend/analisis/verificacion.py
# leyendo los criterios.
_CODIGOS = Literal[
    "D01", "D02", "D03", "D04", "D05", "D06",
    "D07", "D08", "D09", "D10", "D11", "D12",
]


class Evidencia(BaseModel):
    """Dónde se apoya un juicio.

    `cita` es un fragmento literal del trabajo. Literal de verdad: la
    verificación lo busca en el texto, y una paráfrasis no se da por buena.
    """

    model_config = ConfigDict(extra="forbid")

    cita: str
    apartado: str


class Valoracion(BaseModel):
    """Una dimensión valorada, con su evidencia.

    No hay valoración sin evidencia: el campo es obligatorio y el §7 del
    Maestro lo exige. Un juicio que no se puede señalar en el documento no es
    un juicio, es una opinión.
    """

    model_config = ConfigDict(extra="forbid")

    dimension: _CODIGOS
    nivel: Literal[
        "SOLIDO", "ADECUADO", "EN_DESARROLLO",
        "INSUFICIENTE", "NO_APLICABLE", "NO_VERIFICABLE",
    ]
    prioridad: Literal["P1", "P2", "P3", "P4"] | None
    evidencia: Evidencia
    observacion: str


class Patron(BaseModel):
    """Uno de los patrones del §5 del calibrador, si se observa."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    descripcion: str
    evidencia: Evidencia


class AnalisisDelMotor(BaseModel):
    """Todo lo que el motor devuelve, antes de comprobarlo.

    Se llama «del motor» a propósito: esto es lo que dijo, no lo que damos por
    bueno. Lo segundo sale de backend/analisis/verificacion.py.

    No hay campo para la nota, y no es un olvido: `extra="forbid"` hace que
    una nota devuelta por el motor sea un error de validación.
    """

    model_config = ConfigDict(extra="forbid")

    valoraciones: list[Valoracion]
    fortalezas: list[str]
    patrones: list[Patron]
    dudas_para_el_docente: list[str]
    indicios_de_autoria: list[str]


def esquema_estricto() -> dict:
    """El JSON Schema que se le pasa al proveedor.

    Se usa la utilidad del propio cliente para que el esquema sea exactamente
    el que su modo estricto acepta, en vez de construirlo a mano y descubrir
    la diferencia en producción.
    """
    from openai.lib._pydantic import to_strict_json_schema

    return to_strict_json_schema(AnalisisDelMotor)
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/analisis/test_contrato.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 7: Commit**

```bash
git add backend/analisis tests/analisis requirements-dev.txt
git commit -m "feat: el contrato que el motor debe rellenar

El motor no redacta: rellena una estructura fija que el proveedor valida
antes de devolverla. Eso convierte \"el modelo dijo algo\" en \"el modelo
relleno estos campos\", que es lo unico comprobable.

Dos consecuencias del modo estricto que nos vienen bien. Un campo opcional
se traduce a obligatorio-que-admite-nulo, asi que el motor no puede callarse
la prioridad de un hallazgo: tiene que decidirla. Y como no se admiten
propiedades de mas, una nota devuelta por el motor es un error de validacion
antes de que nadie la vea: R3 se cumple en el tipo."
```

---

### Task 2: La primera defensa — cada cita se busca en el texto real

La comprobación de la que depende todo lo demás. El motor cita un fragmento; nosotros lo buscamos en el texto que le enviamos. Si no aparece, ese juicio no llega al alumno.

Un modelo puede inventarse una frase. No puede hacer que exista en el documento.

**Files:**
- Create: `backend/analisis/verificacion.py`
- Create: `tests/analisis/test_verificacion_citas.py`

**Interfaces:**
- Consumes: `Evidencia`, `Valoracion` de `backend.analisis.contrato`.
- Produces:
  - `normalizar_para_buscar(texto: str) -> str`
  - `cita_localizada(cita: str, texto: str) -> bool`
  - `CITA_MINIMA: int`

- [ ] **Step 1: Escribir los tests**

Crear `tests/analisis/test_verificacion_citas.py`:

```python
"""La defensa de la que depende todo lo demás."""

from backend.analisis.verificacion import cita_localizada, normalizar_para_buscar

TRABAJO = """
5. Presupuesto y viabilidad

El presupuesto inicial asciende a 4.500 euros, repartidos entre licencias,
formación y difusión. La recuperación de la inversión se estima en catorce
meses, considerando un margen bruto del treinta por ciento.

6. Conclusiones

El proyecto resulta viable y sostenible a medio plazo.
"""


def test_una_cita_literal_se_localiza() -> None:
    assert cita_localizada("El presupuesto inicial asciende a 4.500 euros", TRABAJO)


def test_una_cita_inventada_no_se_localiza() -> None:
    """El caso que esta defensa existe para cazar."""
    assert not cita_localizada(
        "El presupuesto inicial asciende a 12.000 euros", TRABAJO
    )


def test_la_cita_aguanta_diferencias_de_espaciado() -> None:
    """El texto de un PDF llega con saltos de línea donde no los había."""
    assert cita_localizada(
        "formación y difusión. La recuperación de la inversión", TRABAJO
    )


def test_la_cita_aguanta_diferencias_de_tildes() -> None:
    """Un modelo puede devolver la cita sin acentuar."""
    assert cita_localizada("La recuperacion de la inversion se estima", TRABAJO)


def test_una_parafrasis_no_se_da_por_buena() -> None:
    """Resumir no es citar. Si el motor resume, no hay evidencia localizable."""
    assert not cita_localizada(
        "El trabajo dice que el presupuesto ronda los cuatro mil quinientos euros",
        TRABAJO,
    )


def test_una_cita_demasiado_corta_no_vale() -> None:
    """«el» aparece en cualquier documento y no señala nada."""
    assert not cita_localizada("el", TRABAJO)
    assert not cita_localizada("viable", TRABAJO)


def test_una_cita_vacia_no_vale() -> None:
    assert not cita_localizada("", TRABAJO)
    assert not cita_localizada("     ", TRABAJO)


def test_normalizar_colapsa_espacios_y_quita_tildes() -> None:
    assert normalizar_para_buscar("  La  recuperación\n de la inversión ") == (
        "la recuperacion de la inversion"
    )
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/analisis/test_verificacion_citas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.analisis.verificacion'`

- [ ] **Step 3: Escribir la primera parte de `backend/analisis/verificacion.py`**

```python
"""Lo que comprobamos nosotros antes de creernos lo que dice el motor.

Siete defensas, y ninguna delega en que el modelo se porte bien. Todas son
código de aquí, todas fallan del lado seguro, y todas se prueban contra un
motor hostil en vez de contra uno que colabora.

La primera es la que sostiene las demás: un modelo puede inventarse una frase,
pero no puede hacer que exista en el documento del alumno.
"""

import re
import unicodedata

# Una cita más corta que esto no señala nada: «el» o «viable» aparecen en
# cualquier trabajo y localizarlas no demuestra que el juicio se apoye ahí.
CITA_MINIMA = 20


def normalizar_para_buscar(texto: str) -> str:
    """Minúsculas, sin tildes y con los espacios colapsados.

    Se normaliza porque el texto extraído de un PDF trae saltos de línea donde
    el original tenía un espacio, y porque un modelo puede devolver la cita sin
    acentuar. Ninguna de esas dos diferencias significa que la cita sea falsa.
    """
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def cita_localizada(cita: str, texto: str) -> bool:
    """Si la cita aparece literalmente en el texto del trabajo.

    Literalmente quiere decir literalmente: se admite que cambien los espacios
    y las tildes, y nada más. Una paráfrasis no se da por buena, porque el
    objetivo no es saber si el motor entendió el documento, sino si el docente
    puede ir a la página y leer eso mismo.
    """
    limpia = normalizar_para_buscar(cita)
    if len(limpia) < CITA_MINIMA:
        return False
    return limpia in normalizar_para_buscar(texto)
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/analisis/test_verificacion_citas.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/analisis tests/analisis
git commit -m "feat: la evidencia de cada juicio se busca en el texto real

Un modelo puede inventarse una frase; no puede hacer que exista en el
documento del alumno. Se admite que cambien los espacios y las tildes
—el texto de un PDF trae saltos donde habia espacios— y nada mas: una
parafrasis no se da por buena, porque lo que se quiere garantizar no es
que el motor entendiera el trabajo, sino que el docente pueda ir a la
pagina y leer eso mismo.

Una cita de menos de veinte caracteres tampoco vale: \"el\" aparece en
cualquier documento y localizarlo no demuestra nada."
```
---

### Task 3: Las seis defensas restantes

Con la primera puesta, van las otras seis. Todas actúan sobre el análisis que devolvió el motor y producen un **análisis verificado**, que es cosa distinta: lo primero es lo que dijo, lo segundo es lo que damos por bueno.

Ninguna lanza excepción. Todas degradan del lado seguro y dejan constancia de por qué, porque un análisis que se cae entero por un juicio mal citado es peor que uno que marca ese juicio y sigue.

**Files:**
- Modify: `backend/analisis/verificacion.py`
- Create: `tests/analisis/test_verificacion.py`
- Modify: `tests/conftest.py` (añadir el fixture `criterios_de_analisis`)

**Interfaces:**
- Consumes: `AnalisisDelMotor`, `Valoracion` (Task 1); `cita_localizada` (Task 2); `criteria/v2026-2027/dimensiones.yaml` y `prioridades.yaml`.
- Produces:
  - `Reparo(BaseModel)` con `regla: str`, `detalle: str`
  - `ValoracionVerificada(BaseModel)` = los campos de `Valoracion` más `evidencia_localizada: bool`
  - `AnalisisVerificado(BaseModel)` con `valoraciones: list[ValoracionVerificada]`, `fortalezas`, `patrones`, `dudas_para_el_docente`, `indicios_de_autoria`, `dimensiones_ausentes: list[str]`, `reparos: list[Reparo]`
  - `verificar(raiz: Path, version: str, fase: str, texto: str, analisis: AnalisisDelMotor) -> AnalisisVerificado`
  - `PRIORIDADES_EN_LA_DEVOLUCION: int = 4`

- [ ] **Step 1: Añadir el fixture de criterios**

El fixture `criterios_de_formato` que ya existe solo escribe `formato.yaml`, y
la verificación necesita saber qué dimensiones están activas en cada fase.
Añadir al final de `tests/conftest.py`:

```python
# Las dimensiones tal como las reparte el §8 del Maestro entre las fases. Se
# recortan a seis para que un test quepa de un vistazo, conservando lo que
# importa: que D08 no esté activa en E2, que es lo que permite comprobar que
# una dimensión fuera de fase se descarta.
DIMENSIONES_DE_PRUEBA = """
- codigo: D01
  nombre: Adecuacion al ciclo
  fuente: maestro#8-dimensiones
  activa_en: [TEMA, E1, E2, E3, FINAL]

- codigo: D02
  nombre: Definicion del problema
  fuente: maestro#8-dimensiones
  activa_en: [TEMA, E1, E2, E3, FINAL]

- codigo: D05
  nombre: Fundamentacion y fuentes
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]

- codigo: D07
  nombre: Resultados
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]

- codigo: D08
  nombre: Conclusiones
  fuente: maestro#8-dimensiones
  activa_en: [E3, FINAL]

- codigo: D12
  nombre: Comunicacion
  fuente: maestro#8-dimensiones
  activa_en: [E1, E2, E3, FINAL, DEFENSA]
"""


@pytest.fixture
def criterios_de_analisis(tmp_path: Path) -> Path:
    """Una raíz con los criterios que el análisis necesita leer."""
    raiz = tmp_path / "repo"
    carpeta = raiz / "criteria" / "v2026-2027"
    carpeta.mkdir(parents=True)
    (carpeta / "dimensiones.yaml").write_text(DIMENSIONES_DE_PRUEBA, encoding="utf-8")
    (carpeta / "formato.yaml").write_text(CRITERIOS_DE_PRUEBA, encoding="utf-8")
    return raiz
```

- [ ] **Step 2: Escribir los tests**

Crear `tests/analisis/test_verificacion.py`:

```python
"""Las seis defensas que quedan, probadas contra un motor hostil."""

from pathlib import Path

import pytest

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Valoracion
from backend.analisis.verificacion import verificar

TRABAJO = """
1. Introduccion

El presente proyecto describe la implantacion de un sistema de reservas para
un taller mecanico de tamano medio situado en la provincia de Sevilla.

5. Presupuesto y viabilidad

El presupuesto inicial asciende a 4.500 euros, repartidos entre licencias,
formacion y difusion. La recuperacion de la inversion se estima en catorce
meses, considerando un margen bruto del treinta por ciento.
"""


def _val(dimension="D05", nivel="ADECUADO", prioridad="P2", cita=None, obs="Observacion."):
    return Valoracion(
        dimension=dimension,
        nivel=nivel,
        prioridad=prioridad,
        evidencia=Evidencia(
            cita=cita or "El presupuesto inicial asciende a 4.500 euros",
            apartado="5. Presupuesto y viabilidad",
        ),
        observacion=obs,
    )


def _analisis(valoraciones, **cambios):
    datos = dict(
        valoraciones=valoraciones,
        fortalezas=["La estructura del documento es clara."],
        patrones=[],
        dudas_para_el_docente=[],
        indicios_de_autoria=[],
    )
    datos.update(cambios)
    return AnalisisDelMotor(**datos)


# --- Defensa 1, integrada: la cita ---

def test_una_evidencia_inventada_marca_el_juicio(criterios_de_analisis: Path) -> None:
    """El juicio no se borra: se marca. El docente ve que no se pudo localizar."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(cita="El presupuesto asciende a 99.000 euros de inversion")]),
    )

    assert v.valoraciones[0].evidencia_localizada is False
    assert any("no se ha localizado" in r.detalle for r in v.reparos)


def test_una_evidencia_real_se_da_por_localizada(criterios_de_analisis: Path) -> None:
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([_val()]))

    assert v.valoraciones[0].evidencia_localizada is True
    assert v.reparos == []


# --- Defensa 2: ni una dimension de mas ni de menos ---

def test_una_dimension_que_no_toca_en_esa_fase_se_descarta(criterios_de_analisis: Path) -> None:
    """D08 no esta activa en E2. Aunque el motor la devuelva, no cuenta."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(dimension="D05"), _val(dimension="D08")]),
    )

    assert [x.dimension for x in v.valoraciones] == ["D05"]
    assert any("D08" in r.detalle and "no esta activa" in r.detalle for r in v.reparos)


def test_las_dimensiones_que_faltan_se_declaran(criterios_de_analisis: Path) -> None:
    """No se dan por buenas: se dicen."""
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([_val()]))

    assert "D01" in v.dimensiones_ausentes
    assert "D05" not in v.dimensiones_ausentes


def test_una_dimension_repetida_se_queda_con_la_primera(criterios_de_analisis: Path) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(obs="La primera."), _val(obs="La segunda.")]),
    )

    assert len(v.valoraciones) == 1
    assert v.valoraciones[0].observacion == "La primera."
    assert any("dos veces" in r.detalle for r in v.reparos)


# --- Defensa 5: ninguna nota, venga como venga ---

def test_una_nota_en_una_observacion_no_convierte_nada_en_nota(criterios_de_analisis: Path) -> None:
    """El contrato ya impide un campo de nota; esto comprueba que tampoco se
    fabrica una a partir del texto."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(obs="Yo le pondria un 7 sobre 10.")]),
    )

    assert not hasattr(v, "nota")
    assert not hasattr(v.valoraciones[0], "nota")


# --- Defensa 7: ninguna afirmacion de autoria ---

def test_los_indicios_de_autoria_se_conservan_como_indicios(criterios_de_analisis: Path) -> None:
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val()], indicios_de_autoria=["Registro uniforme en todo el texto."]),
    )

    assert v.indicios_de_autoria == ["Registro uniforme en todo el texto."]


def test_un_indicio_redactado_como_afirmacion_se_marca(criterios_de_analisis: Path) -> None:
    """«Este texto ha sido generado por IA» no es un indicio: es un veredicto."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val()],
                  indicios_de_autoria=["Este texto ha sido generado por una IA."]),
    )

    assert any("afirmacion" in r.detalle.lower() for r in v.reparos)


# --- Un motor que devuelve basura entera ---

def test_un_analisis_vacio_no_revienta(criterios_de_analisis: Path) -> None:
    v = verificar(criterios_de_analisis, "v2026-2027", "E2", TRABAJO, _analisis([]))

    assert v.valoraciones == []
    assert len(v.dimensiones_ausentes) > 0


def test_todas_las_dimensiones_inventadas(criterios_de_analisis: Path) -> None:
    """Ni una sobrevive, y el analisis sigue siendo utilizable."""
    v = verificar(
        criterios_de_analisis, "v2026-2027", "E2", TRABAJO,
        _analisis([_val(dimension="D08", cita="inventada del todo y bien larga")]),
    )

    assert v.valoraciones == []
    assert len(v.reparos) >= 1
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/analisis/test_verificacion.py -v`
Expected: FAIL con `ImportError: cannot import name 'verificar'`

- [ ] **Step 4: Añadir a `backend/analisis/verificacion.py`**

```python
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Patron

# El §2.3 del calibrador: tres o cuatro prioridades, no diez. El limite se usa
# al componer la devolucion, no aqui: aqui solo se deja escrito de donde sale.
PRIORIDADES_EN_LA_DEVOLUCION = 4

# Formas de afirmar la autoria que el §11 del Maestro y el punto 9 del anexo B
# del calibrador prohiben. Se buscan sobre el texto normalizado.
_AFIRMACIONES_DE_AUTORIA = (
    "ha sido generado por",
    "esta generado por",
    "fue generado por",
    "escrito por una ia",
    "escrito por chatgpt",
    "es obra de una ia",
)


class Reparo(BaseModel):
    """Algo que el motor devolvio y no se ha dado por bueno."""

    model_config = ConfigDict(extra="forbid")

    regla: str
    detalle: str


class ValoracionVerificada(BaseModel):
    """Una valoracion que ya ha pasado por las comprobaciones."""

    model_config = ConfigDict(extra="forbid")

    dimension: str
    nivel: str
    prioridad: str | None
    evidencia: Evidencia
    observacion: str
    evidencia_localizada: bool


class AnalisisVerificado(BaseModel):
    """Lo que damos por bueno, que no es lo mismo que lo que dijo el motor."""

    model_config = ConfigDict(extra="forbid")

    valoraciones: list[ValoracionVerificada]
    fortalezas: list[str]
    patrones: list[Patron]
    dudas_para_el_docente: list[str]
    indicios_de_autoria: list[str]
    dimensiones_ausentes: list[str]
    reparos: list[Reparo]


def _dimensiones_activas(raiz: Path, version: str, fase: str) -> list[str]:
    """Las dimensiones que corresponden a esa fase, segun los criterios."""
    fichero = raiz / "criteria" / version / "dimensiones.yaml"
    if not fichero.is_file():
        return []
    catalogo = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    return [
        d["codigo"]
        for d in catalogo
        if isinstance(d, dict) and fase in (d.get("activa_en") or [])
    ]


def verificar(
    raiz: Path,
    version: str,
    fase: str,
    texto: str,
    analisis: AnalisisDelMotor,
) -> AnalisisVerificado:
    """Somete lo que dijo el motor a las comprobaciones que no dependen de el.

    Nada de esto lanza una excepcion. Un juicio mal citado se marca, una
    dimension que no toca se descarta, y el resto del analisis sigue siendo
    utilizable: un informe con una observacion menos le sirve al docente, y uno
    que no existe porque el motor se equivoco en un campo, no.
    """
    activas = _dimensiones_activas(raiz, version, fase)
    reparos: list[Reparo] = []
    verificadas: list[ValoracionVerificada] = []
    vistas: set[str] = set()

    for v in analisis.valoraciones:
        if v.dimension not in activas:
            reparos.append(Reparo(
                regla="dimension_activa",
                detalle=f"La dimension {v.dimension} no esta activa en la fase "
                        f"{fase} y se ha descartado.",
            ))
            continue
        if v.dimension in vistas:
            reparos.append(Reparo(
                regla="dimension_repetida",
                detalle=f"La dimension {v.dimension} venia valorada dos veces; "
                        "se ha conservado la primera.",
            ))
            continue
        vistas.add(v.dimension)

        localizada = cita_localizada(v.evidencia.cita, texto)
        if not localizada:
            reparos.append(Reparo(
                regla="evidencia_localizable",
                detalle=f"La evidencia de {v.dimension} no se ha localizado en el "
                        "documento. La observacion se conserva para que la revises, "
                        "pero no pasara a la devolucion.",
            ))
        verificadas.append(ValoracionVerificada(
            dimension=v.dimension,
            nivel=v.nivel,
            prioridad=v.prioridad,
            evidencia=v.evidencia,
            observacion=v.observacion,
            evidencia_localizada=localizada,
        ))

    for indicio in analisis.indicios_de_autoria:
        plano = normalizar_para_buscar(indicio)
        if any(forma in plano for forma in _AFIRMACIONES_DE_AUTORIA):
            reparos.append(Reparo(
                regla="autoria_como_indicio",
                detalle="Un indicio de autoria viene redactado como afirmacion. "
                        "El sistema registra indicios; quien decide eres tu.",
            ))

    return AnalisisVerificado(
        valoraciones=verificadas,
        fortalezas=analisis.fortalezas,
        patrones=analisis.patrones,
        dudas_para_el_docente=analisis.dudas_para_el_docente,
        indicios_de_autoria=analisis.indicios_de_autoria,
        dimensiones_ausentes=[d for d in activas if d not in vistas],
        reparos=reparos,
    )
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/analisis -v`
Expected: PASS, 30 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/analisis tests/
git commit -m "feat: las seis defensas restantes sobre lo que devuelve el motor

Producen un analisis verificado, que no es lo mismo que el analisis del
motor: lo primero es lo que dijo, lo segundo lo que damos por bueno.

Ninguna lanza excepcion. Un juicio mal citado se marca, una dimension que
no toca en esa fase se descarta, una repetida se queda con la primera, y el
resto sigue sirviendo: un informe con una observacion menos le vale al
docente, y uno que no existe porque el motor se equivoco en un campo, no.

Los indicios de autoria se conservan como indicios. Si vienen redactados
como veredicto —\"este texto ha sido generado por una IA\"— se deja un
reparo: el sistema registra indicios y quien decide es el profesor."
```

---

### Task 4: El puerto del proveedor y el adaptador simulado

El mismo patrón que el almacén de la Parte A: un puerto con dos implementaciones. La simulada no es un doble de pruebas, es la que corre mientras no haya clave, y es contra la que se prueba todo salvo el arnés de calibración.

**Files:**
- Create: `backend/analisis/proveedor.py`
- Create: `tests/analisis/test_proveedor.py`

**Interfaces:**
- Consumes: `AnalisisDelMotor` (Task 1).
- Produces:
  - `ErrorDelProveedor(Exception)` y `RespuestaNoValida(ErrorDelProveedor)`
  - `ProveedorAnalisis` (`typing.Protocol`) con `analizar(instruccion: str, texto: str, formato: type[T]) -> T` y la propiedad `nombre: str`. **Es genérico a propósito:** el mismo puerto sirve para pedir el análisis y para pedir la redacción del borrador, que son formularios distintos.
  - `ProveedorSimulado` que lo implementa, con `respuestas: list[AnalisisDelMotor]` y `fallos: list[Exception]` inyectables.

- [ ] **Step 1: Escribir los tests**

Crear `tests/analisis/test_proveedor.py`:

```python
"""El puerto y el proveedor simulado."""

import pytest

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.proveedor import (
    ErrorDelProveedor,
    ProveedorSimulado,
    RespuestaNoValida,
)

VACIO = AnalisisDelMotor(
    valoraciones=[], fortalezas=[], patrones=[],
    dudas_para_el_docente=[], indicios_de_autoria=[],
)


def test_devuelve_la_respuesta_que_se_le_dio() -> None:
    p = ProveedorSimulado(respuestas=[VACIO])

    assert p.analizar("instruccion", "texto", AnalisisDelMotor) is VACIO


def test_registra_lo_que_se_le_pidio() -> None:
    """Los tests de la instruccion necesitan ver que llego al proveedor."""
    p = ProveedorSimulado(respuestas=[VACIO])
    p.analizar("la instruccion", "el texto del trabajo", AnalisisDelMotor)

    assert p.llamadas == [("la instruccion", "el texto del trabajo")]


def test_se_puede_programar_un_fallo() -> None:
    p = ProveedorSimulado(fallos=[RespuestaNoValida("no encaja en el formulario")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)


def test_un_fallo_y_luego_una_respuesta() -> None:
    """Es el caso del reintento: falla una vez y a la segunda va."""
    p = ProveedorSimulado(respuestas=[VACIO], fallos=[RespuestaNoValida("mal")])

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)
    assert p.analizar("i", "t", AnalisisDelMotor) is VACIO


def test_quedarse_sin_respuestas_es_un_error_del_test() -> None:
    """Si un test pide mas analisis de los que programo, que se note."""
    p = ProveedorSimulado(respuestas=[])

    with pytest.raises(AssertionError, match="sin respuestas"):
        p.analizar("i", "t", AnalisisDelMotor)


def test_el_simulado_dice_que_lo_es() -> None:
    """El frontend lo ensena: un analisis simulado no es un analisis."""
    assert ProveedorSimulado(respuestas=[VACIO]).nombre == "simulado"


def test_respuesta_no_valida_es_un_error_del_proveedor() -> None:
    assert issubclass(RespuestaNoValida, ErrorDelProveedor)
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/analisis/test_proveedor.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.analisis.proveedor'`

- [ ] **Step 3: Escribir `backend/analisis/proveedor.py`**

```python
"""De donde sale el juicio. El puerto y el proveedor simulado.

Mismo patron que el almacen de la Parte A: el sistema no depende de quien
responde. Y por el mismo motivo, el simulado no es un doble de pruebas: es lo
que corre mientras no haya clave configurada, para que el flujo se pueda
recorrer entero sin gastar dinero ni enviar el trabajo de nadie a ninguna
parte.

`nombre` existe porque el frontend lo ensena. Un analisis hecho con el
proveedor simulado no es un analisis, y el docente tiene que saberlo antes de
apoyarse en el.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ErrorDelProveedor(Exception):
    """No se ha podido obtener un analisis."""


class RespuestaNoValida(ErrorDelProveedor):
    """El proveedor respondio, pero lo devuelto no encaja en el formulario.

    Se distingue del resto porque es el unico fallo que merece un reintento:
    es el mas comun y el mas barato de resolver.
    """


class ProveedorAnalisis(Protocol):
    """Lo que cualquier proveedor tiene que saber hacer.

    `formato` es el modelo que se espera de vuelta. El puerto es generico
    porque a lo largo del flujo se le piden dos formularios distintos: el
    analisis de las dimensiones y la redaccion de la devolucion. Es la misma
    conversacion con el mismo proveedor, y separarla en dos metodos habria
    obligado a cada implementacion a repetir el mismo codigo dos veces.
    """

    @property
    def nombre(self) -> str: ...

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T: ...


class ProveedorSimulado:
    """Devuelve lo que se le haya programado, en orden.

    Guarda lo que se le pidio en `llamadas`, que es como los tests de la
    instruccion comprueban que lo enviado era lo correcto sin tener que
    inspeccionar la construccion del mensaje por dentro.
    """

    def __init__(
        self,
        respuestas: list[BaseModel] | None = None,
        fallos: list[Exception] | None = None,
    ) -> None:
        self._respuestas = list(respuestas or [])
        self._fallos = list(fallos or [])
        self.llamadas: list[tuple[str, str]] = []

    @property
    def nombre(self) -> str:
        return "simulado"

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T:
        self.llamadas.append((instruccion, texto))
        if self._fallos:
            raise self._fallos.pop(0)
        assert self._respuestas, (
            "El proveedor simulado se ha quedado sin respuestas programadas. "
            "Si esperabas otra llamada, anadela al construirlo."
        )
        return self._respuestas.pop(0)
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/analisis/test_proveedor.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/analisis tests/analisis
git commit -m "feat: puerto del proveedor de analisis y adaptador simulado

Mismo patron que el almacen: el sistema no depende de quien responde. Y por
el mismo motivo, el simulado no es un doble de pruebas: es lo que corre
mientras no haya clave, para que el flujo se pueda recorrer entero sin
gastar dinero ni enviar el trabajo de nadie a ninguna parte.

`nombre` existe porque el frontend lo ensena. Un analisis hecho con el
proveedor simulado no es un analisis, y el docente tiene que saberlo antes
de apoyarse en el.

RespuestaNoValida se distingue del resto de fallos porque es el unico que
merece un reintento: el mas comun y el mas barato de resolver."
```
---

### Task 5: La instrucción, construida desde los criterios

Lo que se le pide al motor no está escrito en el código: se compone leyendo `criteria/`. Cambiar una dimensión, una prioridad o un límite del feedback cambia lo que se le pide **sin tocar Python**. Es la misma relación que ya existe entre `formato.yaml` y la comprobación de formato.

**Files:**
- Create: `backend/analisis/instruccion.py`
- Create: `tests/analisis/test_instruccion.py`

**Interfaces:**
- Consumes: `criteria/<version>/{dimensiones,prioridades,feedback}.yaml`.
- Produces: `construir(raiz: Path, version: str, fase: str, modalidad: str | None = None) -> str`

- [ ] **Step 1: Escribir los tests**

Crear `tests/analisis/test_instruccion.py`:

```python
"""Lo que se le pide al motor sale de los criterios, no del código."""

from pathlib import Path

from backend.analisis.instruccion import construir


def test_pide_solo_las_dimensiones_de_esa_fase(criterios_de_analisis: Path) -> None:
    """D08 no está activa en E2 y no debe aparecer en lo que se le pide."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "D05" in texto
    assert "D08" not in texto


def test_en_una_fase_posterior_pide_mas(criterios_de_analisis: Path) -> None:
    en_e2 = construir(criterios_de_analisis, "v2026-2027", "E2")
    en_final = construir(criterios_de_analisis, "v2026-2027", "FINAL")

    assert "D08" in en_final
    assert len(en_final) > len(en_e2)


def test_lleva_el_nombre_de_cada_dimension(criterios_de_analisis: Path) -> None:
    """El código D05 no le dice nada a nadie; el nombre sí."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Fundamentacion y fuentes" in texto


def test_explica_los_cuatro_niveles_de_prioridad(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    for codigo in ("P1", "P2", "P3", "P4"):
        assert codigo in texto
    assert "No compensa el coste pedagogico" in texto


def test_exige_evidencia_literal(criterios_de_analisis: Path) -> None:
    """Es la instrucción que sostiene la primera defensa."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "literal" in texto.lower()


def test_prohibe_la_nota(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "no propongas" in texto.lower() or "no asignes" in texto.lower()
    assert "nota" in texto.lower()


def test_prohibe_afirmar_la_autoria(criterios_de_analisis: Path) -> None:
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "no afirmes" in texto.lower()


def test_traslada_el_rigor_proporcional(criterios_de_analisis: Path) -> None:
    """El §2 del calibrador: rigor de FP, no auditoría."""
    texto = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Formacion Profesional" in texto or "Formación Profesional" in texto


def test_cambiar_un_criterio_cambia_la_instruccion(
    criterios_de_analisis: Path,
) -> None:
    """La prueba de que la instrucción se lee y no se escribe a mano."""
    dimensiones = criterios_de_analisis / "criteria" / "v2026-2027" / "dimensiones.yaml"
    antes = construir(criterios_de_analisis, "v2026-2027", "E2")

    dimensiones.write_text(
        dimensiones.read_text(encoding="utf-8").replace(
            "Fundamentacion y fuentes", "Rigor de las fuentes citadas"
        ),
        encoding="utf-8",
    )
    despues = construir(criterios_de_analisis, "v2026-2027", "E2")

    assert "Rigor de las fuentes citadas" in despues
    assert antes != despues


def test_sin_criterios_no_se_inventa_una_instruccion(tmp_path: Path) -> None:
    """Sin dimensiones no hay nada que pedir, y se dice en vez de improvisar."""
    import pytest

    with pytest.raises(ValueError, match="dimensiones"):
        construir(tmp_path, "v2026-2027", "E2")
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/analisis/test_instruccion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.analisis.instruccion'`

- [ ] **Step 3: Escribir `backend/analisis/instruccion.py`**

```python
"""Lo que se le pide al motor, compuesto desde los criterios.

Nada de lo que aquí se pide está escrito en este fichero como criterio: las
dimensiones, sus nombres, los niveles de prioridad y los límites del feedback
se leen de `criteria/`. Cambiar un criterio cambia lo que se le pide sin tocar
Python, igual que cambiar `formato.yaml` cambia lo que se comprueba de un PDF.

Lo que sí está aquí es la forma de pedirlo: el tono, el orden y las
prohibiciones. Eso no es criterio académico, es cómo se le habla a un modelo.
"""

from pathlib import Path

import yaml

# Las prohibiciones que no salen de un fichero de criterios porque no son
# criterio de corrección: son límites del sistema, fijados por el §13 del
# Maestro y el anexo B del calibrador.
_PROHIBICIONES = """
No propongas ninguna nota ni calificacion. No la hay: las ponderaciones
oficiales todavia no existen y el sistema no las inventa.

No afirmes que un texto lo ha escrito una inteligencia artificial. Si observas
algo que lo sugiera, registralo como indicio y deja la decision al profesor.

No juzgues ideologias, enfoques personales ni estilos. Senala falta de
neutralidad academica, incoherencia, riesgo etico o ausencia de fuentes solo
cuando haya evidencia en el documento.

Cita siempre de forma literal. Un fragmento copiado del trabajo, no un
resumen: el profesor tiene que poder ir a esa pagina y leer eso mismo. Una
parafrasis no vale como evidencia.
""".strip()


def _cargar(raiz: Path, version: str, nombre: str):
    fichero = raiz / "criteria" / version / f"{nombre}.yaml"
    if not fichero.is_file():
        return None
    return yaml.safe_load(fichero.read_text(encoding="utf-8"))


def construir(
    raiz: Path, version: str, fase: str, modalidad: str | None = None
) -> str:
    """Compone la instrucción para una fase concreta.

    Sin dimensiones no se improvisa nada: si no se pueden leer, se dice. Pedir
    un juicio sin saber qué se está evaluando produciría una respuesta con
    forma de análisis y ningún criterio detrás, que es peor que no tener nada.
    """
    dimensiones = _cargar(raiz, version, "dimensiones")
    if not dimensiones:
        raise ValueError(
            f"No se han podido leer las dimensiones de criteria/{version}/. "
            "Sin ellas no se puede pedir un analisis: no habria nada que valorar."
        )

    activas = [
        d for d in dimensiones
        if isinstance(d, dict) and fase in (d.get("activa_en") or [])
    ]
    prioridades = _cargar(raiz, version, "prioridades") or []
    feedback = _cargar(raiz, version, "feedback") or {}

    partes = [
        "Eres el asistente de correccion de Proyectos Intermodulares de "
        "Formacion Profesional de un profesor. Tu trabajo es valorar una "
        "entrega y darle a el la informacion que necesita para corregirla. "
        "No corriges tu: propones y te detienes.",
        "",
        f"Esta entrega corresponde a la fase {fase}"
        + (f", modalidad {modalidad}." if modalidad else "."),
        "",
        "El nivel de exigencia es el de un Proyecto Intermodular de Formacion "
        "Profesional. Detectar no es perseguir: no conviertas la correccion en "
        "una auditoria empresarial ni en una tesis. No exijas viabilidad "
        "empresarial absoluta ni verifiques cada cifra externa; acepta "
        "estimaciones razonables si estan identificadas y explicadas.",
        "",
        "Valora estas dimensiones, y solo estas:",
    ]
    for d in activas:
        linea = f"- {d['codigo']}: {d.get('nombre', '')}"
        if d.get("observa"):
            linea += f". {d['observa']}"
        partes.append(linea)

    partes += ["", "Clasifica cada hallazgo con uno de estos niveles de prioridad:"]
    for p in prioridades:
        if isinstance(p, dict):
            partes.append(f"- {p['codigo']} ({p.get('nombre','')}): {p.get('efecto','')}")

    economia = (feedback.get("economia_pedagogica") or {}).get("prioridades_maximas")
    if economia:
        partes += [
            "",
            f"Si encuentras muchos problemas, identifica cuales desbloquean el "
            f"desarrollo y cuales pueden esperar. El profesor solo trasladara "
            f"al alumno {economia} como mucho.",
        ]

    partes += ["", _PROHIBICIONES]
    return "\n".join(partes)
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/analisis/test_instruccion.py -v`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/analisis tests/analisis
git commit -m "feat: la instruccion se compone desde los criterios

Las dimensiones, sus nombres, los niveles de prioridad y el limite del
feedback se leen de criteria/. Cambiar un criterio cambia lo que se le pide
al motor sin tocar Python, igual que cambiar formato.yaml cambia lo que se
comprueba de un PDF. Hay un test que lo fija renombrando una dimension y
comprobando que la instruccion cambia.

Lo que si esta en el codigo es la forma de pedirlo —el tono, el orden y las
prohibiciones—, porque eso no es criterio academico sino como se le habla a
un modelo.

Sin dimensiones no se improvisa: se dice. Pedir un juicio sin saber que se
evalua daria una respuesta con forma de analisis y ningun criterio detras."
```

---

### Task 6: El adaptador de OpenAI

El mismo puerto, contra el proveedor real. Se usa la API de Responses con `text_format`, que valida la estructura antes de devolverla y separa la instrucción del contenido — que es exactamente nuestro diseño.

**El modelo no se codifica aquí.** Se lee de la configuración, y si no está, el sistema usa el simulado y lo dice. No se pone un nombre por defecto porque no sabemos qué modelos tiene disponibles la cuenta del profesor, y elegir uno a ciegas produciría un fallo en la primera llamada real con un mensaje que no ayudaría.

**Files:**
- Create: `backend/analisis/openai.py`
- Create: `tests/analisis/test_openai.py`
- Modify: `backend/configuracion.py` (leer `OPENAI_API_KEY` y `REVISOR_MODELO_ANALISIS`)
- Modify: `.env.example`

**Interfaces:**
- Consumes: `AnalisisDelMotor`, `esquema_estricto` (Task 1); `ErrorDelProveedor`, `RespuestaNoValida` (Task 4).
- Produces:
  - `ProveedorOpenAI(clave: str, modelo: str, cliente=None)` que implementa `ProveedorAnalisis`
  - `crear_proveedor(configuracion) -> ProveedorAnalisis` en `backend/analisis/__init__.py`

- [ ] **Step 1: Ampliar la configuración**

En `backend/configuracion.py`, añadir dos claves junto a las que ya hay:

```python
CLAVE_OPENAI = "OPENAI_API_KEY"
MODELO = "REVISOR_MODELO_ANALISIS"
```

Añadir a `Configuracion` los campos `clave_openai: str | None = None` y `modelo_analisis: str | None = None`, y leerlos en `cargar` igual que los demás.

Y en `.env.example`, junto a `OPENAI_API_KEY`:

```
# Modelo con el que se analiza. Sin este valor el sistema arranca igual, pero
# el analisis lo hace el proveedor simulado y lo avisa en pantalla: un
# analisis simulado no es un analisis. Pon aqui el identificador exacto del
# modelo que quieras usar de los que tenga disponibles tu cuenta.
REVISOR_MODELO_ANALISIS=
```

- [ ] **Step 2: Escribir los tests**

Crear `tests/analisis/test_openai.py`:

```python
"""El adaptador real, contra un cliente simulado.

No se llama a OpenAI: se comprueba que se le pide lo que hay que pedirle y que
sus fallos se traducen a algo que el profesor entienda.
"""

import pytest

from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.openai import ProveedorOpenAI
from backend.analisis.proveedor import ErrorDelProveedor, RespuestaNoValida

VACIO = AnalisisDelMotor(
    valoraciones=[], fortalezas=[], patrones=[],
    dudas_para_el_docente=[], indicios_de_autoria=[],
)


class _RespuestaFalsa:
    def __init__(self, parsed=VACIO):
        self.output_parsed = parsed


class _ClienteFalso:
    """Imita lo justo del cliente de OpenAI: responses.parse."""

    def __init__(self, resultado=None, error=None):
        self.recibido = {}
        self._resultado = resultado if resultado is not None else _RespuestaFalsa()
        self._error = error
        self.responses = self

    def parse(self, **kwargs):
        self.recibido = kwargs
        if self._error:
            raise self._error
        return self._resultado


def test_devuelve_el_analisis_ya_validado() -> None:
    cliente = _ClienteFalso()
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    assert p.analizar("instruccion", "texto", AnalisisDelMotor) is VACIO


def test_envia_la_instruccion_separada_del_texto() -> None:
    """Es lo que la API de Responses permite y nuestro diseño aprovecha."""
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar(
        "la instruccion", "el trabajo del alumno", AnalisisDelMotor
    )

    assert cliente.recibido["instructions"] == "la instruccion"
    assert "el trabajo del alumno" in str(cliente.recibido["input"])


def test_pide_la_estructura_del_contrato() -> None:
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["text_format"] is AnalisisDelMotor


def test_usa_el_modelo_configurado() -> None:
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "el-modelo-elegido", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["model"] == "el-modelo-elegido"


def test_pide_la_respuesta_mas_estable_posible() -> None:
    """Un juicio que cambia cada vez que se pulsa no es un juicio."""
    cliente = _ClienteFalso()
    ProveedorOpenAI("clave", "un-modelo", cliente=cliente).analizar("i", "t", AnalisisDelMotor)

    assert cliente.recibido["temperature"] == 0


def test_una_respuesta_que_no_encaja_es_reintentable() -> None:
    """El fallo más común: se distingue para poder reintentarlo una vez."""
    cliente = _ClienteFalso(resultado=_RespuestaFalsa(parsed=None))
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(RespuestaNoValida):
        p.analizar("i", "t", AnalisisDelMotor)


def test_un_fallo_de_red_llega_en_castellano() -> None:
    cliente = _ClienteFalso(error=ConnectionError("connection refused"))
    p = ProveedorOpenAI("clave", "un-modelo", cliente=cliente)

    with pytest.raises(ErrorDelProveedor) as fallo:
        p.analizar("i", "t", AnalisisDelMotor)

    assert "no se ha podido" in str(fallo.value).lower()
    assert "connection refused" in str(fallo.value)


def test_el_nombre_dice_que_modelo_se_uso() -> None:
    """El informe lo guarda: dentro de un año importará con qué se hizo."""
    p = ProveedorOpenAI("clave", "un-modelo", cliente=_ClienteFalso())

    assert p.nombre == "openai:un-modelo"


def test_no_se_construye_sin_modelo() -> None:
    """Antes que elegir uno a ciegas, no arrancar."""
    with pytest.raises(ValueError, match="modelo"):
        ProveedorOpenAI("clave", "", cliente=_ClienteFalso())
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/analisis/test_openai.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.analisis.openai'`

- [ ] **Step 4: Escribir `backend/analisis/openai.py`**

```python
"""El proveedor real, por la API de Responses de OpenAI.

Se usa `responses.parse` y no `chat.completions.parse` por una razón que
encaja con el diseño: permite separar la instruccion —lo que se le pide, que
sale de los criterios— del contenido —el trabajo del alumno—. Ademas valida la
estructura contra el contrato antes de devolverla, asi que una respuesta que
no encaje no llega ni a nuestro codigo.

El modelo no esta escrito aqui. Se configura, y sin el no se construye este
proveedor: elegir uno a ciegas produciria un fallo en la primera llamada real
con un mensaje que no ayudaria a nadie.
"""

from typing import TypeVar

from pydantic import BaseModel

from backend.analisis.proveedor import ErrorDelProveedor, RespuestaNoValida

T = TypeVar("T", bound=BaseModel)

ESPERA = 120.0


class ProveedorOpenAI:
    """Pide el analisis a OpenAI y devuelve el formulario ya validado."""

    def __init__(self, clave: str, modelo: str, cliente=None) -> None:
        if not modelo:
            raise ValueError(
                "No hay modelo de analisis configurado. Indica cual usar en "
                "REVISOR_MODELO_ANALISIS, dentro del fichero .env."
            )
        self._modelo = modelo
        if cliente is None:
            from openai import OpenAI

            cliente = OpenAI(api_key=clave, timeout=ESPERA)
        self._cliente = cliente

    @property
    def nombre(self) -> str:
        """Queda guardado en el informe: dentro de un ano importara."""
        return f"openai:{self._modelo}"

    def analizar(self, instruccion: str, texto: str, formato: type[T]) -> T:
        try:
            respuesta = self._cliente.responses.parse(
                model=self._modelo,
                instructions=instruccion,
                input=texto,
                text_format=formato,
                # Un juicio que cambia cada vez que se pulsa no es un juicio.
                temperature=0,
            )
        except Exception as fallo:
            raise ErrorDelProveedor(
                "No se ha podido obtener el analisis del proveedor. "
                f"Motivo: {fallo}"
            ) from fallo

        analisis = getattr(respuesta, "output_parsed", None)
        if analisis is None:
            raise RespuestaNoValida(
                "El proveedor ha respondido, pero lo devuelto no encaja con lo "
                "que se le pidio. Se puede reintentar."
            )
        return analisis
```

- [ ] **Step 5: Añadir `crear_proveedor` a `backend/analisis/__init__.py`**

```python
"""Pide el juicio a un modelo de lenguaje y lo comprueba antes de creerlo."""


def crear_proveedor(configuracion):
    """OpenAI si hay clave y modelo; el simulado en cualquier otro caso.

    No se falla por falta de configuracion: el sistema arranca igual y avisa
    de que el analisis es simulado. Quien esta probando el flujo no deberia
    necesitar una clave, y quien corrige de verdad vera el aviso.
    """
    from backend.analisis.proveedor import ProveedorSimulado

    if configuracion.clave_openai and configuracion.modelo_analisis:
        from backend.analisis.openai import ProveedorOpenAI

        return ProveedorOpenAI(
            configuracion.clave_openai, configuracion.modelo_analisis
        )
    return ProveedorSimulado(respuestas=[])
```

- [ ] **Step 6: Ejecutar la batería y comitear**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`
Expected: todo en verde.

```bash
git add backend tests .env.example
git commit -m "feat: el proveedor real, por la API de Responses

Se usa responses.parse y no chat.completions.parse porque permite separar la
instruccion —que sale de los criterios— del contenido —el trabajo del
alumno—, que es exactamente nuestro diseno. Y valida la estructura antes de
devolverla, asi que una respuesta que no encaje no llega a nuestro codigo.

El modelo no esta escrito en el codigo: se configura, y sin el este proveedor
no se construye. Elegir uno a ciegas produciria un fallo en la primera
llamada real con un mensaje que no ayudaria a nadie. Sin clave o sin modelo,
el sistema arranca con el simulado y lo avisa.

temperature=0 porque un juicio que cambia cada vez que se pulsa no es un
juicio."
```
---

### Task 7: Qué llega al alumno — las defensas 3 y 4

Antes de redactar nada hay que decidir **qué observaciones pueden salir del informe hacia el borrador**. Son dos reglas, y las dos vienen del calibrador.

Un P4 no llega nunca. Y aunque haya diez candidatas, salen cuatro como mucho, elegidas por prioridad. El resto se queda en el informe, que es donde el docente sí las ve.

**Files:**
- Create: `backend/salidas/__init__.py`
- Create: `backend/salidas/seleccion.py`
- Create: `tests/salidas/test_seleccion.py`

**Interfaces:**
- Consumes: `AnalisisVerificado`, `ValoracionVerificada` (Task 3); `criteria/<version>/feedback.yaml`.
- Produces: `seleccionar_prioridades(raiz: Path, version: str, analisis: AnalisisVerificado) -> list[ValoracionVerificada]`

- [ ] **Step 1: Escribir los tests**

Crear `tests/salidas/test_seleccion.py`:

```python
"""Qué observaciones pueden pasar del informe al borrador."""

from pathlib import Path

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import AnalisisVerificado, ValoracionVerificada
from backend.salidas.seleccion import seleccionar_prioridades


def _v(dimension, prioridad, localizada=True, nivel="EN_DESARROLLO"):
    return ValoracionVerificada(
        dimension=dimension,
        nivel=nivel,
        prioridad=prioridad,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
        observacion=f"Observacion de {dimension}.",
        evidencia_localizada=localizada,
    )


def _analisis(valoraciones):
    return AnalisisVerificado(
        valoraciones=valoraciones, fortalezas=[], patrones=[],
        dudas_para_el_docente=[], indicios_de_autoria=[],
        dimensiones_ausentes=[], reparos=[],
    )


def test_un_p4_no_llega_nunca(criterios_de_analisis: Path) -> None:
    """El §7 del calibrador: no debe cargarse al alumno."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P4"), _v("D07", "P4")]),
    )

    assert elegidas == []


def test_como_mucho_cuatro(criterios_de_analisis: Path) -> None:
    """Economía pedagógica: si hay diez errores, no se trasladan los diez."""
    muchas = [_v(f"D0{i}", "P2") for i in range(1, 8)]

    elegidas = seleccionar_prioridades(criterios_de_analisis, "v2026-2027",
                                       _analisis(muchas))

    assert len(elegidas) == 4


def test_los_criticos_van_primero(criterios_de_analisis: Path) -> None:
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P3"), _v("D07", "P1"), _v("D12", "P2")]),
    )

    assert [v.prioridad for v in elegidas] == ["P1", "P2", "P3"]


def test_un_critico_desplaza_a_los_secundarios(criterios_de_analisis: Path) -> None:
    """Con cinco candidatas y sitio para cuatro, cae el menos prioritario."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D01", "P3"), _v("D02", "P3"), _v("D05", "P1"),
                   _v("D07", "P1"), _v("D12", "P2")]),
    )

    assert len(elegidas) == 4
    assert [v.prioridad for v in elegidas] == ["P1", "P1", "P2", "P3"]


def test_una_evidencia_no_localizada_no_llega_al_alumno(
    criterios_de_analisis: Path,
) -> None:
    """La primera defensa, aplicada donde importa: si no se pudo señalar en el
    documento, el alumno no lo recibe. El docente sí lo ve en el informe."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P1", localizada=False), _v("D07", "P2")]),
    )

    assert [v.dimension for v in elegidas] == ["D07"]


def test_una_valoracion_sin_prioridad_no_es_una_accion(
    criterios_de_analisis: Path,
) -> None:
    """Sin prioridad no hay nada que pedirle al alumno que haga."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", None, nivel="SOLIDO")]),
    )

    assert elegidas == []


def test_el_limite_sale_del_fichero_de_criterios(criterios_de_analisis: Path) -> None:
    """Cambiar el criterio cambia el límite, sin tocar código."""
    fichero = criterios_de_analisis / "criteria" / "v2026-2027" / "feedback.yaml"
    fichero.write_text(
        fichero.read_text(encoding="utf-8").replace(
            "prioridades_maximas: 4", "prioridades_maximas: 2"
        ),
        encoding="utf-8",
    )

    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v(f"D0{i}", "P2") for i in range(1, 6)]),
    )

    assert len(elegidas) == 2
```

- [ ] **Step 2: Añadir `feedback.yaml` al fixture**

En `tests/conftest.py`, dentro de `criterios_de_analisis`, añadir tras la línea que escribe `formato.yaml`:

```python
    (carpeta / "feedback.yaml").write_text(
        "economia_pedagogica:\n"
        "  prioridades_maximas: 4\n"
        "  fuente: calibracion#2-rigor-proporcional\n",
        encoding="utf-8",
    )
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/salidas/test_seleccion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.salidas'`

- [ ] **Step 4: Escribir `backend/salidas/__init__.py` y `seleccion.py`**

`__init__.py`:

```python
"""Compone las dos salidas a partir de un analisis ya verificado."""
```

`seleccion.py`:

```python
"""Que observaciones pueden pasar del informe al borrador del alumno.

Tres filtros, y ninguno es una preferencia de estilo:

Un P4 no llega nunca. El §7 del calibrador dice que no compensa el coste
pedagogico y que no debe cargarse al alumno.

Una observacion cuya evidencia no se pudo localizar en el documento tampoco
llega. El docente la ve en el informe, marcada, y decide; pero no se le pide a
un alumno que corrija algo que el sistema no ha sabido senalar en su trabajo.

Y aunque queden diez, salen cuatro como mucho. Es la regla de economia
pedagogica del §2.3: si hay diez errores, no se trasladan los diez, se
identifican los que desbloquean el desarrollo.
"""

from pathlib import Path

import yaml

from backend.analisis.verificacion import AnalisisVerificado, ValoracionVerificada

# Si el fichero de criterios no dice otra cosa. El valor real vive alli.
_MAXIMO_POR_OMISION = 4

# El orden en que se eligen cuando hay mas candidatas que sitio.
_ORDEN = {"P1": 0, "P2": 1, "P3": 2}


def _maximo(raiz: Path, version: str) -> int:
    fichero = raiz / "criteria" / version / "feedback.yaml"
    if not fichero.is_file():
        return _MAXIMO_POR_OMISION
    datos = yaml.safe_load(fichero.read_text(encoding="utf-8")) or {}
    economia = datos.get("economia_pedagogica") or {}
    return int(economia.get("prioridades_maximas") or _MAXIMO_POR_OMISION)


def seleccionar_prioridades(
    raiz: Path, version: str, analisis: AnalisisVerificado
) -> list[ValoracionVerificada]:
    """Las observaciones que pueden llegar al alumno, ya ordenadas."""
    candidatas = [
        v for v in analisis.valoraciones
        if v.prioridad in _ORDEN and v.evidencia_localizada
    ]
    candidatas.sort(key=lambda v: (_ORDEN[v.prioridad], v.dimension))
    return candidatas[: _maximo(raiz, version)]
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/salidas -v`
Expected: PASS, 7 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/salidas tests/
git commit -m "feat: que observaciones pueden llegar al alumno

Tres filtros y ninguno es preferencia de estilo. Un P4 no llega nunca, por
el 7 del calibrador. Una observacion cuya evidencia no se pudo localizar
tampoco: el docente la ve marcada en el informe y decide, pero no se le pide
a un alumno que corrija algo que el sistema no ha sabido senalar en su
trabajo. Y aunque queden diez, salen cuatro como mucho.

El limite sale del fichero de criterios, con test que lo comprueba
cambiandolo a dos."
```

---

### Task 8: El borrador también es un formulario

Aquí va la decisión que hace comprobable el control de coherencia del §17.2.

El borrador **no se pide como un texto suelto**. Se le pide al motor la misma estructura que describe el Anexo D: apertura, fortalezas, acciones y cierre, cada una en su campo. Con eso, comprobar que el borrador no contradice al informe deja de ser un análisis del lenguaje y pasa a ser una comparación de listas.

Si le pidiéramos un párrafo libre, para saber si dice «está todo bien» habría que interpretarlo — y para interpretarlo haría falta otro modelo, que también podría equivocarse. Así no: **las acciones del borrador son exactamente las observaciones seleccionadas, y eso se cuenta.**

**Files:**
- Create: `backend/salidas/borrador.py`
- Create: `tests/salidas/test_borrador.py`

**Interfaces:**
- Consumes: `seleccionar_prioridades` (Task 7); `ProveedorAnalisis` (Task 4); `criteria/<version>/feedback.yaml`.
- Produces:
  - `Devolucion(BaseModel)` con `apertura: str`, `fortalezas: list[str]`, `acciones: list[str]`, `cierre: str`
  - `instruccion_de_devolucion(raiz, version, analisis, elegidas) -> str`
  - `componer(raiz, version, proveedor, analisis) -> Devolucion`

- [ ] **Step 1: Escribir los tests**

Crear `tests/salidas/test_borrador.py`:

```python
"""El borrador de devolución, pedido como formulario y no como texto suelto."""

from pathlib import Path

import pytest

from backend.analisis.contrato import Evidencia
from backend.analisis.proveedor import ProveedorSimulado
from backend.analisis.verificacion import AnalisisVerificado, ValoracionVerificada
from backend.salidas.borrador import Devolucion, componer, instruccion_de_devolucion


def _v(dimension="D05", prioridad="P2", localizada=True):
    return ValoracionVerificada(
        dimension=dimension, nivel="EN_DESARROLLO", prioridad=prioridad,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
        observacion=f"Falta justificar las cifras de {dimension}.",
        evidencia_localizada=localizada,
    )


def _analisis(valoraciones, fortalezas=None):
    return AnalisisVerificado(
        valoraciones=valoraciones,
        fortalezas=fortalezas if fortalezas is not None else ["La estructura es clara."],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
        dimensiones_ausentes=[], reparos=[],
    )


def _devolucion(acciones=("Justifica las cifras del presupuesto.",)):
    return Devolucion(
        apertura="Has avanzado respecto a la entrega anterior.",
        fortalezas=["La estructura del documento es clara."],
        acciones=list(acciones),
        cierre="Vas bien encaminado; céntrate en lo anterior para la siguiente fase.",
    )


def test_la_devolucion_es_una_estructura_no_un_parrafo() -> None:
    """De aquí sale que la coherencia se pueda comprobar contando."""
    d = _devolucion()

    assert isinstance(d.acciones, list)
    assert d.apertura and d.cierre


def test_la_instruccion_solo_lleva_las_observaciones_elegidas(
    criterios_de_analisis: Path,
) -> None:
    """Lo que no pasa el filtro no se le enseña al motor siquiera."""
    analisis = _analisis([_v("D05", "P2"), _v("D07", "P4")])

    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", analisis, [_v("D05", "P2")]
    )

    assert "D05" in texto
    assert "D07" not in texto


def test_la_instruccion_prohibe_la_nota(criterios_de_analisis: Path) -> None:
    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", _analisis([_v()]), [_v()]
    )

    assert "nota" in texto.lower()


def test_la_instruccion_pide_el_formato_del_calibrador(
    criterios_de_analisis: Path,
) -> None:
    """Dos párrafos, cercano y firme: lo fija el §4 y sale del fichero."""
    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", _analisis([_v()]), [_v()]
    )

    assert "dos" in texto.lower()


def test_componer_devuelve_lo_que_redacto_el_motor(
    criterios_de_analisis: Path,
) -> None:
    proveedor = ProveedorSimulado(respuestas=[_devolucion()])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))

    assert d.apertura.startswith("Has avanzado")


def test_componer_no_pide_nada_si_no_hay_acciones_ni_fortalezas(
    criterios_de_analisis: Path,
) -> None:
    """Sin nada que decir no se gasta una llamada ni se inventa un texto."""
    proveedor = ProveedorSimulado(respuestas=[])

    d = componer(
        criterios_de_analisis, "v2026-2027", proveedor,
        _analisis([_v("D05", "P4")], fortalezas=[]),
    )

    assert d.acciones == []
    assert proveedor.llamadas == []


def test_el_motor_no_puede_anadir_acciones_de_su_cosecha(
    criterios_de_analisis: Path,
) -> None:
    """Si devuelve más acciones que las que se le dieron, se recortan.

    Es el control de coherencia por el lado que importa: el borrador no puede
    pedirle al alumno cosas que no están en el informe.
    """
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(acciones=["La que toca.", "Una que me he inventado.",
                              "Y otra mas."])
    ])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor,
                 _analisis([_v("D05", "P2")]))

    assert len(d.acciones) == 1
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/salidas/test_borrador.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.salidas.borrador'`

- [ ] **Step 3: Escribir `backend/salidas/borrador.py`**

```python
"""El borrador de devolucion, pedido como formulario.

La decision que sostiene el control de coherencia del §17.2: al motor no se le
pide un texto, se le piden los cuatro bloques del Anexo D por separado. Con eso,
comprobar que el borrador no contradice al informe deja de ser un analisis del
lenguaje y pasa a ser una comparacion de listas.

Si se le pidiera un parrafo libre, para saber si dice «esta todo bien» habria
que interpretarlo, y para interpretarlo haria falta otro modelo, que tambien
puede equivocarse. Asi no: las acciones del borrador son exactamente las
observaciones que pasaron el filtro, y eso se cuenta.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.proveedor import ProveedorAnalisis
from backend.analisis.verificacion import AnalisisVerificado, ValoracionVerificada
from backend.salidas.seleccion import seleccionar_prioridades


class Devolucion(BaseModel):
    """Los cuatro bloques del Anexo D."""

    model_config = ConfigDict(extra="forbid")

    apertura: str
    fortalezas: list[str]
    acciones: list[str]
    cierre: str


def _feedback(raiz: Path, version: str) -> dict:
    fichero = raiz / "criteria" / version / "feedback.yaml"
    if not fichero.is_file():
        return {}
    return yaml.safe_load(fichero.read_text(encoding="utf-8")) or {}


def instruccion_de_devolucion(
    raiz: Path,
    version: str,
    analisis: AnalisisVerificado,
    elegidas: list[ValoracionVerificada],
) -> str:
    """Lo que se le pide al motor para redactar.

    Solo se le ensenan las observaciones que ya pasaron el filtro. Lo que no
    puede llegar al alumno no se le muestra siquiera: es mas facil que no
    aparezca en el texto si el motor no lo ha visto.
    """
    criterios = _feedback(raiz, version)
    extension = criterios.get("extension_devolucion") or {}
    estilo = criterios.get("estilo") or {}

    partes = [
        "Redacta la devolucion para el alumno a partir de lo siguiente. "
        "Escribes tu para que el profesor lo revise: el decide si se envia y "
        "con que palabras.",
        "",
        f"Extension: {extension.get('parrafos_habituales', 2)} parrafos. "
        "Cercano, directo, firme y constructivo. Sin condescendencia.",
        "",
    ]
    if analisis.fortalezas:
        partes.append("Fortalezas reales del trabajo:")
        partes += [f"- {f}" for f in analisis.fortalezas]
        partes.append("")
    if elegidas:
        partes.append("Acciones prioritarias, en este orden y sin anadir ninguna mas:")
        partes += [f"- ({v.dimension}) {v.observacion}" for v in elegidas]
        partes.append("")
    for evitar in estilo.get("evitar") or []:
        partes.append(f"Evita: {evitar}")

    partes += [
        "",
        "No menciones ninguna nota ni calificacion. No afirmes que el trabajo "
        "lo haya escrito una inteligencia artificial. No incluyas "
        "deliberaciones tecnicas ni observaciones que no esten arriba.",
    ]
    return "\n".join(partes)


def componer(
    raiz: Path,
    version: str,
    proveedor: ProveedorAnalisis,
    analisis: AnalisisVerificado,
) -> Devolucion:
    """Pide la redaccion y recorta lo que el motor haya anadido de su cosecha.

    El recorte no es desconfianza gratuita: es el control de coherencia del
    §17.2 aplicado donde se puede aplicar sin interpretar texto. El borrador no
    puede pedirle al alumno nada que no este en el informe.
    """
    elegidas = seleccionar_prioridades(raiz, version, analisis)
    if not elegidas and not analisis.fortalezas:
        return Devolucion(apertura="", fortalezas=[], acciones=[], cierre="")

    devolucion = proveedor.analizar(
        instruccion_de_devolucion(raiz, version, analisis, elegidas), "", Devolucion
    )
    return Devolucion(
        apertura=devolucion.apertura,
        fortalezas=devolucion.fortalezas[: len(analisis.fortalezas)],
        acciones=devolucion.acciones[: len(elegidas)],
        cierre=devolucion.cierre,
    )
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/salidas -v`
Expected: PASS, 14 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/salidas tests/salidas
git commit -m "feat: el borrador es un formulario, no un parrafo suelto

Al motor se le piden los cuatro bloques del Anexo D por separado. Con eso,
comprobar que el borrador no contradice al informe deja de ser un analisis
del lenguaje y pasa a ser una comparacion de listas.

Si se le pidiera un parrafo libre, para saber si dice \"esta todo bien\"
habria que interpretarlo, y para eso haria falta otro modelo que tambien
puede equivocarse.

Al motor solo se le ensenan las observaciones que ya pasaron el filtro: es
mas facil que no aparezcan en el texto si no las ha visto. Y si aun asi
anade acciones de su cosecha, se recortan."
```
---

### Task 9: El informe técnico interno

El Anexo C, compuesto desde el análisis verificado. Es la salida donde **sí** aparece todo: los P4, las observaciones cuya evidencia no se localizó, los reparos y las dudas. Al alumno le llega un resumen; al docente, el trabajo entero.

**Files:**
- Create: `backend/salidas/informe.py`
- Create: `tests/salidas/test_informe.py`

**Interfaces:**
- Consumes: `AnalisisVerificado` (Task 3), `seleccionar_prioridades` (Task 7), `EntregaRegistrada` y `FichaDeLectura` de la Parte A.
- Produces:
  - `Informe(BaseModel)` con `identificacion: dict[str, str]`, `control_administrativo: list[str]`, `resumen: str`, `valoraciones: list[ValoracionVerificada]`, `fortalezas: list[str]`, `prioridades: list[ValoracionVerificada]`, `dudas: list[str]`, `indicios: list[str]`, `reparos: list[Reparo]`, `semaforo: str | None`, `motor: str`
  - `componer_informe(raiz, version, entrega, ficha, analisis, motor) -> Informe`

- [ ] **Step 1: Escribir los tests**

Crear `tests/salidas/test_informe.py`:

```python
"""El Anexo C: todo lo que el docente necesita ver."""

from pathlib import Path

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import (
    AnalisisVerificado, Reparo, ValoracionVerificada,
)
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.informe import componer_informe
from datetime import datetime


def _entrega():
    return EntregaRegistrada(
        id="id-1", codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023/AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        recibida_en=datetime(2026, 1, 15, 10, 0), estado="RECIBIDO",
        motivo_bloqueo=None, version_criterios="v2026-2027",
    )


def _v(dimension="D05", prioridad="P2", localizada=True):
    return ValoracionVerificada(
        dimension=dimension, nivel="EN_DESARROLLO", prioridad=prioridad,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
        observacion=f"Observacion de {dimension}.", evidencia_localizada=localizada,
    )


def _analisis(valoraciones, **cambios):
    datos = dict(
        valoraciones=valoraciones, fortalezas=["La estructura es clara."],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
        dimensiones_ausentes=[], reparos=[],
    )
    datos.update(cambios)
    return AnalisisVerificado(**datos)


def test_identifica_la_entrega(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert i.identificacion["alumno"] == "AF023"
    assert i.identificacion["fase"] == "E2"
    assert i.identificacion["criterios"] == "v2026-2027"


def test_deja_constancia_de_con_que_se_analizo(criterios_de_analisis: Path) -> None:
    """Dentro de un año importará si esto lo dijo un modelo o el simulador."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "openai:un-modelo")

    assert i.motor == "openai:un-modelo"


def test_el_informe_si_lleva_los_p4(criterios_de_analisis: Path) -> None:
    """Al alumno no llegan; al docente sí. Esa es la diferencia entre las dos
    salidas."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P4")]), "simulado")

    assert [v.dimension for v in i.valoraciones] == ["D05"]
    assert i.prioridades == []


def test_el_informe_si_lleva_lo_no_localizado(criterios_de_analisis: Path) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1", localizada=False)]), "simulado",
    )

    assert i.valoraciones[0].evidencia_localizada is False
    assert i.prioridades == []


def test_los_reparos_llegan_al_informe(criterios_de_analisis: Path) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], reparos=[Reparo(regla="x", detalle="Algo que revisar.")]),
        "simulado",
    )

    assert i.reparos[0].detalle == "Algo que revisar."


def test_el_informe_no_tiene_nota(criterios_de_analisis: Path) -> None:
    """Ni el campo existe."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert not hasattr(i, "nota")
    assert "nota" not in i.model_dump()


def test_un_p1_pone_el_semaforo_en_rojo(criterios_de_analisis: Path) -> None:
    """El §9 del calibrador: carencia crítica es rojo."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P1")]), "simulado")

    assert i.semaforo == "ROJO"


def test_un_p2_pone_el_semaforo_en_ambar(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P2")]), "simulado")

    assert i.semaforo == "AMBAR"


def test_sin_prioridades_el_semaforo_es_verde(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", None)]), "simulado")

    assert i.semaforo == "VERDE"


def test_sin_ninguna_valoracion_el_semaforo_no_se_inventa(
    criterios_de_analisis: Path,
) -> None:
    """Si el análisis no valoró nada, no hay estado que resumir."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([]), "simulado")

    assert i.semaforo is None
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/salidas/test_informe.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.salidas.informe'`

- [ ] **Step 3: Escribir `backend/salidas/informe.py`**

```python
"""El informe tecnico interno, segun el Anexo C.

Es la salida donde SI aparece todo: los P4, las observaciones cuya evidencia
no se pudo localizar, los reparos de la verificacion y las dudas que el motor
reserva al docente. Al alumno le llega un resumen; al docente, el trabajo
entero. Esa es la diferencia entre las dos salidas, y no es de formato.

No hay campo para la nota. El Anexo C la menciona porque el Maestro la preve
para cuando exista la rubrica; mientras las ponderaciones sigan pendientes, R3
impide inventarla y aqui no existe ni el hueco.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from backend.analisis.verificacion import (
    AnalisisVerificado,
    Reparo,
    ValoracionVerificada,
)
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.seleccion import seleccionar_prioridades

# El §9 del calibrador. Un P1 es carencia critica; un P2 o P3, mejora
# pendiente; sin prioridades, correcto para la fase.
_SEMAFORO_POR_PRIORIDAD = {"P1": "ROJO", "P2": "AMBAR", "P3": "AMBAR"}


class Informe(BaseModel):
    """Los bloques del Anexo C."""

    model_config = ConfigDict(extra="forbid")

    identificacion: dict[str, str]
    control_administrativo: list[str]
    resumen: str
    valoraciones: list[ValoracionVerificada]
    fortalezas: list[str]
    prioridades: list[ValoracionVerificada]
    dudas: list[str]
    indicios: list[str]
    reparos: list[Reparo]
    dimensiones_ausentes: list[str]
    semaforo: str | None
    motor: str


def _semaforo(analisis: AnalisisVerificado) -> str | None:
    """El peor de los estados que se desprenden de las prioridades.

    Sin ninguna valoracion no se devuelve color: no hay estado que resumir, y
    un verde por defecto diria que el trabajo esta bien cuando lo que pasa es
    que no se ha valorado.
    """
    if not analisis.valoraciones:
        return None
    for codigo in ("P1", "P2", "P3"):
        if any(v.prioridad == codigo for v in analisis.valoraciones):
            return _SEMAFORO_POR_PRIORIDAD[codigo]
    return "VERDE"


def componer_informe(
    raiz: Path,
    version: str,
    entrega: EntregaRegistrada,
    ficha,
    analisis: AnalisisVerificado,
    motor: str,
) -> Informe:
    """Compone el informe. `ficha` es la lectura objetiva, o None si no la hay."""
    control: list[str] = []
    if ficha is not None and ficha.medidas is not None:
        control.append(f"{ficha.medidas.total_paginas} paginas en total.")
        contadas = ficha.medidas.estructura.paginas_de_contenido
        control.append(
            f"{contadas} paginas de contenido." if contadas is not None
            else "No se ha podido contar el contenido: no se localizo el indice."
        )
        for c in ficha.comprobaciones:
            if c.veredicto == "NO_CUMPLE":
                control.append(f"{c.criterio}: {c.medido}")

    return Informe(
        identificacion={
            "alumno": entrega.codigo_alumno,
            "ciclo": entrega.ciclo,
            "fase": entrega.fase,
            "version": str(entrega.version),
            "archivo": entrega.nombre_archivo,
            "criterios": entrega.version_criterios,
        },
        control_administrativo=control,
        resumen=" ".join(analisis.fortalezas[:1]) or "Sin resumen del motor.",
        valoraciones=analisis.valoraciones,
        fortalezas=analisis.fortalezas,
        prioridades=seleccionar_prioridades(raiz, version, analisis),
        dudas=analisis.dudas_para_el_docente,
        indicios=analisis.indicios_de_autoria,
        reparos=analisis.reparos,
        dimensiones_ausentes=analisis.dimensiones_ausentes,
        semaforo=_semaforo(analisis),
        motor=motor,
    )
```

- [ ] **Step 4: Ejecutar los tests y comitear**

Run: `python -m pytest tests/salidas -v`
Expected: PASS, 24 tests.

```bash
git add backend/salidas tests/salidas
git commit -m "feat: el informe tecnico interno, segun el Anexo C

Es la salida donde SI aparece todo: los P4, lo que no se pudo localizar, los
reparos de la verificacion y las dudas. Al alumno le llega un resumen; al
docente, el trabajo entero. Esa es la diferencia entre las dos salidas y no
es de formato.

No hay campo para la nota: mientras las ponderaciones sigan pendientes, R3
impide inventarla y aqui no existe ni el hueco.

Sin ninguna valoracion no se devuelve color. Un verde por defecto diria que
el trabajo esta bien cuando lo que pasa es que no se ha valorado."
```

---

### Task 10: El servicio que une el análisis con la lectura

Lo que orquesta: toma una entrega ya leída, pide el análisis, lo verifica, compone las dos salidas y lo guarda. Aquí viven las reglas del §5.2 del spec: atomicidad, reintento único y estado.

**Files:**
- Create: `backend/servicios/analisis_de_entrega.py`
- Create: `tests/backend/test_analisis_de_entrega.py`

**Interfaces:**
- Consumes: `leer` y `localizar` de `lectura_objetiva`; `construir` (Task 5); `verificar` (Task 3); `componer_informe` (Task 9); `componer` (Task 8); `ProveedorAnalisis` (Task 4).
- Produces:
  - `Correccion(BaseModel)` con `entrega: EntregaRegistrada`, `informe: Informe`, `devolucion: Devolucion`, `motor: str`
  - `analizar_entrega(raiz, carpeta, version, almacen, proveedor, entrega) -> Correccion`

- [ ] **Step 1: Escribir los tests**

Crear `tests/backend/test_analisis_de_entrega.py`:

```python
"""El servicio que une la lectura con el análisis."""

from pathlib import Path

import pytest

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Valoracion
from backend.analisis.proveedor import (
    ErrorDelProveedor, ProveedorSimulado, RespuestaNoValida,
)
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.salidas.borrador import Devolucion
from backend.servicios.analisis_de_entrega import analizar_entrega


def _analisis_bueno(cita):
    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita=cita, apartado="5"),
            observacion="Faltan fuentes que respalden las cifras.",
        )],
        fortalezas=["La estructura del documento es clara."],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )


def _devolucion():
    return Devolucion(
        apertura="Has avanzado.", fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con fuentes."], cierre="Sigue asi.",
    )


@pytest.fixture
def entregas_con_pdf(tmp_path: Path, escribir_pdf):
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    escribir_pdf(carpeta / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion",
        "El presente proyecto describe la implantacion de un sistema.",
        "5. Presupuesto",
        "El presupuesto inicial asciende a 4.500 euros en total.",
    ]])
    return carpeta


def _registrar(almacen, carpeta):
    from backend.extraccion import medir
    ruta = carpeta / "AF023_DAM_E2_20260115_v1.pdf"
    return almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo=ruta.name, huella=medir(ruta).huella,
        version_criterios="v2026-2027",
    ))


def test_una_correccion_completa(criterios_de_analisis, entregas_con_pdf) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert c.informe.valoraciones[0].dimension == "D05"
    assert c.devolucion.acciones == ["Justifica las cifras con fuentes."]
    assert c.motor == "simulado"


def test_la_entrega_pasa_a_analizada(criterios_de_analisis, entregas_con_pdf) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                     almacen, proveedor, entrega)

    assert almacen.por_id(entrega.id).estado == "ANALIZADO"


def test_si_el_motor_falla_la_entrega_no_cambia_de_estado(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """Ni media correccion ni un estado que miente."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(fallos=[ErrorDelProveedor("sin red")])

    with pytest.raises(ErrorDelProveedor):
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert almacen.por_id(entrega.id).estado == "RECIBIDO"


def test_una_respuesta_mal_formada_se_reintenta_una_vez(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    """El fallo mas comun y el mas barato de resolver."""
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(
        fallos=[RespuestaNoValida("no encaja")],
        respuestas=[_analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
                    _devolucion()],
    )

    c = analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert c.informe.valoraciones
    assert len(proveedor.llamadas) == 3


def test_no_se_reintenta_dos_veces(criterios_de_analisis, entregas_con_pdf) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(
        fallos=[RespuestaNoValida("uno"), RespuestaNoValida("dos")]
    )

    with pytest.raises(RespuestaNoValida):
        analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                         almacen, proveedor, entrega)

    assert len(proveedor.llamadas) == 2


def test_un_pdf_que_no_se_puede_leer_no_llega_al_motor(
    criterios_de_analisis, tmp_path
) -> None:
    """Sin texto no hay nada que analizar, y no se gasta una llamada."""
    from backend.extraccion.lectura import PdfIlegible

    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    (carpeta / "AF023_DAM_E2_20260115_v1.pdf").write_text("no soy un pdf")
    almacen = AlmacenEnMemoria()
    entrega = almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        version_criterios="v2026-2027",
    ))
    proveedor = ProveedorSimulado(respuestas=[])

    with pytest.raises(PdfIlegible):
        analizar_entrega(criterios_de_analisis, carpeta, "v2026-2027",
                         almacen, proveedor, entrega)

    assert proveedor.llamadas == []


def test_al_motor_se_le_envia_el_texto_del_trabajo(
    criterios_de_analisis, entregas_con_pdf
) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas_con_pdf)
    proveedor = ProveedorSimulado(respuestas=[
        _analisis_bueno("El presupuesto inicial asciende a 4.500 euros"),
        _devolucion(),
    ])

    analizar_entrega(criterios_de_analisis, entregas_con_pdf, "v2026-2027",
                     almacen, proveedor, entrega)

    _, texto_enviado = proveedor.llamadas[0]
    assert "El presupuesto inicial asciende a 4.500 euros" in texto_enviado
```

- [ ] **Step 2: Escribir `backend/servicios/analisis_de_entrega.py`**

```python
"""Del archivo al par de salidas.

Aqui viven las tres reglas del §5.2 del diseno, y las tres tienen la misma
raiz: una correccion a medias es peor que ninguna.

Atomica. O se completan las dos salidas o no se guarda nada. Un informe sin
devolucion, o una entrega marcada como analizada sin analisis, dejarian al
docente delante de algo que no puede usar y que ademas parece terminado.

Un reintento, no mas. Una respuesta que no encaja en el formulario es el fallo
mas comun y el mas barato de resolver, asi que se pide otra vez. Si vuelve a
fallar, no es un tropiezo: es que algo no va bien, y insistir solo gasta
dinero.

El estado no miente. Si el analisis no se completo, la entrega sigue en
RECIBIDO.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from backend.analisis.instruccion import construir
from backend.analisis.proveedor import ProveedorAnalisis, RespuestaNoValida
from backend.analisis.contrato import AnalisisDelMotor
from backend.analisis.verificacion import verificar
from backend.persistencia.modelos import Almacen, EntregaRegistrada
from backend.salidas.borrador import Devolucion, componer
from backend.salidas.informe import Informe, componer_informe
from backend.servicios.lectura_objetiva import leer


class Correccion(BaseModel):
    """Las dos salidas de una entrega, con la ficha que las origina."""

    model_config = ConfigDict(extra="forbid")

    entrega: EntregaRegistrada
    informe: Informe
    devolucion: Devolucion
    motor: str


def analizar_entrega(
    raiz: Path,
    carpeta: Path,
    version: str,
    almacen: Almacen,
    proveedor: ProveedorAnalisis,
    entrega: EntregaRegistrada,
) -> Correccion:
    """Lee, analiza, verifica, compone y guarda. O nada."""
    ficha = leer(raiz, carpeta, version, almacen, entrega)
    if ficha.medidas is None:
        # La lectura ya dejo la entrega bloqueada con su motivo; sin texto no
        # hay nada que analizar y no se gasta una llamada.
        from backend.extraccion.lectura import PdfIlegible

        raise PdfIlegible(
            ficha.entrega.motivo_bloqueo or "No se ha podido leer el archivo."
        )

    texto = ficha.medidas.texto_plano
    instruccion = construir(raiz, version, entrega.fase)

    try:
        crudo = proveedor.analizar(instruccion, texto, AnalisisDelMotor)
    except RespuestaNoValida:
        crudo = proveedor.analizar(instruccion, texto, AnalisisDelMotor)

    analisis = verificar(raiz, version, entrega.fase, texto, crudo)
    informe = componer_informe(
        raiz, version, entrega, ficha, analisis, proveedor.nombre
    )
    devolucion = componer(raiz, version, proveedor, analisis)

    actualizada = almacen.cambiar_estado(entrega.id, "ANALIZADO", None) or entrega
    return Correccion(
        entrega=actualizada,
        informe=informe,
        devolucion=devolucion,
        motor=proveedor.nombre,
    )
```

- [ ] **Step 3: Ejecutar los tests y comitear**

Run: `python -m pytest tests/backend/test_analisis_de_entrega.py -v`
Expected: PASS, 7 tests.

```bash
git add backend/servicios tests/backend
git commit -m "feat: el servicio que une la lectura con el analisis

Las tres reglas tienen la misma raiz: una correccion a medias es peor que
ninguna. O se completan las dos salidas o no se guarda nada; una respuesta
mal formada se reintenta UNA vez porque es el fallo mas comun y el mas
barato, pero no dos, porque entonces no es un tropiezo y insistir solo gasta
dinero; y si el analisis no se completo la entrega sigue en RECIBIDO, porque
un estado que miente es peor que un estado atrasado.

Un PDF ilegible no llega al motor: sin texto no hay nada que analizar y no
se gasta una llamada."
```
---

### Task 11: La API del análisis y la revisión

Los endpoints que el frontend consume. Ninguno aprueba, califica ni comunica: eso sigue siendo del docente.

**Files:**
- Create: `backend/api/analisis.py`
- Modify: `backend/app.py` (registrar el router y el proveedor en `app.state`)
- Create: `tests/backend/test_api_analisis.py`

**Interfaces:**
- Consumes: `analizar_entrega` (Task 10); `crear_proveedor` (Task 6).
- Produces:
  - `POST /api/entregas/{id}/analisis` → `Correccion`
  - `GET /api/entregas/{id}/analisis` → `Correccion` o 404 si no se ha analizado
  - `POST /api/entregas/{id}/revision` con `{decisiones: [{dimension, decision, texto}]}` → `Correccion` con lo aprobado
  - `GET /api/motor` → `{nombre: str, es_simulado: bool, avisos: list[str]}`
  - `crear_app(raiz, configuracion=None, almacen=None, proveedor=None)` con la firma ampliada y compatible.

- [ ] **Step 1: Escribir los tests**

Crear `tests/backend/test_api_analisis.py`:

```python
"""Los endpoints del análisis."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.analisis.contrato import AnalisisDelMotor, Evidencia, Valoracion
from backend.analisis.proveedor import ErrorDelProveedor, ProveedorSimulado
from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.salidas.borrador import Devolucion

CITA = "El presupuesto inicial asciende a 4.500 euros"


def _analisis():
    return AnalisisDelMotor(
        valoraciones=[Valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita=CITA, apartado="5"),
            observacion="Faltan fuentes que respalden las cifras.",
        )],
        fortalezas=["La estructura es clara."],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
    )


def _devolucion():
    return Devolucion(
        apertura="Has avanzado.", fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con fuentes."], cierre="Sigue asi.",
    )


@pytest.fixture
def cliente(criterios_de_analisis: Path, tmp_path: Path, escribir_pdf):
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf", [[
        "1. Introduccion", "El proyecto describe un sistema de reservas.",
        "5. Presupuesto", f"{CITA} en total.",
    ]])
    proveedor = ProveedorSimulado(respuestas=[_analisis(), _devolucion()])
    app = crear_app(
        criterios_de_analisis,
        configuracion=Configuracion(carpeta_entregas=entregas,
                                    version_criterios="v2026-2027"),
        almacen=AlmacenEnMemoria(),
        proveedor=proveedor,
    )
    c = TestClient(app)
    c.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })
    c.identificador = c.get("/api/entregas").json()[0]["id"]
    return c


def test_analizar_devuelve_las_dos_salidas(cliente) -> None:
    r = cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 200
    assert r.json()["informe"]["valoraciones"][0]["dimension"] == "D05"
    assert r.json()["devolucion"]["acciones"]


def test_el_analisis_se_recupera_despues(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    r = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 200
    assert r.json()["informe"]["valoraciones"][0]["dimension"] == "D05"


def test_sin_analizar_no_hay_analisis_que_devolver(cliente) -> None:
    r = cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert r.status_code == 404
    assert "no se ha analizado" in r.json()["detail"].lower()


def test_analizar_no_repite_la_llamada_al_motor(cliente) -> None:
    """Un análisis cuesta dinero: pedir la ficha no puede volver a pagarlo."""
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")
    cliente.get(f"/api/entregas/{cliente.identificador}/analisis")
    cliente.get(f"/api/entregas/{cliente.identificador}/analisis")

    assert len(cliente.app.state.proveedor.llamadas) == 2


def test_una_entrega_inexistente_da_404(cliente) -> None:
    assert cliente.post("/api/entregas/no-existe/analisis").status_code == 404


def test_un_fallo_del_motor_llega_en_castellano(criterios_de_analisis, tmp_path,
                                                escribir_pdf) -> None:
    entregas = tmp_path / "entregas"
    entregas.mkdir()
    escribir_pdf(entregas / "AF023_DAM_E2_20260115_v1.pdf",
                 [["1. Introduccion", "Texto suficiente del trabajo."]])
    app = crear_app(
        criterios_de_analisis,
        configuracion=Configuracion(carpeta_entregas=entregas,
                                    version_criterios="v2026-2027"),
        almacen=AlmacenEnMemoria(),
        proveedor=ProveedorSimulado(fallos=[ErrorDelProveedor("sin red")]),
    )
    c = TestClient(app)
    c.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })
    ident = c.get("/api/entregas").json()[0]["id"]

    r = c.post(f"/api/entregas/{ident}/analisis")

    assert r.status_code == 503
    assert "sin red" in r.json()["detail"]


def test_el_motor_se_declara(cliente) -> None:
    """Un análisis simulado no es un análisis y el docente debe saberlo."""
    r = cliente.get("/api/motor")

    assert r.json()["es_simulado"] is True
    assert r.json()["avisos"]


def test_la_revision_conserva_solo_lo_aprobado(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "DESCARTADA", "texto": None}],
    })

    assert r.status_code == 200
    assert r.json()["informe"]["prioridades"] == []


def test_la_revision_admite_editar_el_texto(cliente) -> None:
    cliente.post(f"/api/entregas/{cliente.identificador}/analisis")

    r = cliente.post(f"/api/entregas/{cliente.identificador}/revision", json={
        "decisiones": [{"dimension": "D05", "decision": "EDITADA",
                        "texto": "Justifica las cifras con una fuente."}],
    })

    valorada = r.json()["informe"]["valoraciones"][0]
    assert valorada["observacion"] == "Justifica las cifras con una fuente."


def test_no_hay_endpoint_que_apruebe_ni_califique(cliente) -> None:
    """El §13 reserva eso al profesor: la forma de respetarlo es que no exista."""
    rutas = [r.path for r in cliente.app.routes]

    assert not any("aprobar" in r or "nota" in r or "calificar" in r for r in rutas)
```

- [ ] **Step 2: Escribir `backend/api/analisis.py`**

```python
"""Endpoints del analisis y de la revision.

Ninguno aprueba, califica ni comunica. El §13 reserva eso al profesor y la
forma de respetarlo sigue siendo que las operaciones no existan.

El analisis se guarda al hacerse y se devuelve tal cual despues. Pedir la
ficha no puede volver a llamar al motor: cuesta dinero y, sobre todo, daria
otra cosa, y el docente veria cambiar bajo sus pies un juicio que estaba
revisando.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.analisis.proveedor import ErrorDelProveedor
from backend.servicios.analisis_de_entrega import Correccion, analizar_entrega

router = APIRouter(prefix="/api")

_DECISIONES = ("ACEPTADA", "EDITADA", "DESCARTADA")


class Decision(BaseModel):
    dimension: str
    decision: str
    texto: str | None = None


class Revision(BaseModel):
    decisiones: list[Decision]


class EstadoDelMotor(BaseModel):
    nombre: str
    es_simulado: bool
    avisos: list[str]


def _estado(peticion: Request):
    return (peticion.app.state.raiz, peticion.app.state.configuracion,
            peticion.app.state.almacen, peticion.app.state.proveedor)


@router.get("/motor")
def obtener_motor(peticion: Request) -> EstadoDelMotor:
    proveedor = peticion.app.state.proveedor
    simulado = proveedor.nombre == "simulado"
    return EstadoDelMotor(
        nombre=proveedor.nombre,
        es_simulado=simulado,
        avisos=(
            ["No hay motor de analisis configurado. Lo que veas no es un "
             "analisis: son respuestas de prueba. Indica la clave y el modelo "
             "en OPENAI_API_KEY y REVISOR_MODELO_ANALISIS, dentro del .env."]
            if simulado else []
        ),
    )


@router.post("/entregas/{identificador}/analisis")
def analizar(identificador: str, peticion: Request) -> Correccion:
    raiz, configuracion, almacen, proveedor = _estado(peticion)
    entrega = almacen.por_id(identificador)
    if entrega is None:
        raise HTTPException(status_code=404, detail="No existe esa entrega.")
    if configuracion.carpeta_entregas is None:
        raise HTTPException(
            status_code=409, detail="No hay carpeta de entregas configurada."
        )
    try:
        correccion = analizar_entrega(
            raiz, configuracion.carpeta_entregas, configuracion.version_criterios,
            almacen, proveedor, entrega,
        )
    except ErrorDelProveedor as fallo:
        raise HTTPException(status_code=503, detail=str(fallo)) from fallo

    peticion.app.state.correcciones[identificador] = correccion
    return correccion


@router.get("/entregas/{identificador}/analisis")
def obtener_analisis(identificador: str, peticion: Request) -> Correccion:
    correccion = peticion.app.state.correcciones.get(identificador)
    if correccion is None:
        raise HTTPException(
            status_code=404,
            detail="Esta entrega no se ha analizado todavia.",
        )
    return correccion


@router.post("/entregas/{identificador}/revision")
def revisar(identificador: str, cuerpo: Revision, peticion: Request) -> Correccion:
    """Aplica lo que el docente ha decidido observacion por observacion.

    Solo lo aprobado se conserva. Es lo que el §13 llama revision docente, y
    es la unica via por la que una observacion llega a considerarse valida.
    """
    correccion = peticion.app.state.correcciones.get(identificador)
    if correccion is None:
        raise HTTPException(
            status_code=404, detail="Esta entrega no se ha analizado todavia."
        )

    por_dimension = {d.dimension: d for d in cuerpo.decisiones}
    for d in cuerpo.decisiones:
        if d.decision not in _DECISIONES:
            raise HTTPException(
                status_code=400,
                detail=f"«{d.decision}» no es una decision. Son: "
                       + ", ".join(_DECISIONES) + ".",
            )

    conservadas = []
    for v in correccion.informe.valoraciones:
        decision = por_dimension.get(v.dimension)
        if decision is None or decision.decision == "ACEPTADA":
            conservadas.append(v)
        elif decision.decision == "EDITADA":
            conservadas.append(v.model_copy(
                update={"observacion": decision.texto or v.observacion}
            ))

    informe = correccion.informe.model_copy(update={
        "valoraciones": conservadas,
        "prioridades": [p for p in correccion.informe.prioridades
                        if any(c.dimension == p.dimension for c in conservadas)],
    })
    revisada = correccion.model_copy(update={"informe": informe})
    peticion.app.state.correcciones[identificador] = revisada
    return revisada
```

- [ ] **Step 3: Ampliar `backend/app.py`**

Añadir a `crear_app` el parámetro `proveedor=None`, y en el cuerpo:

```python
    from backend.analisis import crear_proveedor

    app.state.proveedor = proveedor or crear_proveedor(app.state.configuracion)
    # Los análisis de esta sesión. Persistirlos en las tablas es la Task 12.
    app.state.correcciones = {}
```

y registrar el router: `app.include_router(analisis.router)`.

- [ ] **Step 4: Ejecutar los tests y comitear**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`

```bash
git add backend tests
git commit -m "feat: la API del analisis y la revision

Ningun endpoint aprueba, califica ni comunica, y hay un test que recorre las
rutas para comprobarlo: el 13 reserva eso al profesor y la forma de
respetarlo sigue siendo que las operaciones no existan.

El analisis se guarda al hacerse y se devuelve tal cual despues. Pedir la
ficha no puede volver a llamar al motor: cuesta dinero y, sobre todo, daria
otra cosa, y el docente veria cambiar bajo sus pies un juicio que estaba
revisando.

Un fallo del proveedor llega como 503 con su motivo en castellano, no como
error del servidor."
```

---

### Task 12: Persistir el análisis en las tablas

Las tres tablas llevan desde agosto esperando esto: `correccion`, `valoracion_dimension` y `evidencia`. Sus restricciones ya protegen lo que hace falta.

**Files:**
- Modify: `backend/persistencia/modelos.py` (ampliar el protocolo `Almacen`)
- Modify: `backend/persistencia/memoria.py` y `supabase.py`
- Modify: `backend/api/analisis.py` (usar el almacén en vez del diccionario)
- Modify: `tests/persistencia/test_paridad.py`

**Interfaces:**
- Produces, en el protocolo `Almacen`:
  - `guardar_correccion(entrega_id: str, informe: Informe, devolucion: Devolucion, motor: str) -> str`
  - `correccion_de(entrega_id: str) -> Correccion | None`

- [ ] **Step 1: Tests de paridad**

Añadir a `tests/persistencia/test_paridad.py` los casos que comparan los dos almacenes: guardar una corrección y recuperarla, recuperar una que no existe, y guardar dos veces sobre la misma entrega —la segunda sustituye a la primera, porque una entrega tiene una corrección: lo impone el `unique (entrega_id)` de la migración—.

- [ ] **Step 2: Implementar en los dos almacenes**

En memoria, un diccionario. En Supabase, tres `POST` encadenados: `correccion`, luego una `valoracion_dimension` por dimensión, luego una `evidencia` por valoración. **Con la misma regla de atomicidad**: si falla a mitad, se borra la corrección y se levanta `ErrorDeAlmacen`; el `on delete cascade` de la migración se lleva por delante lo que colgaba de ella.

- [ ] **Step 3: Sustituir el diccionario de la API**

`app.state.correcciones` desaparece; `obtener_analisis` y `revisar` van al almacén.

- [ ] **Step 4: Ejecutar todo y comitear**

```bash
git add backend tests
git commit -m "feat: el analisis se guarda en las tres tablas que lo esperaban

correccion, valoracion_dimension y evidencia llevaban desde agosto vacias.
Sus restricciones ya protegen lo que hace falta: una evidencia no pasa de
1.500 caracteres y una entrega tiene una sola correccion.

En Supabase son tres escrituras encadenadas y se aplica la misma regla que
en el resto: si falla a mitad se borra la correccion, y el on delete cascade
se lleva lo que colgaba. Media correccion guardada seria peor que ninguna."
```

---

### Task 13: La pantalla de revisión

Donde el docente decide observación por observación. La última pieza del flujo.

**Files:**
- Modify: `frontend/src/lib/tipos.ts` y `api.ts`
- Create: `frontend/src/paginas/Revision.tsx`
- Create: `frontend/src/componentes/Observacion.tsx`
- Create: sus dos ficheros de test
- Modify: `frontend/src/paginas/Ficha.tsx` (botón de analizar) y `App.tsx`

**Interfaces:**
- Consumes: los endpoints de la Task 11.
- Produces: `Revision` y `Observacion` como componentes con nombre.

- [ ] **Step 1: Tests de `Observacion`**

Una observación se ve con su dimensión, su nivel, su prioridad, su cita y su observación. Tres botones: aceptar, editar y descartar. Al editar aparece un área de texto con el texto original, y hay forma de descartar la edición. Los tests cubren los tres caminos, más el que importa: **una observación cuya evidencia no se localizó se ve marcada y avisa de que no llegará al alumno**.

- [ ] **Step 2: Tests de `Revision`**

La pantalla muestra el informe y el borrador. Los tests cubren: que se ven las dos salidas; que el aviso del motor simulado se ve **antes que nada**; que al descartar una observación desaparece de las prioridades; que al guardar se envían todas las decisiones; que un error del servidor se enseña con su mensaje; y que **no hay ningún control de nota, semáforo editable ni botón de aprobar**.

- [ ] **Step 3: Escribir los componentes**

La tinta `senal` marca aquí lo mismo que en el resto: lo que espera decisión —una observación no localizada, una duda del motor, un indicio de autoría, el aviso del motor simulado—. Un `NO_VERIFICABLE` no la lleva.

- [ ] **Step 4: Enganchar en `Ficha.tsx` y `App.tsx`**

La ficha gana un botón «Analizar» que aparece solo si la entrega está en `RECIBIDO` y la lectura no está bloqueada. Al analizar, se abre la revisión.

- [ ] **Step 5: Ejecutar y comitear**

```bash
git add frontend/src
git commit -m "feat: la pantalla de revision observacion por observacion

El aviso de que el motor es simulado va antes que nada: si el docente va a
leer juicios inventados, tiene que saberlo antes de leerlos, no despues.

Una observacion cuya evidencia no se localizo se ve marcada y dice que no
llegara al alumno. Es la primera defensa hecha visible: el docente puede
aceptarla igualmente si la reconoce, pero decidiendolo el.

Sin control de nota, sin semaforo editable y sin boton de aprobar."
```

---

### Task 14: El arnés de calibración

Un comando aparte de la suite, porque depende de la red y cuesta dinero. Pasa los casos del docente por el motor y compara con lo que él diagnosticó.

**Files:**
- Create: `tools/calibrar.py`
- Create: `docs/calibracion/casos.example.yaml`
- Create: `tests/tools/test_calibrar.py`
- Modify: `.env.example` (`REVISOR_CARPETA_CALIBRACION`)

**Interfaces:**
- Produces:
  - `CasoDeCalibracion(BaseModel)` con `codigo`, `archivo`, `fase`, `semaforo_esperado`, `debe_encontrar: list[str]`, `no_debe`, `notas`
  - `cargar_casos(fichero: Path) -> list[CasoDeCalibracion]`
  - `evaluar(caso, informe) -> ResultadoDeCaso`
  - `ejecutar(raiz, casos, carpeta, proveedor) -> InformeDeCalibracion`

- [ ] **Step 1: El fichero de casos, con los nueve del docente**

`docs/calibracion/casos.example.yaml` recoge los P01–P09 tal como el §6 del documento de calibración los describe, **sin los PDF**, que viven fuera del repositorio. Por ejemplo:

```yaml
- codigo: P01
  archivo: P01.pdf
  fase: E3
  semaforo_esperado: ROJO
  debe_encontrar:
    - desarrollo superficial
    - tablas vacias
    - bibliografia ausente
    - paginas en blanco
  no_debe:
    - enumerar cada defecto menor
  notas: Feedback centrado en desarrollar y cerrar.
```

- [ ] **Step 2: Tests del arnés, contra el proveedor simulado**

Comprueban **el arnés**, no el acierto del motor: que un caso cuyo semáforo coincide se marca como acertado; que uno que no, no; que «debe encontrar» se busca en las observaciones y no en el borrador; que un caso sin PDF se salta con su motivo en vez de reventar; y que el informe final cuenta los siete indicadores del §11.1.

- [ ] **Step 3: Escribir `tools/calibrar.py`**

Con esta advertencia en su docstring y en la salida del comando: **no es un test**. Su resultado es un informe para el docente, no un verde o un rojo. Un caso que no coincide puede significar que el motor se equivocó, o que la referencia era discutible, o que el caso está mal descrito. Decide él.

Y una guarda al arrancar: si la carpeta de calibración contiene trabajos reales y `proteccion_datos` sigue pendiente en `PENDIENTE_OFICIAL`, el comando **avisa y pide confirmación explícita** antes de enviar nada.

- [ ] **Step 4: Ejecutar los tests y comitear**

```bash
git add tools docs/calibracion tests .env.example
git commit -m "feat: el arnes de calibracion

Un comando aparte de la suite, porque depende de la red y cuesta dinero. No
es un test y lo dice: su resultado es un informe para el docente, no un
verde. Un caso que no coincide puede significar que el motor se equivoco,
que la referencia era discutible, o que el caso esta mal descrito, y eso lo
decide el.

Avisa antes de enviar nada si proteccion_datos sigue pendiente: los casos de
calibracion son trabajos reales de alumnos del curso pasado."
```

---

### Task 15: Corregir el §19 del Maestro

Lo que el spec dejó apuntado. El §19 describe hoy un circuito con anonimización previa que ya no se aplica, y una fuente superior no puede quedar contradiciendo al código.

**Files:**
- Modify: `docs/maestro/01-documento-maestro.md` (§19)
- Modify: `docs/decisions.md` (decisión nueva)
- Create: `docs/changes/2026-08-29-el-texto-se-envia-integro.md`
- Modify: `criteria/.sincronia.json` (resellar)

- [ ] **Step 1: Corregir la prosa del §19**

Sustituir la mención a la anonimización previa por la descripción de lo que se hace de verdad: el texto del trabajo se transmite íntegro al proveedor durante el procesamiento, no se almacena allí ni en la base de datos, y la clave reside solo en el backend local.

- [ ] **Step 2: Registrar la decisión**

En `docs/decisions.md`, una decisión nueva que diga qué se decidió, quién y cuándo, por qué contradecía al §19 y qué se corrigió. Y que **sigue en pie** que ninguna entrega real pase por el proveedor hasta que se cierre `proteccion_datos`.

- [ ] **Step 3: El documento de cambio**

Siguiendo la plantilla y el precedente de `2026-08-26-supabase-corrige-maestro.md`.

- [ ] **Step 4: Resellar y comitear**

```bash
python tools/verificar_gobernanza.py --sellar
python tools/verificar_gobernanza.py
git add docs criteria
git commit -m "docs: el 19 recoge que el texto se envia integro

Decision del docente del 29/08/2026. El 19 describia un circuito con
anonimizacion previa que ya no se aplica, y una fuente superior no puede
quedar contradiciendo al codigo: es lo mismo que hicimos con Supabase en
D-001.

Sigue en pie que ninguna entrega real pase por el proveedor hasta cerrar
proteccion_datos. Tener la llave no autoriza a usarla con el trabajo de un
alumno."
```

---

## Cierre de la Parte B

Al terminar la Task 15, el sistema hace el flujo entero: recoge el trabajo, lo mide, lo contrasta con los criterios, lo compara con la entrega anterior, lo analiza, compone las dos salidas y se detiene para que el docente revise observación por observación.

Antes de darla por cerrada:

- [ ] **Ejecutar el arnés con los nueve casos reales**, cuando el docente los traiga. Su informe es lo que dirá si el sistema está calibrado, y ninguna suite en verde sustituye a eso.
- [ ] **Actualizar `CLAUDE.md`** con los módulos nuevos.
- [ ] **Comprobar el arranque real** con `python -m backend`, un PDF propio y el motor configurado, verificando que el aviso del motor simulado aparece cuando no lo está.
