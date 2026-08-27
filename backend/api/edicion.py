"""El endpoint de guardado. Un único camino, sin atajos."""

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.servicios.transaccion import CambioDeValor, Resultado, guardar

router = APIRouter(prefix="/api")


class PeticionGuardar(BaseModel):
    ancla: str
    texto_nuevo: str
    cambios: list[CambioDeValor]
    motivo: str
    fuente: str
    hash_esperado: str


@router.post("/guardar")
def guardar_cambio(cuerpo: PeticionGuardar, peticion: Request) -> Resultado:
    raiz: Path = peticion.app.state.raiz
    return guardar(
        raiz=raiz,
        ancla=cuerpo.ancla,
        texto_nuevo=cuerpo.texto_nuevo,
        cambios=cuerpo.cambios,
        motivo=cuerpo.motivo,
        fuente=cuerpo.fuente,
        hash_esperado=cuerpo.hash_esperado,
    )
