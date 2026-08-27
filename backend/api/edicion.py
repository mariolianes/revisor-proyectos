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


# La función es síncrona a propósito: el guardado ejecuta git y escribe en el
# disco durante segundos, y como 'def' Starlette lo hace en un hilo del pool,
# de modo que el resto de la aplicación sigue respondiendo. Eso significa que
# dos peticiones pueden solaparse de verdad; quien lo impide es el cerrojo de
# 'guardar', que está en la transacción y no aquí para que ningún camino que
# escriba pueda saltárselo.
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
