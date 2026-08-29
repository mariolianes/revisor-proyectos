"""El Anexo C: todo lo que el docente necesita ver."""

from datetime import datetime
from pathlib import Path

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import (
    AnalisisVerificado,
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    Reparo,
    ValoracionVerificada,
)
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.informe import componer_informe


def _entrega():
    return EntregaRegistrada(
        id="id-1", codigo_alumno="AF023", ciclo="DAM", fase="E2", version=1,
        nombre_archivo="AF023/AF023_DAM_E2_20260115_v1.pdf", huella="a" * 64,
        recibida_en=datetime(2026, 1, 15, 10, 0), estado="RECIBIDO",
        motivo_bloqueo=None, version_criterios="v2026-2027",
    )


def _v(dimension="D05", prioridad="P2", localizada=True):
    return ValoracionVerificada(
        dimension=dimension, nivel="EN_DESARROLLO", prioridad=prioridad,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
        observacion=f"Observación de {dimension}.", evidencia_localizada=localizada,
    )


def _fortaleza(descripcion="La estructura es clara.", localizada=True):
    # El brief de esta tarea traia `fortalezas=["La estructura es clara."]`
    # -una lista de cadenas- pero `AnalisisVerificado.fortalezas` exige
    # `list[FortalezaVerificada]` (ver backend/analisis/verificacion.py); una
    # cadena suelta no valida contra ese modelo y `AnalisisVerificado(**datos)`
    # lanzaria un error de Pydantic antes de llegar a `componer_informe`. Se
    # corrige aquí construyendo el objeto real, con su propia evidencia.
    return FortalezaVerificada(
        descripcion=descripcion,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="2"),
        evidencia_localizada=localizada,
    )


def _indicio(localizada=True, descripcion="El estilo cambia en el apartado 4."):
    return IndicioDeAutoriaVerificado(
        descripcion=descripcion,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="4"),
        evidencia_localizada=localizada,
    )


def _analisis(valoraciones, **cambios):
    datos = dict(
        valoraciones=valoraciones, fortalezas=[_fortaleza()],
        patrones=[], dudas_para_el_docente=[], indicios_de_autoria=[],
        dimensiones_ausentes=[], reparos=[],
    )
    datos.update(cambios)
    return AnalisisVerificado(**datos)


def test_identifica_la_entrega(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert i.identificacion["alumno"] == "AF023"
    assert i.identificacion["fase"] == "E2"
    assert i.identificacion["criterios"] == "v2026-2027"


def test_deja_constancia_de_con_que_se_analizo(criterios_de_analisis: Path) -> None:
    """Dentro de un año importará si esto lo dijo un modelo o el simulador."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "openai:un-modelo")

    assert i.motor == "openai:un-modelo"


def test_el_informe_si_lleva_los_p4(criterios_de_analisis: Path) -> None:
    """Al alumno no llegan; al docente sí. Esa es la diferencia entre las dos
    salidas."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P4")]), "simulado")

    assert [v.dimension for v in i.valoraciones] == ["D05"]
    assert i.prioridades == []


def test_el_informe_si_lleva_lo_no_localizado(criterios_de_analisis: Path) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1", localizada=False)]), "simulado",
    )

    assert i.valoraciones[0].evidencia_localizada is False
    assert i.prioridades == []


def test_los_reparos_llegan_al_informe(criterios_de_analisis: Path) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], reparos=[Reparo(regla="x", detalle="Algo que revisar.")]),
        "simulado",
    )

    assert i.reparos[0].detalle == "Algo que revisar."


def test_el_informe_no_tiene_nota(criterios_de_analisis: Path) -> None:
    """Ni el campo existe. Tampoco la lleva ninguno de los bloques
    anidados: ni una valoración, ni una prioridad."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert not hasattr(i, "nota")
    assert "nota" not in i.model_dump()
    for bloque in (i.valoraciones, i.prioridades, i.fortalezas, i.indicios):
        for elemento in bloque:
            assert "nota" not in elemento.model_dump()


def test_un_p1_pone_el_semaforo_en_rojo(criterios_de_analisis: Path) -> None:
    """El §9 del calibrador: carencia crítica es rojo."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P1")]), "simulado")

    assert i.semaforo == "ROJO"


def test_un_p2_pone_el_semaforo_en_ambar(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P2")]), "simulado")

    assert i.semaforo == "AMBAR"


def test_sin_prioridades_el_semaforo_es_verde(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", None)]), "simulado")

    assert i.semaforo == "VERDE"


def test_sin_ninguna_valoracion_el_semaforo_es_gris(
    criterios_de_analisis: Path,
) -> None:
    """Si el análisis no valoró nada, no hay estado que resumir con VERDE,
    AMBAR ni ROJO -ninguno de los tres describe "no se pudo evaluar"-, pero
    tampoco se deja un hueco vacío que el docente tenga que interpretar:
    GRIS nombra la incidencia («no evaluable [...] o criterio bloqueado por
    falta de información», calibrado en `semaforo.yaml`) y trae su propia
    recomendación, no inventada."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([]), "simulado")

    assert i.semaforo == "GRIS"
    assert i.recomendacion == "Resolver incidencia; no emitir juicio académico automático"


def test_si_todas_las_citas_resultaron_inventadas_el_semaforo_es_gris(
    criterios_de_analisis: Path,
) -> None:
    """Caso raro y peligroso: el motor devuelve valoraciones con prioridad
    P1, pero ninguna de sus citas se localizó en el documento -las citas se
    inventaron-. Un semáforo que mirara solo la prioridad diría ROJO con la
    misma seguridad que si la evidencia fuera real, y el docente confiaría
    en un juicio que no tiene ninguna base verificada. El semáforo se calcula
    solo sobre lo que sí se localizó; si no hay nada localizado, el análisis
    no es evaluable -GRIS-, igual que si no hubiera habido ninguna
    valoración: las dos situaciones dejan al docente sin nada verificado de
    lo que partir, y merecen el mismo nombre."""
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([
            _v("D05", "P1", localizada=False),
            _v("D07", "P1", localizada=False),
        ]),
        "simulado",
    )

    assert i.semaforo == "GRIS"
    assert i.recomendacion == "Resolver incidencia; no emitir juicio académico automático"
    # Pero las valoraciones no desaparecen: el docente las ve enteras.
    assert len(i.valoraciones) == 2


def test_gris_no_es_lo_mismo_que_verde(criterios_de_analisis: Path) -> None:
    """Misma observación -sin prioridad, así que si contara igual que
    "revisado y sin nada que objetar" saldría VERDE-, pero con la evidencia
    localizada o sin localizar decide colores opuestos: GRIS dice "no se ha
    podido revisar"; VERDE dice "revisado y correcto". Confundirlos sería
    peor que dejar el semáforo vacío."""
    gris = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", None, localizada=False)]), "simulado",
    )
    verde = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", None, localizada=True)]), "simulado",
    )

    assert gris.semaforo == "GRIS"
    assert verde.semaforo == "VERDE"


def test_una_valoracion_localizada_basta_aunque_otra_no_lo_este(
    criterios_de_analisis: Path,
) -> None:
    """El filtro es por valoración, no todo o nada: si una parte del
    análisis sí se pudo verificar, esa parte sigue informando el semáforo."""
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([
            _v("D05", "P1", localizada=False),
            _v("D07", "P2", localizada=True),
        ]),
        "simulado",
    )

    assert i.semaforo == "AMBAR"


def test_la_recomendacion_acompana_al_semaforo_y_no_es_una_nota(
    criterios_de_analisis: Path,
) -> None:
    """§Anexo C: «Semáforo, nota y recomendación» en el resultado
    provisional. La nota no existe -R3, mientras no haya rúbrica-, pero el
    semáforo y la recomendación sí: los dos proponen, ninguno califica. La
    recomendación sale de `criteria/v2026-2027/semaforo.yaml`, no de un
    texto inventado aquí."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P1")]), "simulado")

    assert i.semaforo == "ROJO"
    assert i.recomendacion == "Revisión docente y plan de corrección"


def test_dimensiones_no_valoradas_quedan_a_la_vista(
    criterios_de_analisis: Path,
) -> None:
    """Caso raro: el motor falla a mitad de análisis y solo llega a
    valorar una dimensión de las ocho activas en la fase. Si el informe
    solo enseñara el semáforo -que puede salir VERDE porque lo poco que se
    valoró estaba bien- el docente creería que el trabajo entero se revisó.
    `dimensiones_ausentes` viaja siempre, para que ese silencio se vea."""
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", None)], dimensiones_ausentes=["D01", "D02", "D03"]),
        "simulado",
    )

    assert i.semaforo == "VERDE"
    assert i.dimensiones_ausentes == ["D01", "D02", "D03"]


def test_las_prioridades_descartadas_son_solo_lo_que_sobro_por_el_limite(
    criterios_de_analisis: Path,
) -> None:
    """Siete P1 con evidencia caben en el límite de cuatro: tres se quedan
    fuera y el informe tiene que decir cuáles y por qué -no un recuento-.
    Un P4 y una observación sin evidencia localizada nunca fueron
    candidatos, así que no aparecen ni en `prioridades` ni en
    `prioridades_descartadas`: mezclarlos daría una idea falsa de lo que se
    dejó fuera solo por el límite."""
    siete_p1 = [_v(f"D0{i}", "P1") for i in range(1, 8)]
    nunca_candidatos = [
        _v("D08", "P4"),
        _v("D09", "P1", localizada=False),
    ]
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis(siete_p1 + nunca_candidatos), "simulado",
    )

    assert [v.dimension for v in i.prioridades] == ["D01", "D02", "D03", "D04"]
    assert [v.dimension for v in i.prioridades_descartadas] == ["D05", "D06", "D07"]
    dimensiones_descartadas = {v.dimension for v in i.prioridades_descartadas}
    assert "D08" not in dimensiones_descartadas
    assert "D09" not in dimensiones_descartadas
    # Pero D08 y D09 siguen enteras en `valoraciones`: no desaparecen, solo
    # no cuentan como «descartadas por el límite».
    assert {"D08", "D09"}.issubset({v.dimension for v in i.valoraciones})


def test_sin_exceso_no_hay_prioridades_descartadas(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1"), _v("D07", "P2")]), "simulado",
    )

    assert i.prioridades_descartadas == []


def test_las_fortalezas_llegan_con_su_evidencia_no_solo_el_texto(
    criterios_de_analisis: Path,
) -> None:
    """Rastreable hasta una cita: si el informe solo llevara el texto de la
    fortaleza, el docente no podría comprobar de dónde sale ni si la cita se
    localizó de verdad en el documento."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert i.fortalezas[0].descripcion == "La estructura es clara."
    assert i.fortalezas[0].evidencia.cita
    assert i.fortalezas[0].evidencia_localizada is True


def test_el_resumen_no_es_una_fortaleza_suelta(criterios_de_analisis: Path) -> None:
    """El fallo que se corrige: el resumen ya no puede ser el texto de la
    primera fortaleza, localizada o no. Es la regresión que este cambio
    cierra, así que se comprueba de forma literal."""
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], fortalezas=[_fortaleza("La estructura es clara.")]),
        "simulado",
    )

    assert i.resumen != "La estructura es clara."
    assert "La estructura es clara." not in i.resumen


def test_el_resumen_no_lleva_una_fortaleza_con_la_cita_inventada(
    criterios_de_analisis: Path,
) -> None:
    """El caso peligroso de verdad: una fortaleza cuya evidencia NO se ha
    localizado -la cita pudo inventarla el motor- no puede titular el
    informe. Si `_resumen` dejara de filtrar por `evidencia_localizada` en
    algún punto de su composición, este test tiene que fallar: es la
    protección explícita que el brief pidió para el filtro de evidencia
    localizada del resumen."""
    fortaleza_inventada = _fortaleza(
        "Esta fortaleza tiene la cita inventada por el motor.", localizada=False,
    )
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], fortalezas=[fortaleza_inventada]),
        "simulado",
    )

    assert "Esta fortaleza tiene la cita inventada por el motor." not in i.resumen
    assert "inventada" not in i.resumen


def test_el_resumen_dice_el_semaforo(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P1")]), "simulado")

    assert "ROJO" in i.resumen


def test_el_resumen_cuenta_las_prioridades_elegidas_por_gravedad(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1"), _v("D06", "P1"), _v("D07", "P2")]),
        "simulado",
    )

    assert "2 P1" in i.resumen
    assert "1 P2" in i.resumen
    assert "3 prioridades verificadas" in i.resumen


def test_el_resumen_dice_si_no_hay_ninguna_prioridad(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", None)]), "simulado")

    assert "Ninguna prioridad verificada" in i.resumen


def test_el_resumen_cuenta_las_descartadas_por_el_limite(
    criterios_de_analisis: Path,
) -> None:
    siete_p1 = [_v(f"D0{i}", "P1") for i in range(1, 8)]
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis(siete_p1), "simulado",
    )

    assert "3 más quedaron fuera solo por el límite" in i.resumen


def test_el_resumen_dice_las_dimensiones_sin_valorar(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", None)], dimensiones_ausentes=["D01", "D02"]),
        "simulado",
    )

    assert "2 dimensiones de la fase sin valorar: D01, D02" in i.resumen


def test_el_resumen_cuenta_los_reparos(criterios_de_analisis: Path) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis(
            [_v()],
            reparos=[
                Reparo(regla="x", detalle="Algo."),
                Reparo(regla="y", detalle="Otra cosa."),
            ],
        ),
        "simulado",
    )

    assert "2 reparos de verificación registrados" in i.resumen


def test_los_indicios_llegan_con_su_evidencia_y_su_aviso(
    criterios_de_analisis: Path,
) -> None:
    """Ningún indicio se presenta como un veredicto. La verificación ya le
    puso el aviso del §13 a cada indicio -un `Reparo` con `regla:
    "autoria_es_indicio"`-, y ese aviso viaja en `reparos` junto al indicio
    en `indicios`: el informe no separa el indicio de su advertencia."""
    indicio = _indicio()
    aviso = Reparo(
        regla="autoria_es_indicio",
        detalle="Esto es un indicio de autoría, no un veredicto: la decisión "
                "es del profesor (§13).",
    )
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], indicios_de_autoria=[indicio], reparos=[aviso]),
        "simulado",
    )

    assert i.indicios[0].descripcion == indicio.descripcion
    assert i.indicios[0].evidencia.cita
    assert any(r.regla == "autoria_es_indicio" for r in i.reparos)


def test_llamar_seleccionar_prioridades_una_vez_basta(
    criterios_de_analisis: Path, monkeypatch,
) -> None:
    """`seleccionar_prioridades` es pura, y el brief pide explícitamente que
    `componer_informe` la llame una sola vez: llamarla dos veces duplicaría
    trabajo sin motivo (no haría daño por sí solo, al ser pura, pero delata
    una redacción descuidada del compositor)."""
    import backend.salidas.informe as informe_mod

    llamadas = []
    original = informe_mod.seleccionar_prioridades

    def contador(raiz, version, analisis):
        llamadas.append(1)
        return original(raiz, version, analisis)

    monkeypatch.setattr(informe_mod, "seleccionar_prioridades", contador)

    componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                     _analisis([_v("D05", "P1")]), "simulado")

    assert len(llamadas) == 1
