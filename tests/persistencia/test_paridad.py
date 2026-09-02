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

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import ValoracionVerificada
from backend.persistencia.alumnos import AlumnoNuevo, AlumnoRegistrado
from backend.persistencia.memoria import AlmacenEnMemoria
from backend.persistencia.modelos import EntregaNueva, EntregaRegistrada
from backend.persistencia.supabase import (
    RAIZ,
    AlmacenSupabase,
    _correspondencia_de_prioridades,
)
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe

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
    if isinstance(valor, AlumnoRegistrado):
        # Sin `id`, por el mismo motivo que una `EntregaRegistrada`: lo
        # genera cada almacén por su cuenta y no puede coincidir.
        return (
            valor.student_id, valor.curso, valor.ccaa_code, valor.centro_code,
            valor.ciclo_code, valor.estado_matricula, valor.platform_id,
        )
    assert isinstance(valor, EntregaRegistrada), valor
    return (
        valor.codigo_alumno, valor.ciclo, valor.fase, valor.version,
        valor.nombre_archivo, valor.huella, valor.estado,
        valor.motivo_bloqueo, valor.version_criterios, valor.modalidad,
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


# --- la modalidad es del proyecto -------------------------------------------


def test_sin_declarar_modalidad_las_dos_entregas_quedan_sin_ella(
    dos_almacenes,
) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes, lambda a: a.registrar(_entrega("E1"))
    )

    assert memoria == supabase
    assert memoria[-1] is None


def test_la_modalidad_declarada_al_crear_el_proyecto_se_guarda_en_los_dos(
    dos_almacenes,
) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes,
        lambda a: a.registrar(_entrega("E1", modalidad="profesional")),
    )

    assert memoria == supabase
    assert memoria[-1] == "PROFESIONAL"


def test_la_modalidad_es_del_proyecto_y_manda_la_primera_en_los_dos(
    dos_almacenes,
) -> None:
    """En la base de datos la modalidad la tiene `proyecto`, con la misma
    clave (alumno_id, version_criterios) que ya usa `_proyecto` para el
    ciclo. Con el mismo alumno declarando dos modalidades, la primera que
    se fijó tiene que mandar en los dos almacenes, igual que el ciclo."""
    def guion(almacen):
        almacen.registrar(_entrega("E1", modalidad="PROFESIONAL"))
        segunda = almacen.registrar(_entrega("E2", modalidad="INVESTIGACION"))
        return [segunda.modalidad, [e.modalidad for e in almacen.listar()]]

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria == ["PROFESIONAL", ["PROFESIONAL", "PROFESIONAL"]]


def test_una_entrega_sin_modalidad_no_borra_la_ya_fijada_en_los_dos(
    dos_almacenes,
) -> None:
    def guion(almacen):
        almacen.registrar(_entrega("E1", modalidad="REVISION"))
        segunda = almacen.registrar(_entrega("E2"))
        return segunda.modalidad

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase == "REVISION"


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


# --- guardar_correccion / correccion_de -------------------------------------
#
# Task 12: el análisis y sus dos salidas. `entrega_id` va siempre atado a una
# entrega registrada de verdad -es como se usa desde la API-, aunque el
# servidor de mentira no imponga la clave ajena: registrarla primero es lo
# realista y evita que un test pase por una vía que `AlmacenSupabase` nunca
# recorre en producción.


def _valoracion(
    dimension: str = "D05",
    cita: str = "El presupuesto asciende a 4.500 euros en total del proyecto",
    evidencia_localizada: bool = True,
    nivel: str = "EN_DESARROLLO",
    prioridad: str | None = "P2",
    observacion: str = "Falta justificar las cifras con una fuente.",
    apartado: str = "5",
) -> ValoracionVerificada:
    return ValoracionVerificada(
        dimension=dimension, nivel=nivel, prioridad=prioridad,
        evidencia=Evidencia(cita=cita, apartado=apartado),
        observacion=observacion,
        evidencia_localizada=evidencia_localizada,
    )


def _informe(**cambios) -> Informe:
    datos = dict(
        identificacion={
            "alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": "1",
            "archivo": "AF023_DAM_E2_20260115_v1.pdf", "criterios": "v2026-2027",
        },
        control_administrativo=["2 páginas en total."],
        resumen="Resumen del análisis.",
        sintesis_provisional="Síntesis provisional del análisis.",
        valoraciones=[_valoracion()],
        fortalezas=[], prioridades=[_valoracion()], prioridades_descartadas=[],
        dudas=["¿El presupuesto incluye impuestos?"], indicios=[], reparos=[],
        dimensiones_ausentes=[],
        semaforo_propuesto="AMBAR",
        semaforo_final_docente=None,
        recomendacion="Aplicar cambios antes de cerrar la siguiente fase",
        nota_propuesta_sistema=None,
        estado_nota="pendiente_de_rubrica",
        version_rubrica=None,
        ponderaciones_nota=None,
        nota_final_docente=None,
        motivo_modificacion_nota=None,
        motor="simulado",
    )
    datos.update(cambios)
    return Informe(**datos)


def _devolucion() -> Devolucion:
    return Devolucion(
        apertura="Has avanzado.", fortalezas=["La estructura es clara."],
        acciones=["Justifica las cifras con una fuente."], cierre="Sigue así.",
    )


def _sin_id(correccion):
    """Lo comparable de una `Correccion`: todo menos el `id`.

    El `id` lo genera cada almacén por su cuenta -uuid4 en memoria, la base
    de datos en Supabase-, igual que el de una entrega: no puede coincidir
    entre los dos.
    """
    if correccion is None:
        return None
    return (
        correccion.informe.model_dump(mode="json"),
        correccion.devolucion.model_dump(mode="json")
        if correccion.devolucion is not None else None,
        correccion.motor,
        correccion.aviso,
    )


def test_guardar_una_correccion_y_recuperarla_da_lo_mismo_en_los_dos(
    dos_almacenes,
) -> None:
    def guion(almacen):
        entrega = almacen.registrar(_entrega("E2"))
        identificador = almacen.guardar_correccion(
            entrega.id, _informe(), _devolucion(), "simulado", "un aviso"
        )
        # El id que devuelve guardar_correccion es el mismo que trae la
        # corrección recuperada, dentro de cada almacén.
        recuperada = almacen.correccion_de(entrega.id)
        assert recuperada is not None and recuperada.id == identificador
        return recuperada

    memoria, supabase = dos_almacenes
    resultado_memoria = _sin_id(guion(memoria))
    resultado_supabase = _sin_id(guion(supabase))

    assert resultado_memoria == resultado_supabase
    assert resultado_memoria[0]["valoraciones"][0]["dimension"] == "D05"
    assert resultado_memoria[1]["acciones"]
    assert resultado_memoria[3] == "un aviso"


def test_recuperar_una_correccion_que_no_existe_da_none_en_los_dos(
    dos_almacenes,
) -> None:
    def guion(almacen):
        entrega = almacen.registrar(_entrega("E2"))
        # Nunca se analiza: no hay corrección para ninguna de las dos.
        return [
            almacen.correccion_de(entrega.id),
            almacen.correccion_de(UUID_INEXISTENTE),
            almacen.correccion_de(NO_ES_UN_UUID),
        ]

    memoria, supabase = dos_almacenes
    assert [_sin_id(c) for c in guion(memoria)] == [None, None, None]
    assert [_sin_id(c) for c in guion(supabase)] == [None, None, None]


def test_guardar_dos_veces_sobre_la_misma_entrega_sustituye_en_los_dos(
    dos_almacenes,
) -> None:
    """Una entrega tiene una corrección: `unique (entrega_id)`. La segunda
    llamada no acumula una segunda fila, sustituye la primera entera -es lo
    que necesitan tanto un reanálisis como una revisión del docente."""
    def guion(almacen):
        entrega = almacen.registrar(_entrega("E2"))
        primera_id = almacen.guardar_correccion(
            entrega.id, _informe(), _devolucion(), "simulado"
        )
        segundo_informe = _informe(
            resumen="Segundo resumen, tras revisión.",
            valoraciones=[_valoracion(dimension="D06")],
            prioridades=[_valoracion(dimension="D06")],
        )
        segunda_id = almacen.guardar_correccion(
            entrega.id, segundo_informe, _devolucion(), "simulado"
        )
        recuperada = almacen.correccion_de(entrega.id)
        assert recuperada is not None and recuperada.id == segunda_id
        return [primera_id != segunda_id, recuperada]

    memoria, supabase = dos_almacenes
    distintos_m, recuperada_m = guion(memoria)
    distintos_s, recuperada_s = guion(supabase)

    assert distintos_m is True and distintos_s is True
    assert _sin_id(recuperada_m) == _sin_id(recuperada_s)
    # La primera no sobrevive: solo queda el segundo informe.
    assert recuperada_m.informe.valoraciones[0].dimension == "D06"
    assert len(recuperada_m.informe.valoraciones) == 1


def test_guardar_una_correccion_sin_devolucion_da_lo_mismo_en_los_dos(
    dos_almacenes,
) -> None:
    """El caso de `InformeSinBorrador`: el informe es válido y ya está
    guardado; el borrador no existe. No se fuerza una `Devolucion` vacía -se
    confundiría con la que ya se produce a propósito cuando no hay nada que
    redactar-, se guarda `None`."""
    def guion(almacen):
        entrega = almacen.registrar(_entrega("E2"))
        aviso = "El informe se ha completado; el borrador no."
        almacen.guardar_correccion(
            entrega.id, _informe(), None, "simulado", aviso
        )
        return almacen.correccion_de(entrega.id)

    memoria, supabase = dos_almacenes
    recuperada_m = guion(memoria)
    recuperada_s = guion(supabase)

    assert _sin_id(recuperada_m) == _sin_id(recuperada_s)
    assert recuperada_m.devolucion is None
    assert recuperada_m.aviso == "El informe se ha completado; el borrador no."


def test_una_cita_de_mas_de_1500_caracteres_falla_igual_en_los_dos(
    dos_almacenes,
) -> None:
    """D-001: el límite de `evidencia.fragmento` en la migración, comprobado
    en código antes de escribir -por eso falla igual con o sin credenciales-.
    """
    informe_con_cita_larga = _informe(valoraciones=[_valoracion(cita="x" * 1501)])

    def guion(almacen):
        entrega = almacen.registrar(_entrega("E2"))
        return _intentar(lambda: almacen.guardar_correccion(
            entrega.id, informe_con_cita_larga, _devolucion(), "simulado"
        ))

    memoria, supabase = dos_almacenes
    fallo_memoria = guion(memoria)
    fallo_supabase = guion(supabase)

    assert isinstance(fallo_memoria, ValueError)
    assert isinstance(fallo_supabase, ValueError)
    assert str(fallo_memoria) == str(fallo_supabase)
    assert "1500" in str(fallo_memoria) or "1.500" in str(fallo_memoria)
    # Nada queda a medio guardar: ni la corrección ni sus hijas.
    assert memoria.correccion_de(memoria.listar()[0].id) is None
    assert supabase.correccion_de(supabase.listar()[0].id) is None


def test_la_tabla_estructurada_coincide_con_lo_reconstruido(
    dos_almacenes, postgrest,
) -> None:
    """Guardar una corrección escribe la información dos veces en Supabase:
    el `jsonb` que se relee (`correccion.informe`, ver
    `AlmacenSupabase.correccion_de`) y las filas de
    `valoracion_dimension`/`evidencia`, que son la proyección consultable
    por SQL y la que aplica el límite de D-001 con un `CHECK` real. Las dos
    representaciones tienen que decir lo mismo: si un cambio futuro tocara
    una y no la otra, el docente vería un informe que no cuadra con lo que
    la base de datos dice tener, y nada lo avisaría sin este test.

    Se comparan los cinco campos que se escriben por duplicado -nivel,
    prioridad, observación, y el apartado y la cita de la evidencia-, no
    solo dimensión y nivel: la prioridad es la que decide qué se traslada al
    alumno (`salidas/seleccion.py`), y una consulta SQL futura sobre la
    tabla estructurada tiene que poder confiar en que coincide con lo que el
    docente ve en la ficha, campo por campo.

    Salvo la prioridad: `valoracion_dimension.prioridad` es del tipo
    enumerado `prioridad` -CRITICA, ALTA, MEDIA, BAJA-, y lo que se relee del
    `jsonb` de `correccion.informe` habla en el vocabulario del docente -P1
    a P4-. Las dos representaciones no dicen lo mismo por error: son el
    mismo dato en dos vocabularios distintos, a propósito -es lo que declara
    `criteria/v2026-2027/prioridades.yaml`, en su campo `en_base_de_datos`-,
    así que la comparación traduce ese único campo con la misma
    correspondencia que usa `AlmacenSupabase.guardar_correccion`
    (`_correspondencia_de_prioridades`, leída del propio fichero de
    criterios y no copiada aquí a mano) antes de comparar; los otros cuatro
    campos sí tienen que coincidir tal cual.

    Se ejecuta en los dos almacenes -memoria no tiene una segunda
    representación con la que discrepar, solo guarda el objeto que se le
    da-, para que la comparación de siempre (memoria == supabase) también
    alcance a lo que aquí se reconstruye, y no solo a Supabase por su cuenta.
    """
    informe = _informe(valoraciones=[
        _valoracion(
            dimension="D05", nivel="EN_DESARROLLO", prioridad="P2",
            observacion="Falta justificar las cifras con una fuente.",
            apartado="5",
            cita="El presupuesto asciende a 4.500 euros en total",
        ),
        _valoracion(
            dimension="D06", nivel="INSUFICIENTE", prioridad="P1",
            observacion="El reparto de tareas del equipo no queda claro.",
            apartado="3",
            cita="La memoria describe el reparto de tareas del equipo",
        ),
    ])

    def guion(almacen):
        entrega = almacen.registrar(_entrega("E2"))
        almacen.guardar_correccion(entrega.id, informe, _devolucion(), "simulado")
        guardada = almacen.correccion_de(entrega.id)
        assert guardada is not None
        return {
            v.dimension: (
                v.nivel, v.prioridad, v.observacion,
                v.evidencia.apartado, v.evidencia.cita,
            )
            for v in guardada.informe.valoraciones
        }

    memoria, supabase = dos_almacenes
    reconstruido_memoria = guion(memoria)
    reconstruido_supabase = guion(supabase)

    esperado = {
        "D05": (
            "EN_DESARROLLO", "P2", "Falta justificar las cifras con una fuente.",
            "5", "El presupuesto asciende a 4.500 euros en total",
        ),
        "D06": (
            "INSUFICIENTE", "P1", "El reparto de tareas del equipo no queda claro.",
            "3", "La memoria describe el reparto de tareas del equipo",
        ),
    }
    assert reconstruido_memoria == esperado
    assert reconstruido_supabase == esperado

    # Lo que de verdad quedó en la tabla estructurada tras la escritura
    # sobre `supabase` -no el jsonb, que es lo que acaba de comparar
    # `reconstruido_supabase`-.
    correccion_id = postgrest.tablas["correccion"][0]["id"]
    filas_valoracion = {
        fila["id"]: fila for fila in postgrest.tablas["valoracion_dimension"]
        if fila["correccion_id"] == correccion_id
    }
    assert {f["dimension"] for f in filas_valoracion.values()} == {"D05", "D06"}

    estructurado = {}
    for fila in postgrest.tablas["evidencia"]:
        valoracion = filas_valoracion.get(fila["valoracion_id"])
        if valoracion is None:
            continue
        estructurado[valoracion["dimension"]] = (
            valoracion["nivel"], valoracion["prioridad"], valoracion["observacion"],
            fila["apartado"], fila["fragmento"],
        )

    # La prioridad de `reconstruido_supabase` está en el vocabulario del
    # docente -viene del `jsonb`-; la de `estructurado` está en el de la
    # columna -viene de `valoracion_dimension`, un tipo enumerado-. Se
    # traduce la del docente antes de comparar, con la misma correspondencia
    # que usa el código, no con una copiada a mano aquí.
    correspondencia = _correspondencia_de_prioridades(RAIZ, "v2026-2027")
    esperado_estructurado = {
        dimension: (nivel, correspondencia[prioridad], observacion, apartado, cita)
        for dimension, (nivel, prioridad, observacion, apartado, cita)
        in reconstruido_supabase.items()
    }
    assert estructurado == esperado_estructurado


# --- dar_de_alta_alumno / listar_alumnos / alumnos_por_platform_id ---------
#
# El registro maestro de alumnos (importador de listados). Mismo criterio que
# el resto del fichero: lo comparable de una `AlumnoRegistrado` es todo menos
# `id`, y un `ValueError` se compara por su mensaje.


def _alumno_nuevo(**cambios) -> AlumnoNuevo:
    datos = dict(
        curso="2026-2027", ccaa_code="AND", centro_code="AND-MAL-01",
        ciclo_code="MYP",
    )
    datos.update(cambios)
    return AlumnoNuevo(**datos)


def test_dar_de_alta_un_alumno_nuevo_asigna_el_mismo_student_id_en_los_dos(
    dos_almacenes,
) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes, lambda a: a.dar_de_alta_alumno(_alumno_nuevo())
    )

    assert memoria == supabase
    assert memoria[0] == "ALU-260001"


def test_el_segundo_alumno_del_curso_continua_la_secuencia_en_los_dos(
    dos_almacenes,
) -> None:
    def guion(almacen):
        almacen.dar_de_alta_alumno(_alumno_nuevo())
        return almacen.dar_de_alta_alumno(_alumno_nuevo(centro_code="AND-SEV-02"))

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[0] == "ALU-260002"


def test_dar_de_alta_con_un_student_id_ya_existente_actualiza_en_vez_de_duplicar(
    dos_almacenes,
) -> None:
    """Reimportar un listado con datos corregidos no crea una segunda fila."""
    def guion(almacen):
        primero = almacen.dar_de_alta_alumno(_alumno_nuevo())
        actualizado = almacen.dar_de_alta_alumno(_alumno_nuevo(
            student_id=primero.student_id, estado_matricula="TRASLADADO",
        ))
        return [actualizado, almacen.listar_alumnos()]

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert len(memoria[1]) == 1
    assert memoria[0][5] == "TRASLADADO"


def test_un_platform_id_duplicado_falla_igual_en_los_dos(dos_almacenes) -> None:
    def guion(almacen):
        almacen.dar_de_alta_alumno(_alumno_nuevo(platform_id="cesur-99"))
        return _intentar(lambda: almacen.dar_de_alta_alumno(
            _alumno_nuevo(centro_code="AND-SEV-02", platform_id="cesur-99")
        ))

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria.startswith("ValueError: El ID de plataforma")
    assert "cesur-99" in memoria and "ALU-260001" in memoria


def test_reimportar_el_mismo_platform_id_con_su_propio_student_id_no_choca(
    dos_almacenes,
) -> None:
    """Actualizar la propia fila con su propio ID de plataforma no es un
    choque contra sí misma."""
    def guion(almacen):
        primero = almacen.dar_de_alta_alumno(_alumno_nuevo(platform_id="cesur-99"))
        return almacen.dar_de_alta_alumno(_alumno_nuevo(
            student_id=primero.student_id, platform_id="cesur-99",
            estado_matricula="BAJA",
        ))

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert memoria[5] == "BAJA"


def test_un_alumno_invalido_falla_igual_en_los_dos(dos_almacenes) -> None:
    memoria, supabase = _los_dos(
        dos_almacenes,
        lambda a: _intentar(lambda: a.dar_de_alta_alumno(
            _alumno_nuevo(ciclo_code="DAM")
        )),
    )

    assert memoria == supabase
    assert "ciclo reconocido" in memoria


def test_listar_alumnos_vacio_es_lista_vacia_en_los_dos(dos_almacenes) -> None:
    memoria, supabase = _los_dos(dos_almacenes, lambda a: a.listar_alumnos())

    assert memoria == supabase == []


def test_alumnos_por_platform_id_encuentra_lo_mismo_en_los_dos(dos_almacenes) -> None:
    def guion(almacen):
        almacen.dar_de_alta_alumno(_alumno_nuevo(platform_id="cesur-99"))
        return [
            almacen.alumnos_por_platform_id("cesur-99"),
            almacen.alumnos_por_platform_id("no-existe"),
        ]

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase
    assert len(memoria[0]) == 1
    assert memoria[1] == []


def test_el_ciclo_del_registro_maestro_manda_sobre_el_que_declara_una_entrega(
    dos_almacenes,
) -> None:
    """Un alumno dado de alta por el listado con un ciclo, y luego declarado
    con otro por una entrega, conserva el del listado -en los dos almacenes-.

    Es la corrección que motivó unificar, en `AlmacenEnMemoria`, el
    diccionario aparte que llevaba el ciclo (`_ciclo_del_alumno`) con el
    registro maestro nuevo: antes de esa unificación, memoria no sabía nada
    del alumno dado de alta por `dar_de_alta_alumno` y dejaba mandar al
    ciclo que declarara la primera entrega, mientras que Supabase -que
    siempre leyó y escribió la misma columna `alumno.ciclo`- ya respetaba el
    ciclo del listado. Los dos almacenes respondían distinto a lo mismo.
    """
    def guion(almacen):
        registrado = almacen.dar_de_alta_alumno(_alumno_nuevo(ciclo_code="CIN"))
        entrega = almacen.registrar(_entrega("E1", codigo_alumno=registrado.student_id, ciclo="MYP"))
        return entrega.ciclo

    memoria, supabase = _los_dos(dos_almacenes, guion)

    assert memoria == supabase == "CIN"
