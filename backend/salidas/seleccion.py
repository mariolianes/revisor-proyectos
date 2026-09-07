"""Qué observaciones pueden pasar del informe al borrador del alumno.

Cuatro filtros, y ninguno es una preferencia de estilo:

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

Y de las que quedan, salen como mucho las que la economía pedagógica del
§2.3 permite -tres en un trabajo con base, cuatro en uno con una carencia
crítica, o el número que fije `feedback.yaml`-, agrupadas por la causa que
explican, no elegidas como hallazgos aislados. El docente lo pidió así el
2026-08-31, con un caso real: un proyecto de importación textil al que se le
trasladaron cuatro observaciones sueltas cuando la causa real eran tres o
cuatro problemas de fondo. Ver `_grupo_de_cada_causa` para cómo se agrupa y
qué se pierde al hacerlo así, y `docs/decisions.md` (D-019) para la decisión
completa.

Esta función es pura y no deja rastro en `analisis`: lo que el límite deja
fuera se devuelve en `descartadas`, no se anota aquí dentro. Al borrador
(Task 8) y al informe (Task 9) los va a llamar cada uno, por separado, sobre
el mismo análisis verificado; si esta función mutara `analisis.reparos` para
avisar del recorte, la segunda llamada añadiría un segundo aviso idéntico, y
el docente acabaría leyendo dos veces que se descartaron las mismas tres
observaciones. Que constar el recorte en el informe es una decisión de quien
compone el informe, no un efecto secundario de quien selecciona; a quien
compone el informe se le entrega la lista completa -dimensión, prioridad y
observación de cada una-, no solo un recuento. Una selección silenciosa sería
peor que una lista larga: por eso `descartadas` no cuenta, enumera.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.verificacion import (
    AnalisisVerificado,
    ValoracionVerificada,
    semaforo_por_valoraciones,
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


def _feedback(raiz: Path, version: str) -> dict:
    fichero = raiz / "criteria" / version / "feedback.yaml"
    if not fichero.is_file():
        return {}
    return yaml.safe_load(fichero.read_text(encoding="utf-8")) or {}


def _maximo(raiz: Path, version: str, color: str) -> int:
    """El límite de la economía pedagógica, leído de `feedback.yaml`.

    Ya no es un tope fijo: `color` es el semáforo que
    `semaforo_por_valoraciones` calcula sobre el mismo análisis -el estado
    del trabajo, no una opinión aparte-, y `prioridades_maximas_por_semaforo`
    puede fijar un número distinto para cada uno. Si ese mapa no trae el
    color que llega, o si el fichero entero no lo declara, se cae en
    `prioridades_maximas` -el tope absoluto de siempre-, exactamente igual
    que antes de que existiera esta distinción.

VERDE sí tiene entrada desde D-026, y conviene saber por qué. Hasta
    entonces un P3 sin P1 ni P2 daba AMBAR y VERDE no tenía nunca ninguna
    candidata; ahora ese caso da VERDE con alerta y sí las tiene. Sin
    entrada propia habría caído en el tope absoluto de cuatro, y un trabajo
    que "cumple la fase y puede avanzar" habría recibido más acciones que un
    ÁMBAR.

    GRIS sigue sin tenerla: no evaluable no produce ninguna valoración
    fiable de la que partir, así que `candidatas` ya está vacía antes de que
    este número llegue a usarse.
    """
    economia = _feedback(raiz, version).get("economia_pedagogica") or {}
    por_color = economia.get("prioridades_maximas_por_semaforo") or {}
    si_este_color = por_color.get(color)
    if si_este_color is not None:
        return int(si_este_color)
    return int(economia.get("prioridades_maximas") or _MAXIMO_POR_OMISION)


def _grupo_de_cada_causa(raiz: Path, version: str) -> dict[str, str]:
    """A qué causa raíz pertenece cada dimensión, según `feedback.yaml`.

    Las doce dimensiones del §8 no son compartimentos independientes -§2.5
    del calibrador-: varias, repartidas entre dimensiones distintas, pueden
    ser la misma causa vista más de una vez. Este mapa es la única pieza que
    hace falta para tratarlas como una sola prioridad en vez de varias, y
    sale entera de `agrupacion_de_causa` en `criteria/<version>/feedback.yaml`,
    no de una tabla escrita a mano en este módulo: si el profesor cambia qué
    dimensiones van juntas, este código las agrupa distinto sin que nadie
    toque una línea aquí.

    Una dimensión que no aparece en ningún grupo del fichero -o que el
    fichero no exista- queda como su propio grupo de un solo miembro: el
    código que llama a esto usa `dimension` como clave de repuesto cuando el
    mapa no trae nada, así que la ausencia de agrupación no descarta ninguna
    observación, solo deja de fusionarla con otra.
    """
    agrupacion = _feedback(raiz, version).get("agrupacion_de_causa") or {}
    mapa: dict[str, str] = {}
    for grupo in agrupacion.get("grupos") or []:
        if not isinstance(grupo, dict):
            continue
        codigo = grupo.get("codigo")
        for dimension in grupo.get("dimensiones") or []:
            mapa[dimension] = codigo
    return mapa


class SeleccionDePrioridades(BaseModel):
    """Lo que sale de aplicar los cuatro filtros: lo elegido para el alumno,
    y lo que quedó fuera -por el límite, o por ser la misma causa que otra
    observación ya elegida-.

    `descartadas` no lleva los P4 ni las observaciones sin evidencia
    localizada: esas nunca llegaron a ser candidatas, y su motivo de
    exclusión ya está en otro sitio -el propio campo `prioridad`, o
    `evidencia_localizada`, dentro de `analisis.valoraciones`, que el informe
    interno muestra entero-. Aquí solo están las que sí tenían prioridad y
    evidencia para el alumno y aun así no cupieron, ya fuera porque no había
    sitio o porque su causa ya estaba representada por otra de más
    prioridad.
    """

    model_config = ConfigDict(extra="forbid")

    elegidas: list[ValoracionVerificada]
    descartadas: list[ValoracionVerificada]


def seleccionar_prioridades(
    raiz: Path, version: str, analisis: AnalisisVerificado
) -> SeleccionDePrioridades:
    """Las observaciones que pueden llegar al alumno, ya ordenadas, junto con
    las que quedaron fuera del límite o de la causa ya representada.

    Solo entran como candidatas las que tienen una prioridad que
    `prioridades.yaml` marca como capaz de llegar al alumno (nunca un P4,
    hoy) y cuya evidencia se localizó en el documento. El orden dentro de
    cada nivel de prioridad se desempata por dimensión -no por el orden en
    que el motor las enumeró-: dos ejecuciones sobre el mismo trabajo no
    pueden darle al alumno prioridades distintas solo porque el motor haya
    listado sus hallazgos en otro orden esta vez.

    A partir de ahí, dos pasadas sobre la misma lista ordenada:

    1. La primera se queda con la observación de mayor prioridad de cada
       causa -ver `_grupo_de_cada_causa`- y manda al resto de esa misma
       causa a una lista aparte, sin descartarla todavía: son la misma causa
       vista más de una vez, y de ellas solo se traslada la más grave.
    2. Si, cubiertas todas las causas distintas que había, siguen sobrando
       huecos hasta el máximo de `_maximo`, esos huecos se rellenan con lo
       que quedó aparte en la primera pasada -por orden de prioridad-: el
       límite es sobre cuántas prioridades le llegan al alumno, no sobre
       cuántas causas distintas hay, y un trabajo con solo dos causas no
       debe inventarse una tercera para llenar el hueco, pero uno con seis
       observaciones de la misma causa tampoco debe perder las tres
       siguientes si de verdad caben.

    Lo que no entra en ninguna de las dos pasadas -por exceder el máximo, o
    por ser una causa ya representada sin que sobrara hueco- va en
    `descartadas`, no se pierde.

    El máximo mismo depende del estado del trabajo: `semaforo_por_valoraciones`
    calcula el mismo semáforo que `backend/salidas/informe.py` va a proponer
    para este análisis -no una lectura aparte-, y `_maximo` lo traduce al
    número que le corresponde. Es la misma señal, no una nueva: el semáforo
    ya resume «trabajo con base» o «carencia crítica», y ese es justo el
    criterio que el profesor pidió para variar entre tres y cuatro.

    Es una función pura: no toca `analisis`. Llamarla dos veces con la misma
    entrada da el mismo resultado y no deja ninguna marca de la primera vez.
    """
    orden = _orden_de_las_prioridades_que_llegan_al_alumno(raiz, version)
    candidatas = [
        v for v in analisis.valoraciones
        if v.prioridad in orden and v.evidencia_localizada
    ]
    candidatas.sort(key=lambda v: (orden[v.prioridad], v.dimension))

    grupos = _grupo_de_cada_causa(raiz, version)
    color = semaforo_por_valoraciones(analisis.valoraciones)
    maximo = _maximo(raiz, version, color)

    primera_por_causa: list[ValoracionVerificada] = []
    resto_de_la_misma_causa: list[ValoracionVerificada] = []
    causas_vistas: set[str] = set()
    for v in candidatas:
        causa = grupos.get(v.dimension, v.dimension)
        if causa in causas_vistas:
            resto_de_la_misma_causa.append(v)
        else:
            causas_vistas.add(causa)
            primera_por_causa.append(v)

    elegidas = primera_por_causa[:maximo]
    huecos_libres = maximo - len(elegidas)
    if huecos_libres > 0:
        elegidas += resto_de_la_misma_causa[:huecos_libres]
    # Reordenada por prioridad otra vez: un hueco relleno en la segunda
    # pasada puede ser más grave que algo que ya estaba en la primera -por
    # ejemplo, un segundo P1 de una causa ya representada, rellenando el
    # hueco que dejó un P3 de una causa distinta- y el orden que ve el
    # alumno tiene que seguir siendo por prioridad, no por en qué pasada
    # entró cada observación.
    elegidas.sort(key=lambda v: (orden[v.prioridad], v.dimension))

    elegidos_ids = {id(v) for v in elegidas}
    descartadas = [v for v in candidatas if id(v) not in elegidos_ids]

    return SeleccionDePrioridades(elegidas=elegidas, descartadas=descartadas)
