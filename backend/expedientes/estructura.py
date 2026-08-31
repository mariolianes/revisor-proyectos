"""La arquitectura de expedientes del docente: rutas, códigos y reglas
técnicas, leídas de `config/estructura_expedientes.yaml`, nunca declaradas
aquí.

El docente lo pidió así, textualmente, al entregar el documento de
arquitectura -ver el encabezado del propio YAML para la cita completa-: sus
reglas estables no deben interpretarse de nuevo en cada ejecución, sino
vivir en una configuración estructurada. Este módulo es el que la lee -con
el mismo patrón que ya usa `backend/analisis/precios.py` con
`config/precios_openai.yaml`- y el único sitio del backend que sabe construir
una ruta de esta arquitectura. Ningún otro módulo debe escribir a mano
`"02_EXPEDIENTES_ALUMNOS"` ni ningún otro nombre de carpeta: si el docente
cambia un nombre, cambia aquí y en el YAML, en ningún otro fichero.

Este módulo no toca disco más que para leer el propio YAML. Crear carpetas de
verdad es responsabilidad de `backend/expedientes/creacion.py`, que además
comprueba que la ruta base no caiga dentro del repositorio antes de escribir
nada -ver su docstring-. Separar las dos cosas permite que este módulo, y por
tanto la forma del árbol, se compruebe con tests que no tocan el sistema de
archivos del docente en absoluto.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator

FICHERO_ESTRUCTURA = "config/estructura_expedientes.yaml"

# Un nombre de carpeta válido: sin tildes, sin espacios, sin ningún carácter
# que una ruta larga de Windows trate mal. Es la comprobación técnica de la
# exigencia del docente -"nombres de carpeta sin tildes ni caracteres
# problemáticos"-, no solo una promesa en un comentario del YAML: si algún
# día alguien edita el fichero y añade una carpeta con una tilde, la carga
# falla aquí, antes de que ese nombre llegue nunca a `Path.mkdir`.
_PATRON_NOMBRE_DE_CARPETA = re.compile(r"^[A-Za-z0-9_-]+$")


def _validar_nombre_de_carpeta(valor: str) -> str:
    if not _PATRON_NOMBRE_DE_CARPETA.match(valor):
        raise ValueError(
            f"«{valor}» no sirve como nombre de carpeta de esta arquitectura: "
            "solo se admiten letras sin tilde, dígitos, guion y guion bajo. "
            "El docente exigió expresamente que ningún nombre de carpeta "
            "lleve tildes ni caracteres fuera de eso, por las rutas largas "
            "de Windows."
        )
    return valor


NombreDeCarpeta = Annotated[str, AfterValidator(_validar_nombre_de_carpeta)]


class EstructuraInvalida(ValueError):
    """`config/estructura_expedientes.yaml` no tiene la forma que exige el
    sistema, o no se ha podido leer."""


class CarpetaRaiz(BaseModel):
    """Una de las ocho carpetas del primer nivel, bajo la raíz de la
    arquitectura."""

    model_config = ConfigDict(extra="forbid")

    carpeta: NombreDeCarpeta
    vigilada: bool
    descripcion: str


class Comunidad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    carpeta: NombreDeCarpeta
    nombre: str


class Fase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    carpeta: NombreDeCarpeta
    orden: int


class EntradaTrabajos(BaseModel):
    """Cómo se organiza cada comunidad dentro de `01_ENTRADA_TRABAJOS`."""

    model_config = ConfigDict(extra="forbid")

    subcarpeta_vigilada: NombreDeCarpeta
    subcarpeta_incidencias: NombreDeCarpeta


class Centros(BaseModel):
    """El patrón de código de centro, por ejemplo `AND-MAL-01`."""

    model_config = ConfigDict(extra="forbid")

    patron: str
    ejemplo: str
    descripcion: str


class CarpetaDeExpediente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carpeta: NombreDeCarpeta
    tiene_entregas: bool


class ExpedienteAlumno(BaseModel):
    """La forma del expediente de un alumno, nombrado solo por su ID."""

    model_config = ConfigDict(extra="forbid")

    patron_id: str
    ejemplo_id: str
    carpetas: list[CarpetaDeExpediente]
    subcarpetas_de_entrega: list[NombreDeCarpeta]


class Raiz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_carpeta: NombreDeCarpeta
    variable_de_entorno: str


class ConfiguracionExpedientes(BaseModel):
    """La arquitectura entera, tal como la describe el YAML.

    `pendiente_de_definir` se conserva sin tipar -es, por definición, lo que
    todavía no tiene forma firme-, y ningún camino de este módulo lee un
    valor de ahí para tomar una decisión: mientras algo siga a `null`, este
    módulo no lo usa, ni lo sustituye por un valor razonable.
    """

    model_config = ConfigDict(extra="forbid")

    version_configuracion: str
    raiz: Raiz
    carpetas_raiz: list[CarpetaRaiz]
    comunidades: list[Comunidad]
    fases: list[Fase]
    entrada_trabajos: EntradaTrabajos
    ciclos: list[str]
    centros: Centros
    expediente_alumno: ExpedienteAlumno
    pendiente_de_definir: dict[str, object]

    @model_validator(mode="after")
    def _sin_codigos_repetidos(self) -> "ConfiguracionExpedientes":
        """Un código o un nombre de carpeta duplicado no se detecta solo,
        y una comunidad con dos filas produciría una carpeta de entrada que
        pisa a otra sin que nadie lo note al mirar el YAML. Se comprueba
        aquí, una vez, para no repetir esta guarda en cada consumidor.
        """
        _sin_repetidos([c.codigo for c in self.comunidades], "el código de comunidad")
        _sin_repetidos([c.carpeta for c in self.comunidades], "la carpeta de comunidad")
        _sin_repetidos([f.codigo for f in self.fases], "el código de fase")
        _sin_repetidos([f.carpeta for f in self.fases], "la carpeta de fase")
        _sin_repetidos(self.ciclos, "el ciclo")
        _sin_repetidos([c.carpeta for c in self.carpetas_raiz], "la carpeta raíz")
        _sin_repetidos(
            [c.carpeta for c in self.expediente_alumno.carpetas],
            "la carpeta del expediente",
        )
        return self


def _sin_repetidos(valores: list[str], que_es: str) -> None:
    vistos: set[str] = set()
    for valor in valores:
        if valor in vistos:
            raise ValueError(
                f"«{valor}» aparece más de una vez como {que_es} en "
                f"{FICHERO_ESTRUCTURA}. Cada uno debe ser único."
            )
        vistos.add(valor)


def cargar_estructura(raiz: Path) -> ConfiguracionExpedientes:
    """Lee y valida `config/estructura_expedientes.yaml`.

    No hay valor por omisión: sin este fichero, o con un fichero que no
    encaja en el esquema, no hay arquitectura de expedientes con la que
    trabajar, y se avisa con `EstructuraInvalida` en vez de arrancar con una
    estructura inventada o a medias.
    """
    fichero = raiz / FICHERO_ESTRUCTURA
    if not fichero.is_file():
        raise EstructuraInvalida(
            f"No se encuentra «{fichero}». La arquitectura de expedientes se "
            "configura ahí, no se improvisa en el código."
        )
    try:
        bruto = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    except yaml.YAMLError as fallo:
        raise EstructuraInvalida(f"«{fichero}» no es un YAML válido: {fallo}") from fallo

    if not isinstance(bruto, dict):
        raise EstructuraInvalida(
            f"«{fichero}» debería contener un mapa de configuración, y "
            f"contiene {type(bruto).__name__}."
        )

    try:
        return ConfiguracionExpedientes.model_validate(bruto)
    except Exception as fallo:  # noqa: BLE001 - se traduce a un error propio
        raise EstructuraInvalida(
            f"«{fichero}» no tiene la forma que exige el sistema: {fallo}"
        ) from fallo


# --- Validación de códigos sueltos -----------------------------------------


def comunidad_de(cfg: ConfiguracionExpedientes, codigo: str) -> Comunidad | None:
    return next((c for c in cfg.comunidades if c.codigo == codigo), None)


def fase_de(cfg: ConfiguracionExpedientes, codigo: str) -> Fase | None:
    return next((f for f in cfg.fases if f.codigo == codigo), None)


def ciclo_valido(cfg: ConfiguracionExpedientes, codigo: str) -> bool:
    return codigo in cfg.ciclos


def codigo_de_centro_valido(cfg: ConfiguracionExpedientes, codigo: str) -> bool:
    """Si `codigo` tiene la forma de un código de centro -patrón de
    `centros`- Y su primer tramo es una comunidad conocida.

    Las dos comprobaciones importan por separado: `AND-MAL-01` encaja en el
    patrón y su comunidad `AND` existe; `XYZ-MAL-01` encaja en el mismo
    patrón mecánico pero no corresponde a ninguna comunidad de este curso, y
    dejar pasar eso solo porque "tiene la forma" sería aceptar un centro que
    no puede existir.
    """
    if not re.match(cfg.centros.patron, codigo):
        return False
    primer_tramo = codigo.split("-", 1)[0]
    return comunidad_de(cfg, primer_tramo) is not None


def id_de_alumno_valido(cfg: ConfiguracionExpedientes, id_alumno: str) -> bool:
    return re.match(cfg.expediente_alumno.patron_id, id_alumno) is not None


# --- Rutas relativas, sin tocar disco ---------------------------------------
#
# Todo lo que sigue devuelve un `Path` relativo a la raíz de la arquitectura
# (la carpeta `CESUR_2026-2027`, o la que indique REVISOR_RAIZ_EXPEDIENTES).
# Nada de esto crea ni comprueba nada en el sistema de archivos: eso es
# `backend/expedientes/creacion.py`. Mantener las dos cosas separadas es lo
# que permite probar la forma del árbol con tests que no dependen de ninguna
# carpeta real.


def _raiz_entrada(cfg: ConfiguracionExpedientes) -> str:
    return next(c.carpeta for c in cfg.carpetas_raiz if c.carpeta.startswith("01_"))


def _raiz_expedientes(cfg: ConfiguracionExpedientes) -> str:
    return next(c.carpeta for c in cfg.carpetas_raiz if c.carpeta.startswith("02_"))


def ruta_entrada_pendientes(
    cfg: ConfiguracionExpedientes, codigo_comunidad: str, codigo_fase: str
) -> Path:
    """La carpeta PENDIENTES que se vigila para una comunidad y una fase.

    Lanza `ValueError` si el código de comunidad o de fase no existe en la
    configuración: una ruta construida sobre un código inventado apuntaría a
    una carpeta que la arquitectura no reconoce, y es mejor que falle aquí a
    que se cree en silencio una carpeta más, fuera del árbol vigilado.
    """
    comunidad = comunidad_de(cfg, codigo_comunidad)
    if comunidad is None:
        raise ValueError(f"«{codigo_comunidad}» no es un código de comunidad conocido.")
    fase = fase_de(cfg, codigo_fase)
    if fase is None:
        raise ValueError(f"«{codigo_fase}» no es un código de fase conocido.")
    return Path(
        _raiz_entrada(cfg), comunidad.carpeta, fase.carpeta,
        cfg.entrada_trabajos.subcarpeta_vigilada,
    )


def ruta_entrada_incidencias(cfg: ConfiguracionExpedientes, codigo_comunidad: str) -> Path:
    comunidad = comunidad_de(cfg, codigo_comunidad)
    if comunidad is None:
        raise ValueError(f"«{codigo_comunidad}» no es un código de comunidad conocido.")
    return Path(
        _raiz_entrada(cfg), comunidad.carpeta, cfg.entrada_trabajos.subcarpeta_incidencias,
    )


def ruta_expediente(cfg: ConfiguracionExpedientes, id_alumno: str) -> Path:
    """La carpeta del expediente de un alumno, nombrada solo con su ID.

    Nunca lleva el nombre, la comunidad, el centro ni el ciclo del alumno en
    la ruta -es la exigencia expresa del docente-, y por construcción no
    puede llevarlos: esta función no recibe ninguno de esos datos.
    """
    if not id_de_alumno_valido(cfg, id_alumno):
        raise ValueError(
            f"«{id_alumno}» no tiene la forma de un ID de expediente "
            f"({cfg.expediente_alumno.patron_id}, por ejemplo "
            f"{cfg.expediente_alumno.ejemplo_id})."
        )
    return Path(_raiz_expedientes(cfg), id_alumno)


def rutas_del_expediente(cfg: ConfiguracionExpedientes, id_alumno: str) -> list[Path]:
    """Todas las carpetas del expediente de un alumno: las ocho de primer
    nivel y, dentro de las que tienen `tiene_entregas: true`, las cinco
    subcarpetas de entrega."""
    base = ruta_expediente(cfg, id_alumno)
    rutas = []
    for carpeta in cfg.expediente_alumno.carpetas:
        ruta_carpeta = base / carpeta.carpeta
        rutas.append(ruta_carpeta)
        if carpeta.tiene_entregas:
            rutas += [
                ruta_carpeta / sub for sub in cfg.expediente_alumno.subcarpetas_de_entrega
            ]
    return rutas
