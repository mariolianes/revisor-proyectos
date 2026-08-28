"""Los dos almacenes se comportan igual, y hay quien lo comprueba.

`AlmacenEnMemoria` y `AlmacenSupabase` prometen responder lo mismo a lo
mismo: es lo que sostiene que el sistema se comporte igual con credenciales
y sin ellas, y lo que permite que el docente pruebe sin base de datos y
luego corrija con ella. Hasta aquí esa promesa no la sostenía nada: los dos
almacenes tenían la comprobación de identidad duplicada palabra por
palabra, y quitar «ciclo» de la tupla en uno solo de los dos dejaba los
tests en verde.

Esta batería ejecuta la misma secuencia contra los dos y compara los
resultados. Lo que no se puede comparar directamente se dice, no se omite:

- `id` es un UUID que genera cada almacén por su cuenta -uuid4 en memoria,
  la base de datos en Supabase-, así que no puede coincidir. Lo que sí se
  compara es que sea coherente dentro de cada almacén: que `por_id` del id
  que devolvió `registrar` traiga esa misma entrega.
- `recibida_en` lo pone el reloj en el momento de registrar, así que
  tampoco. Lo que sí se compara es el orden que produce en `listar`.

Todo lo demás -los nueve campos que el docente ve- se compara campo a
campo, y los errores por su mensaje entero, porque el mensaje también es
parte de la respuesta: el profesor no debería leer un texto distinto según
haya credenciales.
"""

import re

import pytest

from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva, EntregaRegistrada
from backend.persistencia.supabase import AlmacenSupabase

# `postgrest` viene de tests/conftest.py.

URL = "https://ejemplo.supabase.co"
CLAVE = "clave-de-servicio"

UUID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"
NO_ES_UN_UUID = "esto-no-es-un-uuid"

# El aviso de una huella repetida nombra la ficha con la que choca, y ese
# identificador no puede coincidir entre los dos almacenes -lo genera cada
# uno por su cuenta-. Se sustituye por una marca antes de comparar: lo que
# se compara es el mensaje, no el UUID que lleva dentro.
UN_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)


def _entrega(fase: str, version: int = 1, **cambios) -> EntregaNueva:
    datos = dict(
        codigo_alumno="AF023", ciclo="DAM", fase=fase, version=version,
        nombre_archivo=f"AF023_DAM_{fase}_20260115_v{version}.pdf",
        huella=f"{fase.lower()}{version}".ljust(64, "0"),
        version_criterios="v2026-2027",
    )
    datos.update(cambios)
    return EntregaNueva(**datos)


def _comparable(valor):
    """Lo que de una respuesta se puede comparar entre los dos almacenes.

    Sin `id` ni `recibida_en`, por lo que dice el docstring del módulo. Un
    `ValueError` se compara por su mensaje: el aviso es tan parte de la
    respuesta como el dato.
    """
    if valor is None or isinstance(valor, (str, bool, int)):
        return valor
    if isinstance(valor, list):
        return [_comparable(elemento) for elemento in valor]
    if isinstance(valor, ValueError):
        return UN_UUID.sub("«id de la ficha»", f"ValueError: {valor}")
    assert isinstance(valor, EntregaRegistrada), valor
    return (
        valor.codigo_alumno, valor.ciclo, valor.fase, valor.version,
        valor.nombre_archivo, valor.huella, valor.estado,
        valor.motivo_bloqueo, valor.version_criterios,
    )


def _intentar(operacion):
    """Ejecuta y devuelve el resultado, o el ValueError si lo hubo."""
    try:
        return operacion()
    except ValueError as fallo:
        return fallo


@pytest.fixture
def dos_almacenes(postgrest):
    """El de memoria y el de Supabase contra el PostgREST simulado."""
    return (
        AlmacenEnMemoria(),
        AlmacenSupabase(URL, CLAVE, cliente=postgrest.cliente()),
    )


def _los_dos(dos_almacenes, guion):
    """Ejecuta el mismo guión contra los dos y devuelve las dos respuestas."""
    return tuple(_comparable(guion(almacen)) for almacen in dos_almacenes)


# --- registrar -------------------------------------------------------------


def test_registrar_devuelve_lo_mismo_en_los_dos(dos_almacenes) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes, lambda a: a.registrar(_entrega("E1"))
    )

    assert memoria == supabase


def test_la_misma_huella_con_los_mismos_datos_no_duplica_en_ninguno(
    dos_almacenes,
) -> None:
    """El caso legítimo: el mismo archivo confirmado dos veces."""
    def guion(almacen):
        primera = almacen.registrar(_entrega("E1"))
        segunda = almacen.registrar(_entrega("E1"))
        # Ni ficha nueva ni error: la que ya había. El id no se compara
        # entre almacenes, pero sí que sea el mismo dentro de cada uno.
        assert primera.id == segunda.id
        return [segunda, almacen.listar()]

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert len(memoria[1]) == 1


def test_la_misma_huella_con_datos_distintos_falla_igual_en_los_dos(
    dos_almacenes,
) -> None:
    """Un error de atribución, con el mismo texto en los dos almacenes."""
    def guion(almacen):
        almacen.registrar(_entrega("E1"))
        return _intentar(
            lambda: almacen.registrar(_entrega("E2", huella=_entrega("E1").huella))
        )

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria.startswith("ValueError: El archivo")
    assert "E1" in memoria and "E2" in memoria


@pytest.mark.parametrize("campo,valor", [
    ("codigo_alumno", "AF999"),
    ("fase", "E2"),
    ("version", 2),
])
def test_cada_campo_de_identidad_choca_igual_en_los_dos(
    dos_almacenes, campo: str, valor
) -> None:
    """Los tres campos, uno a uno.

    Es el test que faltaba: con la comprobación duplicada en los dos
    almacenes, quitar un campo de la tupla de uno solo no rompía nada.
    """
    def guion(almacen):
        almacen.registrar(_entrega("E1"))
        # Se parte de la misma entrega y se cambia un solo campo: así lo
        # único que difiere es ese campo, y la huella sigue siendo la misma.
        otra = _entrega("E1").model_copy(update={campo: valor})
        return _intentar(lambda: almacen.registrar(otra))

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria.startswith("ValueError: El archivo")


def test_el_ciclo_no_forma_parte_de_la_identidad_en_ninguno(dos_almacenes) -> None:
    """El ciclo es del alumno, no de la entrega, y no puede acusar a nadie.

    Estuvo entre los campos de identidad y el efecto era este: el docente
    confirmaba declarando un ciclo distinto al del alumno, el sistema
    aceptaba la entrega y le ponía el ciclo del alumno, y al volver a
    confirmar el mismo archivo con los mismos datos se le decía que había
    cambiado el dato. No lo había cambiado él. La discrepancia la cuenta el
    aviso de `api/entregas.confirmar`, que informa sin bloquear.
    """
    def guion(almacen):
        almacen.registrar(_entrega("E1", ciclo="DAM"))
        # Misma huella, mismos datos, otro ciclo: no es un error de
        # atribución, es la misma entrega.
        return almacen.registrar(_entrega("E1", ciclo="DAW"))

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    # Ni excepción ni ficha nueva: la que ya había, con el ciclo del alumno.
    assert memoria[1] == "DAM"


def test_una_version_invalida_se_rechaza_igual_en_los_dos(dos_almacenes) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes,
        lambda a: _intentar(lambda: a.registrar(_entrega("E1", version=0))),
    )

    assert memoria == supabase
    assert "empieza en 1" in memoria


# --- el ciclo es del alumno ------------------------------------------------


def test_el_ciclo_es_del_alumno_y_manda_el_primero_en_los_dos(
    dos_almacenes,
) -> None:
    """En la base de datos el ciclo lo tiene `alumno` y no `entrega`.

    Con el mismo alumno declarado en dos ciclos, memoria devolvía DAW y
    listaba ['DAM', 'DAW'], mientras que Supabase devolvía DAW y listaba
    ['DAM', 'DAM'] -contradiciéndose consigo mismo entre la ficha recién
    confirmada y la lista al recargarla-. Ahora los dos hacen lo que
    respeta el esquema: el ciclo con el que se dio de alta el alumno.
    """
    def guion(almacen):
        almacen.registrar(_entrega("E1", ciclo="DAM"))
        segunda = almacen.registrar(_entrega("E2", ciclo="DAW"))
        return [segunda.ciclo, [e.ciclo for e in almacen.listar()]]

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria == ["DAM", ["DAM", "DAM"]]


# --- anterior_de -----------------------------------------------------------


def _registrar_varias(almacen):
    """TEMA, E1 y E2 del mismo alumno, y una E1 de otro para estorbar."""
    almacen.registrar(_entrega("TEMA"))
    almacen.registrar(_entrega("E1"))
    almacen.registrar(_entrega("E2"))
    almacen.registrar(_entrega(
        "E1", codigo_alumno="AF999", huella="f" * 64,
        nombre_archivo="AF999_DAM_E1_20260115_v1.pdf",
    ))


def test_anterior_de_elige_la_misma_entre_varias_candidatas(dos_almacenes) -> None:
    def guion(almacen):
        _registrar_varias(almacen)
        return almacen.anterior_de("AF023", "E3", 1)

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[2] == "E2"


def test_anterior_de_puede_ser_una_version_previa_de_la_misma_fase(
    dos_almacenes,
) -> None:
    def guion(almacen):
        almacen.registrar(_entrega("E2", version=1))
        return almacen.anterior_de("AF023", "E2", 2)

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[2:4] == ("E2", 1)


def test_anterior_de_sin_nada_previo_da_none_en_los_dos(dos_almacenes) -> None:
    def guion(almacen):
        _registrar_varias(almacen)
        return almacen.anterior_de("AF023", "TEMA", 1)

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase is None


def test_anterior_de_no_se_lleva_las_entregas_de_otro_alumno(dos_almacenes) -> None:
    def guion(almacen):
        _registrar_varias(almacen)
        return almacen.anterior_de("AF999", "E2", 1)

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[0] == "AF999"


def test_anterior_de_con_una_fase_que_no_existe_falla_igual(dos_almacenes) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes,
        lambda a: _intentar(lambda: a.anterior_de("AF023", "E9", 1)),
    )

    assert memoria == supabase
    assert "no es una fase" in memoria


# --- por_id ----------------------------------------------------------------


def test_por_id_con_el_identificador_bueno_trae_la_entrega(dos_almacenes) -> None:
    def guion(almacen):
        registrada = almacen.registrar(_entrega("E1"))
        recuperada = almacen.por_id(registrada.id)
        # El id no se compara entre almacenes, pero dentro de cada uno
        # tiene que ser el mismo: es lo que hace utilizable la URL de la ficha.
        assert recuperada is not None and recuperada.id == registrada.id
        return recuperada

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase


@pytest.mark.parametrize("identificador", [UUID_INEXISTENTE, NO_ES_UN_UUID, ""])
def test_por_id_con_un_identificador_que_no_vale_da_none_en_los_dos(
    dos_almacenes, identificador: str
) -> None:
    """Incluido el que no tiene forma de UUID, que en Postgres da un 400."""
    memoria, supabase = _los_dos(
        dos_almacenes, lambda a: a.por_id(identificador)
    )

    assert memoria == supabase is None


def test_por_huella_se_comporta_igual_en_los_dos(dos_almacenes) -> None:
    def guion(almacen):
        almacen.registrar(_entrega("E1"))
        return [almacen.por_huella(_entrega("E1").huella),
                almacen.por_huella("z" * 64)]

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[1] is None


# --- cambiar_estado --------------------------------------------------------


def test_cambiar_estado_devuelve_lo_mismo_en_los_dos(dos_almacenes) -> None:
    def guion(almacen):
        registrada = almacen.registrar(_entrega("E1"))
        return almacen.cambiar_estado(registrada.id, "ANALIZADO", None)

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[6] == "ANALIZADO"


def test_bloquear_con_motivo_lo_guarda_igual_en_los_dos(dos_almacenes) -> None:
    def guion(almacen):
        registrada = almacen.registrar(_entrega("E1"))
        almacen.cambiar_estado(registrada.id, "BLOQUEADO", "Falta el anexo.")
        return almacen.por_id(registrada.id)

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[6] == "BLOQUEADO"
    assert memoria[7] == "Falta el anexo."


@pytest.mark.parametrize("identificador", [UUID_INEXISTENTE, NO_ES_UN_UUID, ""])
def test_cambiar_estado_de_algo_que_no_existe_da_none_en_los_dos(
    dos_almacenes, identificador: str
) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes, lambda a: a.cambiar_estado(identificador, "ANALIZADO", None)
    )

    assert memoria == supabase is None


def test_un_estado_que_no_existe_falla_igual_en_los_dos(dos_almacenes) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes,
        lambda a: _intentar(lambda: a.cambiar_estado(UUID_INEXISTENTE, "PATATA", None)),
    )

    assert memoria == supabase
    assert "no es un estado del flujo" in memoria


def test_bloquear_sin_motivo_falla_igual_en_los_dos(dos_almacenes) -> None:
    """Y el estado inválido gana sobre el identificador inválido en los dos."""
    memoria, supabase = _los_dos(
        dos_almacenes,
        lambda a: _intentar(lambda: a.cambiar_estado(NO_ES_UN_UUID, "BLOQUEADO", "  ")),
    )

    assert memoria == supabase
    assert "exige decir el motivo" in memoria


# --- listar ----------------------------------------------------------------


def test_listar_da_las_mismas_entregas_en_el_mismo_orden(dos_almacenes) -> None:
    """La más reciente primero, en los dos."""
    def guion(almacen):
        _registrar_varias(almacen)
        return almacen.listar()

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    # Reverso del orden de registro: TEMA, E1, E2 y la E1 del otro alumno.
    assert [fila[0] for fila in memoria] == ["AF999", "AF023", "AF023", "AF023"]
    assert [fila[2] for fila in memoria] == ["E1", "E2", "E1", "TEMA"]


def test_listar_vacio_es_una_lista_vacia_en_los_dos(dos_almacenes) -> None:
    memoria, supabase = _los_dos(dos_almacenes, lambda a: a.listar())

    assert memoria == supabase == []


def test_es_duradero_es_lo_unico_que_los_dos_no_comparten(dos_almacenes) -> None:
    """La única diferencia declarada, y el frontend la enseña."""
    memoria, supabase = dos_almacenes

    assert memoria.es_duradero is False
    assert supabase.es_duradero is True
