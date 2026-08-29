"""`validar_textos_acotados`: los límites de longitud aplicados en código,
no solo en la base de datos.

D-001 acota la cita (`Evidencia.cita`), y solo la de las valoraciones tiene
una fila con CHECK en la migración (`evidencia.fragmento_acotado`). Pero el
resto de la prosa que este módulo guarda -el resumen, la observación de
cada valoración, las dudas para el docente, el detalle de cada reparo, y la
devolución entera- no tiene ningún límite propio, ni en la base de datos
-son columnas `jsonb`, sin CHECK- ni en ningún tipo del contrato
(`backend/analisis/contrato.py`). Sin acotarla, el límite de la cita se
rodea con nada más que verbosidad: un motor que en vez de citar «explicara»
pegando medio párrafo del alumno en la observación dejaría al §19 del
Documento Maestro afirmando algo que no se cumple.

Esta batería comprueba dos cosas por separado: que las citas se acotan en
sus cuatro canales (valoraciones, prioridades, fortalezas e indicios de
autoría -no solo `valoraciones`: `revisar()` (`backend/api/analisis.py`)
aplica la decisión del docente por dimensión y reutiliza el mismo resultado
en las tres listas, pero nada en los tipos obliga a que compartan objeto, y
esta validación es la última defensa antes de escribir, no el sitio para
confiar en que otra capa mantuvo la coherencia- y que `dudas` y `reparos`
quedan fuera del límite de cita por no llevar evidencia), y que cada campo
de prosa se acota con el límite que le corresponde, no uno reutilizado de
otro campo.
"""

import pytest

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import (
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    Reparo,
    ValoracionVerificada,
)
from backend.persistencia.correccion import (
    LIMITE_DE_APERTURA_O_CIERRE,
    LIMITE_DE_CITA,
    LIMITE_DE_DUDA,
    LIMITE_DE_LINEA_DE_DEVOLUCION,
    LIMITE_DE_OBSERVACION,
    LIMITE_DE_REPARO,
    LIMITE_DE_RESUMEN,
    TextoFueraDeLimite,
    validar_textos_acotados,
)
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe

_IDENTIFICACION = {
    "alumno": "AF023", "ciclo": "DAM", "fase": "E2", "version": "1",
    "archivo": "AF023_DAM_E2_20260115_v1.pdf", "criterios": "v2026-2027",
}


def _informe(**cambios) -> Informe:
    datos = dict(
        identificacion=_IDENTIFICACION, control_administrativo=[],
        resumen="Resumen.", valoraciones=[], fortalezas=[], prioridades=[],
        prioridades_descartadas=[], dudas=[], indicios=[], reparos=[],
        dimensiones_ausentes=[], semaforo="GRIS", recomendacion=None,
        motor="simulado",
    )
    datos.update(cambios)
    return Informe(**datos)


def _valoracion(
    dimension: str = "D05", cita: str = "cita corta y localizable",
    observacion: str = "observacion corta",
) -> ValoracionVerificada:
    return ValoracionVerificada(
        dimension=dimension, nivel="ADECUADO", prioridad=None,
        evidencia=Evidencia(cita=cita, apartado="5"),
        observacion=observacion, evidencia_localizada=True,
    )


def _devolucion(**cambios) -> Devolucion:
    datos = dict(
        apertura="Apertura corta.", fortalezas=["Fortaleza corta."],
        acciones=["Acción corta."], cierre="Cierre corto.",
    )
    datos.update(cambios)
    return Devolucion(**datos)


# --- las citas, en sus cuatro canales ---------------------------------------


def test_una_cita_dentro_del_limite_no_hace_nada() -> None:
    informe = _informe(valoraciones=[_valoracion(cita="x" * LIMITE_DE_CITA)])

    validar_textos_acotados(informe)  # no levanta


@pytest.mark.parametrize(
    "canal", ["valoraciones", "prioridades", "prioridades_descartadas",
              "fortalezas", "indicios"],
)
def test_una_cita_larga_se_rechaza_en_los_cinco_canales(canal: str) -> None:
    """Los cuatro tipos que llevan `Evidencia` -valoraciones, fortalezas e
    indicios de autoría-, más `prioridades` y `prioridades_descartadas` por
    separado: en principio comparten instancia con `valoraciones`
    (`analisis/verificacion.py`), y `revisar()`
    (`backend/api/analisis.py`) aplica la decisión del docente una sola vez
    por dimensión y reutiliza el mismo resultado en las tres listas. Se
    comprueban los tres por separado de todos modos, como defensa: nada en
    los tipos obliga a que compartan objeto. `dudas` y `reparos` quedan
    fuera de este test -son texto libre sin evidencia, no citan el
    documento-, pero sí tienen el suyo más abajo.
    """
    cita_larga = "x" * (LIMITE_DE_CITA + 1)
    evidencia = Evidencia(cita=cita_larga, apartado="5")

    if canal in ("valoraciones", "prioridades", "prioridades_descartadas"):
        informe = _informe(**{canal: [_valoracion(cita=cita_larga)]})
    elif canal == "fortalezas":
        informe = _informe(fortalezas=[FortalezaVerificada(
            descripcion="Fortaleza", evidencia=evidencia,
            evidencia_localizada=True,
        )])
    else:
        informe = _informe(indicios=[IndicioDeAutoriaVerificado(
            descripcion="Indicio", evidencia=evidencia,
            evidencia_localizada=True,
        )])

    with pytest.raises(ValueError, match=str(LIMITE_DE_CITA + 1)):
        validar_textos_acotados(informe)


def test_el_mensaje_no_culpa_al_alumno() -> None:
    """El límite es del sistema; si se supera es un fallo del motor, no un
    dato del alumno que recortar. El mensaje lo dice así, no como si hubiera
    que editar el trabajo del alumno.
    """
    informe = _informe(valoraciones=[_valoracion(cita="x" * (LIMITE_DE_CITA + 1))])

    with pytest.raises(ValueError) as info:
        validar_textos_acotados(informe)

    assert "fallo del motor" in str(info.value)


def test_el_fallo_lleva_los_datos_para_que_otra_capa_componga_su_mensaje() -> None:
    """`str(fallo)` asume que el texto largo lo escribió el motor -«esto
    indica un fallo del motor»-, y esa suposición no vale en todos los
    canales que guardan una corrección: `revisar()`
    (`backend/api/analisis.py`) guarda de nuevo después de aplicar una
    edición del docente, y ahí el texto lo ha escrito él a mano. Por eso
    `TextoFueraDeLimite` lleva `etiqueta`, `longitud` y `limite` como
    atributos propios -no solo dentro del mensaje-: quien la capture en ese
    canal compone su propio aviso a partir de estos tres datos, sin tener
    que analizar la frase ni heredar la acusación equivocada.
    """
    texto = "x" * (LIMITE_DE_OBSERVACION + 7)
    informe = _informe(valoraciones=[_valoracion(observacion=texto)])

    with pytest.raises(TextoFueraDeLimite) as info:
        validar_textos_acotados(informe)

    fallo = info.value
    assert fallo.etiqueta == "La observación de D05"
    assert fallo.longitud == len(texto)
    assert fallo.limite == LIMITE_DE_OBSERVACION


# --- la prosa: un límite propio por campo, no el de la cita -----------------
#
# (nombre del caso, su límite, un constructor que recibe el texto ya
# demasiado largo y devuelve `(informe, devolucion)`). `devolucion` es
# `None` salvo en los cuatro casos que la tocan: `validar_textos_acotados`
# solo la comprueba cuando se guarda -es el caso de `InformeSinBorrador`- así
# que un `Informe` sin `Devolucion` tiene que seguir aceptándose.

_CASOS_DE_PROSA = [
    ("resumen", LIMITE_DE_RESUMEN,
     lambda texto: (_informe(resumen=texto), None)),
    ("observacion_de_valoracion", LIMITE_DE_OBSERVACION,
     lambda texto: (_informe(valoraciones=[_valoracion(observacion=texto)]), None)),
    ("observacion_de_prioridad", LIMITE_DE_OBSERVACION,
     lambda texto: (_informe(prioridades=[_valoracion(observacion=texto)]), None)),
    ("observacion_de_prioridad_descartada", LIMITE_DE_OBSERVACION,
     lambda texto: (
         _informe(prioridades_descartadas=[_valoracion(observacion=texto)]), None
     )),
    ("duda_para_el_docente", LIMITE_DE_DUDA,
     lambda texto: (_informe(dudas=[texto]), None)),
    ("detalle_de_un_reparo", LIMITE_DE_REPARO,
     lambda texto: (
         _informe(reparos=[Reparo(regla="dimension_activa", detalle=texto)]), None
     )),
    ("apertura_de_la_devolucion", LIMITE_DE_APERTURA_O_CIERRE,
     lambda texto: (_informe(), _devolucion(apertura=texto))),
    ("cierre_de_la_devolucion", LIMITE_DE_APERTURA_O_CIERRE,
     lambda texto: (_informe(), _devolucion(cierre=texto))),
    ("fortaleza_de_la_devolucion", LIMITE_DE_LINEA_DE_DEVOLUCION,
     lambda texto: (_informe(), _devolucion(fortalezas=[texto]))),
    ("accion_de_la_devolucion", LIMITE_DE_LINEA_DE_DEVOLUCION,
     lambda texto: (_informe(), _devolucion(acciones=[texto]))),
]


@pytest.mark.parametrize(
    "nombre,limite,construir", _CASOS_DE_PROSA, ids=[c[0] for c in _CASOS_DE_PROSA],
)
def test_un_campo_de_prosa_dentro_de_su_limite_no_hace_nada(
    nombre: str, limite: int, construir,
) -> None:
    informe, devolucion = construir("x" * limite)

    validar_textos_acotados(informe, devolucion)  # no levanta


@pytest.mark.parametrize(
    "nombre,limite,construir", _CASOS_DE_PROSA, ids=[c[0] for c in _CASOS_DE_PROSA],
)
def test_un_campo_de_prosa_por_encima_de_su_limite_se_rechaza(
    nombre: str, limite: int, construir,
) -> None:
    informe, devolucion = construir("x" * (limite + 1))

    with pytest.raises(ValueError, match=str(limite + 1)):
        validar_textos_acotados(informe, devolucion)


def test_los_limites_de_prosa_no_son_todos_el_mismo_numero() -> None:
    """Ninguno copia el de la cita a propósito -una observación necesita
    más aire que una cita, y un borrador más aún-. Si un futuro cambio los
    igualara todos «por simplicidad», este test lo nota.
    """
    limites = {c[1] for c in _CASOS_DE_PROSA}

    assert len(limites) > 1
    assert LIMITE_DE_CITA not in limites
