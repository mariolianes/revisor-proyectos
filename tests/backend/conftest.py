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
    subprocess.run(["git", "config", "user.email", "prueba@ejemplo-invalido"],
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
