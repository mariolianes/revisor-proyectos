"""Las reglas de GOVERNANCE.md, lo que vigilan y lo que no, y lo que falta
oficialmente.

Cuántas son no se cuenta aquí ni en ningún comentario: se cuenta solo. Un
comentario que dijera «las siete» habría que acordarse de tocarlo cada vez
que GOVERNANCE.md gana una regla, y ese acordarse es exactamente lo que
falló cuando llegó R8. `test_estado_reglas.py` compara este módulo con
GOVERNANCE.md y con lo que de verdad usa el verificador, así que un olvido
no depende de que alguien se acuerde de leer un comentario.
"""

import re
from collections import defaultdict
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
    # 'verificada' si hay código que la comprueba; 'parcial' si protege una
    # parte real de lo que promete y dejar el resto sin cubrir es un hecho
    # conocido, no un olvido; 'pendiente' si la regla está escrita en
    # GOVERNANCE.md pero todavía no vigila nada.
    estado: str


# Lo que cada regla NO cubre. Sale en pantalla porque una regla que promete
# más de lo que hace es peor que una regla que no existe. Por eso está cada
# regla de GOVERNANCE.md y no solo las que ya funcionan: callarse la que
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
        "Dentro del análisis y el borrador de devolución -la parte del flujo "
        "de corrección que ya existe- la reserva es real por dos vías: "
        "`backend/api/entregas.py` no tiene ninguna operación que fije "
        "APROBADO ni COMUNICADO, así que el backend no puede aprobar una nota "
        "ni comunicarla al alumno aunque quisiera; y `backend/salidas/"
        "borrador.py` descarta cualquier borrador donde el motor haya escrito "
        "una nota, un apto o no apto, o un juicio de autoría, en vez de "
        "dejarlo pasar. La revisión observación por observación "
        "(`POST /entregas/{identificador}/revision`) es la única vía por la "
        "que una valoración pasa a considerarse aceptada.",
        "El resto de las nueve decisiones del §13 no tiene todavía ningún "
        "estado que bloquear, porque esa parte del flujo no está construida: "
        "no hay operación para autorizar un cambio de tema o modalidad, para "
        "decidir si una carencia impide avanzar de fase, ni para valorar la "
        "presentación ante el tribunal. Interpretar una situación ambigua o "
        "excepcional tampoco es un estado del sistema: sigue siendo, como "
        "todo lo demás aquí, algo que decide el profesor fuera de esta "
        "pantalla.",
        "parcial"),
    Descripcion(
        "R8", "La prosa en castellano lleva sus tildes",
        "La instrucción que se manda al motor, el informe técnico, el "
        "borrador de devolución y los textos de la interfaz llevan sus "
        "tildes. Mira solo prosa -cadenas, comentarios, docstrings y el "
        "cuerpo de los documentos-, nunca identificadores, claves ni rutas.",
        "El vocabulario es una lista corta de palabras cuya forma sin tilde "
        "no es válida en castellano por sí sola: una palabra fuera de esa "
        "lista puede llevar una falta y pasar sin protesta. Un texto sin "
        "tildes correcto -la salida de una función que las quita, o un PDF "
        "simulado que se compara carácter a carácter- necesita su "
        "`sin-tilde:` o `sin-tilde-fichero:` con motivo, o la regla lo "
        "denuncia igual.",
        "verificada"),
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


def _agrupar_por_regla(infracciones: list) -> dict[str, list[Infraccion]]:
    """Reparte las infracciones por código de regla, sin perder ninguna.

    Antes esto se hacía con un diccionario que solo conocía los códigos de
    `REGLAS`: una infracción que llegara con un código sin describir aquí
    -R8 antes de esta corrección, o mañana una R9 recién añadida al
    verificador y todavía sin su `Descripcion`- se filtraba con un
    `if infraccion.regla in por_regla`, y el docente veía «conforme» y «0
    infracciones» sobre un repositorio que no lo estaba. `defaultdict` no
    descarta nada: cualquier código que aparezca queda agrupado, lo describa
    `REGLAS` o no, y `construir_reglas` decide después qué hacer con lo que
    sobra.
    """
    por_regla: dict[str, list[Infraccion]] = defaultdict(list)
    for infraccion in infracciones:
        por_regla[infraccion.regla].append(Infraccion(
            regla=infraccion.regla,
            fichero=infraccion.fichero,
            detalle=infraccion.detalle,
        ))
    return por_regla


def construir_reglas(infracciones: list) -> list[Regla]:
    """La lista de reglas que ve el profesor, a partir de `REGLAS` y de lo
    que ha encontrado el verificador.

    Ninguna infracción se pierde: una que llegue con un código que `REGLAS`
    no describe sale igual, agrupada bajo una entrada genérica que dice
    exactamente eso -que a `backend/api/estado.py` le falta describirla-, en
    vez de desaparecer de la pantalla. Es la misma garantía que
    `test_estado_reglas.py` comprueba de forma estática antes de que el
    código llegue a ejecutarse: aquí es la red que queda si, aun así, algo se
    escapa.
    """
    por_regla = _agrupar_por_regla(infracciones)
    codigos_descritos = {regla.codigo for regla in REGLAS}

    reglas = [
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
    ]

    for codigo in sorted(set(por_regla) - codigos_descritos):
        reglas.append(Regla(
            codigo=codigo,
            nombre="Regla sin describir en esta pantalla",
            vigila="",
            limite=(
                f"El verificador ha encontrado infracciones de «{codigo}», "
                "pero backend/api/estado.py todavía no la describe. Añade "
                "una Descripcion para este código en REGLAS."
            ),
            estado="sin_describir",
            infracciones=len(por_regla[codigo]),
            detalles=por_regla[codigo],
        ))

    return reglas


@router.get("/estado")
def obtener_estado(peticion: Request) -> EstadoGobernanza:
    raiz: Path = peticion.app.state.raiz
    infracciones = ejecutar(raiz, [], False)
    return EstadoGobernanza(
        conforme=not infracciones,
        reglas=construir_reglas(infracciones),
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
