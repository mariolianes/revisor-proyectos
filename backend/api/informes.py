"""El informe por comunidad, centro, ciclo y fase (punto 7 del orden de
implantación). Todo lo que devuelve son cifras, códigos de alumno y colores
de semáforo: ningún nombre, y ningún endpoint que pudiera llegar a tenerlo
-ver el docstring de `backend/servicios/informe_centro.py`-.
"""

from fastapi import APIRouter, HTTPException, Request

from backend.persistencia.modelos import Almacen
from backend.servicios.informe_centro import InformeCentro, componer_informe_centro

router = APIRouter(prefix="/api")


def _almacen(peticion: Request) -> Almacen:
    return peticion.app.state.almacen


@router.get("/informes/centro")
def obtener_informe_centro(
    peticion: Request,
    ccaa: str | None = None,
    centro: str | None = None,
    ciclo: str | None = None,
    curso: str | None = None,
    fase: str | None = None,
) -> InformeCentro:
    """Los cinco filtros son opcionales y se combinan con Y. Sin ninguno,
    es el informe del curso entero.

    `componer_informe_centro` valida `ccaa`, `ciclo`, `fase` y `curso`
    contra sus vocabularios cerrados -`centro` no tiene uno: el catálogo de
    centros es abierto (`config/centros.yaml`)- y levanta `ValueError` con
    un texto en castellano si alguno no es válido; aquí se traduce a 400,
    igual que el resto de la API.
    """
    try:
        return componer_informe_centro(
            _almacen(peticion), ccaa=ccaa, centro=centro, ciclo=ciclo,
            curso=curso, fase=fase,
        )
    except ValueError as fallo:
        raise HTTPException(status_code=400, detail=str(fallo)) from fallo
