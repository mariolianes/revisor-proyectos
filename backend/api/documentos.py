"""Endpoints de lectura."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.modelos import Documento, Seccion
from backend.servicios.dependencias import CriterioDerivado, criterios_de
from backend.servicios.propuesta import Propuesta, proponer
from backend.servicios.repositorio import leer_seccion, listar_documentos

router = APIRouter(prefix="/api")


class SeccionConCriterios(BaseModel):
    seccion: Seccion
    criterios: list[CriterioDerivado]


class PeticionPropuesta(BaseModel):
    ancla: str
    texto_nuevo: str


def _raiz(peticion: Request) -> Path:
    return peticion.app.state.raiz


@router.get("/documentos")
def obtener_documentos(peticion: Request) -> list[Documento]:
    return listar_documentos(_raiz(peticion))


@router.get("/secciones/{ancla}")
def obtener_seccion(ancla: str, peticion: Request) -> SeccionConCriterios:
    raiz = _raiz(peticion)
    seccion = leer_seccion(raiz, ancla)
    if seccion is None:
        raise HTTPException(status_code=404, detail=f"No existe la sección «{ancla}».")
    return SeccionConCriterios(seccion=seccion, criterios=criterios_de(raiz, ancla))


@router.post("/propuesta")
def obtener_propuesta(cuerpo: PeticionPropuesta, peticion: Request) -> list[Propuesta]:
    return proponer(_raiz(peticion), cuerpo.ancla, cuerpo.texto_nuevo)
