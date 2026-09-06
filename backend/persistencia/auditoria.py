"""El registro de auditoría del §19.1: qué se hizo, cuándo y con qué criterios.

La tabla `registro` existe desde el esquema inicial, citando este apartado, y
hasta hoy **no la escribía nadie**. Se descubrió mirando la base después del
primer recorrido completo del circuito: entrega, análisis, corrección y
revisión, y cero filas de auditoría.

El §19.1 enumera lo que hay que poder reconstruir:

| Dato | Motivo |
|---|---|
| ID de ejecución | Reconstruir qué ocurrió |
| Código de alumno y fase | Relacionar la corrección |
| Hash o nombre/versionado del archivo | Identificar la entrada sin alterarla |
| Versión de criterios | Explicar el juicio |
| Fecha y estado | Controlar el proceso |
| Decisiones docentes | Diferenciar propuesta y resultado final |

**Dónde se anota, y por qué ahí.** Dentro de los métodos del almacén que
escriben, no en quien los llama. Un registro que depende de que alguien se
acuerde de invocarlo acaba con huecos justo en los caminos menos
transitados -que son los que más falta hace poder reconstruir-. Anotando en
el punto de escritura, una vía nueva hacia la base queda auditada por
construcción o no llega a existir.

**Qué no entra aquí, nunca.** Ni el texto del trabajo, ni una cita, ni el
nombre de nadie. `detalle` lleva códigos, cifras y estados. Es la misma
frontera que ya respeta `ejecucion_motor`, y hay un test que la comprueba
sobre cada anotación que el sistema sabe producir.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

# El único actor del sistema. No hay autenticación ni la va a haber mientras
# esto sea la herramienta personal del docente (§19), así que el campo
# `usuario` de la tabla no distingue a nadie: dice que lo hizo él, desde su
# equipo. Se escribe una constante y no un nombre, que además sería un dato
# personal en una tabla que no debe llevarlos.
DOCENTE = "docente"

# Las acciones que el sistema sabe anotar hoy. Se enumeran para que una
# acción escrita a mano con otro nombre no se cuele y parta el histórico en
# dos vocabularios.
ENTREGA_REGISTRADA = "ENTREGA_REGISTRADA"
ESTADO_CAMBIADO = "ESTADO_CAMBIADO"
CORRECCION_GUARDADA = "CORRECCION_GUARDADA"

ACCIONES: tuple[str, ...] = (
    ENTREGA_REGISTRADA,
    ESTADO_CAMBIADO,
    CORRECCION_GUARDADA,
)

# Tope de lo que cabe en `detalle`, contado sobre su forma serializada. No
# es una restricción de la base: es la guarda que impide que alguien meta
# aquí, sin darse cuenta, un trozo del trabajo del alumno. Un detalle
# legítimo -códigos, cifras, estados- no se acerca a este número.
LIMITE_DE_DETALLE = 1000


class Anotacion(BaseModel):
    """Una línea del registro de auditoría."""

    model_config = ConfigDict(extra="forbid")

    accion: str
    entidad: str | None = None
    entidad_id: str | None = None
    version_criterios: str | None = None
    detalle: dict = Field(default_factory=dict)
    usuario: str = DOCENTE
    ocurrido_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def model_post_init(self, _contexto) -> None:
        # Las dos comprobaciones van aquí y no en quien construye la
        # anotación: pydantic las envuelve en un `ValidationError`, que
        # conserva el mensaje. Se prefiere eso a una excepción propia que
        # alguien pudiera olvidarse de provocar.
        if self.accion not in ACCIONES:
            raise ValueError(
                f"«{self.accion}» no es una acción conocida del registro. "
                "Las que hay son: " + ", ".join(ACCIONES) + "."
            )
        import json

        largo = len(json.dumps(self.detalle, ensure_ascii=False, default=str))
        if largo > LIMITE_DE_DETALLE:
            raise ValueError(
                f"El detalle de esta anotación ocupa {largo} caracteres y el "
                f"límite es {LIMITE_DE_DETALLE}. En el registro van códigos, "
                "cifras y estados, nunca texto del trabajo ni citas."
            )


def de_entrega(entrega) -> Anotacion:
    """La anotación de una entrega que acaba de registrarse.

    Lleva lo que pide el §19.1: código de alumno y fase para relacionar la
    corrección, huella y nombre para identificar la entrada sin alterarla, y
    versión de criterios para explicar el juicio.
    """
    return Anotacion(
        accion=ENTREGA_REGISTRADA,
        entidad="entrega",
        entidad_id=entrega.id,
        version_criterios=entrega.version_criterios,
        detalle={
            "codigo_alumno": entrega.codigo_alumno,
            "fase": entrega.fase,
            "version": entrega.version,
            "huella": entrega.huella,
            "nombre_archivo": entrega.nombre_archivo,
            "estado": entrega.estado,
        },
    )


def de_cambio_de_estado(entrega, motivo: str | None) -> Anotacion:
    """El «fecha y estado» del §19.1.

    No lleva el estado del que se venía, y es deliberado: averiguarlo exigía
    una lectura más contra la base en cada cambio, y el histórico ya lo dice
    -el estado anterior es el de la línea anterior de esta misma entrega-.
    Pagar una petición por dato que ya está en la secuencia no compensa.
    """
    return Anotacion(
        accion=ESTADO_CAMBIADO,
        entidad="entrega",
        entidad_id=entrega.id,
        version_criterios=entrega.version_criterios,
        detalle={
            "codigo_alumno": entrega.codigo_alumno,
            "fase": entrega.fase,
            "estado": entrega.estado,
            "motivo": motivo,
        },
    )


def de_correccion(entrega_id: str, informe, motor: str) -> Anotacion:
    """Las «decisiones docentes» del §19.1: qué propuso el sistema y qué
    aprobó él, en la misma línea, que es lo que permite distinguirlos.

    No se anota ninguna observación ni ninguna cita: solo cuántas hubo. El
    contenido ya está en `correccion`, y repetirlo aquí sería meter texto del
    trabajo en la tabla de auditoría.
    """
    valoraciones = getattr(informe, "valoraciones", []) or []
    return Anotacion(
        accion=CORRECCION_GUARDADA,
        entidad="correccion",
        entidad_id=entrega_id,
        version_criterios=getattr(informe, "version_criterios", None),
        detalle={
            "motor": motor,
            "semaforo_propuesto": getattr(informe, "semaforo_propuesto", None),
            "semaforo_final_docente": getattr(informe, "semaforo_final_docente", None),
            "con_alertas": getattr(informe, "con_alertas", None),
            "valoraciones": len(valoraciones),
            "con_evidencia_localizada": sum(
                1 for v in valoraciones if getattr(v, "evidencia_localizada", False)
            ),
        },
    )
