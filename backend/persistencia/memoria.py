"""Almacén en memoria.

No es un doble de pruebas: es lo que corre cuando no hay credenciales de
Supabase, para que el sistema sea utilizable desde el primer minuto. Por eso
declara `es_duradero = False` y el frontend lo enseña. Un sistema que
aparenta guardar y no guarda es peor que uno que no guarda.
"""

import uuid
from datetime import datetime

from backend.persistencia.auditoria import (
    Anotacion,
    de_cambio_de_estado,
    de_correccion,
    de_entrega,
)
from backend.persistencia.alumnos import (
    ESTADO_MATRICULA_INICIAL,
    AlumnoNuevo,
    AlumnoRegistrado,
    error_de_platform_id_duplicado,
    generar_student_id,
    validar_alumno,
)
from backend.persistencia.consumo import RegistroDeConsumo
from backend.persistencia.correccion import (
    LIMITE_DE_OBSERVACION,
    Correccion,
    validar_textos_acotados,
)
from backend.persistencia.modelos import (
    ESTADO_INICIAL,
    EntregaNueva,
    EntregaRegistrada,
    choca_con_lo_declarado,
    error_de_atribucion,
    validar,
    validar_estado,
    validar_fase,
)
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe


class AlmacenEnMemoria:
    """Las entregas de esta sesión, y solo de esta sesión."""

    def __init__(self) -> None:
        self._entregas: dict[str, EntregaRegistrada] = {}
        # El registro de auditoría del §19.1. Se escribe desde los propios
        # métodos que guardan, no desde quien los llama: ver el docstring de
        # `backend/persistencia/auditoria.py`.
        self._registro: list[Anotacion] = []
        # El registro maestro de alumnos (Task del importador de listados):
        # student_id -> sus datos, sin nombre. Es también de aquí de donde
        # sale el ciclo de un alumno para una entrega -antes vivía en un
        # diccionario aparte, `_ciclo_del_alumno`-, porque en Supabase el
        # ciclo lo lleva la misma fila `alumno` que ahora crea o consulta el
        # registro maestro (`alumno.ciclo`), y tenerlo en dos sitios en
        # memoria abría la puerta a que un alumno dado de alta por el
        # listado con un ciclo, y luego declarado con otro por una entrega,
        # respondiera un ciclo en Supabase y otro en memoria: justo la clase
        # de divergencia que `tests/persistencia/test_paridad.py` existe
        # para atrapar.
        self._alumnos: dict[str, dict] = {}
        # La modalidad es del proyecto, no de la entrega: en la base de
        # datos la lleva la tabla `proyecto` -clave (alumno_id,
        # version_criterios), igual que `AlmacenSupabase._proyecto`- y
        # `entrega` no la tiene. La primera modalidad DECLARADA manda -no
        # necesariamente la de la primera entrega: una fase TEMA puede
        # llegar sin modalidad todavía, antes de validar el tema (§3.2), y
        # la primera entrega que sí la declare es la que la fija-, y
        # ninguna declaración posterior la sustituye: cambiarla es una
        # decisión expresa del profesor (§3.2) que este almacén no toma por
        # su cuenta. Ver el aviso que compone `api/entregas.confirmar`
        # cuando lo declarado no coincide.
        self._modalidad_del_proyecto: dict[tuple[str, str], str] = {}
        # Una corrección por entrega: guardar dos veces sobre la misma
        # entrega sustituye el valor del diccionario entero, igual que
        # `unique (entrega_id)` sustituye la fila en Supabase.
        self._correcciones: dict[str, Correccion] = {}
        # A diferencia de `_correcciones`, es una lista y no un diccionario
        # por entrega: una entrega real de un mismo alumno puede analizarse
        # más de una vez -un reanálisis, un intento que falló y se repite-,
        # y cada ejecución es su propio gasto. Sustituir por la última
        # perdería el histórico de lo gastado, que es justo el dato que
        # esto existe para conservar.
        self._consumos: list[RegistroDeConsumo] = []

    @property
    def es_duradero(self) -> bool:
        return False

    def registrar(self, entrega: EntregaNueva) -> EntregaRegistrada:
        validar(entrega)
        ya_estaba = self.por_huella(entrega.huella)
        if ya_estaba is not None:
            # Misma huella es el mismo archivo, aunque lo hayan renombrado.
            # Pero si lo que se declara ahora no coincide con la ficha bajo
            # la que ya está, es un error de atribución: no se resuelve en
            # silencio a favor del primero que llegó.
            if choca_con_lo_declarado(ya_estaba, entrega):
                raise error_de_atribucion(ya_estaba, entrega)
            return ya_estaba

        # El ciclo con el que se dio de alta el alumno manda sobre el que se
        # declara ahora, igual que en Supabase: allí `_alumno` reutiliza la
        # fila existente y el ciclo vive en ella. Si el alumno no existe
        # todavía en el registro maestro -no vino de un listado importado-,
        # se crea aquí mismo con el ciclo declarado, igual que
        # `AlmacenSupabase._alumno` inserta una fila mínima de `alumno` la
        # primera vez que le llega una entrega de un código nuevo.
        alumno_existente = self._alumnos.get(entrega.codigo_alumno)
        if alumno_existente is None:
            alumno_existente = {
                "id": str(uuid.uuid4()),
                "student_id": entrega.codigo_alumno,
                "curso": "",
                "ccaa_code": "",
                "centro_code": "",
                "ciclo_code": entrega.ciclo,
                "estado_matricula": ESTADO_MATRICULA_INICIAL,
                "platform_id": None,
            }
            self._alumnos[entrega.codigo_alumno] = alumno_existente
        datos = entrega.model_dump()
        datos["ciclo"] = alumno_existente["ciclo_code"]
        clave_proyecto = (entrega.codigo_alumno, entrega.version_criterios)
        if entrega.modalidad is not None and clave_proyecto not in self._modalidad_del_proyecto:
            self._modalidad_del_proyecto[clave_proyecto] = entrega.modalidad
        datos["modalidad"] = self._modalidad_del_proyecto.get(clave_proyecto)
        registrada = EntregaRegistrada(
            id=str(uuid.uuid4()),
            recibida_en=datetime.now(),
            estado=ESTADO_INICIAL,
            motivo_bloqueo=None,
            **datos,
        )
        self._entregas[registrada.id] = registrada
        self.anotar(de_entrega(registrada))
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
        validar_fase(fase)
        from backend.vigilancia.nombres import FASES

        orden_actual = (FASES.index(fase), version)
        candidatas = [
            entrega
            for entrega in self._entregas.values()
            if entrega.codigo_alumno == codigo_alumno
            # Una fila guardada puede llevar una fase que ya no está en
            # FASES -un dato heredado de otra versión de criterios-. Sin
            # este filtro, FASES.index(entrega.fase) revienta con un
            # ValueError en inglés en vez de descartar sin más esa fila.
            # AlmacenSupabase.anterior_de ya descarta estas filas -no puede
            # indexar lo que no está en el enum de la tabla-; aquí se hace
            # lo mismo para que los dos almacenes se comporten igual.
            and entrega.fase in FASES
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
        self.anotar(de_cambio_de_estado(cambiada, motivo))
        return cambiada

    def guardar_correccion(
        self,
        entrega_id: str,
        informe: Informe,
        devolucion: Devolucion | None,
        motor: str,
        aviso: str | None = None,
        limite_de_observacion: int = LIMITE_DE_OBSERVACION,
    ) -> str:
        # Misma regla que en Supabase, y antes de tocar nada: los límites de
        # longitud no dependen de que haya credenciales.
        validar_textos_acotados(informe, devolucion, limite_de_observacion)
        identificador = str(uuid.uuid4())
        self._correcciones[entrega_id] = Correccion(
            id=identificador, informe=informe, devolucion=devolucion,
            motor=motor, aviso=aviso,
        )
        self.anotar(de_correccion(entrega_id, informe, motor))
        return identificador

    def correccion_de(self, entrega_id: str) -> Correccion | None:
        return self._correcciones.get(entrega_id)

    def anotar(self, anotacion: Anotacion) -> None:
        self._registro.append(anotacion)

    def listar_registro(self) -> list[Anotacion]:
        return list(self._registro)

    def registrar_consumo(self, registro: RegistroDeConsumo) -> None:
        """Añade el registro a la lista de esta sesión. No es duradero -se
        pierde al cerrar, igual que el resto de este almacén (`es_duradero`
        es `False`)-."""
        self._consumos.append(registro)

    def consumos(self) -> list[RegistroDeConsumo]:
        """Lo registrado en esta sesión. No forma parte del `Protocol`
        `Almacen` -solo lo usan las pruebas, para comprobar qué se ha
        guardado-; `AlmacenSupabase` no lo implementa porque leer el
        histórico completo desde la base de datos es un consumo aparte que
        nadie ha pedido todavía."""
        return list(self._consumos)

    def dar_de_alta_alumno(self, alumno: AlumnoNuevo) -> AlumnoRegistrado:
        validar_alumno(alumno)

        if alumno.platform_id is not None:
            chocado = next(
                (
                    datos for sid, datos in self._alumnos.items()
                    # Acotado al curso: entre cursos, el mismo ID de CESUR es
                    # un repetidor con identidad nueva, no un choque
                    # (`decisiones#3-repetidores`).
                    if sid != alumno.student_id
                    and datos.get("platform_id") == alumno.platform_id
                    and datos.get("curso") == alumno.curso
                ),
                None,
            )
            if chocado is not None:
                raise error_de_platform_id_duplicado(
                    alumno.platform_id, chocado["student_id"]
                )

        if alumno.student_id is not None:
            student_id = alumno.student_id
        else:
            existentes_del_curso = [
                sid for sid, datos in self._alumnos.items()
                if datos["curso"] == alumno.curso
            ]
            student_id = generar_student_id(alumno.curso, existentes_del_curso)

        existente = self._alumnos.get(student_id)
        datos = {
            "id": existente["id"] if existente else str(uuid.uuid4()),
            "student_id": student_id,
            "curso": alumno.curso,
            "ccaa_code": alumno.ccaa_code,
            "centro_code": alumno.centro_code,
            "ciclo_code": alumno.ciclo_code,
            "estado_matricula": alumno.estado_matricula,
            "platform_id": alumno.platform_id,
            "matricula_anterior": alumno.matricula_anterior,
        }
        self._alumnos[student_id] = datos
        return AlumnoRegistrado(**datos)

    def listar_alumnos(self) -> list[AlumnoRegistrado]:
        return [AlumnoRegistrado(**datos) for datos in self._alumnos.values()]

    def alumnos_por_platform_id(self, platform_id: str) -> list[AlumnoRegistrado]:
        return [
            AlumnoRegistrado(**datos) for datos in self._alumnos.values()
            if datos.get("platform_id") == platform_id
        ]
