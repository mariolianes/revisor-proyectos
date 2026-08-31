"""El Anexo C: todo lo que el docente necesita ver."""

from datetime import date, datetime
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
from backend.salidas.informe import (
    calcular_nota_interna,
    componer_informe,
    componer_sintesis_provisional,
    rubrica_pendiente,
    semaforo_por_valoraciones,
)
from backend.salidas.seleccion import SeleccionDePrioridades


def _entrega(fase="E2"):
    return EntregaRegistrada(
        id="id-1", codigo_alumno="AF023", ciclo="DAM", fase=fase, version=1,
        nombre_archivo=f"AF023/AF023_DAM_{fase}_20260115_v1.pdf", huella="a" * 64,
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

    assert i.semaforo_propuesto == "ROJO"


def test_un_p2_pone_el_semaforo_en_ambar(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P2")]), "simulado")

    assert i.semaforo_propuesto == "AMBAR"


def test_sin_prioridades_el_semaforo_es_verde(criterios_de_analisis: Path) -> None:
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", None)]), "simulado")

    assert i.semaforo_propuesto == "VERDE"


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

    assert i.semaforo_propuesto == "GRIS"
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

    assert i.semaforo_propuesto == "GRIS"
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

    assert gris.semaforo_propuesto == "GRIS"
    assert verde.semaforo_propuesto == "VERDE"


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

    assert i.semaforo_propuesto == "AMBAR"


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

    assert i.semaforo_propuesto == "ROJO"
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

    assert i.semaforo_propuesto == "VERDE"
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

    # Agrupadas por causa (§2.5 del calibrador): D01-D03 son la misma causa
    # -"Planteamiento y encaje"- y D05-D06 también -"Base documental y
    # método"-, así que de cada grupo solo entra la de mayor prioridad
    # -D01 y D05- y el resto de su mismo grupo -D02, D03, D06- se descarta
    # aunque hubiera hueco, porque la causa ya está representada.
    assert [v.dimension for v in i.prioridades] == ["D01", "D04", "D05", "D07"]
    assert [v.dimension for v in i.prioridades_descartadas] == ["D02", "D03", "D06"]
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
    informe. Si `componer_resumen` dejara de filtrar por `evidencia_localizada` en
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


# --- Doble semáforo (D-016) -------------------------------------------------


def test_semaforo_final_docente_empieza_vacio(criterios_de_analisis: Path) -> None:
    """Recién analizado, nadie ha cerrado ninguna revisión todavía."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v("D05", "P1")]), "simulado")

    assert i.semaforo_propuesto == "ROJO"
    assert i.semaforo_final_docente is None


def test_semaforo_por_valoraciones_coincide_con_el_semaforo_propuesto(
    criterios_de_analisis: Path,
) -> None:
    """`semaforo_por_valoraciones` es la función que `revisar()`
    (`backend/api/analisis.py`) reutiliza para comprobar la compatibilidad
    del semáforo final: tiene que dar el mismo resultado que
    `semaforo_propuesto` cuando se le pasa exactamente el mismo conjunto de
    valoraciones con el que se compuso el informe."""
    valoraciones = [_v("D05", "P1"), _v("D06", "P2")]
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis(valoraciones), "simulado")

    assert semaforo_por_valoraciones(valoraciones) == i.semaforo_propuesto == "ROJO"


def test_semaforo_por_valoraciones_ignora_lo_no_localizado() -> None:
    """Mismo criterio que `_semaforo`, extraído a función pública: un P1
    cuya cita no se localizó no puede sostener un ROJO."""
    assert semaforo_por_valoraciones([_v("D05", "P1", localizada=False)]) == "GRIS"


def test_semaforo_por_valoraciones_sin_nada_da_gris() -> None:
    assert semaforo_por_valoraciones([]) == "GRIS"


# --- Nota interna (D-015) ---------------------------------------------------


def test_sin_rubrica_la_nota_esta_pendiente(criterios_de_analisis: Path) -> None:
    """Hoy no hay rúbrica oficial -`rubrica` y `ponderaciones` siguen en
    `docs/PENDIENTE_OFICIAL.md` del repositorio real, y la fixture
    `criterios_de_analisis` ni siquiera copia `docs/`, así que
    `rubrica_pendiente` tampoco encuentra el fichero-: el estado es
    `pendiente_de_rubrica` y no hay ningún número."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega("E2"), None,
                         _analisis([_v("D05", "P1")]), "simulado")

    assert i.estado_nota == "pendiente_de_rubrica"
    assert i.nota_propuesta_sistema is None
    assert i.version_rubrica is None
    assert i.ponderaciones_nota is None
    assert i.nota_final_docente is None


def test_fases_sin_nota_de_informe_son_no_aplicable(
    criterios_de_analisis: Path,
) -> None:
    """TEMA no puntúa como entrega y DEFENSA se valora a mano (§6.5): las
    dos quedan `no_aplicable`, no `pendiente_de_rubrica` -no es que falte un
    dato, es que este cálculo no les corresponde-."""
    for fase in ("TEMA", "DEFENSA"):
        i = componer_informe(
            criterios_de_analisis, "v2026-2027", _entrega(fase), None,
            _analisis([_v("D05", "P1")]), "simulado",
        )
        assert i.estado_nota == "no_aplicable", fase
        assert i.nota_propuesta_sistema is None, fase


def test_rubrica_pendiente_sin_fichero_da_true(tmp_path: Path) -> None:
    """Mismo criterio que `proteccion_datos_pendiente`: sin
    `docs/PENDIENTE_OFICIAL.md`, la duda no se resuelve a favor de inventar
    una nota."""
    assert rubrica_pendiente(tmp_path) is True


def test_rubrica_pendiente_si_las_dos_entradas_siguen_en_el_fichero(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "- **rubrica** — pendiente.\n- **ponderaciones** — pendiente.\n",
        encoding="utf-8",
    )

    assert rubrica_pendiente(tmp_path) is True


def test_rubrica_pendiente_si_solo_una_de_las_dos_se_resuelve(
    tmp_path: Path,
) -> None:
    """No basta con cerrar `rubrica` sin cerrar `ponderaciones`, ni al
    revés: `criteria/v2026-2027/ponderaciones.yaml` declara con sus propias
    palabras que bloquea `nota_final` y `nota_propuesta`, así que sin las
    dos a la vez no hay con qué calcular nada."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "- **ponderaciones** — pendiente.\n", encoding="utf-8",
    )

    assert rubrica_pendiente(tmp_path) is True


def test_rubrica_pendiente_falso_cuando_las_dos_se_resuelven(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "Ya no queda nada pendiente sobre calificación.\n", encoding="utf-8",
    )

    assert rubrica_pendiente(tmp_path) is False


def _raiz_con_rubrica(tmp_path: Path) -> Path:
    """Una raíz de prueba con la rúbrica ya resuelta: la vía por la que
    entrará una rúbrica real cuando `docs/PENDIENTE_OFICIAL.md` deje de
    nombrarla. Los números de aquí son de prueba, no una rúbrica oficial:
    ese fichero no existe todavía en el repositorio real, y esta función
    vive solo en `tests/`.
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "PENDIENTE_OFICIAL.md").write_text(
        "Nada pendiente sobre calificación en esta copia de prueba.\n",
        encoding="utf-8",
    )
    criterios = tmp_path / "criteria" / "v2026-2027"
    criterios.mkdir(parents=True)
    (criterios / "rubrica.yaml").write_text(
        "version: v2026-2027-prueba\n"
        "ponderaciones:\n"
        "  D05: 0.5\n"
        "  D06: 0.5\n"
        "escala:\n"
        "  SOLIDO: 10.0\n"
        "  ADECUADO: 7.5\n"
        "  EN_DESARROLLO: 5.0\n"
        "  INSUFICIENTE: 2.5\n",
        encoding="utf-8",
    )
    return tmp_path


def test_con_rubrica_cargada_se_calcula_la_nota_propuesta(tmp_path: Path) -> None:
    raiz = _raiz_con_rubrica(tmp_path)
    valoraciones = [
        ValoracionVerificada(
            dimension="D05", nivel="SOLIDO", prioridad=None,
            evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
            observacion="obs", evidencia_localizada=True,
        ),
        ValoracionVerificada(
            dimension="D06", nivel="EN_DESARROLLO", prioridad="P2",
            evidencia=Evidencia(cita="Otra cita bastante larga del trabajo.", apartado="6"),
            observacion="obs", evidencia_localizada=True,
        ),
    ]

    nota, estado, version_rubrica, ponderaciones = calcular_nota_interna(
        raiz, "v2026-2027", "E2", valoraciones,
    )

    # (10.0 * 0.5 + 5.0 * 0.5) / (0.5 + 0.5) = 7.5
    assert nota == 7.5
    assert estado == "propuesta"
    assert version_rubrica == "v2026-2027-prueba"
    assert ponderaciones == {"D05": 0.5, "D06": 0.5}


def test_la_nota_propuesta_solo_cuenta_lo_localizado(tmp_path: Path) -> None:
    """Misma defensa que el semáforo: una valoración cuya cita no se
    localizó no puede pesar en un número que el docente va a auditar."""
    raiz = _raiz_con_rubrica(tmp_path)
    valoraciones = [
        ValoracionVerificada(
            dimension="D05", nivel="SOLIDO", prioridad=None,
            evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
            observacion="obs", evidencia_localizada=True,
        ),
        ValoracionVerificada(
            dimension="D06", nivel="INSUFICIENTE", prioridad="P1",
            evidencia=Evidencia(cita="Cita que no se localizó en el documento.", apartado="6"),
            observacion="obs", evidencia_localizada=False,
        ),
    ]

    nota, estado, _, ponderaciones = calcular_nota_interna(
        raiz, "v2026-2027", "E2", valoraciones,
    )

    assert nota == 10.0  # solo D05 cuenta
    assert estado == "propuesta"
    assert ponderaciones == {"D05": 0.5}


def test_la_nota_propuesta_via_componer_informe(tmp_path: Path) -> None:
    """El mismo cálculo, pero pasando por `componer_informe`, para
    comprobar que el informe entero lo recoge, no solo la función suelta."""
    raiz = _raiz_con_rubrica(tmp_path)
    i = componer_informe(
        raiz, "v2026-2027", _entrega("E2"), None,
        _analisis([_v("D05", None)]), "simulado",
    )

    assert i.estado_nota == "propuesta"
    assert i.nota_propuesta_sistema is not None
    assert i.nota_final_docente is None


# --- Síntesis provisional (D-017) -------------------------------------------


def test_la_sintesis_provisional_tiene_varias_lineas(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1")], dimensiones_ausentes=["D01"],
                  reparos=[Reparo(regla="x", detalle="Algo.")]),
        "simulado",
    )

    lineas = i.sintesis_provisional.splitlines()
    assert 4 <= len(lineas) <= 6


def test_la_sintesis_nombra_las_dimensiones_y_las_prioridades(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1"), _v("D06", "P2")]), "simulado",
    )

    assert "D05 (P1)" in i.sintesis_provisional
    assert "D06 (P2)" in i.sintesis_provisional


def test_la_sintesis_incluye_las_fortalezas_fiables(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], fortalezas=[_fortaleza("La estructura es clara.")]),
        "simulado",
    )

    assert "La estructura es clara." in i.sintesis_provisional


def test_la_sintesis_no_incluye_una_fortaleza_sin_localizar(
    criterios_de_analisis: Path,
) -> None:
    """La misma defensa que ya protege a `resumen`: una fortaleza cuya cita
    no se localizó no puede aparecer en un texto que el docente va a
    convertir en la síntesis que entrega -sería exactamente el problema de
    la cita inventada que D-011 cerró, reabierto en un campo nuevo."""
    fortaleza_inventada = _fortaleza(
        "Esta fortaleza tiene la cita inventada por el motor.", localizada=False,
    )
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()], fortalezas=[fortaleza_inventada]),
        "simulado",
    )

    assert "inventada" not in i.sintesis_provisional
    assert "Ninguna fortaleza verificada." in i.sintesis_provisional


def test_el_resumen_y_la_sintesis_provisional_conviven(
    criterios_de_analisis: Path,
) -> None:
    """D-017 no sustituye a `resumen` -D-011 solo señalaba un hueco, no
    pedía borrar el recuento factual-: los dos campos existen a la vez y
    dicen cosas relacionadas pero no idénticas."""
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v("D05", "P1")]), "simulado",
    )

    assert i.resumen
    assert i.sintesis_provisional
    assert i.resumen != i.sintesis_provisional
    assert "Semáforo propuesto: ROJO" in i.resumen
    assert "Semáforo propuesto: ROJO" in i.sintesis_provisional


def test_componer_sintesis_provisional_es_pura_y_reutilizable() -> None:
    """Público, como `componer_resumen`: no hay motivo para que solo
    `componer_informe` pueda llamarla."""
    seleccion = SeleccionDePrioridades(elegidas=[], descartadas=[])

    texto = componer_sintesis_provisional("VERDE", seleccion, [], [], [])

    assert texto == componer_sintesis_provisional("VERDE", seleccion, [], [], [])
    assert "Ninguna prioridad verificada para la devolución." in texto
    assert "Ninguna fortaleza verificada." in texto


# --- cabecera: modalidad y fecha (§17.1, decisión del docente) -------------


def test_sin_modalidad_registrada_la_cabecera_lo_dice(criterios_de_analisis: Path) -> None:
    """`entrega.modalidad` es `None` por omisión -no existe todavía una
    pantalla de validación de tema-, y la cabecera no puede dejar la clave
    ausente ni en blanco: el docente tiene que ver que no se ha declarado,
    no adivinarlo."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert i.identificacion["modalidad"] == "No registrada"


def test_con_modalidad_registrada_la_cabecera_la_lleva(criterios_de_analisis: Path) -> None:
    entrega = _entrega().model_copy(update={"modalidad": "PROFESIONAL"})

    i = componer_informe(criterios_de_analisis, "v2026-2027", entrega, None,
                         _analisis([_v()]), "simulado")

    assert i.identificacion["modalidad"] == "PROFESIONAL"


def test_la_cabecera_lleva_la_fecha_de_esta_ejecucion(criterios_de_analisis: Path) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()]), "simulado", fecha=date(2026, 8, 30),
    )

    assert i.identificacion["fecha"] == "2026-08-30"


def test_sin_fecha_explicita_se_usa_la_de_hoy(
    criterios_de_analisis: Path, monkeypatch,
) -> None:
    """Cada ejecución imprime su propia fecha sin que quien llama tenga
    que pasarla -es lo que usa `analizar_entrega` en producción-, así que
    el valor por omisión tiene que ser el día real, no uno fijo."""
    import backend.salidas.informe as informe_mod

    class _FechaFija(date):
        @classmethod
        def today(cls):
            return date(2026, 1, 1)

    monkeypatch.setattr(informe_mod, "date", _FechaFija)

    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert i.identificacion["fecha"] == "2026-01-01"


# --- continuidad (§17.1, D-012) ---------------------------------------------
#
# `componer_informe` delega la clasificación en
# `backend.evolucion.continuidad.clasificar_continuidad` (probada aparte,
# en `tests/evolucion/test_continuidad.py`); lo que se comprueba aquí es
# el cableado propio de este módulo: qué nota compone según lo que le llega
# de `hay_entrega_anterior` y `prioridades_anteriores`, y que la clasificación
# de verdad llega al campo `continuidad` del informe.


def test_sin_declarar_entrega_anterior_la_nota_dice_primera_entrega(
    criterios_de_analisis: Path,
) -> None:
    """Valor por omisión de `componer_informe`: quien no declara nada sobre
    la continuidad obtiene el mismo resultado que una primera entrega de
    verdad, no un error ni una lista vacía sin explicación."""
    i = componer_informe(criterios_de_analisis, "v2026-2027", _entrega(), None,
                         _analisis([_v()]), "simulado")

    assert i.continuidad == []
    assert "primera entrega" in i.continuidad_nota.lower()


def test_con_entrega_anterior_pero_sin_correccion_la_nota_lo_dice(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()]), "simulado",
        hay_entrega_anterior=True, prioridades_anteriores=None,
    )

    assert i.continuidad == []
    assert "analisis guardado" in i.continuidad_nota.lower() or \
        "análisis guardado" in i.continuidad_nota.lower()


def test_con_correccion_anterior_sin_prioridades_la_nota_lo_dice(
    criterios_de_analisis: Path,
) -> None:
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()]), "simulado",
        hay_entrega_anterior=True, prioridades_anteriores=[],
    )

    assert i.continuidad == []
    assert "prioridades" in i.continuidad_nota.lower()


def test_con_prioridades_anteriores_pero_sin_ficha_todo_es_no_verificable(
    criterios_de_analisis: Path,
) -> None:
    """Sin `ficha` no hay texto nuevo con el que comparar -es el caso que
    puede darse al probar `componer_informe` sola, sin pasar por
    `analizar_entrega`-, así que no se inventa ninguna certeza: cada
    prioridad anterior queda NO_VERIFICABLE."""
    anterior = _v("D06", "P2")
    i = componer_informe(
        criterios_de_analisis, "v2026-2027", _entrega(), None,
        _analisis([_v()]), "simulado",
        hay_entrega_anterior=True, prioridades_anteriores=[anterior],
    )

    assert i.continuidad_nota is None
    assert len(i.continuidad) == 1
    assert i.continuidad[0].dimension == "D06"
    assert i.continuidad[0].estado == "NO_VERIFICABLE"
