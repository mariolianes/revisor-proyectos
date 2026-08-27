"""Modelos compartidos por las tres APIs."""

from pydantic import BaseModel


class Seccion(BaseModel):
    """Una sección de un documento normativo."""

    ancla: str
    titulo: str
    texto: str
    hash: str
    criterios_que_la_citan: int = 0


class Documento(BaseModel):
    """Uno de los tres documentos maestros."""

    clave: str
    titulo: str
    fichero: str
    secciones: list[Seccion]
