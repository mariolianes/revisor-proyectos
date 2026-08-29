"""Almacén en memoria.

No es un doble de pruebas: es lo que corre cuando no hay credenciales de
Supabase, para que el sistema sea utilizable desde el primer minuto. Por eso
declara `es_duradero = False` y el frontend lo enseña. Un sistema que
aparenta guardar y no guarda es peor que uno que no guarda.
"""

import uuid
from datetime import datetime

from backend.persistencia.correccion import Correccion, validar_textos_acotados
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
        # El ciclo es del alumno, no de la entrega: en la base de datos lo
        # lleva la tabla `alumno` y la tabla `entrega` no lo tiene. Aquí
        # hace falta guardarlo aparte para no comportarse distinto que
        # AlmacenSupabase, que reutiliza el alumno ya existente con el
        # ciclo con el que se creó. El primero que se registra manda.
        self._ciclo_del_alumno: dict[str, str] = {}
        # Una corrección por entrega: guardar dos veces sobre la misma
        # entrega sustituye el valor del diccionario entero, igual que
        # `unique (entrega_id)` sustituye la fila en Supabase.
        self._correcciones: dict[str, Correccion] = {}

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
        # fila existente y el ciclo vive en ella. Sin esto, el mismo alumno
        # registrado en dos ciclos salía con un ciclo distinto en cada
        # entrega en memoria y con el primero en Supabase.
        datos = entrega.model_dump()
        datos["ciclo"] = self._ciclo_del_alumno.setdefault(
            entrega.codigo_alumno, entrega.ciclo
        )
        registrada = EntregaRegistrada(
            id=str(uuid.uuid4()),
            recibida_en=datetime.now(),
            estado=ESTADO_INICIAL,
            motivo_bloqueo=None,
            **datos,
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
        return cambiada

    def guardar_correccion(
        self,
        entrega_id: str,
        informe: Informe,
        devolucion: Devolucion | None,
        motor: str,
        aviso: str | None = None,
    ) -> str:
        # Misma regla que en Supabase, y antes de tocar nada: los límites de
        # longitud no dependen de que haya credenciales.
        validar_textos_acotados(informe, devolucion)
        identificador = str(uuid.uuid4())
        self._correcciones[entrega_id] = Correccion(
            id=identificador, informe=informe, devolucion=devolucion,
            motor=motor, aviso=aviso,
        )
        return identificador

    def correccion_de(self, entrega_id: str) -> Correccion | None:
        return self._correcciones.get(entrega_id)
