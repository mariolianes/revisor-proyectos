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
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P4"), _v("D07", "P4")]),
    )

    assert elegidas == []


def test_como_mucho_cuatro(criterios_de_analisis: Path) -> None:
    """Economía pedagógica: si hay diez errores, no se trasladan los diez."""
    muchas = [_v(f"D0{i}", "P2") for i in range(1, 8)]

    elegidas = seleccionar_prioridades(criterios_de_analisis, "v2026-2027",
                                       _analisis(muchas))

    assert len(elegidas) == 4


def test_los_criticos_van_primero(criterios_de_analisis: Path) -> None:
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P3"), _v("D07", "P1"), _v("D12", "P2")]),
    )

    assert [v.prioridad for v in elegidas] == ["P1", "P2", "P3"]


def test_un_critico_desplaza_a_los_secundarios(criterios_de_analisis: Path) -> None:
    """Con cinco candidatas y sitio para cuatro, cae el menos prioritario."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D01", "P3"), _v("D02", "P3"), _v("D05", "P1"),
                   _v("D07", "P1"), _v("D12", "P2")]),
    )

    assert len(elegidas) == 4
    assert [v.prioridad for v in elegidas] == ["P1", "P1", "P2", "P3"]


def test_una_evidencia_no_localizada_no_llega_al_alumno(
    criterios_de_analisis: Path,
) -> None:
    """La primera defensa, aplicada donde importa: si no se pudo señalar en el
    documento, el alumno no lo recibe. El docente sí lo ve en el informe."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P1", localizada=False), _v("D07", "P2")]),
    )

    assert [v.dimension for v in elegidas] == ["D07"]


def test_una_valoracion_sin_prioridad_no_es_una_accion(
    criterios_de_analisis: Path,
) -> None:
    """Sin prioridad no hay nada que pedirle al alumno que haga."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", None, nivel="SOLIDO")]),
    )

    assert elegidas == []


def test_el_limite_sale_del_fichero_de_criterios(criterios_de_analisis: Path) -> None:
    """Cambiar el criterio cambia el límite, sin tocar código."""
    fichero = criterios_de_analisis / "criteria" / "v2026-2027" / "feedback.yaml"
    fichero.write_text(
        fichero.read_text(encoding="utf-8").replace(
            "prioridades_maximas: 4", "prioridades_maximas: 2"
        ),
        encoding="utf-8",
    )

    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v(f"D0{i}", "P2") for i in range(1, 6)]),
    )

    assert len(elegidas) == 2


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

    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027",
        _analisis([_v("D05", "P3"), _v("D07", "P1")]),
    )

    assert [v.dimension for v in elegidas] == ["D07"]


def test_los_indicios_de_autoria_nunca_llegan_a_las_elegidas(
    criterios_de_analisis: Path,
) -> None:
    """El §13 reserva la autoría al docente. Un indicio no es del mismo tipo
    que devuelve esta función -`IndicioDeAutoriaVerificado` frente a
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

    elegidas = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)

    assert [v.dimension for v in elegidas] == ["D05"]
    assert all(isinstance(v, ValoracionVerificada) for v in elegidas)


def test_ninguna_elegida_lleva_una_nota(criterios_de_analisis: Path) -> None:
    """R3: el sistema propone y se detiene, no califica. No hay nota en
    ninguna salida; aquí se comprueba en la más cercana al alumno."""
    elegidas = seleccionar_prioridades(
        criterios_de_analisis, "v2026-2027", _analisis([_v("D05", "P1")]),
    )

    assert elegidas
    for v in elegidas:
        assert not hasattr(v, "nota")
        assert "nota" not in v.model_dump()


def test_el_exceso_por_el_limite_queda_registrado_como_reparo(
    criterios_de_analisis: Path,
) -> None:
    """Cuatro caben; el resto no desaparece en silencio. El docente tiene que
    poder ver que hubo más candidatas de las que llegaron a la devolución, y
    cuáles son: una selección callada haría creer que solo hay cuatro
    problemas cuando hay siete."""
    analisis = _analisis([_v(f"D0{i}", "P1") for i in range(1, 8)])

    elegidas = seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)

    elegidas_dims = [v.dimension for v in elegidas]
    assert elegidas_dims == ["D01", "D02", "D03", "D04"]

    reparo = next(r for r in analisis.reparos if r.regla == "limite_de_prioridades")
    for dimension in ("D05", "D06", "D07"):
        assert dimension in reparo.detalle
        assert dimension not in elegidas_dims


def test_sin_exceso_no_se_anade_ningun_reparo_de_limite(
    criterios_de_analisis: Path,
) -> None:
    """El reparo del límite solo aparece cuando de verdad sobra algo: no es un
    aviso que se pegue a cualquier selección."""
    analisis = _analisis([_v("D05", "P1"), _v("D07", "P2")])

    seleccionar_prioridades(criterios_de_analisis, "v2026-2027", analisis)

    assert not any(r.regla == "limite_de_prioridades" for r in analisis.reparos)
