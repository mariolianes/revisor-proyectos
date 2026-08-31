"""El borrador de devolución, pedido como formulario y no como texto suelto."""

from pathlib import Path

import pytest

from backend.analisis.contrato import Evidencia
from backend.analisis.proveedor import ProveedorSimulado
from backend.analisis.verificacion import (
    AnalisisVerificado,
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    Reparo,
    ValoracionVerificada,
)
from backend.salidas.borrador import (
    PETICION_DEL_BORRADOR,
    BorradorNoValido,
    Devolucion,
    componer,
    instruccion_de_devolucion,
)
from backend.salidas.seleccion import seleccionar_prioridades


def _v(dimension="D05", prioridad="P2", localizada=True):
    return ValoracionVerificada(
        dimension=dimension, nivel="EN_DESARROLLO", prioridad=prioridad,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
        observacion=f"Falta justificar las cifras de {dimension}.",
        evidencia_localizada=localizada,
    )


def _fortaleza(descripcion="La estructura es clara.", localizada=True):
    return FortalezaVerificada(
        descripcion=descripcion,
        evidencia=Evidencia(cita="Otra cita bastante larga del trabajo.", apartado="2"),
        evidencia_localizada=localizada,
    )


def _indicio(descripcion="El estilo cambia de forma notable en el apartado 4."):
    return IndicioDeAutoriaVerificado(
        descripcion=descripcion,
        evidencia=Evidencia(cita="Una tercera cita larga del trabajo.", apartado="4"),
        evidencia_localizada=True,
    )


def _analisis(valoraciones, fortalezas=None, **cambios):
    """`fortalezas` son `FortalezaVerificada`, no cadenas sueltas: es el
    tipo real de `AnalisisVerificado.fortalezas` en verificacion.py."""
    datos = dict(
        valoraciones=valoraciones,
        fortalezas=fortalezas if fortalezas is not None else [_fortaleza()],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
        dimensiones_ausentes=[], reparos=[],
    )
    datos.update(cambios)
    return AnalisisVerificado(**datos)


def _devolucion(
    acciones=("Justifica las cifras del presupuesto.",),
    apertura="Has avanzado respecto a la entrega anterior.",
    fortalezas=("La estructura del documento es clara.",),
    cierre="Vas bien encaminado; céntrate en lo anterior para la siguiente fase.",
):
    return Devolucion(
        apertura=apertura,
        fortalezas=list(fortalezas),
        acciones=list(acciones),
        cierre=cierre,
    )


# --- La estructura, no un párrafo -------------------------------------------


def test_la_devolucion_es_una_estructura_no_un_parrafo() -> None:
    """De aquí sale que la coherencia se pueda comprobar contando."""
    d = _devolucion()

    assert isinstance(d.acciones, list)
    assert d.apertura and d.cierre


# --- La instrucción -----------------------------------------------------


def test_la_instruccion_solo_lleva_las_observaciones_elegidas(
    criterios_de_analisis: Path,
) -> None:
    """Lo que no pasa el filtro no se le enseña al motor siquiera."""
    analisis = _analisis([_v("D05", "P2"), _v("D07", "P4")])

    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", analisis, [_v("D05", "P2")]
    )

    assert "D05" in texto
    assert "D07" not in texto


def test_la_instruccion_prohibe_la_nota(criterios_de_analisis: Path) -> None:
    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", _analisis([_v()]), [_v()]
    )

    assert "nota" in texto.lower()


def test_la_instruccion_pide_el_formato_del_calibrador(
    criterios_de_analisis: Path,
) -> None:
    """Dos párrafos, cercano y firme: lo fija el §4 y sale del fichero."""
    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", _analisis([_v()]), [_v()]
    )

    assert "dos" in texto.lower()


def test_la_instruccion_recoge_lo_que_debe_contener_el_texto(
    criterios_de_analisis: Path,
) -> None:
    """Los cuatro elementos del §4 -avance, fortaleza, carencia, acciones-
    salen de `feedback.yaml`, no de una lista escrita a mano aquí: si el
    profesor cambiara `debe_contener`, la instrucción cambiaría con él."""
    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", _analisis([_v()]), [_v()]
    )

    assert "fortaleza" in texto.lower()
    assert "acciones priorizadas" in texto.lower()


# --- Regla 1: nunca una nota, ni puntuación, ni porcentaje, ni apto ---------


def test_una_evidencia_valida_no_se_bloquea_por_error(
    criterios_de_analisis: Path,
) -> None:
    """Control: un borrador limpio no dispara el filtro de reglas duras."""
    proveedor = ProveedorSimulado(respuestas=[_devolucion()])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))

    assert d.apertura


def test_una_nota_del_motor_nunca_llega_al_alumno(criterios_de_analisis: Path) -> None:
    """R1: el sistema propone y se detiene; la nota es del profesor."""
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(cierre="Con este trabajo, tu nota sería un notable.")
    ])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))


def test_un_porcentaje_del_motor_nunca_llega_al_alumno(
    criterios_de_analisis: Path,
) -> None:
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(cierre="Has cumplido el 80% de lo que se pedía.")
    ])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))


def test_una_fraccion_sobre_diez_nunca_llega_al_alumno(
    criterios_de_analisis: Path,
) -> None:
    """Una nota numérica sin la palabra «nota» -«7/10»- es la misma nota."""
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(cierre="Este trabajo estaria en torno a un 7/10.")
    ])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))


def test_un_apto_no_apto_del_motor_nunca_llega_al_alumno(
    criterios_de_analisis: Path,
) -> None:
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(cierre="Con estas carencias, el trabajo no es apto todavia.")
    ])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))


# --- Regla 2: nunca sin evidencia localizada --------------------------------


def test_una_evidencia_no_localizada_no_entra_en_la_instruccion(
    criterios_de_analisis: Path,
) -> None:
    """Defensa en profundidad: aunque a `instruccion_de_devolucion` le
    llegue directamente una observación sin evidencia localizada -por
    ejemplo, porque quien la llama se saltó `seleccionar_prioridades`-, esta
    función no se la enseña al motor."""
    sin_localizar = _v("D09", "P1", localizada=False)
    con_localizar = _v("D05", "P2", localizada=True)

    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027",
        _analisis([sin_localizar, con_localizar]),
        [sin_localizar, con_localizar],
    )

    assert "D09" not in texto
    assert "D05" in texto


def test_una_fortaleza_no_localizada_no_entra_en_la_instruccion(
    criterios_de_analisis: Path,
) -> None:
    fortaleza_falsa = _fortaleza("Una fortaleza que no se pudo localizar.", localizada=False)
    fortaleza_real = _fortaleza("Una fortaleza real y localizada.", localizada=True)

    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v()], fortalezas=[fortaleza_falsa, fortaleza_real]),
        [_v()],
    )

    assert "no se pudo localizar" not in texto
    assert "real y localizada" in texto


def test_componer_recorta_por_el_numero_de_fortalezas_localizadas(
    criterios_de_analisis: Path,
) -> None:
    """Si una fortaleza no tenía evidencia localizada, no cuenta para el
    hueco que el motor puede rellenar: solo cabe una, no dos."""
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(fortalezas=["La primera.", "La segunda, de mas."])
    ])
    analisis = _analisis(
        [_v()],
        fortalezas=[
            _fortaleza("Real y localizada.", localizada=True),
            _fortaleza("Sin localizar.", localizada=False),
        ],
    )

    d = componer(criterios_de_analisis, "v2026-2027", proveedor, analisis)

    assert d.fortalezas == ["La primera."]


# --- Regla 3: nunca un indicio de autoría -----------------------------------


def test_un_indicio_de_autoria_no_entra_en_la_instruccion(
    criterios_de_analisis: Path,
) -> None:
    """El §13 reserva la autoría al docente. `instruccion_de_devolucion` no
    lee `indicios_de_autoria` en ningún punto: aunque el análisis traiga
    varios, no hay manera de que aparezcan en lo que se le enseña al motor."""
    indicio = _indicio("El estilo del apartado 4 sugiere el uso de una IA.")
    analisis = _analisis([_v()], indicios_de_autoria=[indicio, indicio])

    texto = instruccion_de_devolucion(
        criterios_de_analisis, "v2026-2027", analisis, [_v()],
    )

    assert "apartado 4" not in texto
    assert "sugiere" not in texto


def test_el_motor_no_puede_colar_un_indicio_de_autoria(
    criterios_de_analisis: Path,
) -> None:
    """Aunque no se le haya enseñado ningún indicio, el motor podría
    inventarse uno -alucinarlo, o desobedecer la instrucción que se lo
    prohíbe-. Esta es la comprobación posterior, no la instrucción."""
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(cierre="Este texto parece generado por una inteligencia artificial.")
    ])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))


def test_el_motor_no_puede_colar_un_indicio_de_autoria_sin_nombrar_la_ia(
    criterios_de_analisis: Path,
) -> None:
    """La misma garantía, con una formulación que no nombra ningún modelo
    conocido: «ha sido generado por» es tan indicio como «generado por
    ChatGPT», y el §13 la reserva igual."""
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(cierre="Este apartado ha sido generado por un sistema no identificado.")
    ])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))


# --- Regla 4: nunca nada del informe interno --------------------------------


def test_nada_del_informe_interno_entra_en_la_instruccion(
    criterios_de_analisis: Path,
) -> None:
    """Dudas para el docente, reparos, y lo descartado solo por el límite de
    la economía pedagógica son del informe interno (Task 9): esta función
    no los recibe ni los lee, así que no pueden aparecer en lo que se le
    enseña al motor."""
    muchas = [_v(f"D0{i}", "P1") for i in range(1, 8)]  # 7 candidatas, caben 4
    analisis = _analisis(
        muchas,
        dudas_para_el_docente=["¿Habrá copiado el apartado 3 de otro trabajo?"],
        reparos=[Reparo(regla="evidencia_localizable", detalle="Un reparo interno cualquiera.")],
    )
    elegidas = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis).elegidas

    texto = instruccion_de_devolucion(criterios_de_analisis, "v2026-2027", analisis, elegidas)

    assert "copiado" not in texto.lower()
    assert "reparo interno" not in texto.lower()
    assert "D06" not in texto and "D07" not in texto  # descartadas por el límite


# --- El recorte de lo que el motor añade de su cosecha ----------------------


def test_componer_devuelve_lo_que_redacto_el_motor(
    criterios_de_analisis: Path,
) -> None:
    proveedor = ProveedorSimulado(respuestas=[_devolucion()])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v()]))

    assert d.apertura.startswith("Has avanzado")


def test_componer_no_pide_nada_si_no_hay_acciones_ni_fortalezas(
    criterios_de_analisis: Path,
) -> None:
    """Sin nada que decir no se gasta una llamada ni se inventa un texto."""
    proveedor = ProveedorSimulado(respuestas=[])

    d = componer(
        criterios_de_analisis, "v2026-2027", proveedor,
        _analisis([_v("D05", "P4")], fortalezas=[]),
    )

    assert d.acciones == []
    assert proveedor.llamadas == []


def test_el_motor_no_puede_anadir_acciones_de_su_cosecha(
    criterios_de_analisis: Path,
) -> None:
    """Si devuelve más acciones que las que se le dieron, se recortan.

    Es el control de coherencia por el lado que importa: el borrador no puede
    pedirle al alumno cosas que no están en el informe.
    """
    proveedor = ProveedorSimulado(respuestas=[
        _devolucion(acciones=["La que toca.", "Una que me he inventado.",
                              "Y otra mas."])
    ])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor,
                 _analisis([_v("D05", "P2")]))

    assert len(d.acciones) == 1


def test_el_borrador_no_se_pide_con_el_texto_vacio(criterios_de_analisis) -> None:
    """La API de OpenAI responde 400 si el campo del texto llega vacío, y así
    estaba: el borrador no se generó nunca contra el motor real.

    No lo cazó ningún test porque todos usan `ProveedorSimulado`, que acepta
    cualquier cosa —el mismo punto ciego que dejó pasar la prioridad «P1»
    contra el enum de la base de datos—. Se vio ejecutando el flujo entero
    contra el servicio de verdad, y este test es lo que impide que vuelva:
    comprueba lo que se le pide al proveedor, no lo que el proveedor
    responde.

    Lo que sigue importando, y por eso se mira aparte: en ese hueco no puede
    ir el trabajo del alumno. La instrucción ya lleva las prioridades
    verificadas con sus citas; el documento no viaja dos veces.
    """
    proveedor = ProveedorSimulado(respuestas=[_devolucion()])
    analisis = _analisis([_v()])

    componer(criterios_de_analisis, "v2026-2027", proveedor, analisis)

    _, texto = proveedor.llamadas[0]
    assert texto.strip(), "el proveedor recibió el texto vacío y la API real lo rechaza"
    assert texto == PETICION_DEL_BORRADOR
    # Y no es el trabajo: ninguna cita del análisis viaja en ese hueco.
    for v in analisis.valoraciones:
        assert v.evidencia.cita not in texto


# --- D-020: el borrador no puede decir menos de lo que dice el semáforo ----


def test_un_rojo_con_su_p1_en_elegidas_no_se_bloquea(
    criterios_de_analisis: Path,
) -> None:
    """Control: el caso normal -un P1 fiable que sí llega a `elegidas`,
    porque `seleccionar_prioridades` lo ordena primero- no dispara la
    comprobación de coherencia. Sin esto, no se podría distinguir un falso
    positivo de la protección real."""
    proveedor = ProveedorSimulado(respuestas=[_devolucion()])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v("D05", "P1")]))

    assert d.apertura


def test_un_p1_excluido_del_alumno_rechaza_un_borrador_rojo(
    criterios_de_analisis: Path,
) -> None:
    """Rotura deliberada: si `prioridades.yaml` marcara P1 con
    `llega_al_alumno: nunca` -un error de configuración, no el valor real del
    repositorio-, `seleccionar_prioridades` dejaría `elegidas` vacía aunque
    exista un P1 fiable, porque ya no está en el `orden` que decide quién
    puede llegar al alumno (`backend/salidas/seleccion.py`). El semáforo
    seguiría diciendo ROJO -`semaforo_por_valoraciones` no mira
    `llega_al_alumno`, solo `evidencia_localizada`-, y el borrador se
    quedaría sin ninguna acción que lo explique: exactamente lo que describió
    el docente sobre P07, un color severo con un texto que no lo sostiene.
    `componer` tiene que rechazarlo antes de llamar al motor.

    Nótese que la mutación «obvia» -bajar
    `economia_pedagogica.prioridades_maximas` a 0 en `feedback.yaml`- NO
    sirve para esta prueba: `_maximo` en `seleccion.py` lee ese valor con
    `... or _MAXIMO_POR_OMISION`, y en Python `0 or 4` da `4` -un 0 explícito
    se trata como «no puesto» y el límite por omisión sigue aplicando-. Es un
    quirk de ese módulo, no de esta comprobación, y por eso esta prueba
    fuerza el hueco por el lado de `prioridades.yaml` en su lugar.
    """
    import yaml

    fichero = criterios_de_analisis / "criteria" / "v2026-2027" / "prioridades.yaml"
    datos = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    for entrada in datos:
        if entrada["codigo"] == "P1":
            entrada["llega_al_alumno"] = "nunca"
    fichero.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")

    proveedor = ProveedorSimulado(respuestas=[_devolucion()])

    with pytest.raises(BorradorNoValido):
        componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v("D05", "P1")]))

    assert proveedor.llamadas == [], "no hacía falta llamar al motor: el dato ya era incoherente"


def test_un_p3_en_verde_con_alertas_no_se_bloquea(
    criterios_de_analisis: Path,
) -> None:
    """Control adicional: con el mapeo de D-019, un P3 sin P1 ni P2 propone
    VERDE_CON_ALERTAS, y esa misma prioridad sí llega a `elegidas` -no hay
    incoherencia que bloquear en el caso normal de la nueva escala."""
    proveedor = ProveedorSimulado(respuestas=[_devolucion(acciones=["La única prioridad."])])

    d = componer(criterios_de_analisis, "v2026-2027", proveedor, _analisis([_v("D05", "P3")]))

    assert d.apertura


def test_la_instruccion_incluye_el_color_calculado_y_su_lectura_calibrada(
    criterios_de_analisis: Path,
) -> None:
    """La mitigación de D-020 para el tono: el motor recibe el color y su
    texto `calibrado` -tal cual lo declara `semaforo.yaml`-, no un texto
    inventado en este módulo, para anclar la severidad de `apertura` y
    `cierre` a lo que ya se calculó."""
    analisis = _analisis([_v("D05", "P1")])
    elegidas = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis).elegidas

    texto = instruccion_de_devolucion(criterios_de_analisis, "v2026-2027", analisis, elegidas)

    assert "ROJO" in texto
    assert "carencia" in texto.lower()  # del texto `calibrado` de ROJO en semaforo.yaml
