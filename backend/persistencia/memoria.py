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
    validar_fase,
)

# Lo declarado se compara en estos campos para decidir si una huella
# repetida es de verdad el mismo archivo confirmado dos veces. El nombre o
# la ruta quedan fuera a propósito: es dónde está el fichero, no de quién
# es, y moverlo de subcarpeta no debe dar error.
_CAMPOS_DE_IDENTIDAD = ("codigo_alumno", "ciclo", "fase", "version")


def _choca_con_lo_declarado(
    existente: EntregaRegistrada, nueva: EntregaNueva
) -> bool:
    return any(
        getattr(existente, campo) != getattr(nueva, campo)
        for campo in _CAMPOS_DE_IDENTIDAD
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
            # Pero si lo que se declara ahora no coincide con la ficha bajo
            # la que ya está, es un error de atribución: no se resuelve en
            # silencio a favor del primero que llegó.
            if _choca_con_lo_declarado(ya_estaba, entrega):
                raise ValueError(
                    f"El archivo «{entrega.huella}» ya está registrado como "
                    f"{ya_estaba.codigo_alumno}/{ya_estaba.ciclo}/"
                    f"{ya_estaba.fase} v{ya_estaba.version} (ficha "
                    f"{ya_estaba.id}), pero ahora se declara como "
                    f"{entrega.codigo_alumno}/{entrega.ciclo}/{entrega.fase} "
                    f"v{entrega.version}. Si es el mismo trabajo, corrige el "
                    "dato que no coincide antes de confirmarlo."
                )
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
