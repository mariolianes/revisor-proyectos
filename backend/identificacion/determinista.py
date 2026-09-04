"""De quién es un trabajo: la escalera determinista del docente.

`decisiones#6-identificacion` la fija en cinco prioridades, y `decisiones#4-
portada` fija la secuencia completa. Lo que este módulo garantiza es lo que
él pidió con más insistencia: **la automatización puede detenerse; lo que no
puede es asignar un trabajo a la persona equivocada**.

De ahí salen las dos reglas que gobiernan todo el fichero:

1. **La contradicción se comprueba primero.** Su prioridad 5 dice
   «Incidencias siempre», y «siempre» quiere decir que gana a cualquier
   asignación automática que las prioridades 1 a 3 hubieran concedido. Un
   trabajo cuyo identificador de plataforma apunta a un alumno y cuya portada
   nombra a otro no se asigna al primero porque el identificador tenga más
   prioridad: se detiene.
2. **Nunca se decide por parecido.** No hay umbral, no hay distancia de
   edición, no hay «el más probable». O las palabras del nombre coinciden, o
   no coinciden. Ver `backend/identificacion/nombres.py`.

**Dónde se ejecuta esto.** Solo en el equipo del docente, y antes de
minimizar. Él lo cerró así en `decisiones#4-portada`: «leer el nombre dentro
del equipo no contradice la capa de privacidad: lo que debe evitarse es
enviar el nombre al servidor o incluirlo en el texto remitido al modelo». El
orden es leer, identificar y **después** enmascarar; nunca al revés, porque
sobre un texto ya minimizado no habría nombre que reconocer.

`Identificacion`, lo que devuelve este módulo, **no lleva ningún nombre**: ni
el del alumno, ni el que se leyó de la portada. Lleva un `student_id` o una
razón para detenerse. Eso es deliberado: es el objeto que cruza la frontera
hacia el resto del sistema, y si no lleva nombre no puede filtrarlo.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.identificacion.nombres import (
    es_el_mismo_nombre,
    es_nombre_parcial_de,
    nombra_a,
    nombra_parcialmente_a,
)

# Los cinco peldaños, con el número que les da el docente en su tabla.
POR_PLATAFORMA = 1
POR_NOMBRE_COMPLETO = 2
POR_NOMBRE_Y_PORTADA = 3
SIN_CONFIRMAR = 4
CONTRADICCION = 5

# Lo que devuelve cada peldaño.
ASIGNADO = "asignacion_automatica"
INCIDENCIAS = "incidencias"


class CandidatoLocal(BaseModel):
    """Un alumno del listado local, para comparar contra él.

    Vive solo en el equipo del docente. `nombre` entra aquí y no sale: no
    aparece en `Identificacion`.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: str
    nombre: str
    platform_id: str | None = None


class Identificacion(BaseModel):
    """De quién es el trabajo, o por qué no se ha podido decidir.

    Sin nombres, a propósito: ver el docstring del módulo.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: str | None
    prioridad: int
    resultado: str
    motivo: str

    @property
    def a_incidencias(self) -> bool:
        return self.resultado == INCIDENCIAS


def _contradiccion(
    candidato_por_plataforma: CandidatoLocal | None,
    candidatos_por_nombre: list[CandidatoLocal],
    nombre_de_portada: str | None,
) -> str | None:
    """El motivo de la contradicción, o `None` si no la hay.

    Prioridad 5 del docente: «contradicción entre identificador, nombre,
    portada o matrícula → Incidencias siempre». Se comprueba antes que nada
    porque «siempre» significa que gana a las tres asignaciones automáticas.
    """
    if candidato_por_plataforma is None:
        return None

    otros_por_nombre = [
        c for c in candidatos_por_nombre
        if c.student_id != candidato_por_plataforma.student_id
    ]
    if otros_por_nombre:
        return (
            "el identificador de plataforma apunta a un alumno y el nombre "
            "del archivo a otro distinto"
        )

    if nombre_de_portada is not None and not es_el_mismo_nombre(
        nombre_de_portada, candidato_por_plataforma.nombre
    ):
        if not es_nombre_parcial_de(
            nombre_de_portada, candidato_por_plataforma.nombre
        ):
            return (
                "el identificador de plataforma apunta a un alumno y la "
                "portada nombra a otro distinto"
            )
    return None


def identificar(
    *,
    candidatos: list[CandidatoLocal],
    platform_id: str | None = None,
    nombre_del_archivo: str | None = None,
    nombre_de_portada: str | None = None,
) -> Identificacion:
    """La escalera entera, en el orden que fija el docente.

    `candidatos` son los alumnos del curso y la comunidad esperados -acotar
    esa lista es responsabilidad de quien llama, porque él pide unicidad
    «dentro del curso y comunidad esperados» y este módulo no sabe de
    matrículas-.

    `nombre_del_archivo` y `nombre_de_portada` son los nombres de persona ya
    extraídos, no el nombre del fichero en bruto: quién los extrae y cómo no
    es asunto de esta función.
    """
    por_plataforma = None
    if platform_id:
        coincidencias = [c for c in candidatos if c.platform_id == platform_id]
        if len(coincidencias) == 1:
            por_plataforma = coincidencias[0]
        elif len(coincidencias) > 1:
            return Identificacion(
                student_id=None, prioridad=CONTRADICCION, resultado=INCIDENCIAS,
                motivo=(
                    "hay más de un alumno con ese identificador de "
                    "plataforma en el curso: el listado se contradice a sí "
                    "mismo y no se puede asignar nada hasta resolverlo"
                ),
            )

    # `nombra_a` y no `es_el_mismo_nombre`: lo que llega en
    # `nombre_del_archivo` es el nombre de un fichero, que trae el del alumno
    # con palabras de más -la fase, la fecha, «TFG»-. Ver el comentario de
    # `backend/identificacion/nombres.py`.
    por_nombre = [
        c for c in candidatos
        if nombre_del_archivo and nombra_a(nombre_del_archivo, c.nombre)
    ]

    # Prioridad 5, la primera que se mira: «Incidencias siempre».
    contradiccion = _contradiccion(por_plataforma, por_nombre, nombre_de_portada)
    if contradiccion is not None:
        return Identificacion(
            student_id=None, prioridad=CONTRADICCION, resultado=INCIDENCIAS,
            motivo=contradiccion,
        )

    # Prioridad 1: identificador exacto de la plataforma.
    if por_plataforma is not None:
        return Identificacion(
            student_id=por_plataforma.student_id, prioridad=POR_PLATAFORMA,
            resultado=ASIGNADO,
            motivo="identificador de plataforma exacto",
        )

    # Prioridad 2: nombre completo, único en el curso y la comunidad.
    if len(por_nombre) == 1:
        return Identificacion(
            student_id=por_nombre[0].student_id, prioridad=POR_NOMBRE_COMPLETO,
            resultado=ASIGNADO,
            motivo="nombre completo único en el curso y la comunidad",
        )
    if len(por_nombre) > 1:
        return Identificacion(
            student_id=None, prioridad=SIN_CONFIRMAR, resultado=INCIDENCIAS,
            motivo=(
                f"el nombre coincide con {len(por_nombre)} alumnos del mismo "
                "curso y comunidad, y no hay identificador de plataforma con "
                "el que desempatar"
            ),
        )

    # Prioridad 3: nombre parcial más al menos un apellido, candidato único
    # y portada compatible. Las tres condiciones, no dos.
    if nombre_del_archivo:
        parciales = [
            c for c in candidatos
            if nombra_parcialmente_a(nombre_del_archivo, c.nombre)
        ]
        if len(parciales) == 1:
            unico = parciales[0]
            if nombre_de_portada is None:
                return Identificacion(
                    student_id=None, prioridad=SIN_CONFIRMAR,
                    resultado=INCIDENCIAS,
                    motivo=(
                        "el nombre del archivo está incompleto y hay un único "
                        "candidato, pero no se ha podido leer la portada con "
                        "la que confirmarlo"
                    ),
                )
            compatible = es_el_mismo_nombre(
                nombre_de_portada, unico.nombre
            ) or es_nombre_parcial_de(nombre_de_portada, unico.nombre)
            if compatible:
                return Identificacion(
                    student_id=unico.student_id,
                    prioridad=POR_NOMBRE_Y_PORTADA, resultado=ASIGNADO,
                    motivo=(
                        "nombre y apellido con candidato único, confirmado "
                        "por la portada"
                    ),
                )
            return Identificacion(
                student_id=None, prioridad=CONTRADICCION, resultado=INCIDENCIAS,
                motivo=(
                    "el nombre del archivo y la portada apuntan a personas "
                    "distintas"
                ),
            )
        if len(parciales) > 1:
            return Identificacion(
                student_id=None, prioridad=SIN_CONFIRMAR, resultado=INCIDENCIAS,
                motivo=(
                    f"el nombre incompleto encaja con {len(parciales)} "
                    "alumnos y no hay con qué desempatar"
                ),
            )

    # Prioridad 4: todo lo demás.
    return Identificacion(
        student_id=None, prioridad=SIN_CONFIRMAR, resultado=INCIDENCIAS,
        motivo=(
            "no hay identificador de plataforma ni un nombre que coincida "
            "con ningún alumno del curso y la comunidad esperados"
        ),
    )
