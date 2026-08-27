# Lectura objetiva de entregas — Plan de implementación (Parte A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el sistema recoja un PDF de la carpeta de entregas, mida sobre él todo lo que se puede medir sin criterio humano, lo compare con la entrega anterior y deje la ficha guardada, sin valorar nada.

**Architecture:** Cinco módulos nuevos bajo `backend/`, cada uno con una responsabilidad y sin conocer a los demás salvo por sus modelos. `extraccion/` mide sobre el PDF con PyMuPDF y no sabe qué criterios existen. `formato/` compara lo medido con `criteria/v2026-2027/formato.yaml` y no sabe abrir un PDF. `evolucion/` compara dos textos. `vigilancia/` mira la carpeta y propone una identificación. `persistencia/` guarda, detrás de un puerto con dos implementaciones. La API los une; el frontend añade dos pantallas al mismo binario.

**Tech Stack:** Python 3.13, PyMuPDF 1.28.2, FastAPI, Pydantic 2, pytest, httpx (ya presente, se usa como cliente de PostgREST), React 19, Vite, Tailwind, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-27-flujo-de-correccion-design.md`

## Global Constraints

Todo lo que sigue vincula a **todas** las tareas.

- **Idioma:** todo en castellano — identificadores, comentarios, mensajes de error, docstrings y commits. Los mensajes los lee el docente, no un programador.
- **El archivo entregado no se toca.** Ni se mueve, ni se renombra, ni se modifica, ni se copia dentro del repositorio. Se abre en lectura y nada más (§18.1 del Maestro).
- **Nada de PDFs en el repositorio.** `.gitignore` ya excluye `*.pdf`; los PDFs de prueba se **construyen** con PyMuPDF en un fixture y viven en `tmp_path`. Ninguna prueba usa una entrega real.
- **La carpeta de entregas vive fuera del repositorio.** El backend se niega a vigilar una ruta que caiga bajo la raíz del repositorio (R6 y el hook de pre-commit lo harían inutilizable).
- **Lo medible se mide, no se pregunta.** Nada de esta parte llama a ningún modelo de lenguaje. No hay red salvo hacia Supabase.
- **Lo que no se puede medir se declara `NO_VERIFICABLE`, nunca se estima.** Es la regla R3 aplicada a la medición: un dato ausente no se sustituye por uno razonable.
- **La vigilancia propone, nunca decide.** Si el nombre del fichero no permite deducir alumno y fase con certeza, la propuesta va vacía. No se adivina.
- **Sin credenciales de Supabase el sistema arranca igual**, con el almacén en memoria, y lo dice de forma visible. Nunca finge haber guardado.
- **Valores exactos de los criterios:** se leen de `criteria/v2026-2027/formato.yaml` en tiempo de ejecución. Ninguna tarea los copia al código.
- **Trampa de `pyyaml` conocida:** YAML 1.1 lee `no`, `No` y `off` como booleano `False`. Los ficheros de criterios usan `true`/`false`; ningún código nuevo depende de leer la cadena `"no"`.
- **Antes de dar por cerrada cualquier tarea:** `python -m pytest`, `cd frontend && npm test` y `python tools/verificar_gobernanza.py`, los tres en verde.

**Una condición de parada que esta parte no implementa, y por qué.** El §18.2
manda marcar GRIS y 0 una entrega fuera de plazo. Aquí no se hace, porque el
calendario está en `PENDIENTE_OFICIAL` y sin fechas límite oficiales no hay
plazo contra el que comparar. Las columnas `fecha_limite` y `dentro_de_plazo`
existen ya en la tabla `entrega` y se quedan a `NULL`: cuando llegue el
calendario será rellenarlas, no rehacer nada. Estimar las fechas para tener la
comprobación funcionando sería exactamente lo que R3 prohíbe, y el precio de
equivocarse lo pagaría un alumno con un cero.

---

### Task 1: Configuración y carpeta de entregas

El punto de entrada de todo lo demás: de dónde salen los PDFs y cómo se comprueba que esa ruta es utilizable. La comprobación de que la carpeta no cae bajo el repositorio es el corazón de esta tarea, no un detalle: es lo que impide crear un repositorio que no admite commits.

**Files:**
- Create: `backend/configuracion.py`
- Create: `tests/backend/test_configuracion.py`
- Create: `.env.example`
- Modify: `requirements-dev.txt` (añadir `pymupdf==1.28.2`)

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces:
  - `Configuracion` (pydantic `BaseModel`) con campos `carpeta_entregas: Path | None`, `url_supabase: str | None`, `clave_supabase: str | None`, `version_criterios: str`.
  - `cargar(raiz: Path, entorno: dict[str, str] | None = None) -> Configuracion`
  - `ProblemaDeCarpeta` (dataclass) con `motivo: str`; y `revisar_carpeta(raiz: Path, carpeta: Path) -> ProblemaDeCarpeta | None` — devuelve `None` si la carpeta sirve.

- [ ] **Step 1: Añadir PyMuPDF a las dependencias**

En `requirements-dev.txt`, tras la línea `ruamel.yaml==0.18.10`, añadir:

```
pymupdf==1.28.2
```

- [ ] **Step 2: Escribir los tests de `revisar_carpeta`**

Crear `tests/backend/test_configuracion.py`:

```python
"""La carpeta de entregas: qué rutas sirven y cuáles no."""

from pathlib import Path

from backend.configuracion import cargar, revisar_carpeta


def test_carpeta_valida_no_da_problema(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()

    assert revisar_carpeta(raiz, carpeta) is None


def test_carpeta_dentro_del_repositorio_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    carpeta = raiz / "01_ALUMNOS"
    carpeta.mkdir(parents=True)

    problema = revisar_carpeta(raiz, carpeta)

    assert problema is not None
    assert "dentro del repositorio" in problema.motivo


def test_carpeta_que_es_la_propia_raiz_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()

    problema = revisar_carpeta(raiz, raiz)

    assert problema is not None
    assert "dentro del repositorio" in problema.motivo


def test_carpeta_inexistente_se_rechaza(tmp_path: Path) -> None:
    problema = revisar_carpeta(tmp_path / "repo", tmp_path / "no-existe")

    assert problema is not None
    assert "no existe" in problema.motivo


def test_ruta_que_es_un_fichero_se_rechaza(tmp_path: Path) -> None:
    fichero = tmp_path / "cosa.txt"
    fichero.write_text("x", encoding="utf-8")

    problema = revisar_carpeta(tmp_path / "repo", fichero)

    assert problema is not None
    assert "no es una carpeta" in problema.motivo


def test_el_motivo_dice_que_hacer(tmp_path: Path) -> None:
    """El docente lee esto: ha de saber qué corregir, no solo que falla."""
    raiz = tmp_path / "repo"
    carpeta = raiz / "01_ALUMNOS"
    carpeta.mkdir(parents=True)

    problema = revisar_carpeta(raiz, carpeta)

    assert problema is not None
    assert "REVISOR_CARPETA_ENTREGAS" in problema.motivo
```

- [ ] **Step 3: Escribir los tests de `cargar`**

Añadir al final de `tests/backend/test_configuracion.py`:

```python
def test_cargar_sin_entorno_deja_todo_vacio(tmp_path: Path) -> None:
    configuracion = cargar(tmp_path, entorno={})

    assert configuracion.carpeta_entregas is None
    assert configuracion.url_supabase is None
    assert configuracion.clave_supabase is None


def test_cargar_lee_la_carpeta_del_entorno(tmp_path: Path) -> None:
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()

    configuracion = cargar(
        tmp_path / "repo",
        entorno={"REVISOR_CARPETA_ENTREGAS": str(carpeta)},
    )

    assert configuracion.carpeta_entregas == carpeta


def test_cargar_descarta_una_carpeta_que_no_sirve(tmp_path: Path) -> None:
    """Una ruta inservible se ignora: no se arrastra media configuración."""
    raiz = tmp_path / "repo"
    dentro = raiz / "01_ALUMNOS"
    dentro.mkdir(parents=True)

    configuracion = cargar(raiz, entorno={"REVISOR_CARPETA_ENTREGAS": str(dentro)})

    assert configuracion.carpeta_entregas is None


def test_cargar_lee_el_fichero_env(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    (raiz / ".env").write_text(
        f"# comentario\nREVISOR_CARPETA_ENTREGAS={carpeta}\n"
        "SUPABASE_URL=https://ejemplo.supabase.co\n",
        encoding="utf-8",
    )

    configuracion = cargar(raiz, entorno={})

    assert configuracion.carpeta_entregas == carpeta
    assert configuracion.url_supabase == "https://ejemplo.supabase.co"


def test_el_entorno_manda_sobre_el_fichero(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text("SUPABASE_URL=del-fichero\n", encoding="utf-8")

    configuracion = cargar(raiz, entorno={"SUPABASE_URL": "del-entorno"})

    assert configuracion.url_supabase == "del-entorno"


def test_version_de_criterios_por_omision(tmp_path: Path) -> None:
    assert cargar(tmp_path, entorno={}).version_criterios == "v2026-2027"
```

- [ ] **Step 4: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/backend/test_configuracion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.configuracion'`

- [ ] **Step 5: Escribir `backend/configuracion.py`**

```python
"""De dónde salen los PDFs y con qué credenciales se guarda.

La carpeta de entregas vive FUERA del repositorio, y no es una
preferencia: la regla R6 impide que un PDF entre en el árbol versionado,
así que una carpeta interior dejaría el repositorio sin poder comitear en
cuanto llegase el primer trabajo. Por eso se comprueba aquí, al arrancar,
y no se descubre más tarde.
"""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

VERSION_CRITERIOS_POR_OMISION = "v2026-2027"

CARPETA = "REVISOR_CARPETA_ENTREGAS"
URL = "SUPABASE_URL"
CLAVE = "SUPABASE_SERVICE_KEY"
VERSION = "REVISOR_VERSION_CRITERIOS"


@dataclass(frozen=True)
class ProblemaDeCarpeta:
    """Por qué una ruta no sirve como carpeta de entregas."""

    motivo: str


class Configuracion(BaseModel):
    """Lo que el backend necesita saber antes de vigilar nada."""

    carpeta_entregas: Path | None = None
    url_supabase: str | None = None
    clave_supabase: str | None = None
    version_criterios: str = VERSION_CRITERIOS_POR_OMISION


def revisar_carpeta(raiz: Path, carpeta: Path) -> ProblemaDeCarpeta | None:
    """Devuelve el problema que impide usar esa carpeta, o None si sirve."""
    raiz = raiz.resolve()
    carpeta = carpeta.resolve()

    if carpeta == raiz or raiz in carpeta.parents:
        return ProblemaDeCarpeta(
            f"La carpeta de entregas «{carpeta}» está dentro del repositorio. "
            "Los trabajos de los alumnos no pueden vivir en el árbol "
            "versionado: el primero que llegara impediría guardar cualquier "
            f"cambio. Indica en {CARPETA} una carpeta de fuera."
        )
    if not carpeta.exists():
        return ProblemaDeCarpeta(
            f"La carpeta de entregas «{carpeta}» no existe. Créala o corrige "
            f"{CARPETA}."
        )
    if not carpeta.is_dir():
        return ProblemaDeCarpeta(
            f"«{carpeta}» no es una carpeta. {CARPETA} debe apuntar a la "
            "carpeta donde se dejan los trabajos, no a un archivo."
        )
    return None


def _leer_env(raiz: Path) -> dict[str, str]:
    """Pares clave=valor del fichero .env de la raíz, si lo hay."""
    fichero = raiz / ".env"
    if not fichero.is_file():
        return {}
    leido: dict[str, str] = {}
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        leido[clave.strip()] = valor.strip().strip('"').strip("'")
    return leido


def cargar(raiz: Path, entorno: dict[str, str] | None = None) -> Configuracion:
    """Configuración efectiva: el entorno manda sobre el fichero .env.

    Una carpeta que no sirve se descarta entera y se deja a None. Arrastrar
    media configuración solo consigue que el fallo aparezca más tarde y más
    lejos de su causa.
    """
    import os

    valores = _leer_env(raiz)
    valores.update(dict(os.environ) if entorno is None else entorno)

    carpeta: Path | None = None
    if valores.get(CARPETA):
        candidata = Path(valores[CARPETA])
        if revisar_carpeta(raiz, candidata) is None:
            carpeta = candidata.resolve()

    return Configuracion(
        carpeta_entregas=carpeta,
        url_supabase=valores.get(URL) or None,
        clave_supabase=valores.get(CLAVE) or None,
        version_criterios=valores.get(VERSION) or VERSION_CRITERIOS_POR_OMISION,
    )
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/backend/test_configuracion.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 7: Escribir `.env.example`**

```
# Copia este fichero a .env y rellena lo que uses. .env no se versiona.

# Carpeta donde el docente deja los trabajos. TIENE QUE ESTAR FUERA de este
# repositorio: los PDFs no pueden entrar en el arbol versionado.
REVISOR_CARPETA_ENTREGAS=C:/Users/tu-usuario/01_ALUMNOS

# Persistencia. Sin estas dos, el sistema arranca igual pero guarda solo en
# memoria y lo avisa: al cerrar se pierde lo trabajado.
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_KEY=

# Version de criterios con la que se corrige.
REVISOR_VERSION_CRITERIOS=v2026-2027
```

- [ ] **Step 8: Comprobar que `.env.example` sí se versiona y `.env` no**

Run: `git check-ignore -v .env .env.example ; git status --short`
Expected: `.env` aparece ignorado por la regla `.env`; `.env.example` NO aparece ignorado (la regla `!.env.example` lo rescata) y sale como fichero nuevo en `git status`.

- [ ] **Step 9: Ejecutar la batería completa**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`
Expected: 164 passed; `Gobernanza conforme: 0 infracciones.`

- [ ] **Step 10: Commit**

```bash
git add requirements-dev.txt .env.example backend/configuracion.py tests/backend/test_configuracion.py
git commit -m "feat: configuracion y comprobacion de la carpeta de entregas

La carpeta vive fuera del repositorio y el backend lo comprueba al
arrancar. R6 impide que un PDF entre en el arbol versionado, asi que una
carpeta interior dejaria el repositorio sin poder comitear en cuanto
llegara el primer trabajo. Vale mas descubrirlo aqui que entonces."
```

---

### Task 2: Extracción — apertura, páginas y origen del PDF

Lo primero que hay que saber de un archivo: si abre, cuántas páginas tiene, cuáles están vacías y si salió de un procesador de textos o de un escáner. Nada de esto necesita criterio: son hechos del fichero.

**Files:**
- Create: `backend/extraccion/__init__.py`
- Create: `backend/extraccion/medidas.py`
- Create: `backend/extraccion/lectura.py`
- Create: `tests/conftest.py`
- Create: `tests/extraccion/test_lectura.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - En `medidas.py`: `Pagina(BaseModel)` con `numero: int`, `caracteres: int`, `en_blanco: bool`, `ancho_pt: float`, `alto_pt: float`.
  - En `lectura.py`: `PdfIlegible(Exception)`; `abrir(ruta: Path)` — gestor de contexto que cede el `pymupdf.Document`; `leer_paginas(documento) -> list[Pagina]`; `procede_de_escaner(documento) -> bool`.

- [ ] **Step 1: Escribir el fixture que construye PDFs**

Va en `tests/conftest.py`, en la raíz de `tests/`, no dentro de
`tests/extraccion/`. Los directorios de pruebas de este repositorio no son
paquetes —`tests/backend/` y `tests/gobernanza/` no tienen `__init__.py`—,
así que un módulo de prueba no puede importar de otro. Todo lo compartido
entre carpetas de prueba vive en este conftest, que pytest carga solo.

Crear `tests/conftest.py`:

```python
"""PDFs sintéticos con desviaciones conocidas.

Se construyen aquí y viven en tmp_path. Ninguna prueba de este proyecto
toca una entrega real de un alumno, y ningún PDF entra en el repositorio.
"""

from pathlib import Path

import pymupdf
import pytest

# insert_text sitúa la línea base en el punto dado. El interlineado medido
# será la distancia entre líneas base consecutivas.
IZQUIERDA = 72.0
PRIMERA_LINEA = 100.0

# Los criterios de formato reales, con el mínimo de páginas rebajado a 4 y la
# familia puesta en Helvetica, que es la que PyMuPDF incrusta con «helv».
CRITERIOS_DE_PRUEBA = """
extension:
  minimo_paginas_contenido: 4
  excluye: [portada, indice, anexos]
  fuente: maestro#6-estandar-academico

tipografia:
  familia: Helvetica
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
"""


def escribir_pdf(
    ruta: Path,
    paginas: list[list[str]],
    cuerpo: float = 11.0,
    salto: float = 19.0,
    fuente: str = "helv",
    izquierda: float = IZQUIERDA,
) -> Path:
    """Un PDF con las líneas indicadas, una lista de líneas por página."""
    documento = pymupdf.open()
    for lineas in paginas:
        pagina = documento.new_page()
        y = PRIMERA_LINEA
        for linea in lineas:
            pagina.insert_text((izquierda, y), linea, fontname=fuente, fontsize=cuerpo)
            y += salto
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture(name="escribir_pdf")
def _escribir_pdf():
    """El constructor de PDFs, para las pruebas que necesitan uno a medida.

    Se expone como fixture y no se importa directamente porque los
    directorios de prueba no son paquetes: un módulo de prueba no puede
    importar de otro.
    """
    return escribir_pdf


@pytest.fixture
def criterios_de_formato(tmp_path: Path) -> Path:
    """Una raíz con solo criteria/v2026-2027/formato.yaml.

    Los valores son los reales salvo el mínimo de páginas, rebajado a 4 para
    que un PDF de prueba pueda cumplirlo. Vive aquí y no en cada carpeta de
    pruebas porque lo usan las de formato, las del servicio y las de la API.
    """
    raiz = tmp_path / "repo"
    carpeta = raiz / "criteria" / "v2026-2027"
    carpeta.mkdir(parents=True)
    (carpeta / "formato.yaml").write_text(CRITERIOS_DE_PRUEBA, encoding="utf-8")
    return raiz


@pytest.fixture
def criterios_alterados(tmp_path: Path):
    """Una raíz de criterios con un valor cambiado, para probar el fallo.

    Devuelve la función que hace la sustitución: cada prueba altera lo que
    necesita sin repetir el fichero entero.
    """
    def alterar(viejo: str, nuevo: str) -> Path:
        raiz = tmp_path / "alterado"
        carpeta = raiz / "criteria" / "v2026-2027"
        carpeta.mkdir(parents=True)
        (carpeta / "formato.yaml").write_text(
            CRITERIOS_DE_PRUEBA.replace(viejo, nuevo), encoding="utf-8"
        )
        return raiz

    return alterar


@pytest.fixture
def pdf_simple(tmp_path: Path) -> Path:
    """Dos páginas con texto, ninguna vacía."""
    return escribir_pdf(
        tmp_path / "simple.pdf",
        [["Primera linea.", "Segunda linea."], ["Tercera linea."]],
    )


@pytest.fixture
def pdf_con_pagina_en_blanco(tmp_path: Path) -> Path:
    """Tres páginas; la segunda, vacía."""
    return escribir_pdf(
        tmp_path / "con-blanco.pdf",
        [["Texto de la primera."], [], ["Texto de la tercera."]],
    )


@pytest.fixture
def pdf_escaneado(tmp_path: Path) -> Path:
    """Una imagen a página completa y ni un carácter de texto."""
    documento = pymupdf.open()
    pagina = documento.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 850), False)
    pixmap.set_rect(pixmap.irect, (240, 240, 235))
    pagina.insert_image(pagina.rect, pixmap=pixmap)
    ruta = tmp_path / "escaneado.pdf"
    documento.save(ruta)
    documento.close()
    return ruta
```

- [ ] **Step 2: Escribir los tests de lectura**

Crear `tests/extraccion/test_lectura.py`:

```python
"""Lo que se sabe de un PDF sin interpretarlo."""

from pathlib import Path

import pytest

from backend.extraccion.lectura import (
    PdfIlegible,
    abrir,
    leer_paginas,
    procede_de_escaner,
)


def test_cuenta_las_paginas(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        paginas = leer_paginas(documento)

    assert len(paginas) == 2
    assert [pagina.numero for pagina in paginas] == [1, 2]


def test_detecta_la_pagina_en_blanco(pdf_con_pagina_en_blanco: Path) -> None:
    with abrir(pdf_con_pagina_en_blanco) as documento:
        paginas = leer_paginas(documento)

    assert [pagina.en_blanco for pagina in paginas] == [False, True, False]


def test_cuenta_los_caracteres_de_cada_pagina(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        paginas = leer_paginas(documento)

    assert paginas[0].caracteres > paginas[1].caracteres > 0


def test_mide_el_tamano_de_la_pagina(pdf_simple: Path) -> None:
    """A4 son 595 x 842 puntos; se admite el redondeo del propio PDF."""
    with abrir(pdf_simple) as documento:
        paginas = leer_paginas(documento)

    assert paginas[0].ancho_pt == pytest.approx(595, abs=1)
    assert paginas[0].alto_pt == pytest.approx(842, abs=1)


def test_un_pdf_con_texto_no_es_escaneado(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        assert procede_de_escaner(documento) is False


def test_un_pdf_de_imagenes_sin_texto_es_escaneado(pdf_escaneado: Path) -> None:
    with abrir(pdf_escaneado) as documento:
        assert procede_de_escaner(documento) is True


def test_un_fichero_que_no_es_pdf_da_error_legible(tmp_path: Path) -> None:
    falso = tmp_path / "no-es.pdf"
    falso.write_text("esto no es un PDF", encoding="utf-8")

    with pytest.raises(PdfIlegible) as fallo:
        with abrir(falso):
            pass

    assert "no se ha podido abrir" in str(fallo.value).lower()


def test_un_fichero_que_no_existe_da_error_legible(tmp_path: Path) -> None:
    with pytest.raises(PdfIlegible) as fallo:
        with abrir(tmp_path / "fantasma.pdf"):
            pass

    assert "no existe" in str(fallo.value).lower()


def test_un_pdf_sin_paginas_da_error_legible(tmp_path: Path) -> None:
    """PyMuPDF se niega a guardar un PDF de cero páginas, así que se escribe
    a mano. Un PDF así llega cuando una exportación se queda a medias."""
    vacio = tmp_path / "vacio.pdf"
    vacio.write_bytes(
        b"%PDF-1.4
"
        b"1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
"
        b"2 0 obj
<< /Type /Pages /Kids [] /Count 0 >>
endobj
"
        b"trailer
<< /Root 1 0 R /Size 3 >>
%%EOF
"
    )

    with pytest.raises(PdfIlegible) as fallo:
        with abrir(vacio):
            pass

    assert "ninguna página" in str(fallo.value)
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/extraccion/test_lectura.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.extraccion'`

- [ ] **Step 4: Escribir `backend/extraccion/medidas.py`**

```python
"""Lo que se mide sobre un PDF, sin juzgar si está bien o mal.

Estos modelos son hechos: cuántas páginas, qué cuerpo, qué imágenes. La
comparación con lo que exigen los criterios ocurre en backend/formato/, que
no sabe abrir un PDF, igual que este módulo no sabe qué exige el Maestro.
"""

from pydantic import BaseModel


class Pagina(BaseModel):
    """Una página del documento."""

    numero: int
    caracteres: int
    en_blanco: bool
    ancho_pt: float
    alto_pt: float
```

- [ ] **Step 5: Escribir `backend/extraccion/__init__.py`**

```python
"""Medición objetiva de un PDF. No llama a ningún modelo de lenguaje."""
```

- [ ] **Step 6: Escribir `backend/extraccion/lectura.py`**

```python
"""Apertura del PDF y hechos básicos de sus páginas.

El archivo se abre en lectura y nunca se modifica, ni se mueve, ni se
renombra: lo exige el §18.1 del Documento Maestro.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pymupdf

from backend.extraccion.medidas import Pagina

# Una página con menos caracteres que esto no tiene contenido: son restos de
# numeración, encabezado o pie. Un dígito y poco más.
CARACTERES_MINIMOS = 3


class PdfIlegible(Exception):
    """El archivo no se puede leer. Es una parada del §18.2, no un fallo."""


@contextmanager
def abrir(ruta: Path) -> Iterator[pymupdf.Document]:
    """Abre el PDF en lectura y lo cierra pase lo que pase.

    Los mensajes los lee el docente: dicen qué archivo y qué le ocurre, no
    qué excepción lanzó la librería.
    """
    if not ruta.is_file():
        raise PdfIlegible(f"El archivo «{ruta.name}» no existe en la carpeta.")
    try:
        documento = pymupdf.open(ruta)
    except Exception as fallo:
        raise PdfIlegible(
            f"El archivo «{ruta.name}» no se ha podido abrir como PDF. "
            "Puede estar dañado, incompleto o no ser realmente un PDF."
        ) from fallo
    try:
        if documento.needs_pass:
            raise PdfIlegible(
                f"El archivo «{ruta.name}» está protegido con contraseña. "
                "Pide al alumno una copia sin protección."
            )
        if documento.page_count == 0:
            raise PdfIlegible(
                f"El archivo «{ruta.name}» no tiene ninguna página."
            )
        yield documento
    finally:
        documento.close()


def leer_paginas(documento: pymupdf.Document) -> list[Pagina]:
    """Una entrada por página, numeradas desde 1 como las ve el docente."""
    paginas = []
    for indice, pagina in enumerate(documento, start=1):
        texto = pagina.get_text().strip()
        paginas.append(Pagina(
            numero=indice,
            caracteres=len(texto),
            en_blanco=len(texto) < CARACTERES_MINIMOS,
            ancho_pt=pagina.rect.width,
            alto_pt=pagina.rect.height,
        ))
    return paginas


def procede_de_escaner(documento: pymupdf.Document) -> bool:
    """Si el PDF es imagen sin texto extraíble.

    Un trabajo escaneado no es corregible: no se puede medir su tipografía
    ni citar un fragmento. El §6 del Índice comentado lo excluye, y aquí se
    detecta por lo único que lo distingue de forma fiable: que no hay ni un
    carácter de texto en todo el documento.
    """
    return not any(pagina.get_text().strip() for pagina in documento)
```

- [ ] **Step 7: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/extraccion/test_lectura.py -v`
Expected: PASS, 9 tests.

- [ ] **Step 8: Commit**

```bash
git add backend/extraccion tests/extraccion
git commit -m "feat: apertura del PDF, paginas y deteccion de escaneado

Los PDF de prueba se construyen con PyMuPDF en un fixture y viven en
tmp_path: ninguna prueba toca una entrega real y ninguno entra en el
repositorio.

Los mensajes de PdfIlegible los lee el docente, asi que dicen que archivo
falla y que hacer, no que excepcion lanzo la libreria."
```
---

### Task 3: Extracción — tipografía, interlineado, márgenes y alineación

Todo lo que el §6.2 del Maestro exige del cuerpo del texto. Aquí aparece la primera medida que **no se puede convertir en veredicto**: el interlineado. Un PDF guarda la distancia entre líneas base, no el «1,5» que el alumno eligió en Word, y la equivalencia depende de la fuente. Se mide el ratio y se deja a la vista; quien decide qué ratio corresponde a 1,5 es la calibración, no este código.

**Files:**
- Modify: `backend/extraccion/medidas.py` (añadir `MedidasDeTexto`)
- Create: `backend/extraccion/tipografia.py`
- Create: `tests/extraccion/test_tipografia.py`
- Modify: `tests/conftest.py` (añadir dos fixtures)

**Interfaces:**
- Consumes: `abrir` de `backend.extraccion.lectura`; el helper `escribir_pdf` de `tests/conftest.py`.
- Produces:
  - `MedidasDeTexto(BaseModel)` con `familia_dominante: str`, `cuerpo_dominante: float`, `proporcion_cuerpo_dominante: float`, `ratio_interlineado: float | None`, `margen_izquierdo_cm: float | None`, `margen_derecho_cm: float | None`, `margen_superior_cm: float | None`, `margen_inferior_cm: float | None`, `proporcion_lineas_al_margen_derecho: float | None`.
  - `medir_texto(documento: pymupdf.Document) -> MedidasDeTexto`
  - `normalizar_familia(nombre: str) -> str`

- [ ] **Step 1: Añadir los fixtures que hacen falta**

Añadir al final de `tests/conftest.py`:

```python
@pytest.fixture
def pdf_cuerpo_mezclado(tmp_path: Path) -> Path:
    """Mucho texto a cuerpo 11 y un titular a 20: el dominante es el 11."""
    documento = pymupdf.open()
    pagina = documento.new_page()
    pagina.insert_text((IZQUIERDA, 80.0), "TITULO", fontname="helv", fontsize=20.0)
    y = PRIMERA_LINEA + 30
    for _ in range(8):
        pagina.insert_text(
            (IZQUIERDA, y),
            "Linea larga del cuerpo del trabajo con bastante texto.",
            fontname="helv",
            fontsize=11.0,
        )
        y += 19.0
    ruta = tmp_path / "mezclado.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_justificado(tmp_path: Path) -> Path:
    """Cuatro líneas que acaban en el mismo borde derecho y una corta.

    Es lo que distingue el texto justificado: todas las líneas menos la
    última de cada párrafo terminan exactamente en el margen.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()
    y = PRIMERA_LINEA
    for _ in range(4):
        pagina.insert_text(
            (IZQUIERDA, y), "Linea que llega al margen.", fontname="helv", fontsize=11.0
        )
        y += 19.0
    pagina.insert_text((IZQUIERDA, y), "Corta.", fontname="helv", fontsize=11.0)
    ruta = tmp_path / "justificado.pdf"
    documento.save(ruta)
    documento.close()
    return ruta
```

- [ ] **Step 2: Escribir los tests de normalización de la familia**

Crear `tests/extraccion/test_tipografia.py`:

```python
"""Tipografía, interlineado, márgenes y alineación medidos sobre el PDF."""

from pathlib import Path

import pytest

from backend.extraccion.lectura import abrir
from backend.extraccion.tipografia import medir_texto, normalizar_familia


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("Arial", "Arial"),
        ("ABCDEF+Arial", "Arial"),
        ("ABCDEF+Arial-BoldMT", "Arial"),
        ("Arial,Bold", "Arial"),
        ("ArialMT", "Arial"),
        ("Helvetica", "Helvetica"),
        ("TimesNewRomanPSMT", "TimesNewRoman"),
        ("", ""),
    ],
)
def test_normalizar_familia(crudo: str, esperado: str) -> None:
    assert normalizar_familia(crudo) == esperado
```

- [ ] **Step 3: Escribir los tests de medición**

Añadir a `tests/extraccion/test_tipografia.py`:

```python
def test_familia_y_cuerpo_dominantes(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.familia_dominante == "Helvetica"
    assert medidas.cuerpo_dominante == 11.0


def test_el_titular_no_desplaza_al_cuerpo_dominante(pdf_cuerpo_mezclado: Path) -> None:
    """Domina lo que ocupa más caracteres, no lo que aparece primero."""
    with abrir(pdf_cuerpo_mezclado) as documento:
        medidas = medir_texto(documento)

    assert medidas.cuerpo_dominante == 11.0
    assert medidas.proporcion_cuerpo_dominante > 0.9


def test_ratio_de_interlineado(pdf_simple: Path) -> None:
    """El fixture separa las líneas base 19 pt con cuerpo 11: 19/11."""
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.ratio_interlineado == pytest.approx(19 / 11, abs=0.02)


def test_sin_dos_lineas_no_hay_interlineado(tmp_path: Path) -> None:
    """Una sola línea no define ningún salto. No se inventa uno."""
    import pymupdf

    documento = pymupdf.open()
    documento.new_page().insert_text((72.0, 100.0), "Sola.", fontname="helv", fontsize=11.0)
    ruta = tmp_path / "una-linea.pdf"
    documento.save(ruta)
    documento.close()

    with abrir(ruta) as abierto:
        medidas = medir_texto(abierto)

    assert medidas.ratio_interlineado is None


def test_margen_izquierdo_en_centimetros(pdf_simple: Path) -> None:
    """72 pt es exactamente una pulgada: 2,54 cm."""
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.margen_izquierdo_cm == pytest.approx(2.54, abs=0.05)


def test_los_cuatro_margenes_se_miden(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.margen_derecho_cm is not None
    assert medidas.margen_superior_cm is not None
    assert medidas.margen_inferior_cm is not None
    assert medidas.margen_superior_cm > 0


def test_texto_justificado_da_proporcion_alta(pdf_justificado: Path) -> None:
    with abrir(pdf_justificado) as documento:
        medidas = medir_texto(documento)

    assert medidas.proporcion_lineas_al_margen_derecho == pytest.approx(0.8, abs=0.01)


def test_texto_de_lineas_desiguales_da_proporcion_baja(pdf_simple: Path) -> None:
    """Tres líneas de longitudes distintas: solo una llega al borde."""
    with abrir(pdf_simple) as documento:
        medidas = medir_texto(documento)

    assert medidas.proporcion_lineas_al_margen_derecho is not None
    assert medidas.proporcion_lineas_al_margen_derecho < 0.6


def test_un_pdf_sin_texto_no_inventa_medidas(pdf_escaneado: Path) -> None:
    """Un escaneado no tiene tipografía. Todo queda a None o vacío."""
    with abrir(pdf_escaneado) as documento:
        medidas = medir_texto(documento)

    assert medidas.familia_dominante == ""
    assert medidas.cuerpo_dominante == 0.0
    assert medidas.ratio_interlineado is None
    assert medidas.margen_izquierdo_cm is None
    assert medidas.proporcion_lineas_al_margen_derecho is None
```

- [ ] **Step 4: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/extraccion/test_tipografia.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.extraccion.tipografia'`

- [ ] **Step 5: Añadir `MedidasDeTexto` a `backend/extraccion/medidas.py`**

Añadir al final del fichero:

```python
class MedidasDeTexto(BaseModel):
    """Tipografía, interlineado, márgenes y alineación, tal como se miden.

    Los campos opcionales son `None` cuando el documento no da material para
    medirlos —un escaneado no tiene tipografía, una sola línea no define un
    interlineado—. Nunca llevan un valor supuesto: un dato ausente que
    parece presente es peor que un hueco declarado.
    """

    familia_dominante: str
    cuerpo_dominante: float
    proporcion_cuerpo_dominante: float
    ratio_interlineado: float | None = None
    margen_izquierdo_cm: float | None = None
    margen_derecho_cm: float | None = None
    margen_superior_cm: float | None = None
    margen_inferior_cm: float | None = None
    proporcion_lineas_al_margen_derecho: float | None = None
```

- [ ] **Step 6: Escribir `backend/extraccion/tipografia.py`**

```python
"""Tipografía, interlineado, márgenes y alineación.

Sobre el interlineado, que es el punto delicado: un PDF no guarda «1,5
líneas». Guarda dónde cae la línea base de cada línea, y de ahí sale la
distancia real en puntos. Convertir esa distancia en el valor que el alumno
eligió en su procesador de textos depende de la fuente y de la versión del
programa —para Arial 11 a 1,5 líneas sale un ratio cercano a 1,73, no a
1,5—. Aquí se mide el ratio y se deja a la vista. Qué ratio corresponde a
1,5 lo dirá la calibración del §20, no este módulo.

Limitación conocida de los márgenes: se miden sobre todo el texto de la
página, así que un encabezado o un pie reducen el margen superior o el
inferior medidos. El izquierdo y el derecho no se ven afectados.
"""

import re
import statistics
from collections import Counter

import pymupdf

from backend.extraccion.medidas import MedidasDeTexto

PUNTOS_POR_CM = 72 / 2.54

# Las fuentes incrustadas llegan como «ABCDEF+Arial-BoldMT»: seis letras
# mayúsculas y un «+» delante, y el estilo pegado detrás.
PREFIJO_SUBCONJUNTO = re.compile(r"^[A-Z]{6}\+")
SUFIJO_ESTILO = re.compile(
    r"(MT|PS|PSMT)?[-,](Bold|Italic|Oblique|Regular|Light|Medium|BoldItalic|BoldMT|ItalicMT)"
    r"(MT|PS)?$",
    re.I,
)
SUFIJO_SUELTO = re.compile(r"(PSMT|MT|PS)$")

# Un salto mayor que esto no es interlineado: es el hueco entre párrafos o
# entre secciones, y contarlo desplazaría la mediana.
SALTO_MAXIMO_EN_CUERPOS = 3.0

# Dos líneas terminan «en el mismo sitio» si su borde derecho no se separa
# más que esto. Un punto es la anchura de un pelo de letra.
TOLERANCIA_BORDE_PT = 1.0


def normalizar_familia(nombre: str) -> str:
    """«ABCDEF+Arial-BoldMT» → «Arial». La familia, sin estilo ni subconjunto."""
    limpio = PREFIJO_SUBCONJUNTO.sub("", nombre)
    limpio = SUFIJO_ESTILO.sub("", limpio)
    return SUFIJO_SUELTO.sub("", limpio)


def _lineas_de(pagina: pymupdf.Page) -> list[dict]:
    """Las líneas de texto de una página, con sus spans."""
    lineas = []
    for bloque in pagina.get_text("dict")["blocks"]:
        if bloque["type"] != 0:  # 0 es texto; 1 es imagen
            continue
        lineas.extend(bloque["lines"])
    return lineas


def _ratio_de_pagina(lineas: list[dict], cuerpo: float) -> list[float]:
    """Saltos entre líneas base consecutivas, en múltiplos del cuerpo."""
    bases = sorted(
        linea["spans"][0]["origin"][1] for linea in lineas if linea["spans"]
    )
    saltos = []
    for anterior, siguiente in zip(bases, bases[1:]):
        salto = siguiente - anterior
        if 0 < salto <= cuerpo * SALTO_MAXIMO_EN_CUERPOS:
            saltos.append(salto / cuerpo)
    return saltos


def medir_texto(documento: pymupdf.Document) -> MedidasDeTexto:
    """Mide el texto del documento entero.

    Lo dominante se decide por número de caracteres, no por número de
    fragmentos: un titular corto no puede desplazar al cuerpo del trabajo.
    """
    por_estilo: Counter[tuple[str, float]] = Counter()
    ratios: list[float] = []
    margenes: list[tuple[float, float, float, float]] = []
    lineas_totales = 0
    lineas_al_borde = 0

    for pagina in documento:
        lineas = _lineas_de(pagina)
        if not lineas:
            continue

        for linea in lineas:
            for span in linea["spans"]:
                estilo = (normalizar_familia(span["font"]), round(span["size"] * 2) / 2)
                por_estilo[estilo] += len(span["text"])

        izquierdas = [linea["bbox"][0] for linea in lineas]
        derechas = [linea["bbox"][2] for linea in lineas]
        superiores = [linea["bbox"][1] for linea in lineas]
        inferiores = [linea["bbox"][3] for linea in lineas]
        margenes.append((
            min(izquierdas) / PUNTOS_POR_CM,
            (pagina.rect.width - max(derechas)) / PUNTOS_POR_CM,
            min(superiores) / PUNTOS_POR_CM,
            (pagina.rect.height - max(inferiores)) / PUNTOS_POR_CM,
        ))

        borde = max(derechas)
        lineas_totales += len(lineas)
        lineas_al_borde += sum(
            1 for derecha in derechas if borde - derecha <= TOLERANCIA_BORDE_PT
        )

    if not por_estilo:
        return MedidasDeTexto(
            familia_dominante="",
            cuerpo_dominante=0.0,
            proporcion_cuerpo_dominante=0.0,
        )

    (familia, cuerpo), caracteres = por_estilo.most_common(1)[0]
    total = sum(por_estilo.values())

    # El interlineado se calcula con el cuerpo dominante ya conocido: los
    # saltos de un titular no dicen nada del cuerpo del trabajo.
    if cuerpo > 0:
        for pagina in documento:
            ratios.extend(_ratio_de_pagina(_lineas_de(pagina), cuerpo))

    return MedidasDeTexto(
        familia_dominante=familia,
        cuerpo_dominante=cuerpo,
        proporcion_cuerpo_dominante=caracteres / total,
        ratio_interlineado=statistics.median(ratios) if ratios else None,
        margen_izquierdo_cm=statistics.median(m[0] for m in margenes) if margenes else None,
        margen_derecho_cm=statistics.median(m[1] for m in margenes) if margenes else None,
        margen_superior_cm=statistics.median(m[2] for m in margenes) if margenes else None,
        margen_inferior_cm=statistics.median(m[3] for m in margenes) if margenes else None,
        proporcion_lineas_al_margen_derecho=(
            lineas_al_borde / lineas_totales if lineas_totales else None
        ),
    )
```

- [ ] **Step 7: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/extraccion/test_tipografia.py -v`
Expected: PASS, 17 tests (8 de `normalizar_familia` más 9 de medición).

- [ ] **Step 8: Commit**

```bash
git add backend/extraccion tests/extraccion
git commit -m "feat: tipografia, interlineado, margenes y alineacion

El interlineado se mide como ratio entre el salto de linea base y el
cuerpo, y no se traduce. Un PDF no guarda \"1,5 lineas\": guarda donde cae
cada linea base, y la equivalencia depende de la fuente. Para Arial 11 a
1,5 sale un ratio cercano a 1,73. Traducirlo aqui seria inventar la tabla
de conversion; se deja el ratio a la vista y lo decidira la calibracion.

Lo dominante se decide por caracteres y no por fragmentos, para que un
titular corto no desplace al cuerpo del trabajo."
```

---

### Task 4: Extracción — índice, páginas de contenido y anexos

El §6.2 pide un mínimo de páginas «excluidas portada, índice y anexos», así que hay que saber dónde empieza y acaba el contenido. Se localiza por lo que el documento dice de sí mismo: el encabezado del índice y el de los anexos. Si no aparecen, no se deduce nada — la cuenta se declara no verificable y el docente la fija.

**Files:**
- Modify: `backend/extraccion/medidas.py` (añadir `EntradaDeIndice` y `MedidasDeEstructura`)
- Create: `backend/extraccion/estructura.py`
- Create: `tests/extraccion/test_estructura.py`
- Modify: `tests/conftest.py` (añadir un fixture)

**Interfaces:**
- Consumes: `abrir` de `backend.extraccion.lectura`.
- Produces:
  - `EntradaDeIndice(BaseModel)` con `titulo: str`, `pagina_declarada: int`, `pagina_encontrada: int | None`.
  - `MedidasDeEstructura(BaseModel)` con `pagina_del_indice: int | None`, `primera_pagina_de_contenido: int | None`, `primera_pagina_de_anexos: int | None`, `paginas_de_contenido: int | None`, `entradas_de_indice: list[EntradaDeIndice]`, `titulos_no_encontrados: list[str]`, `paginas_declaradas_incorrectas: list[str]`.
  - `medir_estructura(documento: pymupdf.Document) -> MedidasDeEstructura`

- [ ] **Step 1: Añadir el fixture del documento con índice**

Añadir al final de `tests/conftest.py`:

```python
@pytest.fixture
def pdf_con_indice(tmp_path: Path) -> Path:
    """Portada, índice, tres apartados y un anexo.

    Las páginas declaradas en el índice son correctas salvo la del tercer
    apartado, que dice 5 estando en la 6. Es el fallo más común: se añade
    contenido y no se actualiza el índice.
    """
    return escribir_pdf(
        tmp_path / "con-indice.pdf",
        [
            ["PROYECTO INTERMODULAR", "Ciclo DAM", "Curso 2026-2027"],
            ["INDICE", "1. Introduccion .... 3", "2. Objetivos .... 4",
             "3. Desarrollo .... 5", "ANEXOS .... 7"],
            ["1. Introduccion", "Texto de la introduccion del trabajo."],
            ["2. Objetivos", "Texto de los objetivos del trabajo."],
            ["Continuacion de los objetivos, que ocupan dos paginas."],
            ["3. Desarrollo", "Texto del desarrollo del trabajo."],
            ["ANEXOS", "Anexo I. Codigo fuente."],
        ],
    )
```

- [ ] **Step 2: Escribir los tests de estructura**

Crear `tests/extraccion/test_estructura.py`:

```python
"""Índice, contenido y anexos: dónde empieza y acaba lo que se cuenta."""

from pathlib import Path

from backend.extraccion.estructura import medir_estructura
from backend.extraccion.lectura import abrir


def test_localiza_la_pagina_del_indice(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.pagina_del_indice == 2


def test_el_contenido_empieza_tras_el_indice(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_contenido == 3


def test_localiza_el_comienzo_de_los_anexos(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_anexos == 7


def test_cuenta_las_paginas_de_contenido(pdf_con_indice: Path) -> None:
    """De la 3 a la 6: cuatro páginas. Portada, índice y anexo fuera."""
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert estructura.paginas_de_contenido == 4


def test_lee_las_entradas_del_indice(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    titulos = [entrada.titulo for entrada in estructura.entradas_de_indice]
    assert "1. Introduccion" in titulos
    assert "2. Objetivos" in titulos
    assert len(estructura.entradas_de_indice) == 4


def test_detecta_la_pagina_declarada_que_no_cuadra(pdf_con_indice: Path) -> None:
    """El índice dice que «3. Desarrollo» está en la 5, y está en la 6."""
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert any("Desarrollo" in aviso for aviso in estructura.paginas_declaradas_incorrectas)


def test_las_paginas_correctas_no_se_avisan(pdf_con_indice: Path) -> None:
    with abrir(pdf_con_indice) as documento:
        estructura = medir_estructura(documento)

    assert not any(
        "Introduccion" in aviso for aviso in estructura.paginas_declaradas_incorrectas
    )


def test_titulo_del_indice_que_no_aparece_en_el_documento(escribir_pdf, tmp_path: Path) -> None:
    ruta = escribir_pdf(
        tmp_path / "descuadrado.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3", "9. Conclusiones fantasma .... 4"],
            ["1. Introduccion", "Texto."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert any("fantasma" in titulo for titulo in estructura.titulos_no_encontrados)


def test_sin_indice_no_se_deduce_nada(pdf_simple: Path) -> None:
    """No hay índice: no se adivina dónde empieza el contenido."""
    with abrir(pdf_simple) as documento:
        estructura = medir_estructura(documento)

    assert estructura.pagina_del_indice is None
    assert estructura.primera_pagina_de_contenido is None
    assert estructura.paginas_de_contenido is None
    assert estructura.entradas_de_indice == []


def test_sin_anexos_el_contenido_llega_al_final(escribir_pdf, tmp_path: Path) -> None:
    ruta = escribir_pdf(
        tmp_path / "sin-anexos.pdf",
        [
            ["PORTADA"],
            ["INDICE", "1. Introduccion .... 3"],
            ["1. Introduccion", "Texto."],
            ["Mas texto del trabajo."],
        ],
    )

    with abrir(ruta) as documento:
        estructura = medir_estructura(documento)

    assert estructura.primera_pagina_de_anexos is None
    assert estructura.paginas_de_contenido == 2
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/extraccion/test_estructura.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.extraccion.estructura'`

- [ ] **Step 4: Añadir los modelos a `backend/extraccion/medidas.py`**

Añadir al final del fichero:

```python
class EntradaDeIndice(BaseModel):
    """Una línea del índice y dónde está de verdad ese apartado."""

    titulo: str
    pagina_declarada: int
    pagina_encontrada: int | None = None


class MedidasDeEstructura(BaseModel):
    """Dónde empieza y acaba lo que cuenta como contenido.

    Todo opcional por el mismo motivo de siempre: sin índice localizable no
    se sabe dónde empieza el contenido, y esa cuenta se declara ausente en
    lugar de estimarse.
    """

    pagina_del_indice: int | None = None
    primera_pagina_de_contenido: int | None = None
    primera_pagina_de_anexos: int | None = None
    paginas_de_contenido: int | None = None
    entradas_de_indice: list[EntradaDeIndice] = []
    titulos_no_encontrados: list[str] = []
    paginas_declaradas_incorrectas: list[str] = []
```

- [ ] **Step 5: Escribir `backend/extraccion/estructura.py`**

```python
"""Índice, contenido y anexos.

El §6.2 del Maestro cuenta las páginas «excluidas portada, índice y
anexos», así que hay que saber dónde empieza y acaba el contenido. Se
localiza por lo que el propio documento declara: el encabezado del índice y
el de los anexos.

Si el índice no aparece, no se deduce nada. Se podría suponer que la
portada es la primera página y que el contenido empieza en la segunda, y
acertaría muchas veces; pero cuando fallara produciría una cuenta de
páginas equivocada con aspecto de dato medido, y sobre esa cuenta se decide
si un trabajo cumple la extensión mínima. Un hueco declarado es
recuperable; un número inventado, no.
"""

import re
import unicodedata

import pymupdf

from backend.extraccion.medidas import EntradaDeIndice, MedidasDeEstructura

# Una línea de índice: título, relleno de puntos o espacios, y la página.
# El relleno es opcional porque no todos los procesadores lo ponen.
LINEA_DE_INDICE = re.compile(r"^(.{3,120}?)[\s.·_]{2,}(\d{1,3})\s*$")

ENCABEZADOS_DE_INDICE = ("indice", "indice de contenidos", "tabla de contenidos",
                         "contenido", "contenidos", "sumario")
ENCABEZADOS_DE_ANEXOS = ("anexo", "anexos", "apendice", "apendices")

# El índice está al principio: buscarlo más allá de aquí solo produce
# falsos positivos con menciones dentro del texto.
PAGINAS_EN_QUE_BUSCAR_EL_INDICE = 6


def _plano(texto: str) -> str:
    """Sin tildes, sin mayúsculas y sin espacios de sobra, para comparar."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def _lineas_por_pagina(documento: pymupdf.Document) -> list[list[str]]:
    """Las líneas de texto de cada página, en orden."""
    return [
        [linea.strip() for linea in pagina.get_text().splitlines() if linea.strip()]
        for pagina in documento
    ]


def _buscar_indice(paginas: list[list[str]]) -> int | None:
    """Número de la página cuyo encabezado es el del índice, o None."""
    for numero, lineas in enumerate(paginas[:PAGINAS_EN_QUE_BUSCAR_EL_INDICE], start=1):
        for linea in lineas[:5]:
            if _plano(linea) in ENCABEZADOS_DE_INDICE:
                return numero
    return None


def _buscar_anexos(paginas: list[list[str]], desde: int) -> int | None:
    """Primera página cuyo encabezado anuncia los anexos, o None."""
    for numero, lineas in enumerate(paginas, start=1):
        if numero <= desde:
            continue
        for linea in lineas[:2]:
            plano = _plano(linea)
            if plano in ENCABEZADOS_DE_ANEXOS or plano.startswith("anexos "):
                return numero
    return None


def _leer_entradas(lineas: list[str]) -> list[EntradaDeIndice]:
    """Las entradas de la página del índice, sin su propio encabezado."""
    entradas = []
    for linea in lineas:
        if _plano(linea) in ENCABEZADOS_DE_INDICE:
            continue
        coincidencia = LINEA_DE_INDICE.match(linea)
        if coincidencia:
            entradas.append(EntradaDeIndice(
                titulo=coincidencia.group(1).strip(" .·_"),
                pagina_declarada=int(coincidencia.group(2)),
            ))
    return entradas


def _localizar(titulo: str, paginas: list[list[str]], desde: int) -> int | None:
    """Página donde ese título aparece como encabezado, o None.

    Se busca solo en las primeras líneas de cada página y solo desde donde
    acaba el índice: una mención del título dentro de un párrafo no es el
    apartado.
    """
    buscado = _plano(titulo)
    if not buscado:
        return None
    for numero, lineas in enumerate(paginas, start=1):
        if numero <= desde:
            continue
        for linea in lineas[:3]:
            if _plano(linea) == buscado:
                return numero
    return None


def medir_estructura(documento: pymupdf.Document) -> MedidasDeEstructura:
    """Localiza índice, contenido y anexos, y contrasta el índice declarado."""
    paginas = _lineas_por_pagina(documento)
    indice = _buscar_indice(paginas)
    if indice is None:
        return MedidasDeEstructura()

    entradas = _leer_entradas(paginas[indice - 1])
    anexos = _buscar_anexos(paginas, indice)
    contenido = indice + 1 if indice < len(paginas) else None

    no_encontrados: list[str] = []
    descuadrados: list[str] = []
    for entrada in entradas:
        if _plano(entrada.titulo) in ENCABEZADOS_DE_ANEXOS:
            continue
        entrada.pagina_encontrada = _localizar(entrada.titulo, paginas, indice)
        if entrada.pagina_encontrada is None:
            no_encontrados.append(entrada.titulo)
        elif entrada.pagina_encontrada != entrada.pagina_declarada:
            descuadrados.append(
                f"«{entrada.titulo}»: el índice dice página "
                f"{entrada.pagina_declarada} y está en la "
                f"{entrada.pagina_encontrada}."
            )

    ultima = (anexos - 1) if anexos else len(paginas)
    cuenta = max(0, ultima - contenido + 1) if contenido else None

    return MedidasDeEstructura(
        pagina_del_indice=indice,
        primera_pagina_de_contenido=contenido,
        primera_pagina_de_anexos=anexos,
        paginas_de_contenido=cuenta,
        entradas_de_indice=entradas,
        titulos_no_encontrados=no_encontrados,
        paginas_declaradas_incorrectas=descuadrados,
    )
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/extraccion/test_estructura.py -v`
Expected: PASS, 10 tests.

- [ ] **Step 7: Commit**

```bash
git add backend/extraccion tests/extraccion
git commit -m "feat: indice, paginas de contenido y anexos

El 6.2 cuenta las paginas excluidas portada, indice y anexos, asi que hay
que saber donde empieza y acaba el contenido. Se localiza por lo que el
documento declara de si mismo.

Sin indice localizable no se deduce nada. Suponer que la portada es la
primera pagina acertaria casi siempre, pero cuando fallara daria una
cuenta equivocada con aspecto de dato medido, y sobre esa cuenta se decide
si el trabajo cumple la extension minima."
```

---

### Task 5: Extracción — imágenes

Lo que se puede medir de una imagen sin mirarla: cuántas hay, en qué página, qué resolución efectiva tiene al tamaño en que se imprime y cuánta página ocupa. Una captura de pantalla estirada al doble se detecta aquí.

**Files:**
- Modify: `backend/extraccion/medidas.py` (añadir `Imagen`)
- Create: `backend/extraccion/imagenes.py`
- Create: `tests/extraccion/test_imagenes.py`
- Modify: `tests/conftest.py` (añadir un fixture)

**Interfaces:**
- Consumes: `abrir` de `backend.extraccion.lectura`.
- Produces:
  - `Imagen(BaseModel)` con `pagina: int`, `ancho_px: int`, `alto_px: int`, `dpi_efectivo: float`, `proporcion_de_pagina: float`.
  - `leer_imagenes(documento: pymupdf.Document) -> list[Imagen]`

- [ ] **Step 1: Añadir el fixture de imágenes**

Añadir al final de `tests/conftest.py`:

```python
@pytest.fixture
def pdf_con_imagenes(tmp_path: Path) -> Path:
    """Dos imágenes: una nítida y otra de 40x30 px estirada a 200x150 pt.

    La segunda queda a 14,4 ppp efectivos: es la captura de pantalla
    ampliada que se ve borrosa impresa.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()

    nitida = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 450), False)
    nitida.set_rect(nitida.irect, (30, 60, 120))
    pagina.insert_image(pymupdf.Rect(72, 72, 272, 222), pixmap=nitida)

    borrosa = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), False)
    borrosa.set_rect(borrosa.irect, (200, 120, 60))
    pagina.insert_image(pymupdf.Rect(72, 300, 272, 450), pixmap=borrosa)

    ruta = tmp_path / "con-imagenes.pdf"
    documento.save(ruta)
    documento.close()
    return ruta
```

- [ ] **Step 2: Escribir los tests**

Crear `tests/extraccion/test_imagenes.py`:

```python
"""Las imágenes: cuántas, dónde, a qué resolución y cuánto ocupan."""

from pathlib import Path

import pytest

from backend.extraccion.imagenes import leer_imagenes
from backend.extraccion.lectura import abrir


def test_cuenta_las_imagenes(pdf_con_imagenes: Path) -> None:
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    assert len(imagenes) == 2


def test_dice_en_que_pagina_esta_cada_una(pdf_con_imagenes: Path) -> None:
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    assert all(imagen.pagina == 1 for imagen in imagenes)


def test_calcula_la_resolucion_efectiva(pdf_con_imagenes: Path) -> None:
    """40 px repartidos en 200 pt son 14,4 ppp: 40 / (200/72)."""
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    borrosa = min(imagenes, key=lambda imagen: imagen.dpi_efectivo)
    assert borrosa.dpi_efectivo == pytest.approx(14.4, abs=0.1)
    assert borrosa.ancho_px == 40


def test_la_imagen_nitida_tiene_mas_resolucion(pdf_con_imagenes: Path) -> None:
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    nitida = max(imagenes, key=lambda imagen: imagen.dpi_efectivo)
    assert nitida.dpi_efectivo > 200


def test_calcula_la_proporcion_de_pagina(pdf_con_imagenes: Path) -> None:
    """200 x 150 pt sobre una A4 de 595 x 842: en torno al 6 %."""
    with abrir(pdf_con_imagenes) as documento:
        imagenes = leer_imagenes(documento)

    assert all(
        imagen.proporcion_de_pagina == pytest.approx(0.06, abs=0.01)
        for imagen in imagenes
    )


def test_un_documento_sin_imagenes_da_lista_vacia(pdf_simple: Path) -> None:
    with abrir(pdf_simple) as documento:
        assert leer_imagenes(documento) == []
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/extraccion/test_imagenes.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.extraccion.imagenes'`

- [ ] **Step 4: Añadir `Imagen` a `backend/extraccion/medidas.py`**

Añadir al final del fichero:

```python
class Imagen(BaseModel):
    """Una imagen colocada en una página.

    `dpi_efectivo` es la resolución a la que se imprime de verdad: los
    píxeles que tiene repartidos entre el tamaño que ocupa. Es lo que
    delata una captura de pantalla estirada, que en el archivo parece
    correcta y en el papel se ve borrosa.
    """

    pagina: int
    ancho_px: int
    alto_px: int
    dpi_efectivo: float
    proporcion_de_pagina: float
```

- [ ] **Step 5: Escribir `backend/extraccion/imagenes.py`**

```python
"""Las imágenes del documento, medidas sin mirar su contenido.

Aquí no se juzga si una imagen está numerada, titulada o citada en el
texto: eso exige leer y relacionar, y es trabajo de la segunda parte. Aquí
solo hay geometría y píxeles.
"""

import pymupdf

from backend.extraccion.medidas import Imagen

PUNTOS_POR_PULGADA = 72.0


def leer_imagenes(documento: pymupdf.Document) -> list[Imagen]:
    """Una entrada por cada colocación de imagen, en orden de página.

    Una misma imagen repetida en varias páginas produce una entrada por
    página: lo que importa es cómo se ve en cada sitio donde aparece, y el
    mismo archivo puede estar bien dimensionado en una página y estirado en
    otra.
    """
    imagenes = []
    for numero, pagina in enumerate(documento, start=1):
        area_pagina = pagina.rect.get_area()
        for referencia in pagina.get_images(full=True):
            xref, _, ancho_px, alto_px = referencia[0], referencia[1], referencia[2], referencia[3]
            for rectangulo in pagina.get_image_rects(xref):
                if rectangulo.width <= 0 or rectangulo.height <= 0:
                    continue
                dpi_horizontal = ancho_px / (rectangulo.width / PUNTOS_POR_PULGADA)
                dpi_vertical = alto_px / (rectangulo.height / PUNTOS_POR_PULGADA)
                imagenes.append(Imagen(
                    pagina=numero,
                    ancho_px=ancho_px,
                    alto_px=alto_px,
                    # El lado peor mandado es el que se ve borroso.
                    dpi_efectivo=min(dpi_horizontal, dpi_vertical),
                    proporcion_de_pagina=(
                        rectangulo.get_area() / area_pagina if area_pagina else 0.0
                    ),
                ))
    return imagenes
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/extraccion/test_imagenes.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 7: Ejecutar la batería completa**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`
Expected: todo en verde.

- [ ] **Step 8: Commit**

```bash
git add backend/extraccion tests/extraccion
git commit -m "feat: imagenes con resolucion efectiva y superficie

El dpi efectivo es lo que delata una captura de pantalla estirada: en el
archivo parece correcta y en el papel se ve borrosa. Se toma el lado peor
mandado, que es el que se nota.

Una imagen repetida en varias paginas da una entrada por pagina: el mismo
archivo puede estar bien dimensionado en una y estirado en otra."
```
---

### Task 6: La medición completa

Las cuatro mediciones anteriores en una sola llamada y un solo modelo. Es lo que consumen la comprobación de formato, la ficha y el frontend, y lo único que necesitan saber de `extraccion/`.

**Files:**
- Modify: `backend/extraccion/medidas.py` (añadir `Medidas`)
- Modify: `backend/extraccion/__init__.py` (añadir `medir`)
- Create: `tests/extraccion/test_medir.py`

**Interfaces:**
- Consumes: `abrir`, `leer_paginas`, `procede_de_escaner` (Task 2); `medir_texto` (Task 3); `medir_estructura` (Task 4); `leer_imagenes` (Task 5).
- Produces:
  - `Medidas(BaseModel)` con `nombre_archivo: str`, `huella: str`, `paginas: list[Pagina]`, `total_paginas: int`, `paginas_en_blanco: list[int]`, `escaneado: bool`, `texto: MedidasDeTexto`, `estructura: MedidasDeEstructura`, `imagenes: list[Imagen]`, `texto_plano: str`.
  - `medir(ruta: Path) -> Medidas` en `backend.extraccion`.

- [ ] **Step 1: Escribir los tests**

Crear `tests/extraccion/test_medir.py`:

```python
"""La medición completa de un archivo."""

from pathlib import Path

from backend.extraccion import medir


def test_recoge_el_nombre_del_archivo(pdf_con_indice: Path) -> None:
    medidas = medir(pdf_con_indice)

    assert medidas.nombre_archivo == "con-indice.pdf"


def test_la_huella_es_estable(pdf_con_indice: Path) -> None:
    """Dos lecturas del mismo archivo dan la misma huella."""
    assert medir(pdf_con_indice).huella == medir(pdf_con_indice).huella


def test_la_huella_distingue_dos_archivos(pdf_con_indice: Path, pdf_simple: Path) -> None:
    assert medir(pdf_con_indice).huella != medir(pdf_simple).huella


def test_junta_las_cuatro_mediciones(pdf_con_indice: Path) -> None:
    medidas = medir(pdf_con_indice)

    assert medidas.total_paginas == 7
    assert medidas.texto.cuerpo_dominante == 11.0
    assert medidas.estructura.paginas_de_contenido == 4
    assert medidas.imagenes == []


def test_lista_las_paginas_en_blanco(pdf_con_pagina_en_blanco: Path) -> None:
    medidas = medir(pdf_con_pagina_en_blanco)

    assert medidas.paginas_en_blanco == [2]


def test_marca_el_escaneado(pdf_escaneado: Path) -> None:
    medidas = medir(pdf_escaneado)

    assert medidas.escaneado is True
    assert medir(pdf_escaneado).texto.familia_dominante == ""


def test_conserva_el_texto_plano(pdf_con_indice: Path) -> None:
    """Lo necesita la comparación evolutiva. No se guarda en Supabase."""
    medidas = medir(pdf_con_indice)

    assert "Introduccion" in medidas.texto_plano


def test_no_toca_el_archivo(pdf_con_indice: Path) -> None:
    """El §18.1 lo exige: se lee y nada más."""
    antes = pdf_con_indice.read_bytes()
    momento = pdf_con_indice.stat().st_mtime

    medir(pdf_con_indice)

    assert pdf_con_indice.read_bytes() == antes
    assert pdf_con_indice.stat().st_mtime == momento
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/extraccion/test_medir.py -v`
Expected: FAIL con `ImportError: cannot import name 'medir'`

- [ ] **Step 3: Añadir `Medidas` a `backend/extraccion/medidas.py`**

Añadir al final del fichero:

```python
class Medidas(BaseModel):
    """Todo lo medido sobre un archivo, sin valorar nada.

    `texto_plano` vive aquí porque lo necesita la comparación evolutiva,
    pero NO se guarda en Supabase: la decisión D-001 excluye el texto del
    trabajo de la base de datos. Se usa y se descarta.
    """

    nombre_archivo: str
    huella: str
    paginas: list[Pagina]
    total_paginas: int
    paginas_en_blanco: list[int]
    escaneado: bool
    texto: MedidasDeTexto
    estructura: MedidasDeEstructura
    imagenes: list[Imagen]
    texto_plano: str
```

- [ ] **Step 4: Escribir `medir` en `backend/extraccion/__init__.py`**

Reemplazar el contenido del fichero:

```python
"""Medición objetiva de un PDF. No llama a ningún modelo de lenguaje."""

import hashlib
from pathlib import Path

from backend.extraccion.medidas import Medidas

# Leer un PDF de golpe para calcular su huella cargaría en memoria un
# archivo que puede pesar decenas de megas.
TROZO = 1024 * 1024


def _huella(ruta: Path) -> str:
    """SHA-256 del archivo, para identificarlo sin conservarlo (§19.1)."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        while trozo := archivo.read(TROZO):
            resumen.update(trozo)
    return resumen.hexdigest()


def medir(ruta: Path) -> Medidas:
    """Todo lo que se puede saber del archivo sin criterio humano."""
    from backend.extraccion.estructura import medir_estructura
    from backend.extraccion.imagenes import leer_imagenes
    from backend.extraccion.lectura import abrir, leer_paginas, procede_de_escaner
    from backend.extraccion.tipografia import medir_texto

    with abrir(ruta) as documento:
        paginas = leer_paginas(documento)
        return Medidas(
            nombre_archivo=ruta.name,
            huella=_huella(ruta),
            paginas=paginas,
            total_paginas=len(paginas),
            paginas_en_blanco=[p.numero for p in paginas if p.en_blanco],
            escaneado=procede_de_escaner(documento),
            texto=medir_texto(documento),
            estructura=medir_estructura(documento),
            imagenes=leer_imagenes(documento),
            texto_plano="\n".join(pagina.get_text() for pagina in documento),
        )
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/extraccion/test_medir.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/extraccion tests/extraccion
git commit -m "feat: medicion completa de un archivo en una llamada

La huella se calcula por trozos: un PDF puede pesar decenas de megas y no
hay razon para cargarlo entero en memoria.

texto_plano viaja en el modelo porque lo necesita la comparacion
evolutiva, pero no se guarda en Supabase: D-001 excluye el texto del
trabajo de la base de datos."
```

---

### Task 7: Comprobación contra los criterios de formato

Aquí se compara lo medido con lo que exige `criteria/v2026-2027/formato.yaml`. Este módulo **no sabe abrir un PDF** y el de extracción **no sabe qué exige el Maestro**: esa separación es lo que permite cambiar un criterio sin tocar la medición.

Dos criterios salen a propósito como `NO_VERIFICABLE`, y es el punto importante de la tarea:

- **El interlineado.** El criterio dice `1.5`; lo medido es un ratio de salto sobre cuerpo, que para Arial 11 a 1,5 líneas ronda 1,73. La equivalencia no está establecida en ninguna fuente oficial, así que no se decide aquí: se enseña el ratio y se dice por qué no se juzga.
- **Las imágenes.** Numeración, título, fuente y mención en el texto exigen leer y relacionar. Es trabajo de la segunda parte.

**Files:**
- Create: `backend/formato/__init__.py`
- Create: `backend/formato/comprobacion.py`
- Create: `tests/formato/test_comprobacion.py`
- Modify: `docs/PENDIENTE_OFICIAL.md` (añadir la equivalencia del interlineado)

**Interfaces:**
- Consumes: `Medidas` de `backend.extraccion.medidas`.
- Produces:
  - `CUMPLE`, `NO_CUMPLE`, `NO_VERIFICABLE` (constantes `str`).
  - `Comprobacion(BaseModel)` con `criterio: str`, `veredicto: str`, `esperado: str`, `medido: str`, `fuente: str`, `nota: str = ""`.
  - `comprobar(raiz: Path, version: str, medidas: Medidas) -> list[Comprobacion]`

- [ ] **Step 1: Escribir los tests**

Crear `tests/formato/test_comprobacion.py`:

```python
"""Lo medido contra lo exigido."""

from pathlib import Path

import pytest

from backend.extraccion import medir
from backend.formato.comprobacion import (
    CUMPLE,
    NO_CUMPLE,
    NO_VERIFICABLE,
    comprobar,
)

# Los criterios y los PDF vienen de tests/conftest.py: `criterios_de_formato`
# es una raíz con criteria/v2026-2027/formato.yaml dentro.


def _de(comprobaciones: list, criterio: str):
    return next(c for c in comprobaciones if c.criterio == criterio)



def test_extension_suficiente_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """Cuatro páginas de contenido contra un mínimo de cuatro."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "extension").veredicto == CUMPLE


def test_extension_insuficiente_no_cumple(criterios_alterados, pdf_con_indice: Path) -> None:
    raiz = criterios_alterados(
        "minimo_paginas_contenido: 4", "minimo_paginas_contenido: 30"
    )

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "extension")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "30" in comprobacion.esperado
    assert "4" in comprobacion.medido


def test_sin_indice_la_extension_no_es_verificable(criterios_de_formato: Path, pdf_simple: Path) -> None:
    """Sin saber dónde empieza el contenido no se cuenta. No se estima."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_simple))

    comprobacion = _de(resultado, "extension")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "índice" in comprobacion.nota


def test_tipografia_correcta_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "tipografia").veredicto == CUMPLE


def test_familia_distinta_no_cumple(criterios_alterados, pdf_con_indice: Path) -> None:
    raiz = criterios_alterados("familia: Helvetica", "familia: Arial")

    resultado = comprobar(raiz, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "tipografia")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "Helvetica" in comprobacion.medido


def test_el_interlineado_nunca_se_juzga(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """El punto importante: el ratio se enseña, no se traduce."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "interlineado")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "1.73" in comprobacion.medido or "1,73" in comprobacion.medido
    assert "equivalencia" in comprobacion.nota


def test_las_imagenes_esperan_a_la_segunda_parte(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "imagenes")
    assert comprobacion.veredicto == NO_VERIFICABLE
    assert "leer" in comprobacion.nota


def test_escaneado_no_cumple(criterios_de_formato: Path, pdf_escaneado: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_escaneado))

    assert _de(resultado, "archivo").veredicto == NO_CUMPLE


def test_pagina_en_blanco_no_cumple(criterios_de_formato: Path, pdf_con_pagina_en_blanco: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_pagina_en_blanco))

    comprobacion = _de(resultado, "paginas_en_blanco")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "2" in comprobacion.medido


def test_sin_paginas_en_blanco_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "paginas_en_blanco").veredicto == CUMPLE


def test_indice_descuadrado_no_cumple(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """El fixture declara «3. Desarrollo» en la 5 y está en la 6."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    comprobacion = _de(resultado, "indice_paginado")
    assert comprobacion.veredicto == NO_CUMPLE
    assert "Desarrollo" in comprobacion.medido


def test_alineacion_ambigua_no_es_verificable(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """Entre las dos bandas no se decide: se enseña la proporción."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert _de(resultado, "alineacion").veredicto in (NO_CUMPLE, NO_VERIFICABLE)


def test_cada_comprobacion_lleva_su_fuente(criterios_de_formato: Path, pdf_con_indice: Path) -> None:
    """R1 en la salida: ningún veredicto sin la sección que lo respalda."""
    resultado = comprobar(criterios_de_formato, "v2026-2027", medir(pdf_con_indice))

    assert resultado
    assert all("#" in comprobacion.fuente for comprobacion in resultado)


def test_sin_fichero_de_criterios_no_hay_comprobaciones(tmp_path: Path, pdf_simple: Path) -> None:
    assert comprobar(tmp_path, "v2026-2027", medir(pdf_simple)) == []
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/formato/test_comprobacion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.formato'`

- [ ] **Step 3: Escribir `backend/formato/__init__.py`**

```python
"""Compara lo medido con lo que exigen los criterios. No abre PDFs."""
```

- [ ] **Step 4: Escribir `backend/formato/comprobacion.py`**

```python
"""Lo medido contra lo exigido en criteria/<version>/formato.yaml.

Este módulo no sabe abrir un PDF y el de extracción no sabe qué exige el
Maestro. Esa separación es lo que permite cambiar un criterio sin tocar la
medición, y medir mejor sin revisar ningún criterio.

Ningún valor de criterio está escrito aquí: todos se leen del fichero en
cada llamada. Copiarlos al código habría creado un segundo dueño del
criterio, que es lo que la regla R1 existe para impedir.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from backend.extraccion.medidas import Medidas

CUMPLE = "CUMPLE"
NO_CUMPLE = "NO_CUMPLE"
NO_VERIFICABLE = "NO_VERIFICABLE"

# Un texto justificado alinea a la derecha todas las líneas menos la última
# de cada párrafo. Las dos bandas son anchas a propósito: entre ellas la
# medida no distingue, y decir «no lo sé» es más útil que acertar a medias.
JUSTIFICADO_DESDE = 0.75
JUSTIFICADO_HASTA = 0.25

NOTA_INTERLINEADO = (
    "Un PDF no guarda «1,5 líneas»: guarda la distancia entre líneas base. "
    "La equivalencia entre esa distancia y el valor elegido en el procesador "
    "de textos depende de la fuente —para Arial 11 a 1,5 el ratio ronda "
    "1,73— y no está fijada en ninguna fuente oficial. Se enseña lo medido "
    "y lo juzga el docente."
)

NOTA_IMAGENES = (
    "Comprobar numeración, título, fuente y mención en el texto exige leer "
    "el documento y relacionar cada imagen con lo que se dice de ella. "
    "Corresponde a la segunda parte del flujo."
)


class Comprobacion(BaseModel):
    """Un criterio de formato contrastado con lo medido.

    `esperado` y `medido` van como texto porque los lee el docente. `fuente`
    es la sección del Maestro que respalda el criterio: sin ella la
    comprobación no se emite.
    """

    criterio: str
    veredicto: str
    esperado: str
    medido: str
    fuente: str
    nota: str = ""


def _cargar(raiz: Path, version: str) -> dict:
    fichero = raiz / "criteria" / version / "formato.yaml"
    if not fichero.is_file():
        return {}
    return yaml.safe_load(fichero.read_text(encoding="utf-8")) or {}


def _extension(bloque: dict, medidas: Medidas) -> Comprobacion:
    minimo = bloque["minimo_paginas_contenido"]
    contadas = medidas.estructura.paginas_de_contenido
    if contadas is None:
        return Comprobacion(
            criterio="extension",
            veredicto=NO_VERIFICABLE,
            esperado=f"{minimo} páginas de contenido como mínimo",
            medido=f"{medidas.total_paginas} páginas en total",
            fuente=bloque["fuente"],
            nota="No se ha localizado el índice, así que no se sabe dónde "
                 "empieza el contenido ni dónde acaban los anexos. Indica el "
                 "reparto y se cuenta.",
        )
    return Comprobacion(
        criterio="extension",
        veredicto=CUMPLE if contadas >= minimo else NO_CUMPLE,
        esperado=f"{minimo} páginas de contenido como mínimo",
        medido=f"{contadas} páginas de contenido "
               f"(de {medidas.total_paginas} en total)",
        fuente=bloque["fuente"],
    )


def _tipografia(bloque: dict, medidas: Medidas) -> Comprobacion:
    familia = str(bloque["familia"])
    cuerpo = float(bloque["cuerpo"])
    tolerancia = float(bloque.get("tolerancia_cuerpo", 0))
    medido = medidas.texto

    if not medido.familia_dominante:
        return Comprobacion(
            criterio="tipografia",
            veredicto=NO_VERIFICABLE,
            esperado=f"{familia} {cuerpo:g}",
            medido="el documento no tiene texto extraíble",
            fuente=bloque["fuente"],
        )

    coincide = (
        medido.familia_dominante.lower() == familia.lower()
        and abs(medido.cuerpo_dominante - cuerpo) <= tolerancia
    )
    return Comprobacion(
        criterio="tipografia",
        veredicto=CUMPLE if coincide else NO_CUMPLE,
        esperado=f"{familia} {cuerpo:g} (tolerancia {tolerancia:g})",
        medido=f"{medido.familia_dominante} {medido.cuerpo_dominante:g}, "
               f"en el {medido.proporcion_cuerpo_dominante:.0%} del texto",
        fuente=bloque["fuente"],
    )


def _interlineado(bloque: dict, medidas: Medidas) -> Comprobacion:
    """Siempre NO_VERIFICABLE. Ver NOTA_INTERLINEADO."""
    ratio = medidas.texto.ratio_interlineado
    return Comprobacion(
        criterio="interlineado",
        veredicto=NO_VERIFICABLE,
        esperado=f"{bloque['valor']} líneas",
        medido=(f"ratio medido {ratio:.2f} entre líneas base y cuerpo"
                if ratio is not None else "no hay líneas suficientes para medirlo"),
        fuente=bloque["fuente"],
        nota=NOTA_INTERLINEADO,
    )


def _alineacion(bloque: dict, medidas: Medidas) -> Comprobacion:
    proporcion = medidas.texto.proporcion_lineas_al_margen_derecho
    esperado = str(bloque["valor"])
    if proporcion is None:
        return Comprobacion(
            criterio="alineacion", veredicto=NO_VERIFICABLE, esperado=esperado,
            medido="el documento no tiene texto extraíble", fuente=bloque["fuente"],
        )

    medido = f"el {proporcion:.0%} de las líneas llega al margen derecho"
    if proporcion >= JUSTIFICADO_DESDE:
        return Comprobacion(criterio="alineacion", veredicto=CUMPLE,
                            esperado=esperado, medido=medido, fuente=bloque["fuente"])
    if proporcion <= JUSTIFICADO_HASTA:
        return Comprobacion(criterio="alineacion", veredicto=NO_CUMPLE,
                            esperado=esperado, medido=medido, fuente=bloque["fuente"])
    return Comprobacion(
        criterio="alineacion", veredicto=NO_VERIFICABLE, esperado=esperado,
        medido=medido, fuente=bloque["fuente"],
        nota="Entre el 25 % y el 75 % la medida no distingue un texto "
             "justificado de uno alineado a la izquierda con líneas largas. "
             "Míralo en el documento.",
    )


def _margenes(bloque: dict, medidas: Medidas) -> Comprobacion:
    esperado_cm = float(bloque["centimetros"])
    tolerancia = float(bloque.get("tolerancia", 0))
    medido = medidas.texto
    lados = {
        "izquierdo": medido.margen_izquierdo_cm,
        "derecho": medido.margen_derecho_cm,
        "superior": medido.margen_superior_cm,
        "inferior": medido.margen_inferior_cm,
    }
    if any(valor is None for valor in lados.values()):
        return Comprobacion(
            criterio="margenes", veredicto=NO_VERIFICABLE,
            esperado=f"{esperado_cm:g} cm", medido="no hay texto que medir",
            fuente=bloque["fuente"],
        )

    fuera = [
        f"{lado} {valor:.2f} cm"
        for lado, valor in lados.items()
        if abs(valor - esperado_cm) > tolerancia
    ]
    return Comprobacion(
        criterio="margenes",
        veredicto=CUMPLE if not fuera else NO_CUMPLE,
        esperado=f"{esperado_cm:g} cm (tolerancia {tolerancia:g})",
        medido=", ".join(f"{lado} {valor:.2f} cm" for lado, valor in lados.items()),
        fuente=bloque["fuente"],
        nota="" if not fuera else
             "Los márgenes superior e inferior se miden sobre todo el texto "
             "de la página: un encabezado o un pie los reducen.",
    )


def _archivo(bloque: dict, medidas: Medidas) -> Comprobacion:
    admite = bool(bloque.get("admite_escaneado", False))
    return Comprobacion(
        criterio="archivo",
        veredicto=NO_CUMPLE if (medidas.escaneado and not admite) else CUMPLE,
        esperado=f"{bloque.get('formato', 'PDF')} generado desde el original"
                 + ("" if admite else ", no escaneado"),
        medido="PDF escaneado, sin texto extraíble" if medidas.escaneado
               else "PDF con texto extraíble",
        fuente=bloque["fuente"],
    )


def _paginas_en_blanco(bloque: dict, medidas: Medidas) -> Comprobacion:
    permitidas = bool(bloque.get("permitidas", False))
    hay = medidas.paginas_en_blanco
    return Comprobacion(
        criterio="paginas_en_blanco",
        veredicto=NO_CUMPLE if (hay and not permitidas) else CUMPLE,
        esperado="ninguna página en blanco" if not permitidas
                 else "se admiten páginas en blanco",
        medido="ninguna" if not hay
               else "páginas " + ", ".join(str(numero) for numero in hay),
        fuente=bloque["fuente"],
    )


def _imagenes(bloque: dict, medidas: Medidas) -> Comprobacion:
    """Siempre NO_VERIFICABLE en esta parte. Ver NOTA_IMAGENES."""
    return Comprobacion(
        criterio="imagenes",
        veredicto=NO_VERIFICABLE,
        esperado="numeradas, tituladas, con fuente si son ajenas y citadas "
                 "en el texto",
        medido=f"{len(medidas.imagenes)} imágenes colocadas",
        fuente=bloque["fuente"],
        nota=NOTA_IMAGENES,
    )


def _indice_paginado(bloque: dict, medidas: Medidas) -> Comprobacion:
    estructura = medidas.estructura
    if estructura.pagina_del_indice is None:
        return Comprobacion(
            criterio="indice_paginado", veredicto=NO_VERIFICABLE,
            esperado="títulos y páginas del índice coinciden con el documento",
            medido="no se ha localizado el índice", fuente=bloque["fuente"],
        )

    problemas = list(estructura.paginas_declaradas_incorrectas)
    problemas += [
        f"«{titulo}» aparece en el índice pero no se encuentra en el documento."
        for titulo in estructura.titulos_no_encontrados
    ]
    return Comprobacion(
        criterio="indice_paginado",
        veredicto=CUMPLE if not problemas else NO_CUMPLE,
        esperado="títulos y páginas del índice coinciden con el documento",
        medido=" ".join(problemas) if problemas
               else f"{len(estructura.entradas_de_indice)} entradas, todas correctas",
        fuente=bloque["fuente"],
    )


# Cada criterio del fichero con la función que lo comprueba. Un criterio que
# no esté aquí simplemente no se comprueba: no se inventa un veredicto.
COMPROBADORES = {
    "extension": _extension,
    "tipografia": _tipografia,
    "interlineado": _interlineado,
    "alineacion": _alineacion,
    "margenes": _margenes,
    "archivo": _archivo,
    "paginas_en_blanco": _paginas_en_blanco,
    "imagenes": _imagenes,
    "indice_paginado": _indice_paginado,
}


def comprobar(raiz: Path, version: str, medidas: Medidas) -> list[Comprobacion]:
    """Un resultado por criterio de formato presente en el fichero.

    El orden es el del fichero de criterios, que es el que el docente
    conoce.
    """
    criterios = _cargar(raiz, version)
    resultado = []
    for nombre, bloque in criterios.items():
        comprobador = COMPROBADORES.get(nombre)
        if comprobador is None or not isinstance(bloque, dict):
            continue
        if "fuente" not in bloque:
            # R1: sin fuente trazable el criterio no existe, así que
            # tampoco existe su comprobación.
            continue
        resultado.append(comprobador(bloque, medidas))
    return resultado
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/formato/test_comprobacion.py -v`
Expected: PASS, 14 tests.

- [ ] **Step 6: Registrar la equivalencia pendiente**

Añadir a `docs/PENDIENTE_OFICIAL.md`, respetando el formato de las entradas existentes:

```markdown
- **equivalencia_interlineado** — a qué distancia entre líneas base
  corresponde el «1,5» que exige el §6.2. Un PDF no guarda el valor elegido
  en el procesador de textos, sino la separación real, y la conversión
  depende de la fuente: para Arial 11 a 1,5 líneas el ratio ronda 1,73. Hasta
  fijarlo, la comprobación del interlineado se emite como `NO_VERIFICABLE`
  con el ratio medido a la vista. Se espera del banco de calibración del §20.
```

- [ ] **Step 7: Ejecutar la batería completa**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`
Expected: todo en verde. La gobernanza no protesta: no se ha tocado `criteria/`.

- [ ] **Step 8: Commit**

```bash
git add backend/formato tests/formato docs/PENDIENTE_OFICIAL.md
git commit -m "feat: comprobacion de formato contra los criterios

Ningun valor de criterio esta escrito en el codigo: todos se leen del
fichero en cada llamada. Copiarlos habria creado un segundo dueno del
criterio, que es lo que R1 impide.

Dos criterios salen NO_VERIFICABLE a proposito. El interlineado, porque un
PDF no guarda 1,5 lineas sino la distancia entre lineas base, y la
equivalencia depende de la fuente y no esta fijada en ninguna fuente
oficial. Y las imagenes, porque numeracion, titulo y mencion exigen leer y
relacionar: son de la segunda parte.

La alineacion usa dos bandas anchas y declara la zona de en medio. Entre el
25 y el 75 por ciento la medida no distingue justificado de alineado a la
izquierda, y decirlo es mas util que acertar a medias."
```

---

### Task 8: Comparación evolutiva

Lo que el §5.1 prohíbe: entregar solo los capítulos nuevos, repetir la versión anterior sin progreso, o eliminar contenido ya validado. Se compara texto normalizado, sin ningún modelo de lenguaje.

**Files:**
- Create: `backend/evolucion/__init__.py`
- Create: `backend/evolucion/comparacion.py`
- Create: `tests/evolucion/test_comparacion.py`

**Interfaces:**
- Consumes: `medidas.texto_plano` (Task 6).
- Produces:
  - `Evolucion(BaseModel)` con `proporcion_conservada: float`, `proporcion_nueva: float`, `parrafos_eliminados: int`, `parrafos_nuevos: int`, `avisos: list[str]`.
  - `comparar(texto_anterior: str, texto_nuevo: str) -> Evolucion`
  - `normalizar(texto: str) -> list[str]`

- [ ] **Step 1: Escribir los tests**

Crear `tests/evolucion/test_comparacion.py`:

```python
"""La entrega nueva contra la anterior."""

from backend.evolucion.comparacion import comparar, normalizar

ANTERIOR = """
1. Introduccion

Este trabajo estudia la gestion de reservas en talleres.

2. Objetivos

El objetivo general es reducir el tiempo de atencion.

3. Metodologia

Se emplea un enfoque incremental por iteraciones.
"""


def test_normalizar_reduce_espacios_y_mayusculas() -> None:
    parrafos = normalizar("  UN   Parrafo.  \n\n\n Otro Párrafo. ")

    assert parrafos == ["un parrafo.", "otro parrafo."]


def test_normalizar_ignora_los_parrafos_muy_cortos() -> None:
    """Numeraciones sueltas y encabezados de una palabra no son contenido."""
    parrafos = normalizar("3\n\nEste parrafo si tiene contenido suficiente.\n\nx")

    assert parrafos == ["este parrafo si tiene contenido suficiente."]


def test_entrega_identica_avisa_de_falta_de_progreso() -> None:
    evolucion = comparar(ANTERIOR, ANTERIOR)

    assert evolucion.proporcion_conservada == 1.0
    assert evolucion.proporcion_nueva == 0.0
    assert any("sin cambios" in aviso for aviso in evolucion.avisos)


def test_entrega_ampliada_no_avisa_de_nada() -> None:
    nuevo = ANTERIOR + """
4. Desarrollo

Se implementa el modulo de reservas con sus pruebas.

5. Resultados

El tiempo de atencion baja de doce a siete minutos.
"""

    evolucion = comparar(ANTERIOR, nuevo)

    assert evolucion.parrafos_nuevos == 2
    assert evolucion.parrafos_eliminados == 0
    assert evolucion.avisos == []


def test_contenido_eliminado_se_avisa() -> None:
    """El §5.1 lo prohíbe: no se quita lo ya validado."""
    recortado = """
1. Introduccion

Este trabajo estudia la gestion de reservas en talleres.
"""

    evolucion = comparar(ANTERIOR, recortado)

    assert evolucion.parrafos_eliminados > 0
    assert any("desaparecido" in aviso for aviso in evolucion.avisos)


def test_entrega_que_solo_trae_lo_nuevo_se_avisa() -> None:
    """Solo los capítulos nuevos, sin el trabajo anterior: §5.1."""
    solo_nuevo = """
4. Desarrollo

Se implementa el modulo de reservas con sus pruebas.

5. Resultados

El tiempo de atencion baja de doce a siete minutos.
"""

    evolucion = comparar(ANTERIOR, solo_nuevo)

    assert evolucion.proporcion_conservada == 0.0
    assert any("documento completo" in aviso for aviso in evolucion.avisos)


def test_sin_entrega_anterior_no_se_compara() -> None:
    evolucion = comparar("", ANTERIOR)

    assert evolucion.avisos == []
    assert evolucion.proporcion_conservada == 0.0
    assert evolucion.parrafos_eliminados == 0


def test_un_retoque_menor_cuenta_como_conservado() -> None:
    """Cambiar una palabra no convierte el párrafo en otro distinto."""
    retocado = ANTERIOR.replace("reducir el tiempo", "acortar el tiempo")

    evolucion = comparar(ANTERIOR, retocado)

    assert evolucion.proporcion_conservada == 1.0
    assert evolucion.parrafos_eliminados == 0


def test_un_retoque_menor_no_se_confunde_con_falta_de_progreso() -> None:
    """El aviso de «sin cambios» exige texto idéntico, no parecido.

    Con el umbral de parecido, un párrafo retocado cuenta como conservado y
    no cuenta como nuevo, así que juzgar el progreso por esas proporciones
    marcaría como estancada una entrega que sí se ha corregido.
    """
    retocado = ANTERIOR.replace("reducir el tiempo", "acortar el tiempo")

    assert comparar(ANTERIOR, retocado).avisos == []
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/evolucion/test_comparacion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.evolucion'`

- [ ] **Step 3: Escribir `backend/evolucion/__init__.py`**

```python
"""Compara una entrega con la anterior. Sin modelos de lenguaje."""
```

- [ ] **Step 4: Escribir `backend/evolucion/comparacion.py`**

```python
"""La entrega nueva frente a la anterior.

El §5.1 prohíbe tres cosas que se detectan contrastando textos: entregar
solo los capítulos nuevos, repetir la versión anterior sin progreso real, y
eliminar contenido ya validado. Ninguna necesita entender el texto, solo
compararlo, así que aquí no interviene ningún modelo de lenguaje.

Los avisos son avisos. No dicen que el alumno haya hecho algo mal: dicen
que hay algo que mirar. Quien decide es el docente.
"""

import difflib
import re
import unicodedata

from pydantic import BaseModel

# Un párrafo más corto que esto es una numeración, un encabezado suelto o
# un pie de página. Contarlo como contenido ensucia las proporciones.
CARACTERES_MINIMOS = 25

# Dos párrafos son el mismo si se parecen tanto: deja pasar el retoque de
# una palabra y no confunde dos párrafos distintos del mismo apartado.
PARECIDO_MINIMO = 0.85

# Por debajo de esto, la entrega nueva no contiene el trabajo anterior.
CONSERVADO_MINIMO = 0.30


class Evolucion(BaseModel):
    """Qué se conserva, qué se ha añadido y qué ha desaparecido."""

    proporcion_conservada: float = 0.0
    proporcion_nueva: float = 0.0
    parrafos_eliminados: int = 0
    parrafos_nuevos: int = 0
    avisos: list[str] = []


def normalizar(texto: str) -> list[str]:
    """Párrafos con contenido, en minúsculas, sin tildes ni espacios de sobra."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    parrafos = []
    for crudo in re.split(r"\n\s*\n", sin_tildes):
        limpio = " ".join(crudo.lower().split())
        if len(limpio) >= CARACTERES_MINIMOS:
            parrafos.append(limpio)
    return parrafos


def _esta_en(parrafo: str, otros: list[str]) -> bool:
    """Si el párrafo aparece en la otra lista, admitiendo retoques menores."""
    return bool(difflib.get_close_matches(parrafo, otros, n=1, cutoff=PARECIDO_MINIMO))


def comparar(texto_anterior: str, texto_nuevo: str) -> Evolucion:
    """Contrasta las dos entregas y avisa de lo que el §5.1 prohíbe."""
    anteriores = normalizar(texto_anterior)
    nuevos = normalizar(texto_nuevo)

    if not anteriores:
        # Primera entrega: no hay con qué comparar y no se finge que sí.
        return Evolucion(parrafos_nuevos=len(nuevos))

    conservados = [parrafo for parrafo in anteriores if _esta_en(parrafo, nuevos)]
    añadidos = [parrafo for parrafo in nuevos if not _esta_en(parrafo, anteriores)]

    proporcion_conservada = len(conservados) / len(anteriores)
    proporcion_nueva = len(añadidos) / len(nuevos) if nuevos else 0.0
    eliminados = len(anteriores) - len(conservados)

    avisos = []
    if proporcion_conservada < CONSERVADO_MINIMO:
        avisos.append(
            "La entrega no parece incluir el trabajo anterior: solo se "
            f"reconoce el {proporcion_conservada:.0%} de lo que había. El §5.1 "
            "pide el documento completo en cada fase, no solo lo nuevo."
        )
    elif eliminados:
        avisos.append(
            f"Han desaparecido {eliminados} párrafos que estaban en la entrega "
            "anterior. El §5.1 no admite eliminar contenido ya validado sin "
            "justificarlo."
        )

    # Identidad exacta, no parecido. Con el umbral de PARECIDO_MINIMO un
    # párrafo retocado cuenta como conservado y no cuenta como nuevo, así
    # que medir el progreso con esas proporciones marcaría como estancada
    # una entrega que sí se ha corregido.
    if anteriores == nuevos:
        avisos.append(
            "La entrega llega sin cambios respecto a la anterior: no se "
            "aprecia progreso."
        )

    return Evolucion(
        proporcion_conservada=proporcion_conservada,
        proporcion_nueva=proporcion_nueva,
        parrafos_eliminados=eliminados,
        parrafos_nuevos=len(añadidos),
        avisos=avisos,
    )
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/evolucion/test_comparacion.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/evolucion tests/evolucion
git commit -m "feat: comparacion evolutiva entre entregas

Detecta las tres cosas que prohibe el 5.1: entregar solo los capitulos
nuevos, repetir la version anterior sin progreso, y eliminar contenido ya
validado. Ninguna necesita entender el texto, solo compararlo, asi que
aqui no interviene ningun modelo.

Los avisos son avisos: dicen que hay algo que mirar, no que el alumno haya
hecho algo mal. Quien decide es el docente."
```
---

### Task 9: Vigilancia de la carpeta y propuesta de identificación

La decisión D-009 en código. El sistema mira la carpeta, encuentra los PDFs que no ha visto y **propone** de quién y de qué fase es cada uno leyendo su nombre. Cuando el nombre no encaja, la propuesta va vacía con el motivo escrito: no se adivina.

El archivo no se mueve, ni se renombra, ni se copia. Se mira y se lee.

**Files:**
- Create: `backend/vigilancia/__init__.py`
- Create: `backend/vigilancia/nombres.py`
- Create: `backend/vigilancia/carpeta.py`
- Create: `tests/vigilancia/test_nombres.py`
- Create: `tests/vigilancia/test_carpeta.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `FASES: tuple[str, ...] = ("TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA")`
  - `PropuestaDeIdentificacion(BaseModel)` con `codigo_alumno: str | None`, `ciclo: str | None`, `fase: str | None`, `fecha: date | None`, `version: int | None`, `motivo: str = ""`; y la propiedad `completa: bool`.
  - `deducir(nombre_archivo: str) -> PropuestaDeIdentificacion`
  - `ArchivoVisto(BaseModel)` con `nombre: str`, `ruta: Path`, `modificado_en: datetime`, `propuesta: PropuestaDeIdentificacion`.
  - `mirar(carpeta: Path, nombres_ya_registrados: set[str]) -> list[ArchivoVisto]`

- [ ] **Step 1: Escribir los tests de deducción**

Crear `tests/vigilancia/test_nombres.py`:

```python
"""Qué se deduce del nombre de un archivo, y qué no."""

from datetime import date

import pytest

from backend.vigilancia.nombres import deducir


def test_nombre_completo_se_deduce_entero() -> None:
    propuesta = deducir("AF023_DAM_E2_20260115_v1.pdf")

    assert propuesta.codigo_alumno == "AF023"
    assert propuesta.ciclo == "DAM"
    assert propuesta.fase == "E2"
    assert propuesta.fecha == date(2026, 1, 15)
    assert propuesta.version == 1
    assert propuesta.completa is True
    assert propuesta.motivo == ""


@pytest.mark.parametrize("fase", ["TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA"])
def test_todas_las_fases_conocidas(fase: str) -> None:
    propuesta = deducir(f"AF023_DAM_{fase}_20260115_v1.pdf")

    assert propuesta.fase == fase


def test_la_fase_se_reconoce_en_minusculas() -> None:
    propuesta = deducir("af023_dam_e2_20260115_v1.pdf")

    assert propuesta.fase == "E2"
    assert propuesta.codigo_alumno == "AF023"


def test_una_fase_desconocida_no_se_inventa() -> None:
    propuesta = deducir("AF023_DAM_E9_20260115_v1.pdf")

    assert propuesta.fase is None
    assert propuesta.completa is False
    assert "E9" in propuesta.motivo


def test_un_nombre_que_no_sigue_la_convencion_no_deduce_nada() -> None:
    propuesta = deducir("trabajo final juan.pdf")

    assert propuesta.codigo_alumno is None
    assert propuesta.fase is None
    assert propuesta.completa is False
    assert "no sigue la convención" in propuesta.motivo


def test_una_fecha_imposible_no_se_inventa() -> None:
    propuesta = deducir("AF023_DAM_E2_20261352_v1.pdf")

    assert propuesta.fecha is None
    assert propuesta.completa is False
    assert "fecha" in propuesta.motivo


def test_sin_version_la_propuesta_sigue_incompleta() -> None:
    propuesta = deducir("AF023_DAM_E2_20260115.pdf")

    assert propuesta.codigo_alumno == "AF023"
    assert propuesta.version is None
    assert propuesta.completa is False


def test_la_version_admite_mayuscula() -> None:
    assert deducir("AF023_DAM_E2_20260115_V3.pdf").version == 3


def test_el_motivo_va_dirigido_al_docente() -> None:
    """Dice qué se esperaba, con un ejemplo, no un patrón de expresión regular."""
    propuesta = deducir("cosa.pdf")

    assert "AF023_DAM_E2_20260115_v1.pdf" in propuesta.motivo
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/vigilancia/test_nombres.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.vigilancia'`

- [ ] **Step 3: Escribir `backend/vigilancia/__init__.py`**

```python
"""Encuentra los archivos y propone de quién son. Nunca decide."""
```

- [ ] **Step 4: Escribir `backend/vigilancia/nombres.py`**

```python
"""Lo que se puede deducir del nombre de un archivo.

La convención del §15.3 es CODIGO_CICLO_FASE_FECHA_VERSION.ext, por ejemplo
AF023_DAM_E2_20260115_v1.pdf.

Este módulo deduce y se detiene. No corrige nombres parecidos, no elige el
alumno más probable y no supone la fase por la fecha. El nombre del archivo
lo escribe el alumno, y confiar en él convertiría la condición de parada del
§18.2 —«alumno o fase no coinciden»— de excepción en rutina. Lo que sale de
aquí es una propuesta que el docente confirma.
"""

import re
from datetime import date

from pydantic import BaseModel, computed_field

FASES: tuple[str, ...] = ("TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA")

EJEMPLO = "AF023_DAM_E2_20260115_v1.pdf"

PATRON = re.compile(
    r"^(?P<codigo>[A-Za-z]{1,4}\d{1,5})"
    r"_(?P<ciclo>[A-Za-z]{2,8})"
    r"_(?P<fase>[A-Za-z0-9]{1,8})"
    r"_(?P<fecha>\d{8})"
    r"(?:_[vV](?P<version>\d{1,2}))?$"
)


class PropuestaDeIdentificacion(BaseModel):
    """De quién y de qué fase parece ser el archivo.

    Un campo a `None` significa que no se ha podido deducir, nunca que se
    haya deducido un valor por omisión.
    """

    codigo_alumno: str | None = None
    ciclo: str | None = None
    fase: str | None = None
    fecha: date | None = None
    version: int | None = None
    motivo: str = ""

    @computed_field
    @property
    def completa(self) -> bool:
        """Si el docente puede confirmarla de un clic, sin escribir nada.

        Va como `computed_field` porque el frontend la lee para decidir si
        enseña el botón de confirmar o el formulario. Una propiedad normal
        de Pydantic no se serializa, y llegaría ausente al navegador.
        """
        return all((
            self.codigo_alumno, self.ciclo, self.fase, self.fecha, self.version
        ))


def deducir(nombre_archivo: str) -> PropuestaDeIdentificacion:
    """Lee el nombre y propone. Lo que no encaja se queda a None con motivo."""
    tronco = nombre_archivo.rsplit(".", 1)[0]
    encaje = PATRON.match(tronco)
    if encaje is None:
        return PropuestaDeIdentificacion(
            motivo=f"El nombre «{nombre_archivo}» no sigue la convención "
                   f"CODIGO_CICLO_FASE_FECHA_VERSION, por ejemplo {EJEMPLO}. "
                   "Indica tú de quién es y de qué fase."
        )

    partes = encaje.groupdict()
    motivos = []

    fase = partes["fase"].upper()
    if fase not in FASES:
        motivos.append(
            f"«{partes['fase']}» no es una fase conocida. Las fases son: "
            + ", ".join(FASES) + "."
        )
        fase = None

    try:
        fecha = date(
            int(partes["fecha"][:4]), int(partes["fecha"][4:6]), int(partes["fecha"][6:])
        )
    except ValueError:
        motivos.append(f"«{partes['fecha']}» no es una fecha válida (AAAAMMDD).")
        fecha = None

    version = int(partes["version"]) if partes["version"] else None
    if version is None:
        motivos.append(
            f"El nombre no indica la versión. Se espera _v1, _v2… como en {EJEMPLO}."
        )

    return PropuestaDeIdentificacion(
        codigo_alumno=partes["codigo"].upper(),
        ciclo=partes["ciclo"].upper(),
        fase=fase,
        fecha=fecha,
        version=version,
        motivo=" ".join(motivos),
    )
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/vigilancia/test_nombres.py -v`
Expected: PASS, 15 tests (9 sueltos más 6 de la parametrización de fases).

- [ ] **Step 6: Escribir los tests de la carpeta**

Crear `tests/vigilancia/test_carpeta.py`:

```python
"""Qué encuentra el vigilante en la carpeta."""

from pathlib import Path

from backend.vigilancia.carpeta import mirar


def _pdf(carpeta: Path, nombre: str) -> Path:
    """Un archivo con extensión .pdf. Mirar no lo abre, así que basta."""
    ruta = carpeta / nombre
    ruta.write_bytes(b"%PDF-1.4\n")
    return ruta


def test_encuentra_los_pdf(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    _pdf(tmp_path, "AF024_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, set())

    assert len(vistos) == 2


def test_ignora_lo_que_no_es_pdf(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    (tmp_path / "notas.txt").write_text("x", encoding="utf-8")
    (tmp_path / "trabajo.docx").write_bytes(b"x")

    vistos = mirar(tmp_path, set())

    assert [visto.nombre for visto in vistos] == ["AF023_DAM_E2_20260115_v1.pdf"]


def test_no_repite_lo_ya_registrado(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    _pdf(tmp_path, "AF024_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, {"AF023_DAM_E2_20260115_v1.pdf"})

    assert [visto.nombre for visto in vistos] == ["AF024_DAM_E2_20260115_v1.pdf"]


def test_cada_archivo_llega_con_su_propuesta(tmp_path: Path) -> None:
    _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")

    visto = mirar(tmp_path, set())[0]

    assert visto.propuesta.codigo_alumno == "AF023"
    assert visto.propuesta.completa is True


def test_un_nombre_raro_llega_con_la_propuesta_vacia(tmp_path: Path) -> None:
    _pdf(tmp_path, "trabajo de clase.pdf")

    visto = mirar(tmp_path, set())[0]

    assert visto.propuesta.completa is False
    assert visto.propuesta.motivo


def test_mira_dentro_de_las_subcarpetas(tmp_path: Path) -> None:
    """El §15.2 organiza por alumno y curso: hay subcarpetas."""
    subcarpeta = tmp_path / "AF023"
    subcarpeta.mkdir()
    _pdf(subcarpeta, "AF023_DAM_E2_20260115_v1.pdf")

    vistos = mirar(tmp_path, set())

    assert len(vistos) == 1
    assert vistos[0].ruta.parent == subcarpeta


def test_el_orden_es_el_mas_reciente_primero(tmp_path: Path) -> None:
    import os
    import time

    viejo = _pdf(tmp_path, "AF023_DAM_E1_20260115_v1.pdf")
    nuevo = _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    antiguo = time.time() - 3600
    os.utime(viejo, (antiguo, antiguo))

    vistos = mirar(tmp_path, set())

    assert vistos[0].ruta == nuevo


def test_una_carpeta_que_no_existe_no_revienta(tmp_path: Path) -> None:
    assert mirar(tmp_path / "fantasma", set()) == []


def test_no_toca_ningun_archivo(tmp_path: Path) -> None:
    """El §18.1: se mira y no se toca."""
    ruta = _pdf(tmp_path, "AF023_DAM_E2_20260115_v1.pdf")
    antes = sorted(p.name for p in tmp_path.rglob("*"))
    momento = ruta.stat().st_mtime

    mirar(tmp_path, set())

    assert sorted(p.name for p in tmp_path.rglob("*")) == antes
    assert ruta.stat().st_mtime == momento
```

- [ ] **Step 7: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/vigilancia/test_carpeta.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.vigilancia.carpeta'`

- [ ] **Step 8: Escribir `backend/vigilancia/carpeta.py`**

```python
"""Lo que hay en la carpeta de entregas y no se ha registrado todavía.

Mirar es mirar: se recorre el árbol, se leen los nombres y se devuelve una
lista. Ningún archivo se abre, se mueve, se renombra ni se copia. El §18.1
lo exige y aquí se cumple por construcción, porque este módulo no tiene
ninguna llamada que escriba.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from backend.vigilancia.nombres import PropuestaDeIdentificacion, deducir

EXTENSION = ".pdf"


class ArchivoVisto(BaseModel):
    """Un archivo de la carpeta que aún no está registrado."""

    nombre: str
    ruta: Path
    modificado_en: datetime
    propuesta: PropuestaDeIdentificacion


def mirar(carpeta: Path, nombres_ya_registrados: set[str]) -> list[ArchivoVisto]:
    """Los PDFs pendientes, el más reciente primero.

    Se compara por nombre y no por huella porque calcular la huella obliga a
    leer el archivo entero, y esto se llama cada vez que el docente abre la
    bandeja. La huella se calcula al registrar, que es cuando importa.
    """
    if not carpeta.is_dir():
        return []

    vistos = []
    for ruta in carpeta.rglob(f"*{EXTENSION}"):
        if not ruta.is_file() or ruta.name in nombres_ya_registrados:
            continue
        vistos.append(ArchivoVisto(
            nombre=ruta.name,
            ruta=ruta,
            modificado_en=datetime.fromtimestamp(ruta.stat().st_mtime),
            propuesta=deducir(ruta.name),
        ))
    return sorted(vistos, key=lambda visto: visto.modificado_en, reverse=True)
```

- [ ] **Step 9: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/vigilancia -v`
Expected: PASS, 24 tests.

- [ ] **Step 10: Commit**

```bash
git add backend/vigilancia tests/vigilancia
git commit -m "feat: vigilancia de la carpeta y propuesta de identificacion

D-009 en codigo. El sistema encuentra los PDF que no ha visto y propone de
quien y de que fase es cada uno leyendo su nombre. Cuando el nombre no
encaja, la propuesta va vacia con el motivo escrito para el docente.

No corrige nombres parecidos, no elige el alumno mas probable y no supone
la fase por la fecha. El nombre lo escribe el alumno, y fiarse de el
convertiria la parada del 18.2 de excepcion en rutina.

Mirar es mirar: este modulo no tiene ninguna llamada que escriba, asi que
el 18.1 se cumple por construccion."
```

---

### Task 10: Persistencia — el puerto y el almacén en memoria

Un puerto con dos implementaciones, como el motor de análisis: lo que se guarda no depende de dónde se guarda. El almacén en memoria no es un juguete de pruebas — es lo que corre cuando no hay credenciales, y por eso avisa de que lo guardado se pierde al cerrar.

**Sobre qué se guarda y qué no.** Se guardan la ficha del alumno, el proyecto y la entrega, en las tablas que ya existen. **No se guardan las medidas ni las comprobaciones**: se recalculan al abrir la ficha, porque medir un PDF es determinista y rápido, y guardarlas exigiría una tabla nueva y una migración para un dato que se puede volver a obtener. Tampoco se guardan el PDF ni el texto, que es lo que fija D-001.

**Files:**
- Create: `backend/persistencia/__init__.py`
- Create: `backend/persistencia/modelos.py`
- Create: `backend/persistencia/memoria.py`
- Create: `tests/persistencia/test_memoria.py`

**Interfaces:**
- Consumes: `FASES` de `backend.vigilancia.nombres`.
- Produces:
  - `ESTADOS: tuple[str, ...]` con los siete del §16.1.
  - `EntregaRegistrada(BaseModel)` con `id: str`, `codigo_alumno: str`, `ciclo: str`, `fase: str`, `version: int`, `nombre_archivo: str`, `huella: str`, `recibida_en: datetime`, `estado: str`, `motivo_bloqueo: str | None`, `version_criterios: str`.
  - `Almacen` (`typing.Protocol`) con `registrar(...) -> EntregaRegistrada`, `listar() -> list[EntregaRegistrada]`, `por_id(id) -> EntregaRegistrada | None`, `por_huella(huella) -> EntregaRegistrada | None`, `anterior_de(codigo_alumno, fase) -> EntregaRegistrada | None`, `cambiar_estado(id, estado, motivo) -> EntregaRegistrada | None`, y la propiedad `es_duradero: bool`.
  - `AlmacenEnMemoria` que lo implementa.

- [ ] **Step 1: Escribir los tests**

Crear `tests/persistencia/test_memoria.py`:

```python
"""El almacén en memoria, que es también el contrato del puerto."""

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva


def _entrega(**cambios) -> EntregaNueva:
    datos = dict(
        codigo_alumno="AF023",
        ciclo="DAM",
        fase="E2",
        version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf",
        huella="a" * 64,
        version_criterios="v2026-2027",
    )
    datos.update(cambios)
    return EntregaNueva(**datos)


def test_una_entrega_registrada_se_recupera() -> None:
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega())

    assert almacen.por_id(guardada.id) == guardada
    assert guardada.codigo_alumno == "AF023"


def test_una_entrega_nueva_nace_recibida() -> None:
    almacen = AlmacenEnMemoria()

    guardada = almacen.registrar(_entrega())

    assert guardada.estado == "RECIBIDO"
    assert guardada.motivo_bloqueo is None


def test_listar_devuelve_lo_registrado() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega())
    almacen.registrar(_entrega(codigo_alumno="AF024", huella="b" * 64))

    assert len(almacen.listar()) == 2


def test_se_encuentra_por_huella() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega())

    assert almacen.por_huella("a" * 64) is not None
    assert almacen.por_huella("z" * 64) is None


def test_el_mismo_archivo_dos_veces_no_se_duplica() -> None:
    """Misma huella es el mismo archivo: se devuelve el registro existente."""
    almacen = AlmacenEnMemoria()
    primera = almacen.registrar(_entrega())

    segunda = almacen.registrar(_entrega(nombre_archivo="copia.pdf"))

    assert segunda.id == primera.id
    assert len(almacen.listar()) == 1


def test_la_anterior_es_la_de_la_fase_previa() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="E1", huella="1" * 64))
    almacen.registrar(_entrega(fase="E2", huella="2" * 64))

    anterior = almacen.anterior_de("AF023", "E2")

    assert anterior is not None
    assert anterior.fase == "E1"


def test_la_anterior_puede_ser_una_version_previa_de_la_misma_fase() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="E2", version=1, huella="1" * 64))

    anterior = almacen.anterior_de("AF023", "E2", version=2)

    assert anterior is not None
    assert anterior.version == 1


def test_sin_entrega_previa_no_hay_anterior() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(fase="TEMA"))

    assert almacen.anterior_de("AF023", "TEMA") is None


def test_la_anterior_es_de_ese_alumno_y_no_de_otro() -> None:
    almacen = AlmacenEnMemoria()
    almacen.registrar(_entrega(codigo_alumno="AF024", fase="E1", huella="1" * 64))

    assert almacen.anterior_de("AF023", "E2") is None


def test_cambiar_de_estado() -> None:
    almacen = AlmacenEnMemoria()
    guardada = almacen.registrar(_entrega())

    cambiada = almacen.cambiar_estado(guardada.id, "BLOQUEADO", "PDF ilegible.")

    assert cambiada is not None
    assert cambiada.estado == "BLOQUEADO"
    assert cambiada.motivo_bloqueo == "PDF ilegible."
    assert almacen.por_id(guardada.id).estado == "BLOQUEADO"


def test_un_estado_desconocido_se_rechaza() -> None:
    almacen = AlmacenEnMemoria()
    guardada = almacen.registrar(_entrega())

    with pytest.raises(ValueError, match="no es un estado"):
        almacen.cambiar_estado(guardada.id, "TERMINADO", None)


def test_bloquear_sin_motivo_se_rechaza() -> None:
    """La tabla lo impone con una restricción; aquí se falla antes y mejor."""
    almacen = AlmacenEnMemoria()
    guardada = almacen.registrar(_entrega())

    with pytest.raises(ValueError, match="motivo"):
        almacen.cambiar_estado(guardada.id, "BLOQUEADO", None)


def test_cambiar_el_estado_de_algo_que_no_existe_da_none() -> None:
    almacen = AlmacenEnMemoria()

    assert almacen.cambiar_estado("no-existe", "ANALIZADO", None) is None


def test_una_fase_desconocida_se_rechaza() -> None:
    almacen = AlmacenEnMemoria()

    with pytest.raises(ValueError, match="no es una fase"):
        almacen.registrar(_entrega(fase="E9"))


def test_el_almacen_en_memoria_dice_que_no_es_duradero() -> None:
    """Lo lee el frontend para avisar al docente. No se finge lo contrario."""
    assert AlmacenEnMemoria().es_duradero is False
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/persistencia/test_memoria.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.persistencia'`

- [ ] **Step 3: Escribir `backend/persistencia/__init__.py`**

```python
"""Dónde se guarda la ficha de una entrega. El puerto y sus dos almacenes."""
```

- [ ] **Step 4: Escribir `backend/persistencia/modelos.py`**

```python
"""Lo que se guarda de una entrega, y lo que no.

No se guarda el PDF. No se guarda el texto del trabajo. Es la decisión
D-001, y lo que hay aquí es exactamente lo que las tablas admiten: la ficha
del alumno codificado, el proyecto, y de la entrega su nombre y su huella.

Tampoco se guardan las medidas ni las comprobaciones. Se recalculan al
abrir la ficha: medir un PDF es determinista y rápido, y conservarlas
exigiría una tabla nueva para un dato que se puede volver a obtener. Si más
adelante hace falta el histórico de lo medido, será su propia migración con
su documento de cambio.
"""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

# Los siete del §16.1, en el orden en que ocurren.
ESTADOS: tuple[str, ...] = (
    "RECIBIDO",
    "BLOQUEADO",
    "ANALIZADO",
    "BORRADORES_GENERADOS",
    "EN_REVISION_DOCENTE",
    "APROBADO",
    "COMUNICADO",
)

ESTADO_INICIAL = "RECIBIDO"
BLOQUEADO = "BLOQUEADO"


class EntregaNueva(BaseModel):
    """Una entrega que el docente acaba de confirmar."""

    codigo_alumno: str
    ciclo: str
    fase: str
    version: int
    nombre_archivo: str
    huella: str
    version_criterios: str


class EntregaRegistrada(BaseModel):
    """Una entrega ya guardada."""

    id: str
    codigo_alumno: str
    ciclo: str
    fase: str
    version: int
    nombre_archivo: str
    huella: str
    recibida_en: datetime
    estado: str
    motivo_bloqueo: str | None
    version_criterios: str


class Almacen(Protocol):
    """Lo que cualquier almacén tiene que saber hacer.

    `es_duradero` no es un detalle: el frontend lo enseña. Un almacén que
    pierde lo guardado al cerrar es utilizable, pero el docente tiene que
    saber que lo es.
    """

    @property
    def es_duradero(self) -> bool: ...

    def registrar(self, entrega: EntregaNueva) -> EntregaRegistrada: ...

    def listar(self) -> list[EntregaRegistrada]: ...

    def por_id(self, identificador: str) -> EntregaRegistrada | None: ...

    def por_huella(self, huella: str) -> EntregaRegistrada | None: ...

    def anterior_de(
        self, codigo_alumno: str, fase: str, version: int = 1
    ) -> EntregaRegistrada | None: ...

    def cambiar_estado(
        self, identificador: str, estado: str, motivo: str | None
    ) -> EntregaRegistrada | None: ...


def validar(entrega: EntregaNueva) -> None:
    """Lo que la base de datos rechazaría, rechazado antes y con mejor aviso."""
    from backend.vigilancia.nombres import FASES

    if entrega.fase not in FASES:
        raise ValueError(
            f"«{entrega.fase}» no es una fase. Las fases son: " + ", ".join(FASES) + "."
        )
    if entrega.version < 1:
        raise ValueError("La versión de una entrega empieza en 1.")
    if not entrega.codigo_alumno.strip():
        raise ValueError("La entrega necesita el código del alumno.")


def validar_estado(estado: str, motivo: str | None) -> None:
    """El estado existe, y si es BLOQUEADO viene con su motivo."""
    if estado not in ESTADOS:
        raise ValueError(
            f"«{estado}» no es un estado del flujo. Son: " + ", ".join(ESTADOS) + "."
        )
    if estado == BLOQUEADO and not (motivo or "").strip():
        raise ValueError(
            "Bloquear una entrega exige decir el motivo: es lo que el docente "
            "leerá para saber qué pedir."
        )
```

- [ ] **Step 5: Escribir `backend/persistencia/memoria.py`**

```python
"""Almacén en memoria.

No es un doble de pruebas: es lo que corre cuando no hay credenciales de
Supabase, para que el sistema sea utilizable desde el primer minuto. Por eso
declara `es_duradero = False` y el frontend lo enseña. Un sistema que
aparenta guardar y no guarda es peor que uno que no guarda.
"""

import uuid
from datetime import datetime

from backend.persistencia.modelos import (
    ESTADO_INICIAL,
    EntregaNueva,
    EntregaRegistrada,
    validar,
    validar_estado,
)


class AlmacenEnMemoria:
    """Las entregas de esta sesión, y solo de esta sesión."""

    def __init__(self) -> None:
        self._entregas: dict[str, EntregaRegistrada] = {}

    @property
    def es_duradero(self) -> bool:
        return False

    def registrar(self, entrega: EntregaNueva) -> EntregaRegistrada:
        validar(entrega)
        ya_estaba = self.por_huella(entrega.huella)
        if ya_estaba is not None:
            # Misma huella es el mismo archivo, aunque lo hayan renombrado.
            return ya_estaba

        registrada = EntregaRegistrada(
            id=str(uuid.uuid4()),
            recibida_en=datetime.now(),
            estado=ESTADO_INICIAL,
            motivo_bloqueo=None,
            **entrega.model_dump(),
        )
        self._entregas[registrada.id] = registrada
        return registrada

    def listar(self) -> list[EntregaRegistrada]:
        return sorted(
            self._entregas.values(),
            key=lambda entrega: entrega.recibida_en,
            reverse=True,
        )

    def por_id(self, identificador: str) -> EntregaRegistrada | None:
        return self._entregas.get(identificador)

    def por_huella(self, huella: str) -> EntregaRegistrada | None:
        for entrega in self._entregas.values():
            if entrega.huella == huella:
                return entrega
        return None

    def anterior_de(
        self, codigo_alumno: str, fase: str, version: int = 1
    ) -> EntregaRegistrada | None:
        """La entrega inmediatamente anterior de ese alumno.

        Puede ser de una fase previa o una versión previa de la misma fase.
        Se elige la más reciente de las que la preceden, que es contra la que
        el docente compara.
        """
        from backend.vigilancia.nombres import FASES

        orden_actual = (FASES.index(fase), version)
        candidatas = [
            entrega
            for entrega in self._entregas.values()
            if entrega.codigo_alumno == codigo_alumno
            and (FASES.index(entrega.fase), entrega.version) < orden_actual
        ]
        if not candidatas:
            return None
        return max(candidatas, key=lambda e: (FASES.index(e.fase), e.version))

    def cambiar_estado(
        self, identificador: str, estado: str, motivo: str | None
    ) -> EntregaRegistrada | None:
        validar_estado(estado, motivo)
        entrega = self._entregas.get(identificador)
        if entrega is None:
            return None
        cambiada = entrega.model_copy(
            update={"estado": estado, "motivo_bloqueo": motivo}
        )
        self._entregas[identificador] = cambiada
        return cambiada
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/persistencia/test_memoria.py -v`
Expected: PASS, 15 tests.

- [ ] **Step 7: Commit**

```bash
git add backend/persistencia tests/persistencia
git commit -m "feat: puerto de persistencia y almacen en memoria

El almacen en memoria no es un doble de pruebas: es lo que corre cuando no
hay credenciales, para que el sistema sea utilizable desde el primer
minuto. Declara es_duradero = False y el frontend lo ensena. Un sistema
que aparenta guardar y no guarda es peor que uno que no guarda.

No se guardan ni las medidas ni las comprobaciones: se recalculan al abrir
la ficha. Medir es determinista y rapido, y conservarlas exigiria una tabla
nueva para un dato que se puede volver a obtener.

Las validaciones repiten lo que las tablas ya imponen, pero fallan antes y
con un aviso que el docente entiende."
```

---

### Task 11: Persistencia — Supabase

La misma interfaz contra las tablas reales, por PostgREST con `httpx`, que ya es dependencia. Sin cliente adicional: son cuatro llamadas HTTP y añadir una librería para eso no compensa.

`registrar` recorre tres tablas: busca o crea el alumno por su código, busca o crea el proyecto, e inserta la entrega. Las tablas tienen RLS activo sin políticas, así que solo funciona con la clave de servicio, que es lo que se pretende.

**Files:**
- Create: `backend/persistencia/supabase.py`
- Create: `tests/persistencia/test_supabase.py`

**Interfaces:**
- Consumes: los modelos y validadores de Task 10.
- Produces: `AlmacenSupabase(url: str, clave: str, cliente: httpx.Client | None = None)` que implementa `Almacen`; `ErrorDeAlmacen(Exception)`; `crear_almacen(configuracion) -> Almacen` en `backend/persistencia/__init__.py`.

- [ ] **Step 1: Escribir los tests con transporte simulado**

Crear `tests/persistencia/test_supabase.py`:

```python
"""El almacén de Supabase, contra un transporte simulado.

No se toca la base de datos real: las pruebas no deben depender de la red ni
dejar filas en un proyecto de verdad. Lo que se comprueba aquí es que se
llama a las tablas correctas, con los filtros correctos, y que un error se
convierte en un mensaje que el docente entiende.
"""

import httpx
import pytest

from backend.persistencia.modelos import EntregaNueva
from backend.persistencia.supabase import AlmacenSupabase, ErrorDeAlmacen

URL = "https://ejemplo.supabase.co"
CLAVE = "clave-de-servicio"

ALUMNO = {"id": "id-alumno", "codigo": "AF023", "ciclo": "DAM"}
PROYECTO = {"id": "id-proyecto", "alumno_id": "id-alumno",
            "version_criterios": "v2026-2027"}
ENTREGA = {
    "id": "id-entrega", "proyecto_id": "id-proyecto", "fase": "E2", "version": 1,
    "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf", "huella_archivo": "a" * 64,
    "recibida_en": "2026-08-27T10:00:00+00:00", "estado": "RECIBIDO",
    "motivo_bloqueo": None, "version_criterios": "v2026-2027",
}


def _entrega() -> EntregaNueva:
    return EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        version_criterios="v2026-2027",
    )


def _almacen(responder) -> AlmacenSupabase:
    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    return AlmacenSupabase(URL, CLAVE, cliente=cliente)


def test_registrar_reutiliza_el_alumno_existente() -> None:
    llamadas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        if peticion.url.path.endswith("/alumno"):
            return httpx.Response(200, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            return httpx.Response(200, json=[PROYECTO])
        # La huella no está registrada: hay que insertar de verdad.
        if peticion.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[ENTREGA])

    registrada = _almacen(responder).registrar(_entrega())

    assert registrada.id == "id-entrega"
    assert registrada.codigo_alumno == "AF023"
    assert "POST /rest/v1/alumno" not in llamadas
    assert "POST /rest/v1/entrega" in llamadas


def test_registrar_crea_el_alumno_si_no_existe() -> None:
    llamadas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        llamadas.append(f"{peticion.method} {peticion.url.path}")
        if peticion.url.path.endswith("/alumno"):
            if peticion.method == "GET":
                return httpx.Response(200, json=[])
            return httpx.Response(201, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            if peticion.method == "GET":
                return httpx.Response(200, json=[])
            return httpx.Response(201, json=[PROYECTO])
        if peticion.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[ENTREGA])

    _almacen(responder).registrar(_entrega())

    assert "POST /rest/v1/alumno" in llamadas
    assert "POST /rest/v1/proyecto" in llamadas


def test_lleva_la_clave_en_las_cabeceras() -> None:
    vistas: dict[str, str] = {}

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.update(peticion.headers)
        return httpx.Response(200, json=[])

    _almacen(responder).listar()

    assert vistas["apikey"] == CLAVE
    assert vistas["authorization"] == f"Bearer {CLAVE}"


def test_no_envia_el_texto_del_trabajo() -> None:
    """D-001: ni el PDF ni el texto salen hacia la base de datos."""
    cuerpos: list[bytes] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        cuerpos.append(peticion.content)
        if peticion.url.path.endswith("/alumno"):
            return httpx.Response(200, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            return httpx.Response(200, json=[PROYECTO])
        if peticion.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[ENTREGA])

    _almacen(responder).registrar(_entrega())

    enviado = b"".join(cuerpos).decode()
    assert "texto_plano" not in enviado
    assert "%PDF" not in enviado


def test_una_huella_ya_conocida_no_se_duplica() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path.endswith("/entrega") and peticion.method == "GET":
            return httpx.Response(200, json=[ENTREGA])
        if peticion.url.path.endswith("/alumno"):
            return httpx.Response(200, json=[ALUMNO])
        if peticion.url.path.endswith("/proyecto"):
            return httpx.Response(200, json=[PROYECTO])
        raise AssertionError("no debería insertar")

    registrada = _almacen(responder).registrar(_entrega())

    assert registrada.id == "id-entrega"


def test_la_consulta_fuerza_el_cruce_interno() -> None:
    """Sin `!inner`, PostgREST no filtra la tabla raíz.

    Un filtro sobre un recurso embebido sin cruce interno devuelve TODAS las
    filas de la raíz, con el embebido a null en las que no casan. Es decir:
    devolvería las entregas de todos los alumnos. Se comprueba en la petición
    porque contra un transporte simulado no hay servidor que lo demuestre.
    """
    vistas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(str(peticion.url))
        return httpx.Response(200, json=[])

    _almacen(responder).listar()

    assert "proyecto!inner" in vistas[0]
    assert "alumno!inner" in vistas[0]


def test_un_error_del_servidor_se_traduce() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    with pytest.raises(ErrorDeAlmacen) as fallo:
        _almacen(responder).listar()

    assert "Supabase" in str(fallo.value)
    assert "401" in str(fallo.value)


def test_sin_red_el_error_lo_dice() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(ErrorDeAlmacen) as fallo:
        _almacen(responder).listar()

    assert "conectar" in str(fallo.value).lower()


def test_cambiar_estado_manda_un_patch() -> None:
    vistos: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistos.append(peticion.method)
        return httpx.Response(200, json=[{**ENTREGA, "estado": "ANALIZADO"}])

    cambiada = _almacen(responder).cambiar_estado("id-entrega", "ANALIZADO", None)

    assert vistos == ["PATCH"]
    assert cambiada is not None
    assert cambiada.estado == "ANALIZADO"


def test_bloquear_sin_motivo_se_rechaza_antes_de_la_red() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        raise AssertionError("no debería llegar a la red")

    with pytest.raises(ValueError, match="motivo"):
        _almacen(responder).cambiar_estado("id-entrega", "BLOQUEADO", None)


def test_el_almacen_de_supabase_es_duradero() -> None:
    assert _almacen(lambda p: httpx.Response(200, json=[])).es_duradero is True
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/persistencia/test_supabase.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.persistencia.supabase'`

- [ ] **Step 3: Escribir `backend/persistencia/supabase.py`**

```python
"""El almacén contra las tablas reales, por PostgREST.

Se usa httpx directamente y no un cliente de Supabase: son cuatro llamadas
HTTP con dos cabeceras, y añadir una dependencia para eso solo traería su
propio ciclo de versiones.

Las tablas tienen RLS activo y ninguna política, así que esto solo funciona
con la clave de servicio. Es lo que se pretende mientras no esté decidido
cómo se autentica el docente: es preferible que no entre nadie a que entre
cualquiera.
"""

from datetime import datetime

import httpx

from backend.persistencia.modelos import (
    EntregaNueva,
    EntregaRegistrada,
    validar,
    validar_estado,
)

ESPERA = 15.0


class ErrorDeAlmacen(Exception):
    """No se ha podido hablar con la base de datos."""


class AlmacenSupabase:
    """Las nueve tablas, vistas por las tres que esta parte usa."""

    def __init__(
        self, url: str, clave: str, cliente: httpx.Client | None = None
    ) -> None:
        self._base = url.rstrip("/") + "/rest/v1"
        self._cliente = cliente or httpx.Client(timeout=ESPERA)
        self._cabeceras = {
            "apikey": clave,
            "Authorization": f"Bearer {clave}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    @property
    def es_duradero(self) -> bool:
        return True

    def _pedir(self, metodo: str, tabla: str, **extras) -> list[dict]:
        try:
            respuesta = self._cliente.request(
                metodo, f"{self._base}/{tabla}", headers=self._cabeceras, **extras
            )
        except httpx.HTTPError as fallo:
            raise ErrorDeAlmacen(
                "No se ha podido conectar con Supabase. Comprueba la conexión "
                "y que SUPABASE_URL es correcta."
            ) from fallo
        if respuesta.status_code >= 400:
            raise ErrorDeAlmacen(
                f"Supabase ha respondido {respuesta.status_code} al acceder a "
                f"«{tabla}»: {respuesta.text[:300]}"
            )
        cuerpo = respuesta.json()
        return cuerpo if isinstance(cuerpo, list) else [cuerpo]

    def _uno(self, tabla: str, **filtros) -> dict | None:
        filas = self._pedir(
            "GET", tabla, params={**filtros, "select": "*", "limit": "1"}
        )
        return filas[0] if filas else None

    def _alumno(self, codigo: str, ciclo: str) -> str:
        existente = self._uno("alumno", codigo=f"eq.{codigo}")
        if existente:
            return existente["id"]
        creado = self._pedir(
            "POST", "alumno", json={"codigo": codigo, "ciclo": ciclo}
        )
        return creado[0]["id"]

    def _proyecto(self, alumno_id: str, version_criterios: str) -> str:
        existente = self._uno(
            "proyecto",
            alumno_id=f"eq.{alumno_id}",
            version_criterios=f"eq.{version_criterios}",
        )
        if existente:
            return existente["id"]
        creado = self._pedir("POST", "proyecto", json={
            "alumno_id": alumno_id, "version_criterios": version_criterios,
        })
        return creado[0]["id"]

    def _componer(self, fila: dict) -> EntregaRegistrada:
        """Una fila de `entrega` más su alumno, tal como la usa el sistema."""
        alumno = fila.get("alumno") or {}
        return EntregaRegistrada(
            id=fila["id"],
            codigo_alumno=alumno.get("codigo", ""),
            ciclo=alumno.get("ciclo", ""),
            fase=fila["fase"],
            version=fila["version"],
            nombre_archivo=fila.get("nombre_archivo") or "",
            huella=fila.get("huella_archivo") or "",
            recibida_en=datetime.fromisoformat(fila["recibida_en"]),
            estado=fila["estado"],
            motivo_bloqueo=fila.get("motivo_bloqueo"),
            version_criterios=fila["version_criterios"],
        )

    # PostgREST devuelve el alumno anidado atravesando las dos claves ajenas:
    # así se lee la entrega y su código de alumno en una sola llamada.
    #
    # El `!inner` no es opcional. Sin él, un filtro sobre un recurso embebido
    # no filtra la tabla raíz: devuelve TODAS las entregas, con el embebido a
    # null en las que no casan. En anterior_de eso significaría traerse las
    # entregas de todos los alumnos. Como toda entrega tiene proyecto y todo
    # proyecto tiene alumno —ambas claves son NOT NULL—, el cruce interno no
    # descarta ninguna fila legítima.
    SELECCION = "*,proyecto!inner(alumno!inner(codigo,ciclo))"

    def _aplanar(self, fila: dict) -> dict:
        anidado = (fila.get("proyecto") or {}).get("alumno") or {}
        return {**fila, "alumno": anidado}

    def registrar(self, entrega: EntregaNueva) -> EntregaRegistrada:
        validar(entrega)
        ya_estaba = self.por_huella(entrega.huella)
        if ya_estaba is not None:
            return ya_estaba

        alumno_id = self._alumno(entrega.codigo_alumno, entrega.ciclo)
        proyecto_id = self._proyecto(alumno_id, entrega.version_criterios)
        filas = self._pedir("POST", "entrega", json={
            "proyecto_id": proyecto_id,
            "fase": entrega.fase,
            "version": entrega.version,
            "nombre_archivo": entrega.nombre_archivo,
            "huella_archivo": entrega.huella,
            "version_criterios": entrega.version_criterios,
        })
        fila = filas[0]
        fila["alumno"] = {"codigo": entrega.codigo_alumno, "ciclo": entrega.ciclo}
        return self._componer(fila)

    def listar(self) -> list[EntregaRegistrada]:
        filas = self._pedir("GET", "entrega", params={
            "select": self.SELECCION, "order": "recibida_en.desc",
        })
        return [self._componer(self._aplanar(fila)) for fila in filas]

    def por_id(self, identificador: str) -> EntregaRegistrada | None:
        filas = self._pedir("GET", "entrega", params={
            "id": f"eq.{identificador}", "select": self.SELECCION, "limit": "1",
        })
        return self._componer(self._aplanar(filas[0])) if filas else None

    def por_huella(self, huella: str) -> EntregaRegistrada | None:
        filas = self._pedir("GET", "entrega", params={
            "huella_archivo": f"eq.{huella}", "select": self.SELECCION, "limit": "1",
        })
        return self._componer(self._aplanar(filas[0])) if filas else None

    def anterior_de(
        self, codigo_alumno: str, fase: str, version: int = 1
    ) -> EntregaRegistrada | None:
        """La más reciente de las entregas que preceden a esta.

        El orden de fases no es alfabético ni cronológico, así que el
        filtrado se hace aquí y no en la consulta: son pocas entregas por
        alumno y la alternativa sería codificar el orden de las fases dentro
        de una cadena de consulta.
        """
        from backend.vigilancia.nombres import FASES

        filas = self._pedir("GET", "entrega", params={
            "select": self.SELECCION,
            "proyecto.alumno.codigo": f"eq.{codigo_alumno}",
        })
        candidatas = [
            self._componer(self._aplanar(fila)) for fila in filas
        ]
        orden_actual = (FASES.index(fase), version)
        previas = [
            entrega for entrega in candidatas
            if entrega.codigo_alumno == codigo_alumno
            and entrega.fase in FASES
            and (FASES.index(entrega.fase), entrega.version) < orden_actual
        ]
        if not previas:
            return None
        return max(previas, key=lambda e: (FASES.index(e.fase), e.version))

    def cambiar_estado(
        self, identificador: str, estado: str, motivo: str | None
    ) -> EntregaRegistrada | None:
        validar_estado(estado, motivo)
        filas = self._pedir(
            "PATCH", "entrega",
            params={"id": f"eq.{identificador}"},
            json={"estado": estado, "motivo_bloqueo": motivo},
        )
        return self._componer(self._aplanar(filas[0])) if filas else None
```

- [ ] **Step 4: Añadir `crear_almacen` a `backend/persistencia/__init__.py`**

Reemplazar el contenido:

```python
"""Dónde se guarda la ficha de una entrega. El puerto y sus dos almacenes."""

from backend.persistencia.modelos import Almacen


def crear_almacen(configuracion) -> Almacen:
    """Supabase si hay credenciales; memoria si no.

    No se falla por falta de credenciales: el sistema arranca igual y avisa
    de que lo guardado se pierde al cerrar. Quien está probando la lectura
    de un PDF no debería necesitar una base de datos, y quien corrige de
    verdad verá el aviso.
    """
    from backend.persistencia.memoria import AlmacenEnMemoria

    if configuracion.url_supabase and configuracion.clave_supabase:
        from backend.persistencia.supabase import AlmacenSupabase

        return AlmacenSupabase(
            configuracion.url_supabase, configuracion.clave_supabase
        )
    return AlmacenEnMemoria()
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/persistencia -v`
Expected: PASS, 25 tests.

- [ ] **Step 6: Ejecutar la batería completa**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`
Expected: todo en verde.

- [ ] **Step 7: Commit**

```bash
git add backend/persistencia tests/persistencia
git commit -m "feat: almacen de Supabase por PostgREST

Se usa httpx directamente y no un cliente de Supabase: son cuatro llamadas
HTTP con dos cabeceras, y anadir una dependencia para eso solo traeria su
propio ciclo de versiones.

Las pruebas van contra un transporte simulado: no tocan la base de datos
real, no dependen de la red y no dejan filas en un proyecto de verdad. Una
de ellas comprueba lo que D-001 exige, que ni el PDF ni el texto salgan
hacia la base de datos.

Sin credenciales se usa el almacen en memoria y se avisa. Quien esta
probando la lectura de un PDF no deberia necesitar una base de datos."
```
---

### Task 12: El servicio de lectura objetiva y su API

Lo que une las seis piezas anteriores: mirar la carpeta, medir un archivo, comprobarlo contra los criterios, compararlo con la entrega anterior y registrarlo. Y los endpoints que el frontend consume.

**La comparación evolutiva necesita el PDF anterior.** Como no se guarda ni el archivo ni su texto (D-001), se vuelve a medir el archivo anterior desde la carpeta. Si ya no está, la comparación no se hace y se dice: es la condición del §18.2 sobre continuar sin el material anterior.

**Files:**
- Create: `backend/servicios/lectura_objetiva.py`
- Create: `backend/api/entregas.py`
- Modify: `backend/app.py` (registrar el router y guardar configuración y almacén en `app.state`)
- Modify: `backend/__main__.py` (avisar por consola de lo que falte)
- Create: `tests/backend/test_lectura_objetiva.py`
- Create: `tests/backend/test_api_entregas.py`

**Interfaces:**
- Consumes: `medir` (Task 6), `comprobar` (Task 7), `comparar` (Task 8), `mirar`/`deducir` (Task 9), `Almacen`/`crear_almacen` (Tasks 10-11), `cargar` (Task 1).
- Produces:
  - `FichaDeLectura(BaseModel)` con `entrega: EntregaRegistrada`, `medidas: Medidas | None`, `comprobaciones: list[Comprobacion]`, `evolucion: Evolucion | None`, `comparada_con: str | None`, `aviso: str = ""`.
  - `leer(raiz, carpeta, version_criterios, almacen, entrega) -> FichaDeLectura`
  - `localizar(carpeta: Path, nombre: str) -> Path | None` — pública porque la usa `api/entregas.py`.
  - `crear_app(raiz, configuracion=None, almacen=None)` con la firma ampliada y compatible.

- [ ] **Step 1: Escribir los tests del servicio**

Crear `tests/backend/test_lectura_objetiva.py`:

```python
"""El servicio que une medición, criterios y comparación."""

from pathlib import Path

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva
from backend.servicios.lectura_objetiva import leer

# `criterios_de_formato` y los PDF vienen de tests/conftest.py.


@pytest.fixture
def entregas(tmp_path: Path) -> Path:
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    return carpeta


def _registrar(almacen, carpeta: Path, origen: Path, fase: str, version: int = 1):
    """Copia el PDF a la carpeta de entregas con nombre de convención."""
    destino = carpeta / f"AF023_DAM_{fase}_20260115_v{version}.pdf"
    destino.write_bytes(origen.read_bytes())
    from backend.extraccion import medir

    return almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase=fase, version=version,
        nombre_archivo=destino.name, huella=medir(destino).huella,
        version_criterios="v2026-2027",
    ))


def test_la_ficha_trae_las_medidas(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.medidas is not None
    assert ficha.medidas.total_paginas == 7


def test_la_ficha_trae_las_comprobaciones(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert len(ficha.comprobaciones) == 9


def test_sin_entrega_anterior_no_hay_comparacion(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "TEMA")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is None
    assert ficha.comparada_con is None
    assert ficha.aviso == ""


def test_con_entrega_anterior_se_compara(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    _registrar(almacen, entregas, pdf_con_indice, "E1")
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is not None
    assert ficha.comparada_con == "AF023_DAM_E1_20260115_v1.pdf"


def test_si_el_archivo_anterior_ya_no_esta_se_dice(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    """§18.2: sin el material anterior no se compara, y se avisa."""
    almacen = AlmacenEnMemoria()
    anterior = _registrar(almacen, entregas, pdf_con_indice, "E1")
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    (entregas / anterior.nombre_archivo).unlink()

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.evolucion is None
    assert "ya no está en la carpeta" in ficha.aviso


def test_un_archivo_que_desaparecio_bloquea_la_entrega(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    (entregas / entrega.nombre_archivo).unlink()

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.medidas is None
    assert ficha.entrega.estado == "BLOQUEADO"
    assert ficha.entrega.motivo_bloqueo is not None


def test_un_pdf_ilegible_bloquea_la_entrega(criterios_de_formato: Path, entregas: Path) -> None:
    almacen = AlmacenEnMemoria()
    roto = entregas / "AF023_DAM_E2_20260115_v1.pdf"
    roto.write_text("esto no es un PDF", encoding="utf-8")
    entrega = almacen.registrar(EntregaNueva(
        codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo=roto.name, huella="a" * 64, version_criterios="v2026-2027",
    ))

    ficha = leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ficha.entrega.estado == "BLOQUEADO"
    assert "no se ha podido abrir" in ficha.entrega.motivo_bloqueo.lower()
    assert ficha.comprobaciones == []


def test_leer_no_modifica_el_archivo(criterios_de_formato: Path, entregas: Path, pdf_con_indice: Path) -> None:
    almacen = AlmacenEnMemoria()
    entrega = _registrar(almacen, entregas, pdf_con_indice, "E2")
    ruta = entregas / entrega.nombre_archivo
    antes = ruta.read_bytes()

    leer(criterios_de_formato, entregas, "v2026-2027", almacen, entrega)

    assert ruta.read_bytes() == antes
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/backend/test_lectura_objetiva.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backend.servicios.lectura_objetiva'`

- [ ] **Step 3: Escribir `backend/servicios/lectura_objetiva.py`**

```python
"""La lectura objetiva de una entrega, de principio a fin.

Une las seis piezas y no añade criterio propio: mide, contrasta con los
criterios, compara con la anterior y devuelve la ficha. No valora, no
puntúa y no redacta nada para el alumno; eso es la segunda parte del flujo.

La comparación evolutiva vuelve a medir el archivo anterior desde la
carpeta. No se guarda ni el PDF ni su texto —lo fija D-001—, así que la
única forma de comparar es que el archivo anterior siga donde estaba. Si no
está, no se compara y se dice: el §18.2 no admite seguir como si nada
cuando falta el material anterior.
"""

from pathlib import Path

from pydantic import BaseModel

from backend.evolucion.comparacion import Evolucion, comparar
from backend.extraccion import medir
from backend.extraccion.lectura import PdfIlegible
from backend.extraccion.medidas import Medidas
from backend.formato.comprobacion import Comprobacion, comprobar
from backend.persistencia.modelos import Almacen, EntregaRegistrada


class FichaDeLectura(BaseModel):
    """Todo lo objetivo que se sabe de una entrega.

    `medidas` es `None` cuando el archivo no se ha podido leer. En ese caso
    la entrega queda en BLOQUEADO con su motivo, que es una salida prevista
    del §18.2 y no un fallo del sistema.
    """

    entrega: EntregaRegistrada
    medidas: Medidas | None = None
    comprobaciones: list[Comprobacion] = []
    evolucion: Evolucion | None = None
    comparada_con: str | None = None
    aviso: str = ""


def _bloquear(almacen: Almacen, entrega: EntregaRegistrada, motivo: str) -> FichaDeLectura:
    bloqueada = almacen.cambiar_estado(entrega.id, "BLOQUEADO", motivo) or entrega
    return FichaDeLectura(entrega=bloqueada)


def leer(
    raiz: Path,
    carpeta: Path,
    version_criterios: str,
    almacen: Almacen,
    entrega: EntregaRegistrada,
) -> FichaDeLectura:
    """Mide la entrega, la contrasta con los criterios y la compara."""
    ruta = localizar(carpeta, entrega.nombre_archivo)
    if ruta is None:
        return _bloquear(
            almacen, entrega,
            f"El archivo «{entrega.nombre_archivo}» ya no está en la carpeta "
            "de entregas. Vuelve a dejarlo donde estaba o corrige la ficha.",
        )

    try:
        medidas = medir(ruta)
    except PdfIlegible as fallo:
        return _bloquear(almacen, entrega, str(fallo))

    ficha = FichaDeLectura(
        entrega=entrega,
        medidas=medidas,
        comprobaciones=comprobar(raiz, version_criterios, medidas),
    )

    anterior = almacen.anterior_de(
        entrega.codigo_alumno, entrega.fase, entrega.version
    )
    if anterior is None:
        return ficha

    ruta_anterior = localizar(carpeta, anterior.nombre_archivo)
    if ruta_anterior is None:
        ficha.aviso = (
            f"No se ha comparado con la entrega anterior: el archivo "
            f"«{anterior.nombre_archivo}» ya no está en la carpeta. Devuélvelo "
            "y vuelve a abrir la ficha, o sigue sin comparación sabiendo que "
            "no se comprueba el progreso."
        )
        return ficha

    try:
        texto_anterior = medir(ruta_anterior).texto_plano
    except PdfIlegible as fallo:
        ficha.aviso = f"No se ha comparado con la entrega anterior: {fallo}"
        return ficha

    ficha.evolucion = comparar(texto_anterior, medidas.texto_plano)
    ficha.comparada_con = anterior.nombre_archivo
    return ficha


def localizar(carpeta: Path, nombre: str) -> Path | None:
    """Busca el archivo por nombre, también dentro de las subcarpetas."""
    directo = carpeta / nombre
    if directo.is_file():
        return directo
    return next((ruta for ruta in carpeta.rglob(nombre) if ruta.is_file()), None)
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/backend/test_lectura_objetiva.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Escribir los tests de la API**

Crear `tests/backend/test_api_entregas.py`:

```python
"""Los endpoints de entregas."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import crear_app
from backend.configuracion import Configuracion
from backend.persistencia.memoria import AlmacenEnMemoria

# `criterios_de_formato` y los PDF vienen de tests/conftest.py.


@pytest.fixture
def cliente(criterios_de_formato: Path, tmp_path: Path, pdf_con_indice: Path):
    raiz = criterios_de_formato

    entregas = tmp_path / "entregas"
    entregas.mkdir()
    (entregas / "AF023_DAM_E2_20260115_v1.pdf").write_bytes(pdf_con_indice.read_bytes())
    (entregas / "cosa rara.pdf").write_bytes(pdf_con_indice.read_bytes())

    app = crear_app(
        raiz,
        configuracion=Configuracion(
            carpeta_entregas=entregas, version_criterios="v2026-2027"
        ),
        almacen=AlmacenEnMemoria(),
    )
    return TestClient(app)


def test_pendientes_devuelve_los_archivos_sin_registrar(cliente) -> None:
    respuesta = cliente.get("/api/entregas/pendientes")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 2


def test_pendientes_marca_cual_se_puede_confirmar_de_un_clic(cliente) -> None:
    pendientes = cliente.get("/api/entregas/pendientes").json()

    por_nombre = {p["nombre"]: p for p in pendientes}
    assert por_nombre["AF023_DAM_E2_20260115_v1.pdf"]["propuesta"]["completa"] is True
    assert por_nombre["cosa rara.pdf"]["propuesta"]["completa"] is False
    assert por_nombre["cosa rara.pdf"]["propuesta"]["motivo"]


def test_confirmar_registra_la_entrega(cliente) -> None:
    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert respuesta.status_code == 200
    assert respuesta.json()["entrega"]["estado"] == "RECIBIDO"
    assert respuesta.json()["medidas"]["total_paginas"] == 7


def test_lo_registrado_desaparece_de_pendientes(cliente) -> None:
    cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    pendientes = cliente.get("/api/entregas/pendientes").json()

    assert [p["nombre"] for p in pendientes] == ["cosa rara.pdf"]


def test_confirmar_un_archivo_que_no_esta_da_404(cliente) -> None:
    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "fantasma.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert respuesta.status_code == 404
    assert "fantasma.pdf" in respuesta.json()["detail"]


def test_una_fase_desconocida_da_400_con_motivo(cliente) -> None:
    respuesta = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E9", "version": 1,
    })

    assert respuesta.status_code == 400
    assert "no es una fase" in respuesta.json()["detail"]


def test_la_ficha_se_recupera_por_su_identificador(cliente) -> None:
    creada = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.get(f"/api/entregas/{creada['entrega']['id']}")

    assert respuesta.status_code == 200
    assert len(respuesta.json()["comprobaciones"]) == 9


def test_una_ficha_inexistente_da_404(cliente) -> None:
    assert cliente.get("/api/entregas/no-existe").status_code == 404


def test_listar_devuelve_lo_registrado(cliente) -> None:
    cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    })

    assert len(cliente.get("/api/entregas").json()) == 1


def test_cambiar_de_estado(cliente) -> None:
    creada = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{creada['entrega']['id']}/estado",
        json={"estado": "BLOQUEADO", "motivo": "Falta la portada."},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "BLOQUEADO"


def test_bloquear_sin_motivo_da_400(cliente) -> None:
    creada = cliente.post("/api/entregas", json={
        "nombre_archivo": "AF023_DAM_E2_20260115_v1.pdf",
        "codigo_alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": 1,
    }).json()

    respuesta = cliente.post(
        f"/api/entregas/{creada['entrega']['id']}/estado",
        json={"estado": "BLOQUEADO", "motivo": ""},
    )

    assert respuesta.status_code == 400
    assert "motivo" in respuesta.json()["detail"]


def test_el_entorno_avisa_de_que_no_se_guarda(cliente) -> None:
    """El almacén en memoria pierde lo guardado, y el docente ha de saberlo."""
    entorno = cliente.get("/api/entorno").json()

    assert entorno["persistencia_duradera"] is False
    assert entorno["hay_carpeta"] is True
    assert entorno["avisos"]


def test_sin_carpeta_los_pendientes_estan_vacios(tmp_path: Path) -> None:
    app = crear_app(
        tmp_path, configuracion=Configuracion(), almacen=AlmacenEnMemoria()
    )
    cliente = TestClient(app)

    assert cliente.get("/api/entregas/pendientes").json() == []
    assert cliente.get("/api/entorno").json()["hay_carpeta"] is False


def test_el_editor_de_criterios_sigue_funcionando(cliente) -> None:
    """La app es una sola: añadir entregas no rompe lo que ya había."""
    assert cliente.get("/api/salud").status_code == 200
```

- [ ] **Step 6: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/backend/test_api_entregas.py -v`
Expected: FAIL — `crear_app()` no acepta `configuracion`.

- [ ] **Step 7: Escribir `backend/api/entregas.py`**

```python
"""Endpoints del flujo de entregas.

Todo lo que devuelven es interno y provisional. Ningún endpoint aprueba
nada, califica nada ni comunica nada al alumno: el §13 reserva eso al
profesor, y la forma de respetarlo es que las operaciones no existan.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.configuracion import Configuracion
from backend.persistencia.modelos import Almacen, EntregaNueva, EntregaRegistrada
from backend.servicios.lectura_objetiva import FichaDeLectura, leer
from backend.vigilancia.carpeta import ArchivoVisto, mirar

router = APIRouter(prefix="/api")


class Confirmacion(BaseModel):
    """Lo que el docente confirma de un archivo pendiente."""

    nombre_archivo: str
    codigo_alumno: str
    ciclo: str
    fase: str
    version: int = 1


class CambioDeEstado(BaseModel):
    estado: str
    motivo: str | None = None


class Entorno(BaseModel):
    """Lo que el frontend necesita saber para avisar al docente."""

    hay_carpeta: bool
    carpeta: str | None
    persistencia_duradera: bool
    version_criterios: str
    avisos: list[str]


def _raiz(peticion: Request) -> Path:
    return peticion.app.state.raiz


def _configuracion(peticion: Request) -> Configuracion:
    return peticion.app.state.configuracion


def _almacen(peticion: Request) -> Almacen:
    return peticion.app.state.almacen


@router.get("/entorno")
def obtener_entorno(peticion: Request) -> Entorno:
    configuracion = _configuracion(peticion)
    almacen = _almacen(peticion)

    avisos = []
    if configuracion.carpeta_entregas is None:
        avisos.append(
            "No hay carpeta de entregas configurada, así que no se vigila "
            "ninguna. Indícala en REVISOR_CARPETA_ENTREGAS, en el fichero .env, "
            "y tiene que estar fuera de este repositorio."
        )
    if not almacen.es_duradero:
        avisos.append(
            "No hay credenciales de Supabase: lo que registres vive solo "
            "mientras el programa esté abierto y se pierde al cerrarlo."
        )

    return Entorno(
        hay_carpeta=configuracion.carpeta_entregas is not None,
        carpeta=str(configuracion.carpeta_entregas)
                if configuracion.carpeta_entregas else None,
        persistencia_duradera=almacen.es_duradero,
        version_criterios=configuracion.version_criterios,
        avisos=avisos,
    )


@router.get("/entregas/pendientes")
def obtener_pendientes(peticion: Request) -> list[ArchivoVisto]:
    """Los archivos de la carpeta que aún no se han confirmado."""
    carpeta = _configuracion(peticion).carpeta_entregas
    if carpeta is None:
        return []
    registrados = {
        entrega.nombre_archivo for entrega in _almacen(peticion).listar()
    }
    return mirar(carpeta, registrados)


@router.get("/entregas")
def obtener_entregas(peticion: Request) -> list[EntregaRegistrada]:
    return _almacen(peticion).listar()


@router.post("/entregas")
def confirmar(cuerpo: Confirmacion, peticion: Request) -> FichaDeLectura:
    """El docente confirma de quién y de qué fase es el archivo.

    Esta es la decisión que D-009 le reserva. El sistema propuso; aquí se
    registra lo que él dice, no lo que se dedujo.
    """
    from backend.extraccion import medir
    from backend.extraccion.lectura import PdfIlegible
    from backend.servicios.lectura_objetiva import localizar

    configuracion = _configuracion(peticion)
    if configuracion.carpeta_entregas is None:
        raise HTTPException(
            status_code=409,
            detail="No hay carpeta de entregas configurada.",
        )

    ruta = localizar(configuracion.carpeta_entregas, cuerpo.nombre_archivo)
    if ruta is None:
        raise HTTPException(
            status_code=404,
            detail=f"«{cuerpo.nombre_archivo}» no está en la carpeta de entregas.",
        )

    try:
        huella = medir(ruta).huella
    except PdfIlegible as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo

    almacen = _almacen(peticion)
    try:
        entrega = almacen.registrar(EntregaNueva(
            codigo_alumno=cuerpo.codigo_alumno.strip().upper(),
            ciclo=cuerpo.ciclo.strip().upper(),
            fase=cuerpo.fase.strip().upper(),
            version=cuerpo.version,
            nombre_archivo=ruta.name,
            huella=huella,
            version_criterios=configuracion.version_criterios,
        ))
    except ValueError as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo

    return leer(
        _raiz(peticion), configuracion.carpeta_entregas,
        configuracion.version_criterios, almacen, entrega,
    )


@router.get("/entregas/{identificador}")
def obtener_ficha(identificador: str, peticion: Request) -> FichaDeLectura:
    """La ficha completa. Las medidas se recalculan, no se guardan."""
    almacen = _almacen(peticion)
    entrega = almacen.por_id(identificador)
    if entrega is None:
        raise HTTPException(
            status_code=404, detail="No existe esa entrega."
        )
    configuracion = _configuracion(peticion)
    if configuracion.carpeta_entregas is None:
        raise HTTPException(
            status_code=409, detail="No hay carpeta de entregas configurada."
        )
    return leer(
        _raiz(peticion), configuracion.carpeta_entregas,
        configuracion.version_criterios, almacen, entrega,
    )


@router.post("/entregas/{identificador}/estado")
def cambiar_estado(
    identificador: str, cuerpo: CambioDeEstado, peticion: Request
) -> EntregaRegistrada:
    try:
        cambiada = _almacen(peticion).cambiar_estado(
            identificador, cuerpo.estado, cuerpo.motivo
        )
    except ValueError as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo
    if cambiada is None:
        raise HTTPException(status_code=404, detail="No existe esa entrega.")
    return cambiada
```

- [ ] **Step 8: Modificar `backend/app.py`**

Reemplazar la función `crear_app` conservando la firma antigua:

```python
def crear_app(raiz: Path, configuracion=None, almacen=None) -> FastAPI:
    """Crea la aplicación atada a una raíz de repositorio concreta.

    `configuracion` y `almacen` se inyectan en las pruebas. En uso normal se
    cargan del entorno, y si no hay credenciales el almacén es el de
    memoria: el sistema arranca igual y lo avisa por la interfaz.
    """
    from backend.api import documentos, edicion, entregas, estado
    from backend.configuracion import cargar
    from backend.persistencia import crear_almacen

    app = FastAPI(title="Revisor de proyectos", docs_url=None, redoc_url=None)
    app.state.raiz = raiz
    app.state.configuracion = configuracion or cargar(raiz)
    app.state.almacen = almacen or crear_almacen(app.state.configuracion)

    app.include_router(documentos.router)
    app.include_router(edicion.router)
    app.include_router(estado.router)
    app.include_router(entregas.router)

    @app.get("/api/salud")
    def salud() -> dict[str, str]:
        return {"estado": "vivo", "raiz": str(raiz)}

    # El front compilado se sirve desde el propio backend: una sola pieza
    # que arrancar, no dos.
    dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if dist.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app
```

- [ ] **Step 9: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/backend/test_api_entregas.py -v`
Expected: PASS, 14 tests.

- [ ] **Step 10: Avisar por consola al arrancar**

En `backend/__main__.py`, antes de arrancar uvicorn, añadir:

```python
def _avisar(raiz: Path) -> None:
    """Dice por consola lo que falta, antes de que el docente lo descubra."""
    from backend.configuracion import cargar

    configuracion = cargar(raiz)
    if configuracion.carpeta_entregas is None:
        print(
            "AVISO: no hay carpeta de entregas configurada. Indícala en "
            "REVISOR_CARPETA_ENTREGAS, dentro del fichero .env, y ha de estar "
            "fuera de este repositorio."
        )
    if not (configuracion.url_supabase and configuracion.clave_supabase):
        print(
            "AVISO: sin credenciales de Supabase. Lo que registres se pierde "
            "al cerrar el programa."
        )
```

Y llamarlo desde donde se construye la aplicación, junto a la comprobación del puerto que ya existe.

- [ ] **Step 11: Ejecutar la batería completa**

Run: `python -m pytest -q && python tools/verificar_gobernanza.py`
Expected: todo en verde.

- [ ] **Step 12: Commit**

```bash
git add backend tests
git commit -m "feat: servicio de lectura objetiva y su API

Une las seis piezas y no anade criterio propio: mide, contrasta con los
criterios, compara con la anterior y devuelve la ficha. No valora, no
puntua y no redacta nada para el alumno.

La comparacion evolutiva vuelve a medir el archivo anterior desde la
carpeta, porque no se guarda ni el PDF ni su texto. Si el anterior ya no
esta, no se compara y se dice: el 18.2 no admite seguir como si nada
cuando falta el material anterior.

Ningun endpoint aprueba, califica ni comunica. El 13 reserva eso al
profesor, y la forma de respetarlo es que las operaciones no existan."
```
---

### Task 13: Frontend — la bandeja de entregas

La pantalla donde el docente ve lo que ha llegado y confirma de quién es. Es D-009 tal como él la vive: una lista, y en cada archivo o un botón de confirmar o un formulario corto con el motivo de por qué no se dedujo.

**Sobre el color.** El repositorio tiene una sola tinta, `senal`, y hasta ahora estaba reservada a la relación entre una sección y los criterios que dependen de ella. En estas pantallas señala **lo que espera una decisión del docente**: una propuesta que no se ha podido deducir, y una comprobación que no cumple. Es el mismo principio —marcar lo único que el ojo no deduce solo— y sigue sin decorar nada. No se usa para títulos, bordes, ni estados normales.

**Files:**
- Modify: `frontend/src/lib/tipos.ts` (añadir los tipos del flujo)
- Modify: `frontend/src/lib/api.ts` (añadir las llamadas)
- Create: `frontend/src/paginas/Entregas.tsx`
- Create: `frontend/src/componentes/ArchivoPendiente.tsx`
- Create: `frontend/src/componentes/ArchivoPendiente.test.tsx`
- Create: `frontend/src/paginas/Entregas.test.tsx`
- Modify: `frontend/src/App.tsx` (añadir la pestaña y el aviso de entorno)

**Interfaces:**
- Consumes: los endpoints de Task 12.
- Produces: `Entregas` y `ArchivoPendiente` como componentes con nombre; los tipos `Propuesta` (renombrado a `PropuestaArchivo` para no chocar con el `Propuesta` del editor), `ArchivoVisto`, `EntregaRegistrada`, `Comprobacion`, `FichaDeLectura`, `Entorno`.

- [ ] **Step 1: Añadir los tipos**

Añadir al final de `frontend/src/lib/tipos.ts`:

```typescript
// --- El flujo de entregas -------------------------------------------------

export interface PropuestaArchivo {
  codigo_alumno: string | null
  ciclo: string | null
  fase: string | null
  fecha: string | null
  version: number | null
  motivo: string
  completa: boolean
}

export interface ArchivoVisto {
  nombre: string
  ruta: string
  modificado_en: string
  propuesta: PropuestaArchivo
}

export interface EntregaRegistrada {
  id: string
  codigo_alumno: string
  ciclo: string
  fase: string
  version: number
  nombre_archivo: string
  huella: string
  recibida_en: string
  estado: string
  motivo_bloqueo: string | null
  version_criterios: string
}

export interface Comprobacion {
  criterio: string
  veredicto: "CUMPLE" | "NO_CUMPLE" | "NO_VERIFICABLE"
  esperado: string
  medido: string
  fuente: string
  nota: string
}

export interface Evolucion {
  proporcion_conservada: number
  proporcion_nueva: number
  parrafos_eliminados: number
  parrafos_nuevos: number
  avisos: string[]
}

export interface MedidasDeEntrega {
  nombre_archivo: string
  total_paginas: number
  paginas_en_blanco: number[]
  escaneado: boolean
  texto: {
    familia_dominante: string
    cuerpo_dominante: number
    ratio_interlineado: number | null
    margen_izquierdo_cm: number | null
  }
  estructura: {
    pagina_del_indice: number | null
    paginas_de_contenido: number | null
  }
  imagenes: { pagina: number; dpi_efectivo: number }[]
}

export interface FichaDeLectura {
  entrega: EntregaRegistrada
  medidas: MedidasDeEntrega | null
  comprobaciones: Comprobacion[]
  evolucion: Evolucion | null
  comparada_con: string | null
  aviso: string
}

export interface Entorno {
  hay_carpeta: boolean
  carpeta: string | null
  persistencia_duradera: boolean
  version_criterios: string
  avisos: string[]
}

export interface Confirmacion {
  nombre_archivo: string
  codigo_alumno: string
  ciclo: string
  fase: string
  version: number
}

export const FASES = ["TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA"] as const
```

- [ ] **Step 2: Añadir las llamadas a la API**

En `frontend/src/lib/api.ts`, ampliar el import de tipos y añadir al objeto `api`:

```typescript
  entorno: () => pedir<Entorno>("/entorno"),

  pendientes: () => pedir<ArchivoVisto[]>("/entregas/pendientes"),

  entregas: () => pedir<EntregaRegistrada[]>("/entregas"),

  confirmar: (datos: Confirmacion) =>
    pedir<FichaDeLectura>("/entregas", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  ficha: (id: string) =>
    pedir<FichaDeLectura>(`/entregas/${encodeURIComponent(id)}`),

  cambiarEstado: (id: string, estado: string, motivo: string | null) =>
    pedir<EntregaRegistrada>(`/entregas/${encodeURIComponent(id)}/estado`, {
      method: "POST",
      body: JSON.stringify({ estado, motivo }),
    }),
```

- [ ] **Step 3: Escribir los tests del componente de archivo pendiente**

Crear `frontend/src/componentes/ArchivoPendiente.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { ArchivoPendiente } from "./ArchivoPendiente"
import type { ArchivoVisto } from "../lib/tipos"

const DEDUCIDO: ArchivoVisto = {
  nombre: "AF023_DAM_E2_20260115_v1.pdf",
  ruta: "/entregas/AF023_DAM_E2_20260115_v1.pdf",
  modificado_en: "2026-08-27T10:00:00",
  propuesta: {
    codigo_alumno: "AF023", ciclo: "DAM", fase: "E2",
    fecha: "2026-01-15", version: 1, motivo: "", completa: true,
  },
}

const SIN_DEDUCIR: ArchivoVisto = {
  nombre: "trabajo de clase.pdf",
  ruta: "/entregas/trabajo de clase.pdf",
  modificado_en: "2026-08-27T10:00:00",
  propuesta: {
    codigo_alumno: null, ciclo: null, fase: null, fecha: null, version: null,
    motivo: "El nombre no sigue la convención.", completa: false,
  },
}

describe("ArchivoPendiente", () => {
  it("enseña lo deducido cuando la propuesta está completa", () => {
    render(<ArchivoPendiente archivo={DEDUCIDO} alConfirmar={vi.fn()} />)

    expect(screen.getByText("AF023_DAM_E2_20260115_v1.pdf")).toBeInTheDocument()
    expect(screen.getByText(/AF023/)).toBeInTheDocument()
    expect(screen.getByText(/E2/)).toBeInTheDocument()
  })

  it("confirma con lo deducido de un solo clic", async () => {
    const alConfirmar = vi.fn()
    render(<ArchivoPendiente archivo={DEDUCIDO} alConfirmar={alConfirmar} />)

    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf",
      codigo_alumno: "AF023", ciclo: "DAM", fase: "E2", version: 1,
    })
  })

  it("enseña el motivo cuando no se ha podido deducir", () => {
    render(<ArchivoPendiente archivo={SIN_DEDUCIR} alConfirmar={vi.fn()} />)

    expect(screen.getByText(/no sigue la convención/)).toBeInTheDocument()
  })

  it("no ofrece confirmar sin rellenar cuando falta información", () => {
    render(<ArchivoPendiente archivo={SIN_DEDUCIR} alConfirmar={vi.fn()} />)

    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled()
  })

  it("permite escribir lo que falta y entonces confirma", async () => {
    const alConfirmar = vi.fn()
    render(<ArchivoPendiente archivo={SIN_DEDUCIR} alConfirmar={alConfirmar} />)

    await userEvent.type(screen.getByLabelText(/código/i), "AF031")
    await userEvent.type(screen.getByLabelText(/ciclo/i), "DAW")
    await userEvent.selectOptions(screen.getByLabelText(/fase/i), "E1")
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      nombre_archivo: "trabajo de clase.pdf",
      codigo_alumno: "AF031", ciclo: "DAW", fase: "E1", version: 1,
    })
  })

  it("deja corregir una propuesta que se dedujo mal", async () => {
    const alConfirmar = vi.fn()
    render(<ArchivoPendiente archivo={DEDUCIDO} alConfirmar={alConfirmar} />)

    await userEvent.click(screen.getByRole("button", { name: /corregir/i }))
    await userEvent.selectOptions(screen.getByLabelText(/fase/i), "E3")
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }))

    expect(alConfirmar).toHaveBeenCalledWith(
      expect.objectContaining({ fase: "E3", codigo_alumno: "AF023" }),
    )
  })
})
```

- [ ] **Step 4: Ejecutar los tests y verificar que fallan**

Run: `cd frontend && npx vitest run src/componentes/ArchivoPendiente.test.tsx`
Expected: FAIL — no existe el módulo.

- [ ] **Step 5: Escribir `frontend/src/componentes/ArchivoPendiente.tsx`**

```typescript
import { useState } from "react"

import { FASES } from "../lib/tipos"
import type { ArchivoVisto, Confirmacion } from "../lib/tipos"

interface Props {
  archivo: ArchivoVisto
  alConfirmar: (datos: Confirmacion) => void
}

/**
 * Un archivo de la carpeta, con lo que el sistema propone y el gesto con el
 * que el docente lo confirma.
 *
 * La propuesta nunca se da por buena sola: aunque venga completa, siempre
 * hay un botón para corregirla. Es lo que D-009 reserva al docente, y la
 * interfaz no debería dejarle sin la puerta de salida.
 */
export function ArchivoPendiente({ archivo, alConfirmar }: Props) {
  const { propuesta } = archivo
  const [editando, setEditando] = useState(!propuesta.completa)
  const [codigo, setCodigo] = useState(propuesta.codigo_alumno ?? "")
  const [ciclo, setCiclo] = useState(propuesta.ciclo ?? "")
  const [fase, setFase] = useState(propuesta.fase ?? "")
  const [version, setVersion] = useState(String(propuesta.version ?? 1))

  const listo = codigo.trim() !== "" && ciclo.trim() !== "" && fase !== ""

  function confirmar() {
    alConfirmar({
      nombre_archivo: archivo.nombre,
      codigo_alumno: codigo.trim().toUpperCase(),
      ciclo: ciclo.trim().toUpperCase(),
      fase,
      version: Number(version) || 1,
    })
  }

  return (
    <li className="border-b border-grisclaro py-5">
      <p className="font-mono text-[13px]">{archivo.nombre}</p>

      {!editando ? (
        <p className="mt-2 text-[13px] text-gris">
          {codigo} · {ciclo} · {fase} · versión {version}
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-4">
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Código
            <input
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            />
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Ciclo
            <input
              value={ciclo}
              onChange={(evento) => setCiclo(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            />
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Fase
            <select
              value={fase}
              onChange={(evento) => setFase(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            >
              <option value="">—</option>
              {FASES.map((cada) => (
                <option key={cada} value={cada}>{cada}</option>
              ))}
            </select>
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Versión
            <input
              type="number"
              min={1}
              value={version}
              onChange={(evento) => setVersion(evento.target.value)}
              className="block mt-1 w-20 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            />
          </label>
        </div>
      )}

      {propuesta.motivo && (
        <p className="mt-3 max-w-lectura text-[13px] senal">{propuesta.motivo}</p>
      )}

      <div className="mt-4 flex gap-5">
        <button
          onClick={confirmar}
          disabled={!listo}
          className="text-[13px] border-b-2 border-tinta pb-1
                     disabled:border-grisclaro disabled:text-gris"
        >
          Confirmar
        </button>
        {!editando && (
          <button
            onClick={() => setEditando(true)}
            className="text-[13px] text-gris pb-1"
          >
            Corregir
          </button>
        )}
      </div>
    </li>
  )
}
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `cd frontend && npx vitest run src/componentes/ArchivoPendiente.test.tsx`
Expected: PASS, 6 tests.

- [ ] **Step 7: Escribir los tests de la pantalla**

Crear `frontend/src/paginas/Entregas.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Entregas } from "./Entregas"
import { api } from "../lib/api"

vi.mock("../lib/api")

const PENDIENTE = {
  nombre: "AF023_DAM_E2_20260115_v1.pdf",
  ruta: "/entregas/AF023_DAM_E2_20260115_v1.pdf",
  modificado_en: "2026-08-27T10:00:00",
  propuesta: {
    codigo_alumno: "AF023", ciclo: "DAM", fase: "E2",
    fecha: "2026-01-15", version: 1, motivo: "", completa: true,
  },
}

const REGISTRADA = {
  id: "id-1", codigo_alumno: "AF023", ciclo: "DAM", fase: "E1", version: 1,
  nombre_archivo: "AF023_DAM_E1_20251201_v1.pdf", huella: "a".repeat(64),
  recibida_en: "2026-08-20T09:00:00", estado: "RECIBIDO",
  motivo_bloqueo: null, version_criterios: "v2026-2027",
}

const ENTORNO = {
  hay_carpeta: true, carpeta: "C:/01_ALUMNOS", persistencia_duradera: true,
  version_criterios: "v2026-2027", avisos: [],
}

describe("Entregas", () => {
  beforeEach(() => {
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.pendientes).mockResolvedValue([PENDIENTE])
    vi.mocked(api.entregas).mockResolvedValue([REGISTRADA])
  })

  it("enseña los archivos pendientes de confirmar", async () => {
    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText("AF023_DAM_E2_20260115_v1.pdf")).toBeInTheDocument()
  })

  it("enseña las entregas ya registradas", async () => {
    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/AF023_DAM_E1_20251201_v1.pdf/)).toBeInTheDocument()
  })

  it("avisa cuando no hay carpeta configurada", async () => {
    vi.mocked(api.entorno).mockResolvedValue({
      ...ENTORNO, hay_carpeta: false, carpeta: null,
      avisos: ["No hay carpeta de entregas configurada."],
    })
    vi.mocked(api.pendientes).mockResolvedValue([])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/No hay carpeta de entregas/)).toBeInTheDocument()
  })

  it("avisa cuando lo registrado no se va a guardar", async () => {
    vi.mocked(api.entorno).mockResolvedValue({
      ...ENTORNO, persistencia_duradera: false,
      avisos: ["Lo que registres se pierde al cerrarlo."],
    })

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/se pierde al cerrarlo/)).toBeInTheDocument()
  })

  it("al confirmar abre la ficha de la entrega", async () => {
    const alAbrirFicha = vi.fn()
    vi.mocked(api.confirmar).mockResolvedValue({
      entrega: { ...REGISTRADA, id: "id-nueva" },
      medidas: null, comprobaciones: [], evolucion: null,
      comparada_con: null, aviso: "",
    })
    const usuario = (await import("@testing-library/user-event")).default
    render(<Entregas alAbrirFicha={alAbrirFicha} />)

    await usuario.click(await screen.findByRole("button", { name: /confirmar/i }))

    await waitFor(() => expect(alAbrirFicha).toHaveBeenCalledWith("id-nueva"))
  })

  it("enseña el error del servidor sin romperse", async () => {
    vi.mocked(api.pendientes).mockRejectedValue(new Error("Servidor apagado."))

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/Servidor apagado/)).toBeInTheDocument()
  })

  it("dice claramente cuando no hay nada pendiente", async () => {
    vi.mocked(api.pendientes).mockResolvedValue([])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/nada nuevo/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 8: Escribir `frontend/src/paginas/Entregas.tsx`**

```typescript
import { useCallback, useEffect, useState } from "react"

import { ArchivoPendiente } from "../componentes/ArchivoPendiente"
import { api } from "../lib/api"
import type {
  ArchivoVisto, Confirmacion, EntregaRegistrada, Entorno,
} from "../lib/tipos"

interface Props {
  alAbrirFicha: (id: string) => void
}

/** La bandeja: lo que ha llegado y lo que ya está registrado. */
export function Entregas({ alAbrirFicha }: Props) {
  const [entorno, setEntorno] = useState<Entorno | null>(null)
  const [pendientes, setPendientes] = useState<ArchivoVisto[]>([])
  const [registradas, setRegistradas] = useState<EntregaRegistrada[]>([])
  const [error, setError] = useState("")
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      const [elEntorno, losPendientes, lasRegistradas] = await Promise.all([
        api.entorno(), api.pendientes(), api.entregas(),
      ])
      setEntorno(elEntorno)
      setPendientes(losPendientes)
      setRegistradas(lasRegistradas)
      setError("")
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { void cargar() }, [cargar])

  async function confirmar(datos: Confirmacion) {
    try {
      const ficha = await api.confirmar(datos)
      alAbrirFicha(ficha.entrega.id)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
    }
  }

  return (
    <div className="max-w-3xl">
      {entorno?.avisos.map((aviso) => (
        <p key={aviso} className="mb-4 max-w-lectura text-[13px] senal">
          {aviso}
        </p>
      ))}

      {error && (
        <p className="mb-6 max-w-lectura text-[13px] senal">{error}</p>
      )}

      <section className="mb-14">
        <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
          Pendientes de confirmar
        </h2>
        {cargando ? (
          <p className="text-[13px] text-gris">Mirando la carpeta…</p>
        ) : pendientes.length === 0 ? (
          <p className="text-[13px] text-gris">
            No hay nada nuevo en la carpeta.
          </p>
        ) : (
          <ul className="regla-fina">
            {pendientes.map((archivo) => (
              <ArchivoPendiente
                key={archivo.nombre}
                archivo={archivo}
                alConfirmar={confirmar}
              />
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
          Registradas
        </h2>
        {registradas.length === 0 ? (
          <p className="text-[13px] text-gris">Todavía no hay ninguna.</p>
        ) : (
          <ol className="regla-fina">
            {registradas.map((entrega) => (
              <li key={entrega.id} className="border-b border-grisclaro">
                <button
                  onClick={() => alAbrirFicha(entrega.id)}
                  className="w-full text-left py-4 px-1 hover:bg-papel transition-colors"
                >
                  <span className="block text-[15px]">
                    {entrega.codigo_alumno} · {entrega.fase} · versión {entrega.version}
                  </span>
                  <span className="block mt-1 font-mono text-[12px] text-gris">
                    {entrega.nombre_archivo}
                  </span>
                  <span className="block mt-1 text-[12px] uppercase tracking-[0.08em]">
                    {entrega.estado === "BLOQUEADO" ? (
                      <span className="senal">bloqueada</span>
                    ) : (
                      <span className="text-gris">{entrega.estado.toLowerCase()}</span>
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}
```

- [ ] **Step 9: Añadir la pestaña en `frontend/src/App.tsx`**

Ampliar el tipo `Vista` a `"entregas" | "documentos" | "estado" | "pendientes"`, poner `"entregas"` como vista inicial y como primera pestaña con el texto `Entregas`, cambiar el `h1` a `Revisor de proyectos`, y añadir en el `main` la rama que renderiza `<Entregas alAbrirFicha={setFichaAbierta} />` y, cuando `fichaAbierta` no es nula, `<Ficha id={fichaAbierta} alVolver={() => setFichaAbierta(null)} />` (el componente `Ficha` llega en la Task 14; hasta entonces, esa rama puede quedar sin escribir y la pestaña funciona sin ella).

- [ ] **Step 10: Ejecutar los tests del frontend**

Run: `cd frontend && npm test`
Expected: PASS, 29 tests (los 16 que ya había más 13 nuevos).

- [ ] **Step 11: Commit**

```bash
git add frontend/src
git commit -m "feat: bandeja de entregas

D-009 tal como lo vive el docente: una lista, y en cada archivo o un boton
de confirmar o un formulario corto con el motivo de por que no se dedujo.

La propuesta nunca se da por buena sola. Aunque venga completa, siempre hay
un boton para corregirla: es lo que D-009 le reserva, y la interfaz no
deberia dejarle sin la puerta de salida.

La tinta senal marca aqui lo que espera una decision suya: una propuesta
que no se dedujo, una entrega bloqueada. Sigue sin decorar nada."
```

---

### Task 14: Frontend — la ficha de la entrega

Lo medido, lo comprobado y lo comparado, en una pantalla. Su trabajo es que el docente vea de un vistazo qué mirar en el PDF antes de sentarse a leerlo.

**Lo que esta pantalla no tiene, y no por olvido:** nota, valoración, semáforo y botón de aprobar. No hay ponderaciones oficiales, así que no hay nota (R3), y aprobar es del §13. Que la pantalla no ofrezca esos gestos es la forma de que el sistema no los haga.

**Files:**
- Create: `frontend/src/paginas/Ficha.tsx`
- Create: `frontend/src/componentes/TablaComprobaciones.tsx`
- Create: `frontend/src/componentes/TablaComprobaciones.test.tsx`
- Create: `frontend/src/paginas/Ficha.test.tsx`
- Modify: `frontend/src/App.tsx` (enganchar la ficha)

**Interfaces:**
- Consumes: `api.ficha`, `api.cambiarEstado` (Task 13); los tipos `FichaDeLectura` y `Comprobacion`.
- Produces: `Ficha` y `TablaComprobaciones` como componentes con nombre.

- [ ] **Step 1: Escribir los tests de la tabla**

Crear `frontend/src/componentes/TablaComprobaciones.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { TablaComprobaciones } from "./TablaComprobaciones"
import type { Comprobacion } from "../lib/tipos"

const CUMPLE: Comprobacion = {
  criterio: "paginas_en_blanco", veredicto: "CUMPLE",
  esperado: "ninguna página en blanco", medido: "ninguna",
  fuente: "indice#6-formato-y-control", nota: "",
}

const NO_CUMPLE: Comprobacion = {
  criterio: "extension", veredicto: "NO_CUMPLE",
  esperado: "20 páginas de contenido como mínimo",
  medido: "12 páginas de contenido (de 18 en total)",
  fuente: "maestro#6-estandar-academico", nota: "",
}

const NO_VERIFICABLE: Comprobacion = {
  criterio: "interlineado", veredicto: "NO_VERIFICABLE",
  esperado: "1.5 líneas", medido: "ratio medido 1.73 entre líneas base y cuerpo",
  fuente: "maestro#6-estandar-academico",
  nota: "La equivalencia no está fijada en ninguna fuente oficial.",
}

describe("TablaComprobaciones", () => {
  it("enseña lo esperado y lo medido de cada criterio", () => {
    render(<TablaComprobaciones comprobaciones={[NO_CUMPLE]} />)

    expect(screen.getByText(/20 páginas de contenido como mínimo/)).toBeInTheDocument()
    expect(screen.getByText(/12 páginas de contenido/)).toBeInTheDocument()
  })

  it("enseña la fuente de cada criterio", () => {
    render(<TablaComprobaciones comprobaciones={[NO_CUMPLE]} />)

    expect(screen.getByText(/maestro#6-estandar-academico/)).toBeInTheDocument()
  })

  it("enseña la nota cuando la hay", () => {
    render(<TablaComprobaciones comprobaciones={[NO_VERIFICABLE]} />)

    expect(screen.getByText(/no está fijada en ninguna fuente oficial/)).toBeInTheDocument()
  })

  it("distingue un no verificable de un incumplimiento", () => {
    render(<TablaComprobaciones comprobaciones={[NO_CUMPLE, NO_VERIFICABLE]} />)

    expect(screen.getByText(/no cumple/i)).toBeInTheDocument()
    expect(screen.getByText(/no se puede comprobar/i)).toBeInTheDocument()
  })

  it("lo que cumple no lleva la tinta de señal", () => {
    const { container } = render(<TablaComprobaciones comprobaciones={[CUMPLE]} />)

    expect(container.querySelectorAll(".senal")).toHaveLength(0)
  })

  it("lo que no cumple sí la lleva", () => {
    const { container } = render(<TablaComprobaciones comprobaciones={[NO_CUMPLE]} />)

    expect(container.querySelectorAll(".senal").length).toBeGreaterThan(0)
  })

  it("un no verificable tampoco la lleva: no es un fallo del alumno", () => {
    const { container } = render(
      <TablaComprobaciones comprobaciones={[NO_VERIFICABLE]} />,
    )

    expect(container.querySelectorAll(".senal")).toHaveLength(0)
  })
})
```

- [ ] **Step 2: Escribir `frontend/src/componentes/TablaComprobaciones.tsx`**

```typescript
import type { Comprobacion } from "../lib/tipos"

const ROTULOS: Record<Comprobacion["veredicto"], string> = {
  CUMPLE: "cumple",
  NO_CUMPLE: "no cumple",
  NO_VERIFICABLE: "no se puede comprobar",
}

/**
 * Cada criterio de formato con lo que se esperaba, lo que se midió y de
 * dónde sale.
 *
 * La tinta de señal marca solo lo que no cumple. Un «no se puede comprobar»
 * no la lleva: no es un fallo del alumno, es un hueco del sistema, y
 * pintarlo igual que un incumplimiento haría que el docente los confundiera.
 */
export function TablaComprobaciones({
  comprobaciones,
}: { comprobaciones: Comprobacion[] }) {
  return (
    <ol className="regla-fina">
      {comprobaciones.map((comprobacion) => (
        <li key={comprobacion.criterio} className="border-b border-grisclaro py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <span className="text-[15px]">
              {comprobacion.criterio.replace(/_/g, " ")}
            </span>
            <span
              className={
                comprobacion.veredicto === "NO_CUMPLE"
                  ? "senal text-[12px] uppercase tracking-[0.08em]"
                  : "text-gris text-[12px] uppercase tracking-[0.08em]"
              }
            >
              {ROTULOS[comprobacion.veredicto]}
            </span>
          </div>
          <dl className="mt-2 max-w-lectura text-[13px]">
            <div className="flex gap-3">
              <dt className="text-gris w-24 shrink-0">Se pide</dt>
              <dd>{comprobacion.esperado}</dd>
            </div>
            <div className="flex gap-3 mt-1">
              <dt className="text-gris w-24 shrink-0">Se ha medido</dt>
              <dd>{comprobacion.medido}</dd>
            </div>
            <div className="flex gap-3 mt-1">
              <dt className="text-gris w-24 shrink-0">Sale de</dt>
              <dd className="font-mono text-[12px] text-gris">
                {comprobacion.fuente}
              </dd>
            </div>
          </dl>
          {comprobacion.nota && (
            <p className="mt-2 max-w-lectura text-[12px] text-gris">
              {comprobacion.nota}
            </p>
          )}
        </li>
      ))}
    </ol>
  )
}
```

- [ ] **Step 3: Escribir los tests de la ficha**

Crear `frontend/src/paginas/Ficha.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Ficha } from "./Ficha"
import { api } from "../lib/api"
import type { FichaDeLectura } from "../lib/tipos"

vi.mock("../lib/api")

const COMPLETA: FichaDeLectura = {
  entrega: {
    id: "id-1", codigo_alumno: "AF023", ciclo: "DAM", fase: "E2", version: 1,
    nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf", huella: "a".repeat(64),
    recibida_en: "2026-08-27T10:00:00", estado: "RECIBIDO",
    motivo_bloqueo: null, version_criterios: "v2026-2027",
  },
  medidas: {
    nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf",
    total_paginas: 24, paginas_en_blanco: [7], escaneado: false,
    texto: {
      familia_dominante: "Arial", cuerpo_dominante: 11,
      ratio_interlineado: 1.73, margen_izquierdo_cm: 2.5,
    },
    estructura: { pagina_del_indice: 2, paginas_de_contenido: 20 },
    imagenes: [{ pagina: 9, dpi_efectivo: 42.1 }],
  },
  comprobaciones: [{
    criterio: "extension", veredicto: "CUMPLE",
    esperado: "20 páginas", medido: "20 páginas",
    fuente: "maestro#6-estandar-academico", nota: "",
  }],
  evolucion: {
    proporcion_conservada: 0.9, proporcion_nueva: 0.3,
    parrafos_eliminados: 2, parrafos_nuevos: 11,
    avisos: ["Han desaparecido 2 párrafos."],
  },
  comparada_con: "AF023_DAM_E1_20251201_v1.pdf",
  aviso: "",
}

describe("Ficha", () => {
  beforeEach(() => {
    vi.mocked(api.ficha).mockResolvedValue(COMPLETA)
  })

  it("enseña de quién es la entrega", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/AF023/)).toBeInTheDocument()
    expect(screen.getByText(/E2/)).toBeInTheDocument()
  })

  it("enseña lo medido", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/24/)).toBeInTheDocument()
    expect(screen.getByText(/Arial/)).toBeInTheDocument()
  })

  it("enseña las comprobaciones", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/maestro#6-estandar-academico/)).toBeInTheDocument()
  })

  it("enseña con qué entrega se ha comparado", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/AF023_DAM_E1_20251201_v1.pdf/)).toBeInTheDocument()
    expect(screen.getByText(/Han desaparecido 2 párrafos/)).toBeInTheDocument()
  })

  it("no ofrece nota ni aprobar", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} />)
    await screen.findByText(/AF023/)

    expect(screen.queryByText(/nota/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /aprobar/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /calificar/i })).not.toBeInTheDocument()
  })

  it("dice por qué no hay nota, para que no parezca un olvido", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/ponderaciones/i)).toBeInTheDocument()
  })

  it("una entrega bloqueada enseña el motivo y nada más", async () => {
    vi.mocked(api.ficha).mockResolvedValue({
      ...COMPLETA,
      entrega: {
        ...COMPLETA.entrega, estado: "BLOQUEADO",
        motivo_bloqueo: "El archivo está protegido con contraseña.",
      },
      medidas: null, comprobaciones: [], evolucion: null, comparada_con: null,
    })

    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/protegido con contraseña/)).toBeInTheDocument()
  })

  it("enseña el aviso cuando no se ha podido comparar", async () => {
    vi.mocked(api.ficha).mockResolvedValue({
      ...COMPLETA, evolucion: null, comparada_con: null,
      aviso: "El archivo anterior ya no está en la carpeta.",
    })

    render(<Ficha id="id-1" alVolver={vi.fn()} />)

    expect(await screen.findByText(/ya no está en la carpeta/)).toBeInTheDocument()
  })

  it("vuelve a la bandeja", async () => {
    const alVolver = vi.fn()
    const usuario = (await import("@testing-library/user-event")).default
    render(<Ficha id="id-1" alVolver={alVolver} />)

    await usuario.click(await screen.findByRole("button", { name: /volver/i }))

    expect(alVolver).toHaveBeenCalled()
  })
})
```

- [ ] **Step 4: Escribir `frontend/src/paginas/Ficha.tsx`**

```typescript
import { useEffect, useState } from "react"

import { TablaComprobaciones } from "../componentes/TablaComprobaciones"
import { api } from "../lib/api"
import type { FichaDeLectura } from "../lib/tipos"

interface Props {
  id: string
  alVolver: () => void
}

/**
 * Lo medido, lo comprobado y lo comparado de una entrega.
 *
 * No hay nota, ni valoración, ni botón de aprobar, y no es un olvido: las
 * ponderaciones siguen en PENDIENTE_OFICIAL y la regla R3 impide inventar
 * un dato pendiente, mientras que aprobar es del §13. Que la pantalla no
 * ofrezca esos gestos es la forma de que el sistema no los haga.
 */
export function Ficha({ id, alVolver }: Props) {
  const [ficha, setFicha] = useState<FichaDeLectura | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let vigente = true
    api.ficha(id)
      .then((leida) => { if (vigente) setFicha(leida) })
      .catch((fallo) => {
        if (vigente) setError(fallo instanceof Error ? fallo.message : String(fallo))
      })
    return () => { vigente = false }
  }, [id])

  if (error) {
    return (
      <div className="max-w-3xl">
        <p className="mb-6 max-w-lectura text-[13px] senal">{error}</p>
        <button onClick={alVolver} className="text-[13px] text-gris">
          Volver
        </button>
      </div>
    )
  }

  if (!ficha) {
    return <p className="text-[13px] text-gris">Leyendo el documento…</p>
  }

  const { entrega, medidas, evolucion } = ficha

  return (
    <div className="max-w-3xl">
      <button onClick={alVolver} className="text-[13px] text-gris mb-8">
        ← Volver
      </button>

      <h2 className="text-[19px] mb-1">
        {entrega.codigo_alumno} · {entrega.ciclo} · {entrega.fase} · versión{" "}
        {entrega.version}
      </h2>
      <p className="font-mono text-[12px] text-gris mb-10">
        {entrega.nombre_archivo}
      </p>

      {entrega.estado === "BLOQUEADO" && entrega.motivo_bloqueo && (
        <p className="mb-10 max-w-lectura text-[13px] senal">
          {entrega.motivo_bloqueo}
        </p>
      )}

      {ficha.aviso && (
        <p className="mb-10 max-w-lectura text-[13px] senal">{ficha.aviso}</p>
      )}

      {medidas && (
        <section className="mb-14">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Lo que se ha medido
          </h3>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-[13px] md:grid-cols-3">
            <Dato rotulo="Páginas" valor={String(medidas.total_paginas)} />
            <Dato
              rotulo="De contenido"
              valor={medidas.estructura.paginas_de_contenido !== null
                ? String(medidas.estructura.paginas_de_contenido)
                : "no se ha podido contar"}
            />
            <Dato
              rotulo="Tipografía"
              valor={medidas.texto.familia_dominante
                ? `${medidas.texto.familia_dominante} ${medidas.texto.cuerpo_dominante}`
                : "sin texto extraíble"}
            />
            <Dato
              rotulo="Interlineado"
              valor={medidas.texto.ratio_interlineado !== null
                ? `ratio ${medidas.texto.ratio_interlineado.toFixed(2)}`
                : "no medible"}
            />
            <Dato
              rotulo="Páginas en blanco"
              valor={medidas.paginas_en_blanco.length
                ? medidas.paginas_en_blanco.join(", ")
                : "ninguna"}
            />
            <Dato rotulo="Imágenes" valor={String(medidas.imagenes.length)} />
          </dl>
        </section>
      )}

      {ficha.comprobaciones.length > 0 && (
        <section className="mb-14">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Formato
          </h3>
          <TablaComprobaciones comprobaciones={ficha.comprobaciones} />
        </section>
      )}

      {evolucion && (
        <section className="mb-14">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Frente a la entrega anterior
          </h3>
          <p className="text-[13px] text-gris mb-3">
            Comparada con{" "}
            <span className="font-mono">{ficha.comparada_con}</span>.
          </p>
          <p className="max-w-lectura text-[13px]">
            Se conserva el {(evolucion.proporcion_conservada * 100).toFixed(0)} % de
            lo anterior. Hay {evolucion.parrafos_nuevos} párrafos nuevos y han
            desaparecido {evolucion.parrafos_eliminados}.
          </p>
          {evolucion.avisos.map((aviso) => (
            <p key={aviso} className="mt-3 max-w-lectura text-[13px] senal">
              {aviso}
            </p>
          ))}
        </section>
      )}

      <p className="max-w-lectura border-t border-grisclaro pt-5 text-[12px] text-gris">
        Esta ficha no propone calificación. Las ponderaciones de la
        programación didáctica siguen pendientes, y el sistema no sustituye un
        dato oficial que falta por una estimación. La valoración y la nota son
        tuyas.
      </p>
    </div>
  )
}

function Dato({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-[0.08em] text-gris">
        {rotulo}
      </dt>
      <dd className="mt-1">{valor}</dd>
    </div>
  )
}
```

- [ ] **Step 5: Enganchar la ficha en `frontend/src/App.tsx`**

Añadir `const [fichaAbierta, setFichaAbierta] = useState<string | null>(null)` e importar `Ficha`. En el `main`, la ficha tiene prioridad sobre la vista: si `fichaAbierta` no es nula, renderizar `<Ficha id={fichaAbierta} alVolver={() => setFichaAbierta(null)} />`. Cambiar de pestaña pone `fichaAbierta` a `null`, igual que ya hace con `anclaEditando`.

- [ ] **Step 6: Ejecutar los tests del frontend**

Run: `cd frontend && npm test`
Expected: PASS, 45 tests.

- [ ] **Step 7: Comprobar que compila y que el lint pasa**

Run: `cd frontend && npm run build && npm run lint`
Expected: sin errores de TypeScript ni de oxlint.

- [ ] **Step 8: Ejecutar la batería completa**

Run: `python -m pytest -q && cd frontend && npm test && cd .. && python tools/verificar_gobernanza.py`
Expected: todo en verde.

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat: ficha de la entrega

Lo medido, lo comprobado y lo comparado en una pantalla, para que el
docente vea que mirar en el PDF antes de sentarse a leerlo.

No hay nota, ni valoracion, ni boton de aprobar, y no es un olvido: las
ponderaciones siguen en PENDIENTE_OFICIAL y R3 impide inventar un dato
pendiente, mientras que aprobar es del 13. Que la pantalla no ofrezca esos
gestos es la forma de que el sistema no los haga. El pie lo dice con todas
las letras para que no parezca una funcion a medio hacer.

La tinta senal marca lo que no cumple, no lo que no se puede comprobar: lo
segundo es un hueco del sistema y no un fallo del alumno, y pintarlos igual
haria que se confundieran."
```

---

## Cierre de la Parte A

Al terminar la Task 14 el sistema hace, de extremo a extremo: mirar la carpeta, proponer de quién es cada archivo, dejar que el docente lo confirme, medir el PDF, contrastarlo con los criterios de formato, compararlo con la entrega anterior y guardar la ficha.

Antes de dar la parte por cerrada:

- [ ] **Registrar el cambio de alcance.** Un fichero en `docs/changes/` si alguna medición ha obligado a matizar la prosa maestra, y la anotación en `docs/PENDIENTE_OFICIAL.md` de la equivalencia del interlineado, que ya entra en la Task 7.
- [ ] **Comprobar el arranque real** con `python -m backend`, una carpeta de entregas de verdad fuera del repositorio y un PDF de prueba propio —nunca de un alumno—, verificando que el aviso de «sin credenciales» aparece si no las hay.
- [ ] **Actualizar `CLAUDE.md`** con las carpetas nuevas en la tabla de estructura.
