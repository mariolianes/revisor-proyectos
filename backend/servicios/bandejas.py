"""Recorrer las bandejas y admitir lo que hay dentro.

Es lo que enchufa `backend/servicios/admision.py` a la arquitectura del
docente: hasta ahora la admisión existía y no la llamaba nadie.

Solo se miran las carpetas `PENDIENTES` de cada comunidad y fase. Es la regla
que él escribió con todas las letras -«solo se vigilan las carpetas
PENDIENTES»- y la que hace que `INCIDENCIAS` sea un destino y no un origen:
si se vigilara, lo que la admisión aparta por no poder identificarlo volvería
a entrar en el circuito en la pasada siguiente, una y otra vez.

**La comunidad y la fase salen de la ruta, no del archivo.** Un trabajo que
está en `AND_ANDALUCIA/E02/PENDIENTES` es de Andalucía y de la segunda
entrega porque el docente lo dejó ahí, y eso es un dato suyo, no una
deducción del sistema. Por eso aquí no hay ninguna heurística sobre el
nombre del fichero para averiguar la fase: la fase ya se sabe.

**Nada de lo que hay aquí sale del equipo.** Los nombres de los alumnos entran
desde el listado local para poder identificar, y no salen: lo que se devuelve
son `Admision`, que no llevan ninguno.
"""

from __future__ import annotations

from pathlib import Path

from backend.expedientes.estructura import (
    ConfiguracionExpedientes,
    ruta_entrada_pendientes,
)
from backend.identificacion.determinista import CandidatoLocal
from backend.servicios.admision import Admision, EntregaAdmitida, admitir


def candidatos_del_curso(almacen, listado_local) -> list[CandidatoLocal]:
    """Los alumnos con los que se puede comparar un archivo.

    El identificador, el centro y el ciclo salen del registro maestro -que sí
    viaja-; el nombre sale del listado local del equipo del docente, que no.
    Un alumno sin nombre en el listado entra igual, con el nombre vacío: no
    se le podrá identificar por nombre, pero sí por identificador de
    plataforma, y omitirlo lo haría invisible también para eso.
    """
    nombres = listado_local.todos() if listado_local is not None else {}
    return [
        CandidatoLocal(
            student_id=alumno.student_id,
            nombre=nombres.get(alumno.student_id, ""),
            platform_id=alumno.platform_id,
        )
        for alumno in almacen.listar_alumnos()
    ]


def ya_admitidas_de(almacen) -> list[EntregaAdmitida]:
    """Lo ya registrado, en la forma que la admisión necesita para reconocer
    un duplicado o un conflicto de versión."""
    return [
        EntregaAdmitida(
            student_id=entrega.codigo_alumno,
            fase=entrega.fase,
            version=entrega.version,
            huella=entrega.huella,
        )
        for entrega in almacen.listar()
    ]


def archivos_pendientes(
    cfg: ConfiguracionExpedientes, raiz_expedientes: Path
) -> list[tuple[Path, str, str]]:
    """Todo lo que espera en una carpeta PENDIENTES.

    Devuelve `(ruta, código de comunidad, código de fase)`. Una carpeta que
    todavía no existe en disco no es un error: la estructura se crea cuando
    el docente la crea, y hasta entonces esa comunidad simplemente no tiene
    nada esperando.
    """
    encontrados = []
    for comunidad in cfg.comunidades:
        for fase in cfg.fases:
            carpeta = raiz_expedientes / ruta_entrada_pendientes(
                cfg, comunidad.codigo, fase.codigo
            )
            if not carpeta.is_dir():
                continue
            for archivo in sorted(carpeta.iterdir()):
                if archivo.is_file():
                    encontrados.append((archivo, comunidad.codigo, fase.codigo))
    return encontrados


def recorrer_bandejas(
    *,
    cfg: ConfiguracionExpedientes,
    raiz_repositorio: Path,
    raiz_expedientes: Path,
    almacen,
    listado_local=None,
) -> list[Admision]:
    """Admite todo lo que espera en las bandejas, en orden.

    Cada archivo se admite contra el estado que dejó el anterior -no contra
    una foto tomada al empezar-: dos versiones del mismo trabajo en la misma
    bandeja tienen que salir como versión 1 y versión 2, no las dos como
    versión 1. Es la razón de que `ya_admitidas` se vaya ampliando dentro del
    bucle en vez de calcularse una sola vez.

    No registra nada en el almacén: devuelve lo que ha pasado con cada
    archivo. Quién decide registrarlo, y cuándo, no es de este módulo -la
    entrega la confirma el docente, y esa frontera es de las que no conviene
    mover sin que él lo pida-.
    """
    candidatos = candidatos_del_curso(almacen, listado_local)
    ya_admitidas = ya_admitidas_de(almacen)

    resultados = []
    for archivo, comunidad, fase in archivos_pendientes(cfg, raiz_expedientes):
        resultado = admitir(
            archivo=archivo,
            codigo_comunidad=comunidad,
            codigo_fase=fase,
            cfg=cfg,
            raiz_repositorio=raiz_repositorio,
            raiz_expedientes=raiz_expedientes,
            candidatos=candidatos,
            ya_admitidas=ya_admitidas,
        )
        resultados.append(resultado)
        if resultado.admitido and resultado.student_id and resultado.huella:
            ya_admitidas.append(EntregaAdmitida(
                student_id=resultado.student_id,
                fase=resultado.fase or fase,
                version=resultado.version or 1,
                huella=resultado.huella,
            ))
    return resultados
