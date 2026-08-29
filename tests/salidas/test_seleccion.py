"""Qué observaciones pueden pasar del informe al borrador del alumno."""

from pathlib import Path

from backend.analisis.contrato import Evidencia
from backend.analisis.verificacion import (
    AnalisisVerificado,
    IndicioDeAutoriaVerificado,
    ValoracionVerificada,
)
from backend.salidas.seleccion import seleccionar_prioridades


def _v(dimension, prioridad, localizada=True, nivel="EN_DESARROLLO"):
    return ValoracionVerificada(
        dimension=dimension,
        nivel=nivel,
        prioridad=prioridad,
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="5"),
        observacion=f"Observación de {dimension}.",
        evidencia_localizada=localizada,
    )


def _analisis(valoraciones, **cambios):
    datos = dict(
        valoraciones=valoraciones, fortalezas=[], patrones=[],
        dudas_para_el_docente=[], indicios_de_autoria=[],
        dimensiones_ausentes=[], reparos=[],
    )
    datos.update(cambios)
    return AnalisisVerificado(**datos)


def test_un_p4_no_llega_nunca(criterios_de_analisis: Path) -> None:
    """El §7 del calibrador: no debe cargarse al alumno."""
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P4"), _v("D07", "P4")]),
    )

    assert seleccion.elegidas == []


def test_como_mucho_cuatro(criterios_de_analisis: Path) -> None:
    """Economía pedagógica: si hay diez errores, no se trasladan los diez."""
    muchas = [_v(f"D0{i}", "P2") for i in range(1, 8)]

    seleccion = seleccionar_prioridades(criterios_de_analisis, "v2026-2027",
                                        _analisis(muchas))

    assert len(seleccion.elegidas) == 4


def test_los_criticos_van_primero(criterios_de_analisis: Path) -> None:
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P3"), _v("D07", "P1"), _v("D12", "P2")]),
    )

    assert [v.prioridad for v in seleccion.elegidas] == ["P1", "P2", "P3"]


def test_un_critico_desplaza_a_los_secundarios(criterios_de_analisis: Path) -> None:
    """Con cinco candidatas y sitio para cuatro, cae el menos prioritario."""
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D01", "P3"), _v("D02", "P3"), _v("D05", "P1"),
                   _v("D07", "P1"), _v("D12", "P2")]),
    )

    assert len(seleccion.elegidas) == 4
    assert [v.prioridad for v in seleccion.elegidas] == ["P1", "P1", "P2", "P3"]


def test_una_evidencia_no_localizada_no_llega_al_alumno(
    criterios_de_analisis: Path,
) -> None:
    """La primera defensa, aplicada donde importa: si no se pudo señalar en el
    documento, el alumno no lo recibe. El docente sí lo ve en el informe."""
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P1", localizada=False), _v("D07", "P2")]),
    )

    assert [v.dimension for v in seleccion.elegidas] == ["D07"]


def test_una_valoracion_sin_prioridad_no_es_una_accion(
    criterios_de_analisis: Path,
) -> None:
    """Sin prioridad no hay nada que pedirle al alumno que haga."""
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", None, nivel="SOLIDO")]),
    )

    assert seleccion.elegidas == []


def test_el_limite_sale_del_fichero_de_criterios(criterios_de_analisis: Path) -> None:
    """Cambiar el criterio cambia el límite, sin tocar código."""
    fichero = criterios_de_analisis / "criteria" / "v2026-2027" / "feedback.yaml"
    fichero.write_text(
        fichero.read_text(encoding="utf-8").replace(
            "prioridades_maximas: 4", "prioridades_maximas: 2"
        ),
        encoding="utf-8",
    )

    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v(f"D0{i}", "P2") for i in range(1, 6)]),
    )

    assert len(seleccion.elegidas) == 2


def test_llega_al_alumno_sale_del_fichero_de_prioridades(
    criterios_de_analisis: Path,
) -> None:
    """El §7 vive en `prioridades.yaml`, no en una lista de códigos escrita a
    mano aquí: si el profesor le pone `nunca` a un P3, deja de ofrecerse sin
    tocar una línea de este módulo."""
    fichero = criterios_de_analisis / "criteria" / "v2026-2027" / "prioridades.yaml"
    fichero.write_text(
        fichero.read_text(encoding="utf-8").replace(
            "llega_al_alumno: como_mucho_una_frase", "llega_al_alumno: nunca"
        ),
        encoding="utf-8",
    )

    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P3"), _v("D07", "P1")]),
    )

    assert [v.dimension for v in seleccion.elegidas] == ["D07"]


def test_los_indicios_de_autoria_nunca_llegan_a_las_elegidas(
    criterios_de_analisis: Path,
) -> None:
    """El §13 reserva la autoría al docente. Un indicio no es del mismo tipo
    que maneja esta función -`IndicioDeAutoriaVerificado` frente a
    `ValoracionVerificada`-, así que no hay forma de que se cuele aquí; este
    test deja la garantía escrita como comportamiento, no solo como tipo."""
    indicio = IndicioDeAutoriaVerificado(
        descripcion="El estilo cambia de forma notable en el apartado 4.",
        evidencia=Evidencia(cita="Una cita bastante larga del trabajo.", apartado="4"),
        evidencia_localizada=True,
    )
    analisis = _analisis(
        [_v("D05", "P1")], indicios_de_autoria=[indicio, indicio, indicio],
    )

    seleccion = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)

    assert [v.dimension for v in seleccion.elegidas] == ["D05"]
    assert all(isinstance(v, ValoracionVerificada) for v in seleccion.elegidas)


def test_ninguna_elegida_lleva_una_nota(criterios_de_analisis: Path) -> None:
    """R3: el sistema propone y se detiene, no califica. No hay nota en
    ninguna salida; aquí se comprueba en la más cercana al alumno."""
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027", _analisis([_v("D05", "P1")]),
    )

    assert seleccion.elegidas
    for v in seleccion.elegidas:
        assert not hasattr(v, "nota")
        assert "nota" not in v.model_dump()


def test_el_exceso_por_el_limite_va_en_descartadas(
    criterios_de_analisis: Path,
) -> None:
    """Cuatro caben; el resto no desaparece. Quien construya el informe
    (Task 9) tiene que poder ver que hubo más candidatas de las que llegaron
    a la devolución, y cuáles son -no un recuento, las observaciones mismas-:
    una selección callada haría creer que solo hay cuatro problemas cuando
    hay siete."""
    analisis = _analisis([_v(f"D0{i}", "P1") for i in range(1, 8)])

    seleccion = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)

    assert [v.dimension for v in seleccion.elegidas] == ["D01", "D02", "D03", "D04"]
    assert [v.dimension for v in seleccion.descartadas] == ["D05", "D06", "D07"]
    for v in seleccion.descartadas:
        assert v.prioridad == "P1"
        assert v.observacion


def test_sin_exceso_no_hay_descartadas(criterios_de_analisis: Path) -> None:
    """`descartadas` solo lleva algo cuando de verdad sobra: no es una lista
    que se rellene de cualquier cosa que no se eligió."""
    seleccion = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P1"), _v("D07", "P2")]),
    )

    assert seleccion.descartadas == []


def test_llamar_dos_veces_da_el_mismo_resultado_y_no_toca_la_entrada(
    criterios_de_analisis: Path,
) -> None:
    """La función es pura: el borrador (Task 8) y el informe (Task 9) la van
    a llamar los dos sobre el mismo análisis, y una segunda llamada no puede
    devolver algo distinto ni dejar una marca de la primera. Este es
    exactamente el error que se cometió en la primera versión de este
    módulo: mutaba `analisis.reparos`, y una segunda llamada duplicaba el
    aviso del recorte."""
    analisis = _analisis([_v(f"D0{i}", "P1") for i in range(1, 8)])
    antes = analisis.model_dump()

    primera = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)
    segunda = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)

    assert primera == segunda
    assert analisis.model_dump() == antes


def test_el_desempate_por_dimension_es_estable_ante_el_orden_de_entrada(
    criterios_de_analisis: Path,
) -> None:
    """Dos ejecuciones sobre el mismo trabajo no pueden darle al alumno
    prioridades distintas solo porque el motor haya enumerado las
    valoraciones en otro orden. `sort` es estable, así que si se quitara el
    desempate por dimensión, el orden de entrada se colaría en el de salida
    sin que ningún otro test lo notara -todos los demás llegan ya
    ordenados-. Este cruza el mismo conjunto en dos órdenes distintos."""
    a, b, c = _v("D07", "P1"), _v("D01", "P1"), _v("D03", "P1")
    esperado = ["D01", "D03", "D07"]

    primer_orden = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027", _analisis([a, b, c]),
    )
    segundo_orden = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027", _analisis([b, c, a]),
    )

    assert [v.dimension for v in primer_orden.elegidas] == esperado
    assert [v.dimension for v in segundo_orden.elegidas] == esperado
