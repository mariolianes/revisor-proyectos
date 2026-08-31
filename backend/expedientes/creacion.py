"""Crea en disco el árbol que describe `backend/expedientes/estructura.py`.

Esta arquitectura vive en el equipo del docente, nunca en el repositorio -el
mismo motivo por el que `REVISOR_CARPETA_ENTREGAS` y `REVISOR_DATOS_LOCALES`
tienen que apuntar fuera de él (`backend/configuracion.py`)-. Antes de crear
una sola carpeta, este módulo comprueba con `revisar_carpeta` que la raíz
indicada no cae dentro del árbol versionado, reutilizando exactamente la
misma guarda -no una copia que pueda desincronizarse de la original-.

Hay un segundo riesgo distinto de escribir en el sitio equivocado: escribir
*demasiado* en el sitio correcto. Una lista de alumnos mal generada, un
fichero duplicado o una variable de entorno que apunte, por error, a la
versión equivocada de un CSV pueden pedir cientos de expedientes de golpe.
`LIMITE_LOTE_SIN_CONFIRMAR` y `LIMITE_DIRECTORIOS_DE_SEGURIDAD` existen para
que esa clase de error se detenga antes de escribir nada, no a mitad de
tanda: se cuenta primero cuánto se va a crear -contar no toca disco- y solo
se crea después de esa cuenta, nunca al revés.

Toda operación es idempotente: volver a pedir la misma estructura, o el
mismo expediente, no falla ni duplica nada. `ResultadoDeConstruccion`
distingue lo que se ha creado de lo que ya existía, para que quien llame -la
CLI de `tools/crear_estructura_expedientes.py`, sobre todo- pueda decir con
precisión qué ha cambiado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from backend.configuracion import ProblemaDeCarpeta, revisar_carpeta
from backend.expedientes.estructura import (
    ConfiguracionExpedientes,
    id_de_alumno_valido,
    ruta_entrada_incidencias,
    ruta_entrada_pendientes,
    rutas_del_expediente,
)

# Más de esto en una sola llamada a `crear_expedientes_en_lote` exige
# `confirmar=True`. El número no pretende ser "el" límite correcto -no hay
# uno objetivamente correcto-, solo uno lo bastante bajo para que crear la
# estructura de un curso entero (varios cientos de alumnos) no pase
# desapercibido como si fuera un lote pequeño de pruebas.
LIMITE_LOTE_SIN_CONFIRMAR = 20

# Tope absoluto de directorios que una sola llamada puede crear, confirmada o
# no. Un curso real de este sistema no se acerca a esta cifra ni de lejos
# -unos pocos cientos de alumnos, unas pocas decenas de carpetas cada uno-;
# superarla es la señal de que algo está mal formado -una lista de alumnos
# duplicada muchas veces, una configuración corrupta-, no de que el curso sea
# grande.
LIMITE_DIRECTORIOS_DE_SEGURIDAD = 5000


@dataclass(frozen=True)
class ResultadoDeConstruccion:
    """Qué ha pasado al pedir una estructura: lo nuevo y lo que ya estaba."""

    creadas: list[Path] = field(default_factory=list)
    ya_existian: list[Path] = field(default_factory=list)

    def __add__(self, otro: "ResultadoDeConstruccion") -> "ResultadoDeConstruccion":
        return ResultadoDeConstruccion(
            creadas=self.creadas + otro.creadas,
            ya_existian=self.ya_existian + otro.ya_existian,
        )


class LoteDemasiadoGrande(ValueError):
    """Un lote pide más expedientes de los que se crean sin confirmar."""


class LimiteDeSeguridadSuperado(ValueError):
    """Una sola llamada pediría más directorios que `LIMITE_DIRECTORIOS_DE_SEGURIDAD`."""


def problema_de_raiz(raiz_repositorio: Path, raiz_expedientes: Path) -> ProblemaDeCarpeta | None:
    """Por qué `raiz_expedientes` no sirve como raíz de esta arquitectura, o
    `None` si sirve.

    Reutiliza `backend.configuracion.revisar_carpeta` tal cual: la regla -no
    dentro del repositorio, tiene que existir, tiene que ser una carpeta- es
    idéntica a la que ya protege `REVISOR_CARPETA_ENTREGAS` y
    `REVISOR_DATOS_LOCALES`, y una copia propia de esa comprobación es
    exactamente el tipo de duplicado que podría desincronizarse el día que
    alguien corrija una sin acordarse de la otra.
    """
    return revisar_carpeta(raiz_repositorio, raiz_expedientes)


def _crear_todas(raiz_expedientes: Path, relativas: list[Path]) -> ResultadoDeConstruccion:
    """Crea cada ruta de `relativas`, colgada de `raiz_expedientes`.

    Se asume que quien llama ya ha comprobado `problema_de_raiz` y el límite
    de seguridad: esta función no repite esas guardas, solo escribe. Cada
    ruta se crea con `parents=True`, así que el orden de la lista no importa
    -una subcarpeta de entrega puede llegar antes que su padre en la lista y
    de todas formas se crea bien-.
    """
    creadas: list[Path] = []
    ya_existian: list[Path] = []
    for relativa in relativas:
        destino = raiz_expedientes / relativa
        if destino.is_dir():
            ya_existian.append(destino)
            continue
        destino.mkdir(parents=True, exist_ok=True)
        creadas.append(destino)
    return ResultadoDeConstruccion(creadas=creadas, ya_existian=ya_existian)


def planificar_estructura_base(cfg: ConfiguracionExpedientes) -> list[Path]:
    """Todas las carpetas de la estructura fija del curso -las ocho de
    primer nivel y la bandeja de entrada de cada comunidad y fase-, sin
    tocar disco. No incluye ningún expediente de alumno: esos se piden aparte,
    con `crear_expediente` o `crear_expedientes_en_lote`, porque su número
    depende de la matrícula y no de la arquitectura.
    """
    relativas: list[Path] = [Path(c.carpeta) for c in cfg.carpetas_raiz]
    for comunidad in cfg.comunidades:
        for fase in cfg.fases:
            relativas.append(ruta_entrada_pendientes(cfg, comunidad.codigo, fase.codigo))
        relativas.append(ruta_entrada_incidencias(cfg, comunidad.codigo))
    return relativas


def construir_estructura_base(
    raiz_repositorio: Path, raiz_expedientes: Path, cfg: ConfiguracionExpedientes,
) -> ResultadoDeConstruccion:
    """Crea la estructura fija del curso -sin expedientes de alumno-.

    Es idempotente: si ya existe, no falla ni duplica nada, y lo que ya
    existía se devuelve en `ya_existian` en vez de en `creadas`.
    """
    problema = problema_de_raiz(raiz_repositorio, raiz_expedientes)
    if problema is not None:
        raise ValueError(problema.motivo)

    relativas = planificar_estructura_base(cfg)
    if len(relativas) > LIMITE_DIRECTORIOS_DE_SEGURIDAD:
        raise LimiteDeSeguridadSuperado(
            f"La estructura base pediría {len(relativas)} carpetas, más del "
            f"límite de seguridad ({LIMITE_DIRECTORIOS_DE_SEGURIDAD}). Eso no "
            "es un curso grande, es una configuración rota: revisa "
            f"{cfg.__class__.__module__}."
        )
    return _crear_todas(raiz_expedientes, relativas)


def planificar_expediente(cfg: ConfiguracionExpedientes, id_alumno: str) -> list[Path]:
    """Las carpetas del expediente de un alumno, sin tocar disco.

    Lanza `ValueError` si `id_alumno` no tiene la forma exigida
    -`rutas_del_expediente` ya hace esa comprobación-, para que un ID mal
    escrito se detenga aquí y no cree una carpeta con un nombre que nadie
    reconocerá después.
    """
    return rutas_del_expediente(cfg, id_alumno)


def crear_expediente(
    raiz_repositorio: Path, raiz_expedientes: Path, cfg: ConfiguracionExpedientes,
    id_alumno: str,
) -> ResultadoDeConstruccion:
    """Crea el expediente de un único alumno. Idempotente, igual que
    `construir_estructura_base`."""
    problema = problema_de_raiz(raiz_repositorio, raiz_expedientes)
    if problema is not None:
        raise ValueError(problema.motivo)

    relativas = planificar_expediente(cfg, id_alumno)
    return _crear_todas(raiz_expedientes, relativas)


def crear_expedientes_en_lote(
    raiz_repositorio: Path, raiz_expedientes: Path, cfg: ConfiguracionExpedientes,
    ids_alumnos: list[str], *, confirmar: bool = False,
) -> ResultadoDeConstruccion:
    """Crea el expediente de varios alumnos a la vez.

    Dos guardas antes de escribir nada, además de `problema_de_raiz`:

    - Más de `LIMITE_LOTE_SIN_CONFIRMAR` IDs sin `confirmar=True` se rechaza
      con `LoteDemasiadoGrande`: la lista puede venir de un CSV mal
      preparado -duplicado, con la matrícula de otro curso, con una columna
      desplazada- y crear cientos de expedientes por ese motivo no debe
      poder ocurrir sin que alguien lo confirme a propósito.
    - El total de directorios planificados -no el número de alumnos, el
      número de carpetas que resultarían- tampoco puede superar
      `LIMITE_DIRECTORIOS_DE_SEGURIDAD`, ni siquiera confirmado: un lote
      confirmado de tamaño razonable y una configuración rota que multiplique
      las carpetas por expediente son dos fallos distintos, y confirmar el
      primero no debe abrir la puerta al segundo.

    Un ID inválido en la lista detiene el lote entero antes de crear nada
    -se planifica todo primero, se escribe después-, en vez de crear los
    expedientes válidos y saltarse el malo en silencio: un lote es una
    entrega de matrícula, y una fila rota en ella suele ser un error de
    origen que hay que corregir, no un alumno que se descarta solo.
    """
    problema = problema_de_raiz(raiz_repositorio, raiz_expedientes)
    if problema is not None:
        raise ValueError(problema.motivo)

    if len(ids_alumnos) > LIMITE_LOTE_SIN_CONFIRMAR and not confirmar:
        raise LoteDemasiadoGrande(
            f"Se piden {len(ids_alumnos)} expedientes de una vez, más del "
            f"límite de {LIMITE_LOTE_SIN_CONFIRMAR} sin confirmar. Si es lo "
            "que quieres de verdad, repite con confirmar=True (--confirmo en "
            "la línea de órdenes). Si no lo es, revisa la lista antes: puede "
            "venir de un fichero duplicado o de la matrícula de otro curso."
        )

    for id_alumno in ids_alumnos:
        if not id_de_alumno_valido(cfg, id_alumno):
            raise ValueError(
                f"«{id_alumno}» no tiene la forma de un ID de expediente "
                f"({cfg.expediente_alumno.patron_id}, por ejemplo "
                f"{cfg.expediente_alumno.ejemplo_id}). No se ha creado ningún "
                "expediente del lote."
            )

    relativas_por_alumno = [planificar_expediente(cfg, i) for i in ids_alumnos]
    total = sum(len(r) for r in relativas_por_alumno)
    if total > LIMITE_DIRECTORIOS_DE_SEGURIDAD:
        raise LimiteDeSeguridadSuperado(
            f"Este lote pediría {total} carpetas en total, más del límite de "
            f"seguridad ({LIMITE_DIRECTORIOS_DE_SEGURIDAD}). No se ha creado "
            "nada."
        )

    resultado = ResultadoDeConstruccion()
    for relativas in relativas_por_alumno:
        resultado = resultado + _crear_todas(raiz_expedientes, relativas)
    return resultado
