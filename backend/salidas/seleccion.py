"""Qué observaciones pueden pasar del informe al borrador del alumno.

Tres filtros, y ninguno es una preferencia de estilo:

Un P4 no llega nunca. El §7 del calibrador dice que no compensa el coste
pedagógico y que no debe cargarse al alumno; `llega_al_alumno: nunca` en
`criteria/<version>/prioridades.yaml` lo dice con esas palabras, y es de ahí
de donde sale la regla, no de un código escrito a mano aquí. Si el profesor
cambiara ese campo, este código lo seguiría sin tocarlo: el filtro solo
acepta las prioridades cuyo `llega_al_alumno` no sea `nunca`.

Una observación cuya evidencia no se pudo localizar en el documento tampoco
llega. El docente la ve en el informe, marcada, y decide; pero no se le pide
a un alumno que corrija algo que el sistema no ha sabido señalar en su
trabajo. Es la primera defensa de `backend/analisis/verificacion.py`,
aplicada aquí, en la frontera hacia el alumno.

Los indicios de autoría no pasan por esta función en ningún caso: no son del
tipo que devuelve -`ValoracionVerificada`, no `IndicioDeAutoriaVerificado`-,
así que no hay manera de que se cuelen aquí. El §13 reserva esa valoración al
docente; el indicio llega al informe interno (Task 9), nunca a esta
selección, y esa garantía es del tipo, no de una comprobación que alguien
pueda olvidar.

Y aunque queden diez, salen cuatro como mucho -o el número que fije
`feedback.yaml`-. Es la regla de economía pedagógica del §2.3: si hay diez
errores, no se trasladan los diez, se identifican los que desbloquean el
desarrollo. Lo que el límite deja fuera no desaparece sin dejar rastro: queda
anotado como un reparo más en el propio análisis, para que el docente sepa
que hubo más candidatas de las que caben en la devolución y cuáles son. Una
selección silenciosa sería peor que una lista larga: le haría creer al
docente que solo hay cuatro problemas cuando puede haber siete.
"""

from pathlib import Path

import yaml

from backend.analisis.verificacion import (
    AnalisisVerificado,
    Reparo,
    ValoracionVerificada,
)

# Si el fichero de criterios no dice otra cosa. El valor real vive en
# criteria/<version>/feedback.yaml, bajo economia_pedagogica.prioridades_maximas.
_MAXIMO_POR_OMISION = 4

# Por si prioridades.yaml no existiera: el orden que fija el §7 del
# calibrador. Es la única constante de este módulo que no sale de un
# fichero, y solo se usa cuando el fichero mismo falta.
_ORDEN_POR_OMISION = {"P1": 0, "P2": 1, "P3": 2}


def _orden_de_las_prioridades_que_llegan_al_alumno(
    raiz: Path, version: str
) -> dict[str, int]:
    """El orden de elección, restringido a lo que SÍ puede llegar al alumno.

    Ni el conjunto de códigos válidos ni su orden se hardcodean: los dos
    salen de `prioridades.yaml`, en el mismo orden en que el fichero los
    declara. Un P4 no entra en el resultado porque su `llega_al_alumno` vale
    `nunca`; si el profesor le pusiera `nunca` a un P3, este código dejaría
    de ofrecerlo sin que nadie tocara una línea aquí.
    """
    fichero = raiz / "criteria" / version / "prioridades.yaml"
    if not fichero.is_file():
        return dict(_ORDEN_POR_OMISION)
    catalogo = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    codigos = [
        p["codigo"]
        for p in catalogo
        if isinstance(p, dict) and p.get("llega_al_alumno") != "nunca"
    ]
    return {codigo: indice for indice, codigo in enumerate(codigos)}


def _maximo(raiz: Path, version: str) -> int:
    """El límite de la economía pedagógica, leído de `feedback.yaml`."""
    fichero = raiz / "criteria" / version / "feedback.yaml"
    if not fichero.is_file():
        return _MAXIMO_POR_OMISION
    datos = yaml.safe_load(fichero.read_text(encoding="utf-8")) or {}
    economia = datos.get("economia_pedagogica") or {}
    return int(economia.get("prioridades_maximas") or _MAXIMO_POR_OMISION)


def seleccionar_prioridades(
    raiz: Path, version: str, analisis: AnalisisVerificado
) -> list[ValoracionVerificada]:
    """Las observaciones que pueden llegar al alumno, ya ordenadas.

    Solo entran las que tienen una prioridad que `prioridades.yaml` marca
    como capaz de llegar al alumno (nunca un P4, hoy) y cuya evidencia se
    localizó en el documento. De las que quedan, se ordenan por prioridad y
    se recortan al máximo que fija `feedback.yaml`.

    Las que sobran por ese recorte no se pierden en silencio: se anotan como
    un `Reparo` en `analisis.reparos`, con sus dimensiones y prioridades, así
    que el informe interno (que muestra todos los reparos) deja constancia de
    que existieron más candidatas de las que caben en la devolución.
    """
    orden = _orden_de_las_prioridades_que_llegan_al_alumno(raiz, version)
    candidatas = [
        v for v in analisis.valoraciones
        if v.prioridad in orden and v.evidencia_localizada
    ]
    candidatas.sort(key=lambda v: (orden[v.prioridad], v.dimension))

    maximo = _maximo(raiz, version)
    elegidas = candidatas[:maximo]
    descartadas_por_limite = candidatas[maximo:]

    if descartadas_por_limite:
        listado = ", ".join(
            f"{v.dimension} ({v.prioridad})" for v in descartadas_por_limite
        )
        analisis.reparos.append(Reparo(
            regla="limite_de_prioridades",
            detalle=(
                f"Había {len(candidatas)} observaciones con evidencia "
                f"localizada y prioridad para el alumno; el límite de "
                f"{maximo} (economía pedagógica) deja fuera de la devolución "
                f"a: {listado}. Se conservan en este informe."
            ),
        ))

    return elegidas
