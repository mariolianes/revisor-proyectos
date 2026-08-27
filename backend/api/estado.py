"""Las seis reglas, lo que vigilan y lo que no, y lo que falta oficialmente."""

import re
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from tools.verificar_gobernanza import ejecutar

router = APIRouter(prefix="/api")

# Lo que cada regla NO cubre. Sale en pantalla porque una regla que promete
# más de lo que hace es peor que una regla que no existe.
REGLAS = [
    ("R1", "Ningún criterio sin origen",
     "Todo criterio declara la sección que lo respalda.",
     "Comprueba que el ancla existe, no que su texto diga lo que el criterio afirma."),
    ("R2", "La prosa manda",
     "Si cambia una sección, hay que revisar lo que deriva de ella.",
     "Solo vigila las secciones que algún criterio cita. Editar una sección "
     "que nadie deriva no hace saltar nada."),
    ("R3", "Lo pendiente no se inventa",
     "Un criterio sin dato oficial se marca y no lleva valor.",
     "La lista de claves prohibidas es corta: otras podrían colarse."),
    ("R4", "Los criterios se congelan",
     "Una versión ya usada para corregir no se modifica.",
     "No vigila nada hasta que alguien congela una versión."),
    ("R5", "Un fichero por cambio",
     "Tocar criterios o prosa exige documentar el cambio.",
     "Exige que exista el documento, no que su contenido sea cierto."),
    ("R6", "Nada personal en el repositorio",
     "Ni entregas, ni nombres, ni datos identificativos.",
     "Es un cedazo: reconoce formatos habituales, no todos."),
]

PATRON_PENDIENTE = re.compile(r"^- \*\*([a-z0-9_]+)\*\* — (.+)$", re.M)


class Regla(BaseModel):
    codigo: str
    nombre: str
    vigila: str
    limite: str
    infracciones: int


class Pendiente(BaseModel):
    clave: str
    explicacion: str


class EstadoGobernanza(BaseModel):
    conforme: bool
    reglas: list[Regla]


@router.get("/estado")
def obtener_estado(peticion: Request) -> EstadoGobernanza:
    raiz: Path = peticion.app.state.raiz
    infracciones = ejecutar(raiz, [], False)
    conteo = {codigo: 0 for codigo, _, _, _ in REGLAS}
    for infraccion in infracciones:
        if infraccion.regla in conteo:
            conteo[infraccion.regla] += 1

    return EstadoGobernanza(
        conforme=not infracciones,
        reglas=[
            Regla(codigo=codigo, nombre=nombre, vigila=vigila,
                  limite=limite, infracciones=conteo[codigo])
            for codigo, nombre, vigila, limite in REGLAS
        ],
    )


@router.get("/pendientes")
def obtener_pendientes(peticion: Request) -> list[Pendiente]:
    raiz: Path = peticion.app.state.raiz
    ruta = raiz / "docs" / "PENDIENTE_OFICIAL.md"
    if not ruta.is_file():
        return []
    texto = ruta.read_text(encoding="utf-8")
    return [
        Pendiente(clave=clave, explicacion=explicacion)
        for clave, explicacion in PATRON_PENDIENTE.findall(texto)
    ]
