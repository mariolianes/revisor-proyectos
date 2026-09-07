"""El recorrido de las bandejas, ya enchufado a la admisión.

Nombres inventados, PDF construidos aquí, y ninguna carpeta del docente.
"""

from pathlib import Path

import pymupdf
import pytest

from backend.expedientes.estructura import (
    cargar_estructura,
    ruta_entrada_incidencias,
    ruta_entrada_pendientes,
)
from backend.persistencia.alumnos import AlumnoNuevo
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.servicios.bandejas import (
    archivos_pendientes,
    candidatos_del_curso,
    recorrer_bandejas,
)

RAIZ = Path(__file__).resolve().parents[2]


class _ListadoFalso:
    """El listado local del equipo del docente, sin tocar disco."""

    def __init__(self, pares: dict[str, str]) -> None:
        self._pares = dict(pares)

    def todos(self) -> dict[str, str]:
        return dict(self._pares)


@pytest.fixture(scope="module")
def cfg():
    return cargar_estructura(RAIZ)


@pytest.fixture
def expedientes(tmp_path: Path) -> Path:
    raiz = tmp_path / "CESUR_2026-2027"
    raiz.mkdir()
    return raiz


@pytest.fixture
def almacen():
    almacen = AlmacenEnMemoria()
    almacen.dar_de_alta_alumno(AlumnoNuevo(
        student_id="ALU-260001", curso="2026-2027", ccaa_code="AND",
        centro_code="AND-MAL-01", ciclo_code="MYP",
    ))
    almacen.dar_de_alta_alumno(AlumnoNuevo(
        student_id="ALU-260002", curso="2026-2027", ccaa_code="AND",
        centro_code="AND-MAL-01", ciclo_code="MYP", platform_id="cesur-2",
    ))
    return almacen


@pytest.fixture
def listado():
    return _ListadoFalso({
        "ALU-260001": "Ana Ficticia Inventada",
        "ALU-260002": "Beatriz Supuesta Imaginaria",
    })


def _en_bandeja(
    expedientes: Path, cfg, comunidad: str, fase: str, nombre: str,
    texto: str = "Proyecto Intermodular",
) -> Path:
    carpeta = expedientes / ruta_entrada_pendientes(cfg, comunidad, fase)
    carpeta.mkdir(parents=True, exist_ok=True)
    documento = pymupdf.open()
    documento.new_page().insert_text((72, 100), texto, fontsize=12)
    ruta = carpeta / nombre
    documento.save(ruta)
    documento.close()
    return ruta


def _recorrer(cfg, expedientes, almacen, listado):
    return recorrer_bandejas(
        cfg=cfg, raiz_repositorio=RAIZ, raiz_expedientes=expedientes,
        almacen=almacen, listado_local=listado,
    )


# --- Qué se mira y qué no ---------------------------------------------------


def test_solo_se_miran_las_carpetas_pendientes(
    cfg, expedientes: Path, almacen, listado
) -> None:
    """La regla que él escribió con todas las letras. Si se vigilara
    INCIDENCIAS, lo que la admisión aparta volvería a entrar en cada pasada,
    una y otra vez."""
    _en_bandeja(expedientes, cfg, "AND", "E2", "Ana_Ficticia_Inventada.pdf")
    incidencias = expedientes / ruta_entrada_incidencias(cfg, "AND")
    incidencias.mkdir(parents=True, exist_ok=True)
    (incidencias / "algo_apartado.pdf").write_bytes(b"apartado")

    encontrados = archivos_pendientes(cfg, expedientes)

    assert [a.name for a, _, _ in encontrados] == ["Ana_Ficticia_Inventada.pdf"]


def test_una_bandeja_que_no_existe_no_es_un_error(cfg, expedientes: Path) -> None:
    """La estructura se crea cuando el docente la crea. Hasta entonces esa
    comunidad simplemente no tiene nada esperando."""
    assert archivos_pendientes(cfg, expedientes) == []


def test_la_comunidad_y_la_fase_salen_de_la_ruta(
    cfg, expedientes: Path, almacen, listado
) -> None:
    """Son un dato del docente -él dejó el archivo ahí-, no una deducción del
    sistema sobre el nombre del fichero."""
    _en_bandeja(expedientes, cfg, "MAD", "FINAL", "cualquier_cosa.pdf")

    (_, comunidad, fase), = archivos_pendientes(cfg, expedientes)

    assert (comunidad, fase) == ("MAD", "FINAL")


# --- El recorrido completo --------------------------------------------------


def test_un_trabajo_identificable_llega_a_su_expediente(
    cfg, expedientes: Path, almacen, listado
) -> None:
    _en_bandeja(expedientes, cfg, "AND", "E2", "Ana_Ficticia_Inventada_Entrega_2.pdf")

    resultado, = _recorrer(cfg, expedientes, almacen, listado)

    assert resultado.admitido
    assert resultado.student_id == "ALU-260001"
    assert (expedientes / resultado.destino).is_file()


def test_la_fase_de_la_bandeja_es_la_que_se_usa(
    cfg, expedientes: Path, almacen, listado
) -> None:
    """El archivo se llama «Entrega_2» y está en la bandeja FINAL. Manda la
    bandeja: la puso ahí el docente."""
    _en_bandeja(expedientes, cfg, "AND", "FINAL", "Ana_Ficticia_Inventada_Entrega_2.pdf")

    resultado, = _recorrer(cfg, expedientes, almacen, listado)

    assert resultado.fase == "FINAL"
    assert "05_ENTREGA_FINAL" in resultado.destino


def test_lo_que_no_se_identifica_va_a_incidencias(
    cfg, expedientes: Path, almacen, listado
) -> None:
    _en_bandeja(expedientes, cfg, "AND", "E2", "trabajo_definitivo.pdf")

    resultado, = _recorrer(cfg, expedientes, almacen, listado)

    assert resultado.a_incidencias
    assert "INCIDENCIAS" in resultado.destino


def test_dos_versiones_en_la_misma_pasada_no_salen_las_dos_como_la_primera(
    cfg, expedientes: Path, almacen, listado
) -> None:
    """Cada archivo se admite contra el estado que dejó el anterior, no
    contra una foto tomada al empezar. Sin eso, dos trabajos del mismo alumno
    en la misma bandeja se pisarían: los dos serían la versión 1 y el segundo
    sobrescribiría al primero en disco."""
    _en_bandeja(
        expedientes, cfg, "AND", "E2", "1_Ana_Ficticia_Inventada.pdf", "Primera"
    )
    _en_bandeja(
        expedientes, cfg, "AND", "E2", "2_Ana_Ficticia_Inventada.pdf", "Segunda"
    )

    primera, segunda = _recorrer(cfg, expedientes, almacen, listado)

    assert primera.version == 1
    assert segunda.version == 2
    assert primera.destino != segunda.destino
    assert (expedientes / primera.destino).is_file()
    assert (expedientes / segunda.destino).is_file()


def test_recorrer_dos_veces_no_duplica_nada(
    cfg, expedientes: Path, almacen, listado
) -> None:
    """La bandeja no se vacía sola -nada se mueve ni se borra-, así que el
    recorrido tiene que ser idempotente por su cuenta. Lo es por la huella."""
    from backend.servicios.admision import DUPLICADO_EXACTO

    _en_bandeja(expedientes, cfg, "AND", "E2", "Ana_Ficticia_Inventada.pdf")
    primera, = _recorrer(cfg, expedientes, almacen, listado)

    # El almacén no registra nada por su cuenta -eso lo confirma el docente-,
    # así que la segunda pasada se hace con lo que ya sabe la primera.
    from backend.servicios.admision import EntregaAdmitida, admitir
    segunda = admitir(
        archivo=expedientes / ruta_entrada_pendientes(cfg, "AND", "E2")
        / "Ana_Ficticia_Inventada.pdf",
        codigo_comunidad="AND", codigo_fase="E2", cfg=cfg,
        raiz_repositorio=RAIZ, raiz_expedientes=expedientes,
        candidatos=candidatos_del_curso(almacen, listado),
        ya_admitidas=[EntregaAdmitida(
            student_id="ALU-260001", fase="E2", version=1, huella=primera.huella,
        )],
    )

    assert segunda.marca == DUPLICADO_EXACTO
    assert segunda.destino is None


# --- De dónde salen los nombres ---------------------------------------------


def test_el_nombre_sale_del_listado_local_y_el_resto_del_registro(
    almacen, listado
) -> None:
    candidatos = candidatos_del_curso(almacen, listado)

    por_id = {c.student_id: c for c in candidatos}
    assert por_id["ALU-260001"].nombre == "Ana Ficticia Inventada"
    assert por_id["ALU-260002"].platform_id == "cesur-2"


def test_un_alumno_sin_nombre_en_el_listado_entra_igual(almacen) -> None:
    """Sin nombre no se le puede identificar por nombre, pero sí por
    identificador de plataforma. Omitirlo lo haría invisible también para
    eso."""
    candidatos = candidatos_del_curso(almacen, _ListadoFalso({}))

    assert len(candidatos) == 2
    assert all(c.nombre == "" for c in candidatos)


def test_sin_listado_local_no_se_rompe_el_recorrido(
    cfg, expedientes: Path, almacen
) -> None:
    """Si el docente todavía no ha importado sus listados, el recorrido no
    revienta: simplemente no identifica a nadie por nombre."""
    _en_bandeja(expedientes, cfg, "AND", "E2", "Ana_Ficticia_Inventada.pdf")

    resultado, = recorrer_bandejas(
        cfg=cfg, raiz_repositorio=RAIZ, raiz_expedientes=expedientes,
        almacen=almacen, listado_local=None,
    )

    assert resultado.a_incidencias
