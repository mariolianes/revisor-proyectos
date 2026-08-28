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
