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

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    # Solo para anotar el protocolo `Almacen`. `from __future__ import
    # annotations` (arriba) hace que estas anotaciones se guarden como
    # cadenas y no se evalúen en tiempo de ejecución, así que este import no
    # se ejecuta nunca fuera de un comprobador de tipos: si se ejecutara,
    # cerraría un ciclo, porque `salidas/informe.py` importa
    # `EntregaRegistrada` de este mismo módulo.
    from backend.persistencia.alumnos import AlumnoNuevo, AlumnoRegistrado
    from backend.persistencia.correccion import Correccion
    from backend.salidas.borrador import Devolucion
    from backend.salidas.informe import Informe

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


def _normalizar_identidad(valor: str) -> str:
    """Quita todo carácter de espacio -no solo los de los extremos- y pasa
    a mayúsculas.

    `"".join(valor.split())` reparte por cualquier carácter de espacio
    Unicode -espacio normal, tabulador, NBSP- y los descarta todos, estén
    en los extremos o en medio. Un `strip()` solo limpia los bordes y deja
    pasar un espacio, un tabulador o un NBSP pegado en medio del código
    -justo lo que aparece al copiar desde un PDF o una web-, y un
    `replace(" ", "")` solo se lleva el espacio ASCII normal y deja el
    NBSP intacto. Ni un código de alumno, ni unas siglas de ciclo, ni el
    nombre de una fase llevan espacios legítimos, así que no hay nada que
    preservar.

    Normalizar y no rechazar es deliberado: el docente puede escribir la
    fase en minúsculas en el formulario, o pegar el código con algún
    espacio de más, y eso no debe fallarle.
    """
    return "".join(valor.split()).upper()


# Las tres modalidades del §3 del Documento Maestro, en el mismo vocabulario
# que declara `create type modalidad as enum (...)` en
# `supabase/migrations/20260827120000_esquema_inicial.sql`. No se inventa
# aquí: es la traducción directa de un tipo que ya existe en el esquema
# aprobado, igual que `FASES` (`backend/vigilancia/nombres.py`) traduce el
# enum `fase` de la misma migración.
MODALIDADES: tuple[str, ...] = ("PROFESIONAL", "INVESTIGACION", "REVISION")


def _normalizar_modalidad(valor: str | None) -> str | None:
    """`None` si no se declara ninguna -la modalidad se fija al validar el
    tema (§3.2), y ese paso todavía no existe en este sistema-, o el valor
    normalizado y comprobado contra `MODALIDADES` si se declara alguna.
    """
    if valor is None:
        return None
    normalizada = _normalizar_identidad(valor)
    if normalizada not in MODALIDADES:
        raise ValueError(
            f"«{valor}» no es una modalidad. Las modalidades son: "
            + ", ".join(MODALIDADES) + "."
        )
    return normalizada


class EntregaNueva(BaseModel):
    """Una entrega que el docente acaba de confirmar."""

    codigo_alumno: str
    ciclo: str
    fase: str
    version: int
    nombre_archivo: str
    huella: str
    version_criterios: str
    # La modalidad es del proyecto, no de la entrega -la tiene la tabla
    # `proyecto`, no `entrega`, en la migración-, exactamente la misma
    # relación que ya tiene `ciclo` con `alumno`. Se acepta aquí, en el
    # mismo formulario con el que se confirma cada entrega, porque hoy no
    # existe una pantalla propia de validación de tema (§3.2) desde la que
    # fijarla una sola vez; `Almacen.registrar` decide qué hacer cuando la
    # modalidad ya estaba fijada por una entrega anterior del mismo
    # proyecto y esta declara otra -ver `memoria.py` y `supabase.py`-.
    # Puede faltar: nadie debería quedar bloqueado por un dato que el
    # Documento Maestro no exige antes de la validación del tema.
    modalidad: str | None = None

    @field_validator("codigo_alumno", "ciclo", "fase")
    @classmethod
    def _normalizar(cls, valor: str) -> str:
        return _normalizar_identidad(valor)

    @field_validator("modalidad")
    @classmethod
    def _validar_modalidad(cls, valor: str | None) -> str | None:
        return _normalizar_modalidad(valor)


class EntregaRegistrada(BaseModel):
    """Una entrega ya guardada.

    Lleva la misma normalización que `EntregaNueva` en los mismos tres
    campos, y no solo por si acaso: quien construye esto no siempre parte
    de un `EntregaNueva` ya limpio. Una fila leída de Supabase puede venir
    de antes de que esta regla existiera, y sin este validador aquí
    también, un alumno guardado con un NBSP en el código volvería a quedar
    bajo una clave que `anterior_de` no reconoce.
    """

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
    # Del proyecto, igual que `ciclo` es del alumno. Ver el comentario de
    # `EntregaNueva.modalidad`.
    modalidad: str | None = None

    @field_validator("codigo_alumno", "ciclo", "fase")
    @classmethod
    def _normalizar(cls, valor: str) -> str:
        return _normalizar_identidad(valor)

    @field_validator("modalidad")
    @classmethod
    def _validar_modalidad(cls, valor: str | None) -> str | None:
        return _normalizar_modalidad(valor)


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

    def guardar_correccion(
        self,
        entrega_id: str,
        informe: Informe,
        devolucion: Devolucion | None,
        motor: str,
        aviso: str | None = None,
        # 800, el valor de `LIMITE_DE_OBSERVACION`
        # (`backend/persistencia/correccion.py`). No se importa esa
        # constante aquí -importar de `correccion.py` en este módulo
        # cerraría el ciclo que el docstring de ese fichero explica-, así
        # que este número es una copia deliberada de un límite que vive en
        # otro sitio, no un valor propio: este `Protocol` no se instancia
        # nunca, solo documenta la forma; las dos implementaciones reales
        # (`memoria.py`, `supabase.py`) sí importan la constante.
        limite_de_observacion: int = 800,
    ) -> str:
        """Guarda el análisis y sus dos salidas. Devuelve el id de la corrección.

        Una entrega tiene una corrección -lo impone `unique (entrega_id)` en
        la migración-: guardar dos veces sobre la misma entrega sustituye la
        anterior entera, no la amplía. Es lo que necesitan tanto un
        reanálisis como una revisión del docente, que en esta API son la
        misma operación: guardar de nuevo con el informe ya corregido.

        `devolucion` es `None` cuando el informe se completó pero el
        borrador no (`InformeSinBorrador`): un informe válido sin borrador es
        un resultado legítimo del análisis, no un dato a medias, y forzar
        aquí una `Devolucion` vacía lo confundiría con el caso -distinto- en
        que no hay nada que redactar.

        `limite_de_observacion` se reenvía tal cual a `validar_textos_
        acotados` (`backend/persistencia/correccion.py`): por omisión, el
        límite del motor (`LIMITE_DE_OBSERVACION`); `revisar()`
        (`backend/api/analisis.py`) llama con `LIMITE_DE_OBSERVACION_
        DOCENTE`, más holgado, porque el texto que guarda esa llamada puede
        llevar una observación que ha escrito el docente a mano, no el
        motor.

        Guardar el análisis son varias escrituras (la corrección, y una
        valoración con su evidencia por cada dimensión valorada). Si alguna
        falla a mitad, no debe quedar una corrección sin sus valoraciones ni
        una fila huérfana: la implementación deshace lo que ya escribió y
        levanta `ErrorDeAlmacen` -de `backend/persistencia/supabase.py`-, en
        vez de dejar una corrección a medio guardar que el docente vería
        como completa.
        """
        ...

    def correccion_de(self, entrega_id: str) -> Correccion | None:
        """La corrección guardada de esta entrega, o `None` si no hay ninguna.

        No hay `motor` a la vista del que decidir un formulario aparte para
        Supabase y otro para memoria: los dos devuelven exactamente el mismo
        tipo, `backend.persistencia.correccion.Correccion`, con sus dos
        salidas ya reconstruidas.
        """
        ...

    def dar_de_alta_alumno(self, alumno: AlumnoNuevo) -> AlumnoRegistrado:
        """Registra o actualiza una fila del registro maestro
        (`backend/persistencia/alumnos.py`). Nunca lleva nombre.

        Si `alumno.student_id` es `None`, asigna uno nuevo con
        `generar_student_id`, contando solo los `student_id` ya usados en
        `alumno.curso`. Si trae un valor, da de alta esa identidad si no
        existía o actualiza sus datos si ya existía -es la misma operación
        para un alta nueva y para una reimportación que corrige un dato-.

        Un `platform_id` que ya pertenece a OTRO `student_id` es un
        `ValueError` con el texto de `error_de_platform_id_duplicado`: dos
        identidades no pueden compartir el mismo ID de CESUR, y esto se
        comprueba antes de escribir nada, en los dos almacenes.
        """
        ...

    def listar_alumnos(self) -> list[AlumnoRegistrado]:
        """Todo el registro maestro. Sin nombre, como siempre."""
        ...

    def alumnos_por_platform_id(self, platform_id: str) -> list[AlumnoRegistrado]:
        """Las identidades que llevan ese ID de CESUR -normalmente ninguna o
        una, salvo el instante entre detectar un choque y resolverlo-.

        Puede devolver identidades de cursos distintos: es justo lo que
        `backend.servicios.importacion_alumnos` necesita para distinguir una
        reimportación del mismo curso -actualiza sin más- de un posible
        repetidor de un curso anterior -se detiene y lo pregunta, D-025-.
        """
        ...


# Lo declarado se compara en estos campos para decidir si una huella
# repetida es de verdad el mismo archivo confirmado dos veces. El nombre o
# la ruta quedan fuera a propósito: es dónde está el fichero, no de quién
# es, y moverlo de subcarpeta no debe dar error.
#
# El ciclo también queda fuera, y por la misma clase de razón: el ciclo no
# es de la entrega, es del alumno -en la base de datos lo tiene la tabla
# `alumno` y la tabla `entrega` no lo tiene-, así que no forma parte de la
# identidad de una entrega. Estuvo dentro, y el efecto era este: el docente
# confirmaba declarando un ciclo distinto al que el alumno tiene, el
# sistema aceptaba la entrega y le ponía el ciclo del alumno -que es lo
# correcto-, y al volver a confirmar el MISMO archivo con los MISMOS datos
# se le acusaba de haber cambiado el dato. No lo había cambiado él: lo
# había cambiado el sistema. Y era justo el caso legítimo que este
# mecanismo existe para dejar pasar, el de un trabajo que se mueve de
# carpeta y se vuelve a confirmar.
#
# La discrepancia de ciclo no se pierde: la cuenta el aviso que compone
# `api/entregas.confirmar`, que informa sin bloquear, que es el sitio
# correcto para algo que el docente tiene que mirar y decidir.
#
# Vive aquí, con el resto de validaciones compartidas, y no en cada
# almacén. Estuvo duplicado palabra por palabra en los dos, con un
# comentario que prometía que se comportaban igual, y esa promesa no la
# sostenía nada: quitar un campo de la tupla en uno solo de los dos dejaba
# los tests en verde. Ahora hay un test de paridad permanente.
CAMPOS_DE_IDENTIDAD = ("codigo_alumno", "fase", "version")


def choca_con_lo_declarado(
    existente: EntregaRegistrada, nueva: EntregaNueva
) -> bool:
    """Si lo que ahora se declara no coincide con la ficha bajo la que ya está."""
    return any(
        getattr(existente, campo) != getattr(nueva, campo)
        for campo in CAMPOS_DE_IDENTIDAD
    )


def error_de_atribucion(
    existente: EntregaRegistrada, nueva: EntregaNueva
) -> ValueError:
    """El aviso de una huella repetida con otros datos declarados.

    También compartido: los dos almacenes tienen que decir lo mismo, y el
    docente no debería leer un texto u otro según haya credenciales.
    """
    return ValueError(
        f"El archivo «{nueva.huella}» ya está registrado como "
        f"{existente.codigo_alumno}/{existente.ciclo}/"
        f"{existente.fase} v{existente.version} (ficha "
        f"{existente.id}), pero ahora se declara como "
        f"{nueva.codigo_alumno}/{nueva.ciclo}/{nueva.fase} "
        f"v{nueva.version}. Si es el mismo trabajo, corrige el "
        "dato que no coincide antes de confirmarlo."
    )


def validar_fase(fase: str) -> None:
    """Que la fase exista, dicho en castellano.

    Separado de `validar` para que cualquier operación que necesite indexar
    `FASES` —`anterior_de`, por ejemplo— pueda comprobarlo antes de indexar
    en vez de dejar que `tuple.index` reviente con un mensaje en inglés.
    """
    from backend.vigilancia.nombres import FASES

    if fase not in FASES:
        raise ValueError(
            f"«{fase}» no es una fase. Las fases son: " + ", ".join(FASES) + "."
        )


def validar(entrega: EntregaNueva) -> None:
    """Lo que la base de datos rechazaría, rechazado antes y con mejor aviso."""
    validar_fase(entrega.fase)
    if entrega.version < 1:
        raise ValueError("La versión de una entrega empieza en 1.")
    if not entrega.codigo_alumno:
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
