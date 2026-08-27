"""Las siete reglas, lo que vigilan y lo que no, y lo que falta oficialmente."""

import re
from pathlib import Path
from typing import NamedTuple

from fastapi import APIRouter, Request
from pydantic import BaseModel

from tools.verificar_gobernanza import ejecutar

router = APIRouter(prefix="/api")


class Descripcion(NamedTuple):
    """Lo que se cuenta de una regla en pantalla."""

    codigo: str
    nombre: str
    vigila: str
    limite: str
    # 'verificada' si hay código que la comprueba; 'pendiente' si la regla
    # está escrita en GOVERNANCE.md pero todavía no vigila nada.
    estado: str


# Lo que cada regla NO cubre. Sale en pantalla porque una regla que promete
# más de lo que hace es peor que una regla que no existe. Por eso están las
# siete de GOVERNANCE.md y no solo las que ya funcionan: callarse la que
# falta sería exactamente el defecto contra el que se hizo esta pantalla.
REGLAS = [
    Descripcion(
        "R1", "Ningún criterio sin origen",
        "Todo criterio declara la sección que lo respalda.",
        "Comprueba que el ancla existe, no que su texto diga lo que el "
        "criterio afirma.",
        "verificada"),
    Descripcion(
        "R2", "La prosa manda",
        "Si cambia una sección, hay que revisar lo que deriva de ella.",
        "Solo vigila las secciones que algún criterio cita. Editar una sección "
        "que nadie deriva no hace saltar nada. Los guardados hechos desde este "
        "editor sellan únicamente las secciones cuyos criterios has decidido "
        "uno por uno: si dejas alguno sin mirar, esa sección no se sella y R2 "
        "sigue protestando.",
        "verificada"),
    Descripcion(
        "R3", "Lo pendiente no se inventa",
        "Un criterio sin dato oficial se marca y no lleva valor.",
        "La lista de claves prohibidas es corta: otras podrían colarse.",
        "verificada"),
    Descripcion(
        "R4", "Los criterios se congelan",
        "Una versión ya usada para corregir no se modifica.",
        "No vigila nada hasta que alguien congela una versión.",
        "verificada"),
    Descripcion(
        "R5", "Un fichero por cambio",
        "Tocar criterios o prosa exige documentar el cambio.",
        "Exige que exista el documento, no que su contenido sea cierto. Además, "
        "en esta pantalla no comprueba si un cambio se hizo sin documentar: "
        "esa mitad de la regla solo se ejecuta sobre lo que hay en staging, y "
        "aquí no hay nada en staging que mirar. Quien lo detecta es el gancho "
        "de commit, en el momento de guardar.",
        "verificada"),
    Descripcion(
        "R6", "Nada personal en el repositorio",
        "Ni entregas, ni nombres, ni datos identificativos.",
        "Es un cedazo: reconoce formatos habituales, no todos.",
        "verificada"),
    Descripcion(
        "R7", "Las reservas del profesor son bloqueos reales",
        "Las nueve decisiones del §13 del Documento Maestro -aprobar una nota, "
        "valorar la autoría, autorizar un cambio de tema...- serán estados que "
        "el sistema no puede atravesar solo: propone y se detiene.",
        "Hoy no vigila nada. Se implementa con el backend de corrección, que "
        "todavía no existe, así que ningún automatismo impide ahora mismo "
        "saltarse una de esas nueve decisiones: lo único que las sostiene es "
        "que ese backend aún no está escrito.",
        "pendiente"),
]

PATRON_PENDIENTE = re.compile(r"^- \*\*([a-z0-9_]+)\*\* — (.+)$", re.M)


class Infraccion(BaseModel):
    regla: str
    fichero: str
    detalle: str


class Regla(BaseModel):
    codigo: str
    nombre: str
    vigila: str
    limite: str
    estado: str
    infracciones: int
    # Las infracciones enteras, no solo cuántas: el número solo dice que hay
    # algo mal en alguna parte, y el docente necesita saber en qué fichero y
    # qué hacer. El texto es el mismo que imprime el verificador.
    detalles: list[Infraccion] = []


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
    por_regla: dict[str, list[Infraccion]] = {regla.codigo: [] for regla in REGLAS}
    for infraccion in infracciones:
        if infraccion.regla in por_regla:
            por_regla[infraccion.regla].append(Infraccion(
                regla=infraccion.regla,
                fichero=infraccion.fichero,
                detalle=infraccion.detalle,
            ))

    return EstadoGobernanza(
        conforme=not infracciones,
        reglas=[
            Regla(
                codigo=regla.codigo,
                nombre=regla.nombre,
                vigila=regla.vigila,
                limite=regla.limite,
                estado=regla.estado,
                infracciones=len(por_regla[regla.codigo]),
                detalles=por_regla[regla.codigo],
            )
            for regla in REGLAS
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
