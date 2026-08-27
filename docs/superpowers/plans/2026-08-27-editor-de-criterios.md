# Editor de criterios — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una aplicación local con la que el docente lee y modifica sus documentos normativos sin poder salirse del procedimiento de gobernanza.

**Architecture:** Backend FastAPI que envuelve `tools/gobernanza` sin reimplementar nada, y frontend React servido por el propio backend. El guardado es una transacción atómica: escribe prosa, escribe YAML, genera el documento de cambio, verifica, sella y comitea — y si algo falla, restaura todo byte a byte.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, httpx. React 18, Vite, TypeScript, Tailwind, shadcn/ui, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-27-editor-de-criterios-design.md`

## Global Constraints

- Idioma de código, identificadores, comentarios, mensajes, documentación y commits: **castellano**.
- Python **3.13**, invocado como `python`. Tests desde la raíz con `python -m pytest`.
- El backend escucha **únicamente en `127.0.0.1`**, puerto **8000**. Nunca `0.0.0.0`.
- **No se reimplementa ninguna regla.** Todo juicio de gobernanza sale de `tools/gobernanza`.
- **No hay atajo.** Ninguna ruta del código permite escribir en `docs/maestro/` o `criteria/` sin pasar por la transacción completa.
- Ninguna prueba escribe en el repositorio real: todas construyen su propio repositorio temporal.
- Ningún dato de personas reales. Los ejemplos usan códigos tipo `AF023`.
- Al terminar cada tarea: `python -m pytest` en verde y `python tools/verificar_gobernanza.py` en conforme.

## Firmas existentes que este plan consume

Verificadas contra el código en `60aa98d`. No las cambies.

```python
# tools/gobernanza/resultado.py
@dataclass(frozen=True)
class Infraccion:
    regla: str
    fichero: str
    detalle: str

def formatear(infracciones: list[Infraccion]) -> str

# tools/gobernanza/criterios.py
def cargar_anclas(raiz: Path) -> set[str]
def entradas_de(ruta_yaml: Path) -> list[dict]
def bloques_raiz(ruta_yaml: Path) -> list[tuple[str, object]]
def verificar_r1(raiz: Path) -> list[Infraccion]
def verificar_r3(raiz: Path) -> list[Infraccion]
PATRON_ANCLA   # captura la ancla completa, p.ej. "maestro#8-dimensiones"

# tools/gobernanza/sincronia.py
FICHERO_SINCRONIA = "criteria/.sincronia.json"
def hash_de_seccion(raiz: Path, ancla: str) -> str | None
def escribir_sincronia(raiz: Path) -> None
def verificar_r2(raiz: Path) -> list[Infraccion]
PATRON_CUALQUIER_ANCLA

# tools/gobernanza/versiones.py
def congelar(raiz: Path, version: str) -> None
def verificar_r4(raiz: Path) -> list[Infraccion]

# tools/gobernanza/cambios.py
CARPETA = "docs/changes"
SECCIONES_OBLIGATORIAS   # tupla de 5 títulos
def verificar_formato_cambios(raiz: Path) -> list[Infraccion]
def verificar_cambio_acompanado(raiz: Path, ficheros_tocados: list[str]) -> list[Infraccion]

# tools/gobernanza/privacidad.py
def verificar_r6(raiz: Path, ficheros: list[str]) -> list[Infraccion]

# tools/verificar_gobernanza.py
def ejecutar(raiz: Path, ficheros: list[str], solo_staged: bool) -> list[Infraccion]
```

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `backend/app.py` | Crea la app, monta las rutas, sirve el front compilado |
| `backend/modelos.py` | Modelos Pydantic compartidos por las tres APIs |
| `backend/servicios/repositorio.py` | Lectura del árbol: documentos, secciones, criterios |
| `backend/servicios/dependencias.py` | Qué criterio deriva de qué sección |
| `backend/servicios/propuesta.py` | Inferencia literal de valores |
| `backend/servicios/transaccion.py` | Escribir, verificar, sellar, comitear, revertir |
| `backend/api/documentos.py` | Endpoints de lectura |
| `backend/api/edicion.py` | Endpoint de guardado |
| `backend/api/estado.py` | Reglas, límites y pendientes |
| `frontend/src/lib/api.ts` | Cliente tipado del backend |
| `frontend/src/paginas/*.tsx` | Una por pantalla |
| `frontend/src/componentes/*.tsx` | Piezas reutilizables |

---

### Task 1: Andamiaje del backend y lectura del repositorio

**Files:**
- Create: `backend/__init__.py`, `backend/app.py`, `backend/modelos.py`
- Create: `backend/servicios/__init__.py`, `backend/servicios/repositorio.py`
- Modify: `requirements-dev.txt`
- Test: `tests/backend/test_repositorio.py`, `tests/backend/conftest.py`

**Interfaces:**
- Consumes: `cargar_anclas`, `PATRON_ANCLA` de `tools.gobernanza.criterios`.
- Produces:
  - `Documento`, `Seccion` (Pydantic) en `backend/modelos.py`
  - `listar_documentos(raiz: Path) -> list[Documento]`
  - `leer_seccion(raiz: Path, ancla: str) -> Seccion | None`
  - `ruta_de_documento(raiz: Path, documento: str) -> Path | None`
  - `crear_app(raiz: Path) -> FastAPI` en `backend/app.py`

- [ ] **Step 1: Añadir dependencias**

En `requirements-dev.txt`, añadir tras las existentes:

```
fastapi==0.115.6
uvicorn==0.34.0
pydantic==2.10.4
httpx==0.28.1
```

Instalar: `python -m pip install -r requirements-dev.txt`

- [ ] **Step 2: Escribir el conftest compartido**

Crear `tests/backend/conftest.py`. Construye un repositorio de mentira con la misma forma que el real. Todas las tareas del backend lo usan.

```python
"""Repositorio de prueba con la forma del real, pero inventado."""

import json
import subprocess
from pathlib import Path

import pytest

MAESTRO = """# Documento Maestro

<!-- ancla: maestro#6-estandar-academico -->
## 6. Estándar académico

El contenido principal tendrá un mínimo de 20 páginas, excluidas portada,
índice y anexos. La tipografía será Arial 11.

<!-- ancla: maestro#8-dimensiones -->
## 8. Dimensiones de evaluación

Doce dimensiones comunes, con peso configurable por fase.

<!-- ancla: maestro#19-privacidad -->
## 19. Privacidad

Se trabaja con códigos anónimos de alumno.
"""

FORMATO = """extension:
  minimo_paginas_contenido: 20
  fuente: maestro#6-estandar-academico

tipografia:
  familia: Arial
  cuerpo: 11
  fuente: maestro#6-estandar-academico
"""

DIMENSIONES = """- codigo: D05
  nombre: Fundamentación y fuentes
  fuente: maestro#8-dimensiones
  activa_en: [E2, E3, FINAL]
"""

PLANTILLA_CAMBIO = "# Plantilla\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repositorio git completo, con documentos, criterios y sello."""
    maestro = tmp_path / "docs" / "maestro"
    maestro.mkdir(parents=True)
    (maestro / "01-documento-maestro.md").write_text(MAESTRO, encoding="utf-8")

    criterios = tmp_path / "criteria" / "v2026-2027"
    criterios.mkdir(parents=True)
    (criterios / "formato.yaml").write_text(FORMATO, encoding="utf-8")
    (criterios / "dimensiones.yaml").write_text(DIMENSIONES, encoding="utf-8")

    cambios = tmp_path / "docs" / "changes"
    cambios.mkdir(parents=True)
    (cambios / "PLANTILLA.md").write_text(PLANTILLA_CAMBIO, encoding="utf-8")

    (tmp_path / "docs" / "PENDIENTE_OFICIAL.md").write_text(
        "# Pendiente de cierre oficial\n\n"
        "- **rubrica** — criterios oficiales. Se espera de la programación.\n",
        encoding="utf-8",
    )

    from tools.gobernanza.sincronia import escribir_sincronia
    escribir_sincronia(tmp_path)

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "prueba"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "prueba@ejemplo.invalid"],
                   cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "inicial"], cwd=tmp_path, check=True)
    return tmp_path


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
```

- [ ] **Step 3: Escribir el test que falla**

Crear `tests/backend/test_repositorio.py`:

```python
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
```

- [ ] **Step 4: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/backend/test_repositorio.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend'`

- [ ] **Step 5: Escribir los modelos**

Crear `backend/modelos.py`:

```python
"""Modelos compartidos por las tres APIs."""

from pydantic import BaseModel


class Seccion(BaseModel):
    """Una sección de un documento normativo."""

    ancla: str
    titulo: str
    texto: str
    hash: str
    criterios_que_la_citan: int = 0


class Documento(BaseModel):
    """Uno de los tres documentos maestros."""

    clave: str
    titulo: str
    fichero: str
    secciones: list[Seccion]
```

- [ ] **Step 6: Escribir el servicio de repositorio**

Crear `backend/servicios/repositorio.py`:

```python
"""Lectura del árbol de documentos normativos.

Solo lee. Cualquier escritura pasa por servicios/transaccion.py.
"""

import re
from pathlib import Path

from backend.modelos import Documento, Seccion
from tools.gobernanza.criterios import PATRON_ANCLA
from tools.gobernanza.sincronia import hash_de_seccion

# Las tres claves válidas y su fichero. Es una lista cerrada a propósito:
# ninguna ruta que venga del cliente se usa para construir un Path.
DOCUMENTOS = {
    "maestro": "01-documento-maestro.md",
    "indice": "02-indice-comentado.md",
    "guia": "03-guia-desarrollo.md",
}

PATRON_ENCABEZADO = re.compile(r"^#{2,3}\s+(.+)$", re.M)


def ruta_de_documento(raiz: Path, documento: str) -> Path | None:
    """Ruta del fichero de un documento, o None si la clave no es válida."""
    nombre = DOCUMENTOS.get(documento)
    if nombre is None:
        return None
    ruta = raiz / "docs" / "maestro" / nombre
    return ruta if ruta.is_file() else None


def _titulo_de(texto: str) -> str:
    """Primer encabezado de nivel 1, o cadena vacía."""
    for linea in texto.splitlines():
        if linea.startswith("# "):
            return linea[2:].strip()
    return ""


def _trocear(texto: str) -> list[tuple[str, str, str]]:
    """Devuelve (ancla, titulo, cuerpo) por cada sección anclada del documento."""
    marcas = list(PATRON_ANCLA.finditer(texto))
    troceado = []
    for indice, marca in enumerate(marcas):
        inicio = marca.end()
        fin = marcas[indice + 1].start() if indice + 1 < len(marcas) else len(texto)
        cuerpo = texto[inicio:fin].strip("\n")
        encabezado = PATRON_ENCABEZADO.search(cuerpo)
        titulo = encabezado.group(1).strip() if encabezado else marca.group(1)
        troceado.append((marca.group(1), titulo, cuerpo))
    return troceado


def listar_documentos(raiz: Path) -> list[Documento]:
    """Los documentos presentes, con sus secciones en el orden del fichero."""
    documentos = []
    for clave, nombre in DOCUMENTOS.items():
        ruta = raiz / "docs" / "maestro" / nombre
        if not ruta.is_file():
            continue
        texto = ruta.read_text(encoding="utf-8")
        secciones = [
            Seccion(
                ancla=ancla,
                titulo=titulo,
                texto=cuerpo,
                hash=hash_de_seccion(raiz, ancla) or "",
            )
            for ancla, titulo, cuerpo in _trocear(texto)
        ]
        documentos.append(Documento(
            clave=clave,
            titulo=_titulo_de(texto),
            fichero=f"docs/maestro/{nombre}",
            secciones=secciones,
        ))
    return documentos


def leer_seccion(raiz: Path, ancla: str) -> Seccion | None:
    """Una sección concreta por su ancla, o None si no existe."""
    for documento in listar_documentos(raiz):
        for seccion in documento.secciones:
            if seccion.ancla == ancla:
                return seccion
    return None
```

- [ ] **Step 7: Crear los `__init__.py` vacíos**

`backend/__init__.py`, `backend/servicios/__init__.py`, `tests/backend/__init__.py` — los tres vacíos.

- [ ] **Step 8: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/backend/test_repositorio.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 9: Escribir la app mínima**

Crear `backend/app.py`:

```python
"""Aplicación del editor de criterios.

Escucha solo en 127.0.0.1: escribe en el disco y ejecuta git.
"""

from pathlib import Path

from fastapi import FastAPI


def crear_app(raiz: Path) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta."""
    app = FastAPI(title="Editor de criterios", docs_url=None, redoc_url=None)
    app.state.raiz = raiz

    @app.get("/api/salud")
    def salud() -> dict[str, str]:
        return {"estado": "vivo", "raiz": str(raiz)}

    return app
```

- [ ] **Step 10: Ejecutar la batería completa y commitear**

Run: `python -m pytest && python tools/verificar_gobernanza.py`
Expected: todo en verde, gobernanza conforme.

```bash
git add backend/ tests/backend/ requirements-dev.txt
git commit -m "feat: andamiaje del backend y lectura de documentos normativos"
```

---

### Task 2: Qué criterio deriva de qué sección

**Files:**
- Create: `backend/servicios/dependencias.py`
- Test: `tests/backend/test_dependencias.py`

**Interfaces:**
- Consumes: `entradas_de`, `bloques_raiz` de `tools.gobernanza.criterios`; `Seccion` de `backend.modelos`.
- Produces:
  - `CriterioDerivado` (Pydantic): `fichero: str`, `identificador: str`, `valores: dict[str, str]`, `fuente: str`
  - `criterios_de(raiz: Path, ancla: str) -> list[CriterioDerivado]`
  - `contar_por_ancla(raiz: Path) -> dict[str, int]`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/backend/test_dependencias.py`:

```python
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
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/backend/test_dependencias.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.servicios.dependencias'`

- [ ] **Step 3: Escribir la implementación**

Crear `backend/servicios/dependencias.py`:

```python
"""Qué criterio deriva de qué sección de la prosa.

Es la información que el editor enseña al lado del texto: antes de tocar
una sección, saber qué depende de ella.
"""

from pathlib import Path

from pydantic import BaseModel

from tools.gobernanza.criterios import cargar_anclas, entradas_de

# Claves que no son valores del criterio sino metadatos de la propia entrada.
CLAVES_INTERNAS = {"fuente", "_clave", "codigo"}


class CriterioDerivado(BaseModel):
    """Un criterio ejecutable que cita una sección concreta como fuente."""

    fichero: str
    identificador: str
    valores: dict[str, str]
    fuente: str


def _identificador(entrada: dict) -> str:
    return str(entrada.get("codigo") or entrada.get("_clave") or "sin identificador")


def _valores(entrada: dict) -> dict[str, str]:
    """Los valores del criterio, en texto, sin sus metadatos."""
    return {
        clave: str(valor)
        for clave, valor in entrada.items()
        if clave not in CLAVES_INTERNAS
    }


def criterios_de(raiz: Path, ancla: str) -> list[CriterioDerivado]:
    """Criterios que declaran esa ancla como su fuente."""
    derivados: list[CriterioDerivado] = []
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return derivados

    for ruta in sorted(carpeta.rglob("*.yaml")):
        relativa = ruta.relative_to(raiz).as_posix()
        for entrada in entradas_de(ruta):
            if entrada.get("fuente") != ancla:
                continue
            derivados.append(CriterioDerivado(
                fichero=relativa,
                identificador=_identificador(entrada),
                valores=_valores(entrada),
                fuente=ancla,
            ))
    return derivados


def contar_por_ancla(raiz: Path) -> dict[str, int]:
    """Cuántos criterios cita cada ancla del repositorio, incluidas las que nadie cita."""
    conteo = {ancla: 0 for ancla in cargar_anclas(raiz)}
    carpeta = raiz / "criteria"
    if not carpeta.is_dir():
        return conteo

    for ruta in sorted(carpeta.rglob("*.yaml")):
        for entrada in entradas_de(ruta):
            fuente = entrada.get("fuente")
            if isinstance(fuente, str) and fuente in conteo:
                conteo[fuente] += 1
    return conteo
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/backend/test_dependencias.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Enganchar el conteo a la lectura de documentos**

En `backend/servicios/repositorio.py`, dentro de `listar_documentos`, calcular el conteo una vez y rellenar `criterios_que_la_citan`:

```python
def listar_documentos(raiz: Path) -> list[Documento]:
    """Los documentos presentes, con sus secciones en el orden del fichero."""
    from backend.servicios.dependencias import contar_por_ancla

    conteo = contar_por_ancla(raiz)
    documentos = []
    for clave, nombre in DOCUMENTOS.items():
        ruta = raiz / "docs" / "maestro" / nombre
        if not ruta.is_file():
            continue
        texto = ruta.read_text(encoding="utf-8")
        secciones = [
            Seccion(
                ancla=ancla,
                titulo=titulo,
                texto=cuerpo,
                hash=hash_de_seccion(raiz, ancla) or "",
                criterios_que_la_citan=conteo.get(ancla, 0),
            )
            for ancla, titulo, cuerpo in _trocear(texto)
        ]
        documentos.append(Documento(
            clave=clave,
            titulo=_titulo_de(texto),
            fichero=f"docs/maestro/{nombre}",
            secciones=secciones,
        ))
    return documentos
```

El import va dentro de la función a propósito: `dependencias` no importa `repositorio`, y así no hay ciclo.

- [ ] **Step 6: Añadir el test del enganche**

Añadir a `tests/backend/test_repositorio.py`:

```python
def test_cada_seccion_sabe_cuantos_criterios_la_citan(repo: Path):
    secciones = {s.ancla: s for s in listar_documentos(repo)[0].secciones}
    assert secciones["maestro#6-estandar-academico"].criterios_que_la_citan == 2
    assert secciones["maestro#8-dimensiones"].criterios_que_la_citan == 1
    assert secciones["maestro#19-privacidad"].criterios_que_la_citan == 0
```

- [ ] **Step 7: Ejecutar la batería y commitear**

Run: `python -m pytest && python tools/verificar_gobernanza.py`

```bash
git add backend/servicios/dependencias.py backend/servicios/repositorio.py tests/backend/
git commit -m "feat: cada seccion sabe que criterios derivan de ella"
```

---

### Task 3: La propuesta, y lo que no se propone

**Files:**
- Create: `backend/servicios/propuesta.py`
- Test: `tests/backend/test_propuesta.py`

**Interfaces:**
- Consumes: `CriterioDerivado`, `criterios_de` de `backend.servicios.dependencias`.
- Produces:
  - `Propuesta` (Pydantic): `fichero: str`, `identificador: str`, `clave: str`, `valor_actual: str`, `valor_propuesto: str | None`, `motivo: str`
  - `proponer(raiz: Path, ancla: str, texto_nuevo: str) -> list[Propuesta]`

Regla: se propone un valor **solo** si el valor actual aparece literalmente en el texto anterior de la sección y ha cambiado de forma inequívoca en el nuevo. Todo lo demás sale con `valor_propuesto = None` y un motivo que dice por qué hay que mirarlo a mano.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/backend/test_propuesta.py`:

```python
from pathlib import Path

from backend.servicios.propuesta import proponer


def test_propone_el_valor_nuevo_cuando_el_numero_cambia_en_el_texto(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_actual == "20"
    assert extension.valor_propuesto == "25"


def test_no_propone_nada_para_un_valor_que_sigue_igual(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "El contenido principal tendrá un mínimo de 25 páginas, excluidas portada,\n"
        "índice y anexos. La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    cuerpo = next(p for p in propuestas if p.clave == "cuerpo")
    assert cuerpo.valor_propuesto is None
    assert "sigue apareciendo" in cuerpo.motivo


def test_marca_para_revisar_a_mano_un_valor_que_no_aparece_en_el_texto(repo: Path):
    texto = "## 8. Dimensiones de evaluación\n\nTrece dimensiones, con peso variable.\n"
    propuestas = proponer(repo, "maestro#8-dimensiones", texto)
    activa = next(p for p in propuestas if p.clave == "activa_en")
    assert activa.valor_propuesto is None
    assert "no aparece literalmente" in activa.motivo


def test_no_propone_cuando_el_valor_desaparece_sin_sustituto_claro(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "La extensión se fijará según la programación didáctica.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None
    assert "ha desaparecido" in extension.motivo


def test_no_propone_cuando_hay_mas_de_un_candidato(repo: Path):
    texto = (
        "## 6. Estándar académico\n\n"
        "Un mínimo de 25 páginas, o de 30 si el proyecto es de investigación.\n"
        "La tipografía será Arial 11.\n"
    )
    propuestas = proponer(repo, "maestro#6-estandar-academico", texto)
    extension = next(p for p in propuestas if p.clave == "minimo_paginas_contenido")
    assert extension.valor_propuesto is None
    assert "más de un" in extension.motivo


def test_una_seccion_sin_criterios_no_produce_propuestas(repo: Path):
    assert proponer(repo, "maestro#19-privacidad", "texto nuevo") == []
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/backend/test_propuesta.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.servicios.propuesta'`

- [ ] **Step 3: Escribir la implementación**

Crear `backend/servicios/propuesta.py`:

```python
"""Inferencia literal de valores al cambiar la prosa.

Deliberadamente corta de alcance. Solo propone un valor nuevo cuando la
correspondencia con el texto es literal e inequívoca; en cualquier otro caso
devuelve el criterio marcado para que lo mire el docente.

Inferir de más aquí sería fabricar un criterio que nadie decidió, que es
exactamente lo que R1 existe para impedir.
"""

import re
from pathlib import Path

from pydantic import BaseModel

from backend.servicios.dependencias import criterios_de
from backend.servicios.repositorio import leer_seccion


class Propuesta(BaseModel):
    """Qué le pasa a un valor de un criterio cuando cambia su sección."""

    fichero: str
    identificador: str
    clave: str
    valor_actual: str
    valor_propuesto: str | None
    motivo: str


def _es_numero(valor: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", valor))


def _apariciones(valor: str, texto: str) -> int:
    return len(re.findall(rf"(?<![\w.,]){re.escape(valor)}(?![\w.,])", texto))


def _contexto(valor: str, texto: str) -> tuple[str, str] | None:
    """Las tres palabras antes y después de la única aparición del valor."""
    encontrado = re.search(rf"(?<![\w.,]){re.escape(valor)}(?![\w.,])", texto)
    if encontrado is None:
        return None
    antes = texto[:encontrado.start()].split()[-3:]
    despues = texto[encontrado.end():].split()[:3]
    return " ".join(antes), " ".join(despues)


def _candidato(valor_viejo: str, texto_viejo: str, texto_nuevo: str) -> str | None:
    """El número que ocupa en el texto nuevo el mismo sitio que ocupaba el viejo."""
    contexto = _contexto(valor_viejo, texto_viejo)
    if contexto is None:
        return None
    antes, despues = contexto
    if not antes:
        return None

    patron = rf"{re.escape(antes)}\s+(\d+(?:[.,]\d+)?)"
    hallados = re.findall(patron, texto_nuevo)
    if len(hallados) == 1:
        return hallados[0]
    return None


def proponer(raiz: Path, ancla: str, texto_nuevo: str) -> list[Propuesta]:
    """Qué se propone cambiar en los criterios que derivan de esta sección."""
    seccion = leer_seccion(raiz, ancla)
    if seccion is None:
        return []
    texto_viejo = seccion.texto

    propuestas: list[Propuesta] = []
    for criterio in criterios_de(raiz, ancla):
        for clave, valor in criterio.valores.items():
            propuestas.append(_evaluar(criterio, clave, valor, texto_viejo, texto_nuevo))
    return propuestas


def _evaluar(criterio, clave: str, valor: str, texto_viejo: str, texto_nuevo: str) -> Propuesta:
    """Decide qué proponer para un valor concreto, o por qué no proponer nada."""
    def resultado(propuesto: str | None, motivo: str) -> Propuesta:
        return Propuesta(
            fichero=criterio.fichero,
            identificador=criterio.identificador,
            clave=clave,
            valor_actual=valor,
            valor_propuesto=propuesto,
            motivo=motivo,
        )

    if not _es_numero(valor):
        return resultado(None, (
            "Este valor no es un número, así que su relación con el texto no es "
            "literal. Revisa a mano si el cambio le afecta."
        ))

    if _apariciones(valor, texto_viejo) != 1:
        return resultado(None, (
            "El valor no aparece literalmente una sola vez en el texto anterior, "
            "así que no se puede saber a qué parte corresponde. Revísalo a mano."
        ))

    if _apariciones(valor, texto_nuevo) == 1:
        return resultado(None, "El valor sigue apareciendo igual en el texto nuevo.")

    candidato = _candidato(valor, texto_viejo, texto_nuevo)
    if candidato is None:
        if _apariciones(valor, texto_nuevo) == 0:
            return resultado(None, (
                "El valor ha desaparecido del texto y no hay uno nuevo que ocupe "
                "su lugar de forma clara. Decide tú qué debe decir el criterio."
            ))
        return resultado(None, (
            "Hay más de un número que podría corresponder a este valor. "
            "Elige tú cuál."
        ))

    return resultado(candidato, (
        f"El texto decía «{valor}» y ahora dice «{candidato}» en el mismo sitio."
    ))
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/backend/test_propuesta.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commitear**

```bash
git add backend/servicios/propuesta.py tests/backend/test_propuesta.py
git commit -m "feat: propuesta literal de valores, y motivo cuando no se puede proponer"
```

---

### Task 4: La transacción de guardado

**Files:**
- Create: `backend/servicios/transaccion.py`
- Test: `tests/backend/test_transaccion.py`

**Interfaces:**
- Consumes: `ejecutar` de `tools.verificar_gobernanza`; `escribir_sincronia` de `tools.gobernanza.sincronia`; `SECCIONES_OBLIGATORIAS` de `tools.gobernanza.cambios`; `leer_seccion` de `backend.servicios.repositorio`.
- Produces:
  - `CambioDeValor` (Pydantic): `fichero: str`, `identificador: str`, `clave: str`, `valor_nuevo: str`
  - `Resultado` (Pydantic): `exito: bool`, `commit: str | None`, `infracciones: list[dict]`, `mensaje: str`
  - `guardar(raiz, ancla, texto_nuevo, cambios, motivo, fuente, hash_esperado) -> Resultado`

Es el corazón del editor. O se completa entera, o el repositorio queda byte a byte como estaba y sin commits nuevos.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/backend/test_transaccion.py`:

```python
import subprocess
from pathlib import Path

from backend.servicios.repositorio import leer_seccion
from backend.servicios.transaccion import CambioDeValor, guardar
from tests.backend.conftest import commits_de, contenido_de

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
    """Un cambio que deja un criterio apuntando a un ancla inexistente."""
    antes, commits = contenido_de(repo), commits_de(repo)
    texto_sin_ancla = "## 6. Estándar académico\n\nTexto sin la marca de ancla.\n"
    resultado = guardar(
        raiz=repo,
        ancla="maestro#6-estandar-academico",
        texto_nuevo=texto_sin_ancla,
        cambios=[],
        motivo="Prueba de reversión",
        fuente="Prueba",
        hash_esperado=leer_seccion(repo, "maestro#6-estandar-academico").hash,
    )
    assert not resultado.exito
    assert resultado.infracciones
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
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/backend/test_transaccion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.servicios.transaccion'`

- [ ] **Step 3: Escribir la implementación**

Crear `backend/servicios/transaccion.py`:

```python
"""El guardado, como transacción atómica.

O se completa entera, o el repositorio queda byte a byte como estaba y sin
commits nuevos. Un guardado a medias deja el repositorio en un estado que
nadie sabe interpretar después, que es justo lo que la gobernanza evita.
"""

import re
import subprocess
import unicodedata
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from backend.servicios.repositorio import leer_seccion
from tools.gobernanza.cambios import CARPETA as CARPETA_CAMBIOS
from tools.gobernanza.sincronia import FICHERO_SINCRONIA, escribir_sincronia
from tools.verificar_gobernanza import ejecutar


class CambioDeValor(BaseModel):
    """Un valor de un criterio que el docente ha decidido cambiar."""

    fichero: str
    identificador: str
    clave: str
    valor_nuevo: str


class Resultado(BaseModel):
    """Cómo acabó el guardado."""

    exito: bool
    commit: str | None = None
    infracciones: list[dict] = []
    mensaje: str = ""


def _git(raiz: Path, *argumentos: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *argumentos], cwd=raiz, capture_output=True, text=True, check=False
    )


def _arbol_limpio(raiz: Path) -> bool:
    return not _git(raiz, "status", "--porcelain").stdout.strip()


def _asunto(motivo: str) -> str:
    """Convierte el motivo en un asunto apto para el nombre del fichero."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", motivo.lower())
        if unicodedata.category(c) != "Mn"
    )
    palabras = re.findall(r"[a-z0-9]+", sin_tildes)[:6]
    return "-".join(palabras) or "cambio"


def _documento_de_cambio(ancla: str, cambios: list[CambioDeValor],
                         motivo: str, fuente: str) -> str:
    """El documento que R5 exige, con sus cinco secciones."""
    if cambios:
        lista = "\n".join(
            f"- `{c.fichero}` · {c.identificador}.{c.clave} → {c.valor_nuevo}"
            for c in cambios
        )
    else:
        lista = "Ningún criterio derivado cambia de valor."

    return (
        f"# {motivo.strip().rstrip('.')}\n\n"
        f"**Fecha:** {date.today().isoformat()}\n"
        f"**Autor:** editor de criterios\n\n"
        f"## Que cambia\n\n"
        f"Se ha modificado la sección `{ancla}` de la prosa normativa.\n\n"
        f"{lista}\n\n"
        f"## Por que\n\n{motivo.strip()}\n\n"
        f"## Fuente que lo respalda\n\n{fuente.strip()}\n\n"
        f"## Que arrastra\n\n"
        f"- La sección `{ancla}` de `docs/maestro/`\n"
        f"- Los criterios listados arriba\n\n"
        f"## Correcciones cerradas afectadas\n\n"
        f"Pendiente de revisar por el docente.\n"
    )


def _sustituir_seccion(texto: str, ancla: str, cuerpo_nuevo: str) -> str | None:
    """Reemplaza el cuerpo de una sección conservando su marca de ancla."""
    marca = f"<!-- ancla: {ancla} -->"
    inicio = texto.find(marca)
    if inicio == -1:
        return None
    desde = inicio + len(marca)
    siguiente = re.search(
        r"^<!-- ancla: (?:maestro|indice|guia)#[a-z0-9-]+ -->$",
        texto[desde:], re.M,
    )
    hasta = desde + siguiente.start() if siguiente else len(texto)
    return texto[:desde] + "\n" + cuerpo_nuevo.strip("\n") + "\n\n" + texto[hasta:]


def _sustituir_valor(contenido: str, clave: str, valor_nuevo: str) -> str:
    """Cambia `clave: valor` conservando la indentación de la línea."""
    return re.sub(
        rf"^(\s*{re.escape(clave)}:\s*).*$",
        lambda m: f"{m.group(1)}{valor_nuevo}",
        contenido, count=1, flags=re.M,
    )


def guardar(raiz: Path, ancla: str, texto_nuevo: str, cambios: list[CambioDeValor],
            motivo: str, fuente: str, hash_esperado: str) -> Resultado:
    """Ejecuta el procedimiento completo, o no deja rastro."""
    if not motivo.strip():
        return Resultado(exito=False, mensaje=(
            "Falta el motivo del cambio. Es lo que permitirá entender esta "
            "decisión dentro de un año."
        ))
    if not fuente.strip():
        return Resultado(exito=False, mensaje=(
            "Falta la fuente que respalda el cambio. Si no hay ninguna, este "
            "cambio no debería hacerse."
        ))

    seccion = leer_seccion(raiz, ancla)
    if seccion is None:
        return Resultado(exito=False, mensaje=f"La sección «{ancla}» no existe.")

    if seccion.hash != hash_esperado:
        return Resultado(exito=False, mensaje=(
            "La sección ha cambiado desde que la abriste. Recarga antes de "
            "guardar para no pisar el otro cambio."
        ))

    if not _arbol_limpio(raiz):
        return Resultado(exito=False, mensaje=(
            "El repositorio tiene cambios sin comitear. Resuélvelos antes de "
            "guardar desde aquí."
        ))

    for cambio in cambios:
        ruta = (raiz / cambio.fichero).resolve()
        carpeta = (raiz / "criteria").resolve()
        if not str(ruta).startswith(str(carpeta)) or not ruta.is_file():
            return Resultado(exito=False, mensaje=(
                f"«{cambio.fichero}» no es un fichero de criterios de este "
                f"repositorio."
            ))

    # A partir de aquí se escribe. Todo lo que se toque se guarda para revertir.
    documento = raiz / "docs" / "maestro" / _fichero_de(ancla)
    tocados: dict[Path, bytes] = {documento: documento.read_bytes()}
    for cambio in cambios:
        ruta = raiz / cambio.fichero
        tocados.setdefault(ruta, ruta.read_bytes())
    # El registro de sincronía se reescribe siempre. Si no existiera, habría
    # que borrarlo al revertir en vez de restaurarlo: por eso se distingue.
    sincronia = raiz / FICHERO_SINCRONIA
    sincronia_existia = sincronia.is_file()
    if sincronia_existia:
        tocados[sincronia] = sincronia.read_bytes()

    nombre_cambio = f"{date.today().isoformat()}-{_asunto(motivo)}.md"
    ruta_cambio = raiz / CARPETA_CAMBIOS / nombre_cambio

    def revertir() -> None:
        for ruta, contenido in tocados.items():
            ruta.write_bytes(contenido)
        ruta_cambio.unlink(missing_ok=True)
        if not sincronia_existia:
            sincronia.unlink(missing_ok=True)
        _git(raiz, "reset")

    try:
        texto_actualizado = _sustituir_seccion(
            documento.read_text(encoding="utf-8"), ancla, texto_nuevo
        )
        if texto_actualizado is None:
            revertir()
            return Resultado(exito=False, mensaje="No se encontró el ancla en el documento.")
        documento.write_text(texto_actualizado, encoding="utf-8")

        for cambio in cambios:
            ruta = raiz / cambio.fichero
            ruta.write_text(
                _sustituir_valor(ruta.read_text(encoding="utf-8"),
                                 cambio.clave, cambio.valor_nuevo),
                encoding="utf-8",
            )

        ruta_cambio.write_text(
            _documento_de_cambio(ancla, cambios, motivo, fuente), encoding="utf-8"
        )

        escribir_sincronia(raiz)

        infracciones = ejecutar(raiz, [], False)
        if infracciones:
            revertir()
            return Resultado(
                exito=False,
                infracciones=[
                    {"regla": i.regla, "fichero": i.fichero, "detalle": i.detalle}
                    for i in infracciones
                ],
                mensaje=(
                    f"El cambio no se ha guardado: {len(infracciones)} "
                    f"infracción(es) de gobernanza."
                ),
            )

        _git(raiz, "add", "-A")
        commit = _git(raiz, "commit", "-q", "-m", f"docs: {motivo.strip()}")
        if commit.returncode != 0:
            revertir()
            _git(raiz, "reset")
            return Resultado(exito=False, mensaje=f"Git rechazó el commit: {commit.stderr}")

        return Resultado(
            exito=True,
            commit=_git(raiz, "rev-parse", "--short", "HEAD").stdout.strip(),
            mensaje="Cambio guardado, verificado y registrado.",
        )

    except OSError as error:
        revertir()
        return Resultado(exito=False, mensaje=f"Error al escribir: {error}")


def _fichero_de(ancla: str) -> str:
    documento, _, _ = ancla.partition("#")
    return {
        "maestro": "01-documento-maestro.md",
        "indice": "02-indice-comentado.md",
        "guia": "03-guia-desarrollo.md",
    }[documento]
```

- [ ] **Step 4: Ejecutar los tests para comprobar que pasan**

Run: `python -m pytest tests/backend/test_transaccion.py -v`
Expected: PASS, 10 tests.

El `_git(raiz, "reset")` dentro de `revertir()` es necesario: sin él, un fallo posterior al `git add -A` dejaría ficheros en el índice y el siguiente guardado los arrastraría.

- [ ] **Step 5: Commitear**

```bash
git add backend/servicios/transaccion.py tests/backend/test_transaccion.py
git commit -m "feat: la transaccion de guardado, atomica o no ocurre"
```

---

### Task 5: Los tres endpoints

**Files:**
- Create: `backend/api/__init__.py`, `backend/api/documentos.py`, `backend/api/edicion.py`, `backend/api/estado.py`
- Modify: `backend/app.py`
- Test: `tests/backend/test_api.py`

**Interfaces:**
- Consumes: todo lo de las tareas 1 a 4.
- Produces: la API que el frontend consume.

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/api/documentos` | `list[Documento]` |
| GET | `/api/secciones/{ancla}` | `Seccion` + `criterios: list[CriterioDerivado]` |
| POST | `/api/propuesta` | `list[Propuesta]` |
| POST | `/api/guardar` | `Resultado` |
| GET | `/api/estado` | reglas, resultado y límites |
| GET | `/api/pendientes` | entradas de `PENDIENTE_OFICIAL.md` |

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/backend/test_api.py`:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app


@pytest.fixture
def cliente(repo: Path) -> TestClient:
    return TestClient(crear_app(repo))


def test_documentos_devuelve_el_maestro_con_sus_secciones(cliente: TestClient):
    respuesta = cliente.get("/api/documentos")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos[0]["clave"] == "maestro"
    assert len(datos[0]["secciones"]) == 3


def test_una_seccion_trae_sus_criterios(cliente: TestClient):
    respuesta = cliente.get("/api/secciones/maestro%236-estandar-academico")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["seccion"]["ancla"] == "maestro#6-estandar-academico"
    assert len(datos["criterios"]) == 2


def test_una_seccion_inexistente_da_404(cliente: TestClient):
    assert cliente.get("/api/secciones/maestro%23no-existe").status_code == 404


def test_propuesta_devuelve_el_valor_inferido(cliente: TestClient):
    respuesta = cliente.post("/api/propuesta", json={
        "ancla": "maestro#6-estandar-academico",
        "texto_nuevo": (
            "## 6. Estándar académico\n\nEl contenido principal tendrá un mínimo "
            "de 25 páginas, excluidas portada, índice y anexos. La tipografía "
            "será Arial 11.\n"
        ),
    })
    assert respuesta.status_code == 200
    propuestas = respuesta.json()
    extension = next(p for p in propuestas if p["clave"] == "minimo_paginas_contenido")
    assert extension["valor_propuesto"] == "25"


def test_guardar_sin_motivo_devuelve_error_legible(cliente: TestClient):
    respuesta = cliente.post("/api/guardar", json={
        "ancla": "maestro#6-estandar-academico",
        "texto_nuevo": "## 6\n\ntexto\n",
        "cambios": [],
        "motivo": "",
        "fuente": "algo",
        "hash_esperado": "x",
    })
    assert respuesta.status_code == 200
    assert respuesta.json()["exito"] is False
    assert "motivo" in respuesta.json()["mensaje"]


def test_estado_enumera_las_seis_reglas_con_sus_limites(cliente: TestClient):
    datos = cliente.get("/api/estado").json()
    assert [r["codigo"] for r in datos["reglas"]] == ["R1", "R2", "R3", "R4", "R5", "R6"]
    r2 = next(r for r in datos["reglas"] if r["codigo"] == "R2")
    assert r2["limite"]
    assert datos["conforme"] is True


def test_pendientes_lee_el_documento(cliente: TestClient):
    datos = cliente.get("/api/pendientes").json()
    assert [p["clave"] for p in datos] == ["rubrica"]
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `python -m pytest tests/backend/test_api.py -v`
Expected: FAIL, los endpoints no existen.

- [ ] **Step 3: Escribir la API de documentos**

Crear `backend/api/documentos.py`:

```python
"""Endpoints de lectura."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.modelos import Documento, Seccion
from backend.servicios.dependencias import CriterioDerivado, criterios_de
from backend.servicios.propuesta import Propuesta, proponer
from backend.servicios.repositorio import leer_seccion, listar_documentos

router = APIRouter(prefix="/api")


class SeccionConCriterios(BaseModel):
    seccion: Seccion
    criterios: list[CriterioDerivado]


class PeticionPropuesta(BaseModel):
    ancla: str
    texto_nuevo: str


def _raiz(peticion: Request) -> Path:
    return peticion.app.state.raiz


@router.get("/documentos")
def obtener_documentos(peticion: Request) -> list[Documento]:
    return listar_documentos(_raiz(peticion))


@router.get("/secciones/{ancla}")
def obtener_seccion(ancla: str, peticion: Request) -> SeccionConCriterios:
    raiz = _raiz(peticion)
    seccion = leer_seccion(raiz, ancla)
    if seccion is None:
        raise HTTPException(status_code=404, detail=f"No existe la sección «{ancla}».")
    return SeccionConCriterios(seccion=seccion, criterios=criterios_de(raiz, ancla))


@router.post("/propuesta")
def obtener_propuesta(cuerpo: PeticionPropuesta, peticion: Request) -> list[Propuesta]:
    return proponer(_raiz(peticion), cuerpo.ancla, cuerpo.texto_nuevo)
```

- [ ] **Step 4: Escribir la API de edición**

Crear `backend/api/edicion.py`:

```python
"""El endpoint de guardado. Un único camino, sin atajos."""

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.servicios.transaccion import CambioDeValor, Resultado, guardar

router = APIRouter(prefix="/api")


class PeticionGuardar(BaseModel):
    ancla: str
    texto_nuevo: str
    cambios: list[CambioDeValor]
    motivo: str
    fuente: str
    hash_esperado: str


@router.post("/guardar")
def guardar_cambio(cuerpo: PeticionGuardar, peticion: Request) -> Resultado:
    raiz: Path = peticion.app.state.raiz
    return guardar(
        raiz=raiz,
        ancla=cuerpo.ancla,
        texto_nuevo=cuerpo.texto_nuevo,
        cambios=cuerpo.cambios,
        motivo=cuerpo.motivo,
        fuente=cuerpo.fuente,
        hash_esperado=cuerpo.hash_esperado,
    )
```

- [ ] **Step 5: Escribir la API de estado**

Crear `backend/api/estado.py`:

```python
"""Las seis reglas, lo que vigilan y lo que no, y lo que falta oficialmente."""

import re
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from tools.verificar_gobernanza import ejecutar

router = APIRouter(prefix="/api")

# Lo que cada regla NO cubre. Sale en pantalla porque una regla que promete
# más de lo que hace es peor que una regla que no existe.
REGLAS = [
    ("R1", "Ningún criterio sin origen",
     "Todo criterio declara la sección que lo respalda.",
     "Comprueba que el ancla existe, no que su texto diga lo que el criterio afirma."),
    ("R2", "La prosa manda",
     "Si cambia una sección, hay que revisar lo que deriva de ella.",
     "Solo vigila las secciones que algún criterio cita. Editar una sección "
     "que nadie deriva no hace saltar nada."),
    ("R3", "Lo pendiente no se inventa",
     "Un criterio sin dato oficial se marca y no lleva valor.",
     "La lista de claves prohibidas es corta: otras podrían colarse."),
    ("R4", "Los criterios se congelan",
     "Una versión ya usada para corregir no se modifica.",
     "No vigila nada hasta que alguien congela una versión."),
    ("R5", "Un fichero por cambio",
     "Tocar criterios o prosa exige documentar el cambio.",
     "Exige que exista el documento, no que su contenido sea cierto."),
    ("R6", "Nada personal en el repositorio",
     "Ni entregas, ni nombres, ni datos identificativos.",
     "Es un cedazo: reconoce formatos habituales, no todos."),
]

PATRON_PENDIENTE = re.compile(r"^- \*\*([a-z0-9_]+)\*\* — (.+)$", re.M)


class Regla(BaseModel):
    codigo: str
    nombre: str
    vigila: str
    limite: str
    infracciones: int


class Pendiente(BaseModel):
    clave: str
    explicacion: str


class EstadoGobernanza(BaseModel):
    conforme: bool
    reglas: list[Regla]


@router.get("/estado")
def obtener_estado(peticion: Request) -> EstadoGobernanza:
    raiz: Path = peticion.app.state.raiz
    infracciones = ejecutar(raiz, [], False)
    conteo = {codigo: 0 for codigo, _, _, _ in REGLAS}
    for infraccion in infracciones:
        if infraccion.regla in conteo:
            conteo[infraccion.regla] += 1

    return EstadoGobernanza(
        conforme=not infracciones,
        reglas=[
            Regla(codigo=codigo, nombre=nombre, vigila=vigila,
                  limite=limite, infracciones=conteo[codigo])
            for codigo, nombre, vigila, limite in REGLAS
        ],
    )


@router.get("/pendientes")
def obtener_pendientes(peticion: Request) -> list[Pendiente]:
    raiz: Path = peticion.app.state.raiz
    ruta = raiz / "docs" / "PENDIENTE_OFICIAL.md"
    if not ruta.is_file():
        return []
    texto = ruta.read_text(encoding="utf-8")
    return [
        Pendiente(clave=clave, explicacion=explicacion)
        for clave, explicacion in PATRON_PENDIENTE.findall(texto)
    ]
```

- [ ] **Step 6: Montar los routers**

Modificar `backend/app.py`, sustituyendo `crear_app`:

```python
def crear_app(raiz: Path) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta."""
    from backend.api import documentos, edicion, estado

    app = FastAPI(title="Editor de criterios", docs_url=None, redoc_url=None)
    app.state.raiz = raiz

    app.include_router(documentos.router)
    app.include_router(edicion.router)
    app.include_router(estado.router)

    @app.get("/api/salud")
    def salud() -> dict[str, str]:
        return {"estado": "vivo", "raiz": str(raiz)}

    return app
```

Crear `backend/api/__init__.py` vacío.

- [ ] **Step 7: Ejecutar la batería y commitear**

Run: `python -m pytest && python tools/verificar_gobernanza.py`
Expected: todo en verde.

```bash
git add backend/ tests/backend/test_api.py
git commit -m "feat: endpoints de documentos, edicion y estado"
```

---

### Task 6: Andamiaje del frontend y sistema visual

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/estilos.css`
- Create: `frontend/src/lib/api.ts`, `frontend/src/lib/tipos.ts`
- Create: `frontend/tailwind.config.js`, `frontend/postcss.config.js`

**Interfaces:**
- Produces: el cliente tipado `api` y los tokens visuales que las pantallas usan.

- [ ] **Step 1: Crear el proyecto**

Desde `frontend/`:

```bash
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
npm install clsx tailwind-merge lucide-react
```

- [ ] **Step 2: Configurar Tailwind con la paleta suiza**

`frontend/tailwind.config.js`:

```js
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        papel: "#FAFAF8",
        tinta: "#111111",
        grisclaro: "#E5E4E0",
        gris: "#6B6B66",
        // Una sola tinta de color, reservada a señalar la relación entre
        // una seccion y lo que deriva de ella. No decora nada mas.
        senal: "#C1301B",
      },
      fontFamily: {
        base: ["Inter", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      maxWidth: {
        lectura: "66ch",
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: Escribir los estilos base**

`frontend/src/estilos.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-feature-settings: "kern" 1, "liga" 1, "tnum" 1;
  }

  body {
    @apply bg-papel text-tinta font-base antialiased;
  }

  /* Rejilla estricta: todo se alinea a una columna de 8px. */
  :root {
    --unidad: 8px;
  }
}

@layer components {
  /* El texto normativo se lee a medida de lectura, nunca a todo lo ancho. */
  .prosa {
    @apply max-w-lectura text-[15px] leading-[1.65];
  }

  .prosa h2 {
    @apply text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mt-8 mb-3;
  }

  .prosa p {
    @apply mb-4;
  }

  /* Una sola tinta, y solo para la relacion seccion <-> criterio. */
  .senal {
    @apply text-senal;
  }

  .regla-fina {
    @apply border-t border-grisclaro;
  }
}
```

- [ ] **Step 4: Escribir los tipos**

`frontend/src/lib/tipos.ts`:

```ts
export interface Seccion {
  ancla: string
  titulo: string
  texto: string
  hash: string
  criterios_que_la_citan: number
}

export interface Documento {
  clave: string
  titulo: string
  fichero: string
  secciones: Seccion[]
}

export interface CriterioDerivado {
  fichero: string
  identificador: string
  valores: Record<string, string>
  fuente: string
}

export interface Propuesta {
  fichero: string
  identificador: string
  clave: string
  valor_actual: string
  valor_propuesto: string | null
  motivo: string
}

export interface CambioDeValor {
  fichero: string
  identificador: string
  clave: string
  valor_nuevo: string
}

export interface Resultado {
  exito: boolean
  commit: string | null
  infracciones: { regla: string; fichero: string; detalle: string }[]
  mensaje: string
}

export interface Regla {
  codigo: string
  nombre: string
  vigila: string
  limite: string
  infracciones: number
}

export interface EstadoGobernanza {
  conforme: boolean
  reglas: Regla[]
}

export interface Pendiente {
  clave: string
  explicacion: string
}
```

- [ ] **Step 5: Escribir el cliente**

`frontend/src/lib/api.ts`:

```ts
import type {
  CambioDeValor, Documento, EstadoGobernanza, Pendiente,
  Propuesta, Resultado, Seccion, CriterioDerivado,
} from "./tipos"

const BASE = "/api"

async function pedir<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${BASE}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  })
  if (!respuesta.ok) {
    const detalle = await respuesta.text()
    throw new Error(`${respuesta.status}: ${detalle}`)
  }
  return respuesta.json() as Promise<T>
}

export const api = {
  documentos: () => pedir<Documento[]>("/documentos"),

  seccion: (ancla: string) =>
    pedir<{ seccion: Seccion; criterios: CriterioDerivado[] }>(
      `/secciones/${encodeURIComponent(ancla)}`,
    ),

  propuesta: (ancla: string, textoNuevo: string) =>
    pedir<Propuesta[]>("/propuesta", {
      method: "POST",
      body: JSON.stringify({ ancla, texto_nuevo: textoNuevo }),
    }),

  guardar: (datos: {
    ancla: string
    texto_nuevo: string
    cambios: CambioDeValor[]
    motivo: string
    fuente: string
    hash_esperado: string
  }) => pedir<Resultado>("/guardar", {
    method: "POST",
    body: JSON.stringify(datos),
  }),

  estado: () => pedir<EstadoGobernanza>("/estado"),
  pendientes: () => pedir<Pendiente[]>("/pendientes"),
}
```

- [ ] **Step 6: Configurar el proxy de desarrollo**

`frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist" },
})
```

- [ ] **Step 7: Comprobar que compila y commitear**

Run: `cd frontend && npm run build`
Expected: build correcto, sin errores de TypeScript.

```bash
git add frontend/
git commit -m "feat: andamiaje del frontend y sistema visual suizo editorial"
```

---

### Task 7: Pantalla de documentos

**Files:**
- Create: `frontend/src/paginas/Documentos.tsx`
- Create: `frontend/src/componentes/ListaSecciones.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/componentes/ListaSecciones.test.tsx`

**Interfaces:**
- Consumes: `api.documentos()`, tipos de `lib/tipos`.
- Produces: `ListaSecciones` con props `{ documento: Documento; alElegir: (ancla: string) => void }`.

- [ ] **Step 1: Instalar el arnés de pruebas**

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Añadir a `frontend/vite.config.ts` dentro de `defineConfig`:

```ts
  test: {
    environment: "jsdom",
    setupFiles: ["./src/configuracion-tests.ts"],
    globals: true,
  },
```

Crear `frontend/src/configuracion-tests.ts`:

```ts
import "@testing-library/jest-dom/vitest"
```

Añadir a `frontend/package.json`, en `scripts`: `"test": "vitest run"`.

- [ ] **Step 2: Escribir el test que falla**

`frontend/src/componentes/ListaSecciones.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { ListaSecciones } from "./ListaSecciones"
import type { Documento } from "../lib/tipos"

const documento: Documento = {
  clave: "maestro",
  titulo: "Documento Maestro",
  fichero: "docs/maestro/01-documento-maestro.md",
  secciones: [
    { ancla: "maestro#8-dimensiones", titulo: "8. Dimensiones", texto: "", hash: "a", criterios_que_la_citan: 12 },
    { ancla: "maestro#19-privacidad", titulo: "19. Privacidad", texto: "", hash: "b", criterios_que_la_citan: 0 },
  ],
}

describe("ListaSecciones", () => {
  it("muestra cuantos criterios cita cada seccion", () => {
    render(<ListaSecciones documento={documento} alElegir={vi.fn()} />)
    expect(screen.getByText("12 criterios")).toBeInTheDocument()
  })

  it("dice explicitamente cuando una seccion no la cita nadie", () => {
    render(<ListaSecciones documento={documento} alElegir={vi.fn()} />)
    expect(screen.getByText("ningún criterio")).toBeInTheDocument()
  })

  it("avisa al elegir una seccion", async () => {
    const alElegir = vi.fn()
    render(<ListaSecciones documento={documento} alElegir={alElegir} />)
    screen.getByText("8. Dimensiones").click()
    expect(alElegir).toHaveBeenCalledWith("maestro#8-dimensiones")
  })
})
```

- [ ] **Step 3: Ejecutar el test para comprobar que falla**

Run: `cd frontend && npm test`
Expected: FAIL, `ListaSecciones` no existe.

- [ ] **Step 4: Escribir el componente**

`frontend/src/componentes/ListaSecciones.tsx`:

```tsx
import type { Documento } from "../lib/tipos"

interface Props {
  documento: Documento
  alElegir: (ancla: string) => void
}

/**
 * Las secciones de un documento, cada una con cuántos criterios dependen de
 * ella. Ese número es lo que el docente no puede deducir mirando el texto,
 * y por eso es lo único que lleva color.
 */
export function ListaSecciones({ documento, alElegir }: Props) {
  return (
    <ol className="regla-fina">
      {documento.secciones.map((seccion) => (
        <li key={seccion.ancla} className="border-b border-grisclaro">
          <button
            onClick={() => alElegir(seccion.ancla)}
            className="w-full text-left py-4 px-1 hover:bg-white transition-colors"
          >
            <span className="block text-[15px]">{seccion.titulo}</span>
            <span className="block mt-1 text-[12px] uppercase tracking-[0.08em]">
              {seccion.criterios_que_la_citan > 0 ? (
                <span className="senal">
                  {seccion.criterios_que_la_citan} criterios
                </span>
              ) : (
                <span className="text-gris">ningún criterio</span>
              )}
            </span>
          </button>
        </li>
      ))}
    </ol>
  )
}
```

- [ ] **Step 5: Escribir la página**

`frontend/src/paginas/Documentos.tsx`:

```tsx
import { useEffect, useState } from "react"

import { ListaSecciones } from "../componentes/ListaSecciones"
import { api } from "../lib/api"
import type { Documento } from "../lib/tipos"

interface Props {
  alElegirSeccion: (ancla: string) => void
}

export function Documentos({ alElegirSeccion }: Props) {
  const [documentos, setDocumentos] = useState<Documento[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.documentos().then(setDocumentos).catch((e) => setError(String(e)))
  }, [])

  if (error) return <p className="text-senal">{error}</p>

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
      {documentos.map((documento) => (
        <section key={documento.clave}>
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-1">
            {documento.titulo}
          </h2>
          <p className="font-mono text-[11px] text-gris mb-4">{documento.fichero}</p>
          <ListaSecciones documento={documento} alElegir={alElegirSeccion} />
        </section>
      ))}
    </div>
  )
}
```

- [ ] **Step 6: Ejecutar los tests y commitear**

Run: `cd frontend && npm test && npm run build`
Expected: 3 tests en verde, build correcto.

```bash
git add frontend/
git commit -m "feat: pantalla de documentos, con las dependencias a la vista"
```

---

### Task 8: Pantalla del editor

**Files:**
- Create: `frontend/src/paginas/Editor.tsx`
- Create: `frontend/src/componentes/PanelCriterios.tsx`
- Create: `frontend/src/componentes/DialogoGuardar.tsx`
- Test: `frontend/src/componentes/DialogoGuardar.test.tsx`

**Interfaces:**
- Consumes: `api.seccion`, `api.propuesta`, `api.guardar`.
- Produces: `DialogoGuardar` con props `{ propuestas, alConfirmar: (datos: {cambios, motivo, fuente}) => void, alCancelar }`.

Es la pantalla que hace que el procedimiento sea el camino natural. Sin motivo y sin fuente, el botón de guardar no se activa.

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/componentes/DialogoGuardar.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { DialogoGuardar } from "./DialogoGuardar"
import type { Propuesta } from "../lib/tipos"

const propuestas: Propuesta[] = [
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "extension",
    clave: "minimo_paginas_contenido",
    valor_actual: "20",
    valor_propuesto: "25",
    motivo: "El texto decía «20» y ahora dice «25» en el mismo sitio.",
  },
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "tipografia",
    clave: "familia",
    valor_actual: "Arial",
    valor_propuesto: null,
    motivo: "Este valor no es un número, revísalo a mano.",
  },
]

describe("DialogoGuardar", () => {
  it("no deja guardar sin motivo ni fuente", () => {
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={vi.fn()} alCancelar={vi.fn()} />)
    expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled()
  })

  it("deja guardar cuando estan los dos", () => {
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={vi.fn()} alCancelar={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "La programación lo sube" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "Programación 2026-27" } })
    expect(screen.getByRole("button", { name: /guardar/i })).toBeEnabled()
  })

  it("envia solo las propuestas aceptadas", () => {
    const alConfirmar = vi.fn()
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={alConfirmar} alCancelar={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /guardar/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      cambios: [{
        fichero: "criteria/v2026-2027/formato.yaml",
        identificador: "extension",
        clave: "minimo_paginas_contenido",
        valor_nuevo: "25",
      }],
      motivo: "motivo",
      fuente: "fuente",
    })
  })

  it("muestra el motivo de lo que hay que revisar a mano", () => {
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={vi.fn()} alCancelar={vi.fn()} />)
    expect(screen.getByText(/revísalo a mano/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Ejecutar el test para comprobar que falla**

Run: `cd frontend && npm test`
Expected: FAIL, `DialogoGuardar` no existe.

- [ ] **Step 3: Escribir el diálogo**

`frontend/src/componentes/DialogoGuardar.tsx`:

```tsx
import { useState } from "react"

import type { CambioDeValor, Propuesta } from "../lib/tipos"

interface Props {
  propuestas: Propuesta[]
  alConfirmar: (datos: { cambios: CambioDeValor[]; motivo: string; fuente: string }) => void
  alCancelar: () => void
}

/**
 * El paso que convierte una edición en un cambio registrado.
 *
 * Motivo y fuente son obligatorios porque es lo que R5 exige y lo que
 * permitirá entender la decisión dentro de un año. No hay forma de
 * saltárselos: sin ellos el botón no se activa.
 */
export function DialogoGuardar({ propuestas, alConfirmar, alCancelar }: Props) {
  const automaticas = propuestas.filter((p) => p.valor_propuesto !== null)
  const aMano = propuestas.filter((p) => p.valor_propuesto === null)

  const [aceptadas, setAceptadas] = useState<Set<string>>(
    new Set(automaticas.map((p) => `${p.identificador}.${p.clave}`)),
  )
  const [motivo, setMotivo] = useState("")
  const [fuente, setFuente] = useState("")

  const puedeGuardar = motivo.trim().length > 0 && fuente.trim().length > 0

  const alternar = (llave: string) => {
    const siguiente = new Set(aceptadas)
    siguiente.has(llave) ? siguiente.delete(llave) : siguiente.add(llave)
    setAceptadas(siguiente)
  }

  const confirmar = () => {
    const cambios: CambioDeValor[] = automaticas
      .filter((p) => aceptadas.has(`${p.identificador}.${p.clave}`))
      .map((p) => ({
        fichero: p.fichero,
        identificador: p.identificador,
        clave: p.clave,
        valor_nuevo: p.valor_propuesto as string,
      }))
    alConfirmar({ cambios, motivo: motivo.trim(), fuente: fuente.trim() })
  }

  return (
    <div className="fixed inset-0 bg-tinta/20 flex items-center justify-center p-8">
      <div className="bg-papel border border-tinta max-w-2xl w-full p-8 max-h-full overflow-y-auto">
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-6">
          Registrar el cambio
        </h2>

        {automaticas.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">Criterios que se actualizarán:</p>
            <ul className="regla-fina">
              {automaticas.map((p) => {
                const llave = `${p.identificador}.${p.clave}`
                return (
                  <li key={llave} className="border-b border-grisclaro py-3 flex gap-3">
                    <input
                      type="checkbox"
                      checked={aceptadas.has(llave)}
                      onChange={() => alternar(llave)}
                      className="mt-1"
                      aria-label={llave}
                    />
                    <div>
                      <p className="font-mono text-[12px]">
                        {p.identificador}.{p.clave}{" "}
                        <span className="text-gris">{p.valor_actual}</span>
                        {" → "}
                        <span className="senal">{p.valor_propuesto}</span>
                      </p>
                      <p className="text-[12px] text-gris mt-1">{p.motivo}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
          </section>
        )}

        {aMano.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">
              Esto no lo puedo decidir yo. Revísalo cuando termines:
            </p>
            <ul className="regla-fina">
              {aMano.map((p) => (
                <li key={`${p.identificador}.${p.clave}`}
                    className="border-b border-grisclaro py-3">
                  <p className="font-mono text-[12px]">
                    {p.identificador}.{p.clave} = {p.valor_actual}
                  </p>
                  <p className="text-[12px] text-gris mt-1">{p.motivo}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <label className="block mb-4">
          <span className="block text-[12px] uppercase tracking-[0.08em] text-gris mb-2">
            ¿Por qué cambias esto?
          </span>
          <textarea
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            rows={3}
            className="w-full border border-grisclaro bg-white p-3 text-[14px]"
          />
        </label>

        <label className="block mb-6">
          <span className="block text-[12px] uppercase tracking-[0.08em] text-gris mb-2">
            ¿Qué fuente lo respalda?
          </span>
          <input
            value={fuente}
            onChange={(e) => setFuente(e.target.value)}
            className="w-full border border-grisclaro bg-white p-3 text-[14px]"
          />
          <span className="block text-[12px] text-gris mt-2">
            La programación didáctica, una instrucción del centro, un acuerdo
            documentado. Si no hay ninguna, este cambio no debería hacerse.
          </span>
        </label>

        <div className="flex gap-3 justify-end">
          <button onClick={alCancelar}
                  className="px-4 py-2 text-[13px] border border-grisclaro">
            Cancelar
          </button>
          <button onClick={confirmar} disabled={!puedeGuardar}
                  className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30">
            Guardar
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Escribir el panel de criterios**

`frontend/src/componentes/PanelCriterios.tsx`:

```tsx
import type { CriterioDerivado } from "../lib/tipos"

interface Props {
  criterios: CriterioDerivado[]
}

/** Lo que depende de la sección que se está editando. */
export function PanelCriterios({ criterios }: Props) {
  if (criterios.length === 0) {
    return (
      <p className="text-[13px] text-gris">
        Ningún criterio deriva de esta sección. Puedes editarla sin que se
        actualice nada más — y sin que ninguna regla lo advierta.
      </p>
    )
  }

  return (
    <div>
      <h3 className="text-[12px] uppercase tracking-[0.08em] senal mb-4">
        Depende de esta sección
      </h3>
      <ul className="regla-fina">
        {criterios.map((criterio) => (
          <li key={`${criterio.fichero}:${criterio.identificador}`}
              className="border-b border-grisclaro py-3">
            <p className="font-mono text-[11px] text-gris">{criterio.fichero}</p>
            <p className="font-mono text-[12px] mt-1">{criterio.identificador}</p>
            <dl className="mt-2 space-y-1">
              {Object.entries(criterio.valores).map(([clave, valor]) => (
                <div key={clave} className="flex gap-2 font-mono text-[12px]">
                  <dt className="text-gris">{clave}</dt>
                  <dd>{valor}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 5: Escribir la página del editor**

`frontend/src/paginas/Editor.tsx`:

```tsx
import { useEffect, useState } from "react"

import { DialogoGuardar } from "../componentes/DialogoGuardar"
import { PanelCriterios } from "../componentes/PanelCriterios"
import { api } from "../lib/api"
import type {
  CambioDeValor, CriterioDerivado, Propuesta, Resultado, Seccion,
} from "../lib/tipos"

interface Props {
  ancla: string
  alVolver: () => void
}

export function Editor({ ancla, alVolver }: Props) {
  const [seccion, setSeccion] = useState<Seccion | null>(null)
  const [criterios, setCriterios] = useState<CriterioDerivado[]>([])
  const [texto, setTexto] = useState("")
  const [propuestas, setPropuestas] = useState<Propuesta[] | null>(null)
  const [resultado, setResultado] = useState<Resultado | null>(null)

  useEffect(() => {
    api.seccion(ancla).then(({ seccion, criterios }) => {
      setSeccion(seccion)
      setCriterios(criterios)
      setTexto(seccion.texto)
    })
  }, [ancla])

  if (!seccion) return <p className="text-gris">Cargando…</p>

  const sinCambios = texto === seccion.texto

  const abrirDialogo = async () => {
    setPropuestas(await api.propuesta(ancla, texto))
  }

  const guardar = async (datos: {
    cambios: CambioDeValor[]
    motivo: string
    fuente: string
  }) => {
    const respuesta = await api.guardar({
      ancla,
      texto_nuevo: texto,
      cambios: datos.cambios,
      motivo: datos.motivo,
      fuente: datos.fuente,
      hash_esperado: seccion.hash,
    })
    setPropuestas(null)
    setResultado(respuesta)
    if (respuesta.exito) {
      const recargada = await api.seccion(ancla)
      setSeccion(recargada.seccion)
      setCriterios(recargada.criterios)
      setTexto(recargada.seccion.texto)
    }
  }

  return (
    <div>
      <button onClick={alVolver} className="text-[12px] text-gris mb-6">
        ← Documentos
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_20rem] gap-12">
        <div>
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-1">
            {seccion.titulo}
          </h2>
          <p className="font-mono text-[11px] text-gris mb-6">{seccion.ancla}</p>

          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className="w-full max-w-lectura min-h-[24rem] border border-grisclaro
                       bg-white p-4 text-[15px] leading-[1.65] font-base"
          />

          <div className="mt-4 flex items-center gap-4">
            <button
              onClick={abrirDialogo}
              disabled={sinCambios}
              className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30"
            >
              Guardar cambio
            </button>
            {sinCambios && (
              <span className="text-[12px] text-gris">No has cambiado nada.</span>
            )}
          </div>

          {resultado && (
            <div className="mt-6 border-t border-grisclaro pt-4">
              <p className="text-[13px]">{resultado.mensaje}</p>
              {resultado.commit && (
                <p className="font-mono text-[12px] text-gris mt-1">
                  commit {resultado.commit}
                </p>
              )}
              {resultado.infracciones.length > 0 && (
                <ul className="mt-3 space-y-2">
                  {resultado.infracciones.map((i, indice) => (
                    <li key={indice} className="text-[12px]">
                      <span className="font-mono senal">[{i.regla}]</span>{" "}
                      <span className="font-mono text-gris">{i.fichero}</span>
                      <p className="text-gris mt-1">{i.detalle}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <aside>
          <PanelCriterios criterios={criterios} />
        </aside>
      </div>

      {propuestas && (
        <DialogoGuardar
          propuestas={propuestas}
          alConfirmar={guardar}
          alCancelar={() => setPropuestas(null)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 6: Ejecutar los tests y commitear**

Run: `cd frontend && npm test && npm run build`
Expected: 7 tests en verde.

```bash
git add frontend/
git commit -m "feat: editor con las dependencias en vivo y el registro obligatorio"
```

---

### Task 9: Estado, pendientes y empaquetado

**Files:**
- Create: `frontend/src/paginas/Estado.tsx`, `frontend/src/paginas/Pendientes.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`, `backend/app.py`
- Create: `editor.cmd`
- Modify: `README.md`

**Interfaces:**
- Consumes: `api.estado()`, `api.pendientes()`.
- Produces: la aplicación completa arrancable con un doble clic.

- [ ] **Step 1: Escribir la pantalla de estado**

`frontend/src/paginas/Estado.tsx`:

```tsx
import { useEffect, useState } from "react"

import { api } from "../lib/api"
import type { EstadoGobernanza } from "../lib/tipos"

export function Estado() {
  const [estado, setEstado] = useState<EstadoGobernanza | null>(null)

  useEffect(() => { api.estado().then(setEstado) }, [])

  if (!estado) return <p className="text-gris">Cargando…</p>

  return (
    <div className="max-w-lectura">
      <p className="text-[15px] mb-8">
        {estado.conforme
          ? "El repositorio está conforme: ninguna regla encuentra nada."
          : "Hay infracciones sin resolver."}
      </p>

      <ul className="regla-fina">
        {estado.reglas.map((regla) => (
          <li key={regla.codigo} className="border-b border-grisclaro py-5">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-[12px] text-gris">{regla.codigo}</span>
              <h3 className="text-[15px]">{regla.nombre}</h3>
              {regla.infracciones > 0 && (
                <span className="senal text-[12px]">{regla.infracciones}</span>
              )}
            </div>
            <p className="text-[13px] mt-2">{regla.vigila}</p>
            <p className="text-[13px] text-gris mt-1">
              <span className="uppercase tracking-[0.08em] text-[11px]">
                No cubre:{" "}
              </span>
              {regla.limite}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 2: Escribir la pantalla de pendientes**

`frontend/src/paginas/Pendientes.tsx`:

```tsx
import { useEffect, useState } from "react"

import { api } from "../lib/api"
import type { Pendiente } from "../lib/tipos"

export function Pendientes() {
  const [pendientes, setPendientes] = useState<Pendiente[]>([])

  useEffect(() => { api.pendientes().then(setPendientes) }, [])

  return (
    <div className="max-w-lectura">
      <p className="text-[15px] mb-8">
        Lo que el sistema no sabe y no va a inventar. Cuando llegue la
        programación oficial, esta lista dice qué desbloquea.
      </p>

      <ul className="regla-fina">
        {pendientes.map((pendiente) => (
          <li key={pendiente.clave} className="border-b border-grisclaro py-4">
            <p className="font-mono text-[13px] senal">{pendiente.clave}</p>
            <p className="text-[13px] text-gris mt-1">{pendiente.explicacion}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 3: Escribir la navegación**

`frontend/src/App.tsx`:

```tsx
import { useState } from "react"

import { Documentos } from "./paginas/Documentos"
import { Editor } from "./paginas/Editor"
import { Estado } from "./paginas/Estado"
import { Pendientes } from "./paginas/Pendientes"

type Vista = "documentos" | "estado" | "pendientes"

export default function App() {
  const [vista, setVista] = useState<Vista>("documentos")
  const [anclaEditando, setAnclaEditando] = useState<string | null>(null)

  const pestanas: { clave: Vista; texto: string }[] = [
    { clave: "documentos", texto: "Documentos" },
    { clave: "estado", texto: "Estado" },
    { clave: "pendientes", texto: "Pendientes" },
  ]

  return (
    <div className="min-h-screen px-8 py-10 md:px-16">
      <header className="mb-12">
        <h1 className="text-[13px] font-semibold uppercase tracking-[0.12em] mb-6">
          Editor de criterios
        </h1>
        <nav className="flex gap-6 regla-fina pt-4">
          {pestanas.map((pestana) => (
            <button
              key={pestana.clave}
              onClick={() => { setVista(pestana.clave); setAnclaEditando(null) }}
              className={
                vista === pestana.clave && !anclaEditando
                  ? "text-[13px] border-b-2 border-tinta pb-1"
                  : "text-[13px] text-gris pb-1"
              }
            >
              {pestana.texto}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {anclaEditando ? (
          <Editor ancla={anclaEditando} alVolver={() => setAnclaEditando(null)} />
        ) : vista === "documentos" ? (
          <Documentos alElegirSeccion={setAnclaEditando} />
        ) : vista === "estado" ? (
          <Estado />
        ) : (
          <Pendientes />
        )}
      </main>
    </div>
  )
}
```

`frontend/src/main.tsx`:

```tsx
import React from "react"
import ReactDOM from "react-dom/client"

import App from "./App"
import "./estilos.css"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 4: Servir el front desde FastAPI**

Añadir al final de `crear_app` en `backend/app.py`, antes del `return`:

```python
    # El front compilado se sirve desde el propio backend: una sola pieza
    # que arrancar, no dos.
    dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if dist.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
```

Y en la cabecera del fichero, junto a los demás imports, dejar `from pathlib import Path` (ya está).

- [ ] **Step 5: Escribir el punto de entrada**

Crear `backend/__main__.py`:

```python
"""Arranca el editor en local.

    python -m backend
"""

from pathlib import Path

import uvicorn

from backend.app import crear_app

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    # Solo 127.0.0.1: esta aplicación escribe en el disco y ejecuta git.
    uvicorn.run(crear_app(raiz), host="127.0.0.1", port=8000, log_level="warning")
```

- [ ] **Step 6: Escribir el arrancador**

Crear `editor.cmd` en la raíz:

```bat
@echo off
REM Arranca el editor de criterios y abre el navegador.
cd /d "%~dp0"

if not exist "frontend\dist\index.html" (
    echo Compilando el frontend...
    pushd frontend
    call npm install
    call npm run build
    popd
)

start "" http://127.0.0.1:8000
python -m backend
```

- [ ] **Step 7: Documentar en el README**

Añadir a `README.md`, tras la sección de puesta en marcha:

```markdown
## Editor de criterios

Para leer y modificar los documentos normativos sin salirte del
procedimiento:

    editor.cmd

Abre `http://127.0.0.1:8000` en el navegador. La primera vez compila el
frontend, lo que tarda un poco.

El editor no permite guardar un cambio sin motivo y sin fuente, y ejecuta las
seis reglas antes de comitear. Si alguna salta, no se guarda nada: el
repositorio queda como estaba.
```

- [ ] **Step 8: Comprobar el conjunto**

```bash
cd frontend && npm test && npm run build && cd ..
python -m pytest
python tools/verificar_gobernanza.py
```

Expected: todo en verde, gobernanza conforme.

Arranque manual: `python -m backend`, abrir `http://127.0.0.1:8000`, comprobar que las cuatro pantallas cargan y que editar una sección y guardarla sin motivo muestra el error.

- [ ] **Step 9: Commitear**

```bash
git add frontend/ backend/ editor.cmd README.md
git commit -m "feat: pantallas de estado y pendientes, y arranque con un doble clic"
```

---

## Verificación final del plan

- [ ] `python -m pytest` — todo en verde
- [ ] `cd frontend && npm test` — todo en verde
- [ ] `python tools/verificar_gobernanza.py` — conforme
- [ ] `editor.cmd` levanta la aplicación y abre el navegador
- [ ] Editar una sección y guardar sin motivo muestra el error y no comitea
- [ ] Editar el mínimo de páginas propone el valor nuevo, y al guardar genera documento de cambio, actualiza el YAML, sella y comitea
- [ ] Una sección que ningún criterio cita se muestra como tal
- [ ] El backend no escucha en `0.0.0.0`
