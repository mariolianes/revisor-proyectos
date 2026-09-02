"""El registro maestro de alumnos: identidad sin nombre.

El §2 del orden de implantación del docente pide poder dar de alta a los
200-250 alumnos de un curso antes de que llegue ninguna entrega, con centro,
ciclo, comunidad autónoma y estado de matrícula -y el ID de CESUR, cuando el
centro lo facilita, que el docente pidió preferir al nombre para emparejar-.

Este módulo reutiliza la tabla `alumno` que ya existía
(`supabase/migrations/20260827120000_esquema_inicial.sql`) en vez de crear
una segunda identidad en paralelo: `codigo` sigue siendo la columna del
identificador -desde esta tarea con forma `ALU-AANNNN` en vez de la que
elegía a mano cada alumno en el nombre de su archivo (`AF023`, `AF024`...)-
y `ciclo` sigue siendo la misma columna de siempre, ahora con el vocabulario
cerrado que pide el docente (MYP, CIN, AYF). Ver
`supabase/migrations/20260831210000_registro_maestro_de_alumnos.sql`.

Ningún modelo de este fichero admite un nombre. `AlumnoNuevo` y
`AlumnoRegistrado` declaran `extra="forbid"`: no es un descuido que se pueda
colar sin que nadie lo note, es que construir el objeto con un campo
`nombre` falla en el momento, antes de que ese dato tenga ninguna
oportunidad de llegar a un almacén. La correspondencia con el nombre real
vive únicamente en `backend.privacidad.listado_local.ListadoLocal`, en el
equipo del docente. Ver D-025 en `docs/decisions.md`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, field_validator

# Las seis comunidades del curso, tal como las declaró el docente.
CCAA_CODES: tuple[str, ...] = ("AND", "MAD", "CAN", "MUR", "ARA", "EXT")

# Los tres ciclos de este curso. No es un catálogo abierto: si el docente
# amplía el número de ciclos que corrige, esta tupla es lo primero que hay
# que tocar, y se toca aquí y solo aquí -config/centros.yaml, en cambio, sí
# es un catálogo abierto, porque los centros de una comunidad crecen sin que
# eso sea una decisión de arquitectura-.
CICLO_CODES: tuple[str, ...] = ("MYP", "CIN", "AYF")

ESTADOS_MATRICULA: tuple[str, ...] = ("ACTIVO", "BAJA", "TRASLADADO", "REPETIDOR")
ESTADO_MATRICULA_INICIAL = "ACTIVO"

PREFIJO_STUDENT_ID = "ALU"
PATRON_CURSO = re.compile(r"^(\d{4})-(\d{4})$")
PATRON_STUDENT_ID = re.compile(rf"^{PREFIJO_STUDENT_ID}-(\d{{2}})(\d{{4}})$")


def _normalizar(valor: str) -> str:
    """Sin ningún carácter de espacio y en mayúsculas.

    Mismo criterio, por el mismo motivo, que
    `backend.persistencia.modelos._normalizar_identidad` y
    `backend.privacidad.listado_local._normalizar_codigo`: un código de
    comunidad, de centro, de ciclo o de estado no lleva espacios legítimos,
    así que no hay nada que preservar al quitarlos todos, no solo los de los
    extremos. Se duplica en vez de importarse de esos módulos porque los dos
    empiezan con `_` -son privados a propósito- y esta es la misma regla de
    tres líneas en su tercer sitio, no una dependencia que merezca romper esa
    frontera.
    """
    return "".join((valor or "").split()).upper()


def validar_curso(curso: str) -> None:
    """Que `curso` tenga forma AAAA-AAAA y que el segundo año sea el
    siguiente al primero."""
    coincidencia = PATRON_CURSO.match(curso)
    if coincidencia is None:
        raise ValueError(
            f"«{curso}» no es un curso académico válido. Se escribe "
            "AAAA-AAAA, por ejemplo 2026-2027."
        )
    primero, segundo = int(coincidencia.group(1)), int(coincidencia.group(2))
    if segundo != primero + 1:
        raise ValueError(
            f"«{curso}» no es un curso académico válido: el segundo año "
            "tiene que ser el siguiente al primero, como en 2026-2027."
        )


def codigo_de_curso(curso: str) -> str:
    """Los dos dígitos que identifican el curso dentro de un `student_id`.

    «2026-2027» -> «26». Es el mismo criterio con el que ya se nombran las
    versiones de criterios (`v2026-2027`), reducido a los dos primeros
    dígitos: bastan para no repetirse hasta dentro de cien años, y un
    `student_id` más largo no aporta nada que el docente necesite leer.
    """
    validar_curso(curso)
    return curso[2:4]


def generar_student_id(curso: str, existentes: Iterable[str]) -> str:
    """El siguiente `student_id` libre para ese curso: ALU-AANNNN.

    Independiente del centro y de la comunidad -lo pidió así el docente,
    porque «esa decisión aporta estabilidad»-. Depende solo del curso y de
    qué números ya están en uso DENTRO de él: dos alumnos del mismo curso en
    comunidades distintas nunca chocan porque comparten el mismo contador,
    no porque se hayan coordinado por otra vía.

    `existentes` es responsabilidad de quien llama: esta función es pura y
    no consulta ningún almacén por su cuenta, para poder probarse sin uno.
    Debe llevar los `student_id` YA USADOS EN ESE CURSO -otros cursos no
    cuentan, porque el número reinicia en cada uno-.

    No decide nada sobre si un alumno repetidor debería conservar el
    `student_id` de un curso anterior: eso es una decisión del docente que
    esta función no toma por su cuenta. Ver D-025 en `docs/decisions.md`,
    donde queda `Pendiente`.
    """
    prefijo_curso = codigo_de_curso(curso)
    patron = re.compile(rf"^{PREFIJO_STUDENT_ID}-{prefijo_curso}(\d{{4}})$")
    maximo = 0
    for existente in existentes:
        coincidencia = patron.match(existente)
        if coincidencia:
            maximo = max(maximo, int(coincidencia.group(1)))
    numero = maximo + 1
    if numero > 9999:
        raise ValueError(
            f"El curso {curso} ya tiene 9999 alumnos registrados con este "
            "formato de student_id; hace falta una decisión del docente "
            "sobre cómo seguir numerando."
        )
    return f"{PREFIJO_STUDENT_ID}-{prefijo_curso}{numero:04d}"


class AlumnoNuevo(BaseModel):
    """Un alta o una actualización del registro maestro.

    `student_id` es `None` cuando se pide un alta nueva -el almacén asigna
    uno con `generar_student_id`-, o un valor concreto cuando se pide dar de
    alta o actualizar una identidad ya conocida -un alumno que ya tenía
    `student_id` y cuyo listado se reimporta con algún dato corregido-.
    Decidir CUÁL de los dos casos es cada fila del listado no es trabajo de
    este modelo: lo hace `backend.servicios.importacion_alumnos`, que es
    quien conoce el listado entero y puede detectar duplicados y
    coincidencias antes de llegar aquí.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: str | None = None
    curso: str
    ccaa_code: str
    centro_code: str
    ciclo_code: str
    estado_matricula: str = ESTADO_MATRICULA_INICIAL
    platform_id: str | None = None

    @field_validator("student_id", "ccaa_code", "centro_code", "ciclo_code", "estado_matricula")
    @classmethod
    def _normalizar_campo(cls, valor):
        return _normalizar(valor) if valor is not None else valor

    @field_validator("platform_id")
    @classmethod
    def _normalizar_platform_id(cls, valor):
        # El ID de CESUR no es un código que este sistema invente: es el que
        # trae la plataforma, y forzarlo a mayúsculas podría desfigurarlo si
        # alguna vez lleva un formato sensible a caja. Aquí solo se recortan
        # espacios; una cadena vacía se trata como si no se hubiera dado.
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None


class AlumnoRegistrado(AlumnoNuevo):
    """Una fila ya guardada del registro maestro. Sigue sin nombre."""

    id: str
    student_id: str


def validar_alumno(alumno: AlumnoNuevo) -> None:
    """Lo que la base de datos rechazaría, dicho en castellano y antes de
    escribir nada -mismo papel que `validar()` en
    `backend/persistencia/modelos.py` para una entrega-."""
    validar_curso(alumno.curso)
    if alumno.ccaa_code not in CCAA_CODES:
        raise ValueError(
            f"«{alumno.ccaa_code}» no es una comunidad autónoma reconocida. "
            "Las comunidades son: " + ", ".join(CCAA_CODES) + "."
        )
    if not alumno.centro_code:
        raise ValueError("El alumno necesita un centro.")
    if alumno.ciclo_code not in CICLO_CODES:
        raise ValueError(
            f"«{alumno.ciclo_code}» no es un ciclo reconocido. Los ciclos "
            "son: " + ", ".join(CICLO_CODES) + "."
        )
    if alumno.estado_matricula not in ESTADOS_MATRICULA:
        raise ValueError(
            f"«{alumno.estado_matricula}» no es un estado de matrícula "
            "reconocido. Los estados son: " + ", ".join(ESTADOS_MATRICULA) + "."
        )
    if alumno.student_id is not None and not PATRON_STUDENT_ID.match(alumno.student_id):
        raise ValueError(
            f"«{alumno.student_id}» no tiene forma de student_id. Se "
            "escribe ALU- seguido de dos dígitos de curso y cuatro de "
            "número, por ejemplo ALU-260001."
        )


def error_de_platform_id_duplicado(platform_id: str, student_id_existente: str) -> ValueError:
    """El mismo texto en los dos almacenes: mismo patrón que
    `error_de_atribucion` en `backend/persistencia/modelos.py`, que existe
    exactamente por esto -que el docente no debería leer un aviso distinto
    según haya credenciales de Supabase o no-."""
    return ValueError(
        f"El ID de plataforma «{platform_id}» ya está asignado a "
        f"{student_id_existente}. Dos identidades no pueden compartir el "
        "mismo ID de CESUR: revisa el listado antes de reimportar esta fila."
    )
