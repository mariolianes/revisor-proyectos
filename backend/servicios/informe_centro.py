"""El informe por comunidad, centro, ciclo y fase. Punto 7 del orden de
implantación del docente: «03_INFORMES_CENTROS — resultados por evaluación,
comunidad, centro y ciclo».

Cuatro bloques, todos leídos del registro maestro y de lo que ya guardan los
otros puntos del sistema -este módulo no escribe nada, solo compone-:

- **Cobertura**: cuántos alumnos hay matriculados en el ámbito, cuántos han
  entregado cada fase y cuántos no. Es la petición literal del docente:
  «registrar los 200-250 alumnos aunque todavía no hayan entregado» sirve
  justamente «para detectar quién no ha entregado» (D-025).
- **Estado del proceso**: cuántas entregas hay en cada uno de los siete
  estados del §16.1.
- **Distribución de semáforos**: los cuatro oficiales del §12.1 -nunca un
  quinto color-, el propuesto por el motor y el confirmado por el docente
  por separado, porque son dos preguntas distintas (D-016).
- **Coste**: modelo exacto, tokens, coste por análisis principal, coste por
  verificación, coste de un reanálisis, promedio por fase y proyección
  mensual y anual -lo que pide, punto por punto, `decisiones#13-
  estabilidad`-, leído de `ejecucion_motor` a través de `Almacen.consumos()`.

**Ningún nombre de alumno, nunca.** Este módulo solo conoce `student_id`
(`AlmacenRegistrado.student_id` / `EntregaRegistrada.codigo_alumno`): la
correspondencia con el nombre real vive únicamente en el equipo del docente
(`backend/privacidad/listado_local.py`) y nunca llega hasta aquí -no hay
ningún parámetro, ninguna dependencia y ningún camino por el que pudiera
llegar-. La lista de «quién no ha entregado» que compone `_componer_
cobertura` es una lista de `student_id`; si el docente necesita nombres
para escribir un correo, los resuelve en su equipo, con `ListadoLocal`,
después de leer este informe -la misma frontera de dos pasos que ya fija
D-025 para cualquier listado de faltas de entrega-.

**Un grupo pequeño puede identificar a una persona sin necesidad de su
nombre.** Si un ciclo tiene tres matriculados y el informe dice que uno
está en rojo, el docente sabe quién es -es su trabajo, y el sistema no se lo
puede ni se lo debe ocultar-, pero cualquiera que reciba este informe
después de él también podría deducirlo, sin que ningún nombre ni ningún
`student_id` tenga que aparecer para conseguirlo: el `student_id` sí
aparece, y es precisamente la clave que permite señalar cuál de los tres es.
Por debajo de `UMBRAL_GRUPO_PEQUENO` matriculados en el ámbito filtrado,
este informe deja de listar los `student_id` de quién no ha entregado -ver
`Cobertura.aviso_grupo_pequeno`-. Los recuentos agregados (cuántos
matriculados, cuántos han entregado, la distribución de semáforos, el
coste) se muestran siempre, con cualquier tamaño de grupo: un número solo,
sin ningún identificador que lo acompañe, no permite señalar a una persona
concreta del mismo modo que sí lo permite una lista con nombre propio de
cada una -y sin esos recuentos, un centro pequeño quedaría invisible para
el propio mecanismo que existe para vigilar que nadie se quede sin corregir-.
`UMBRAL_GRUPO_PEQUENO` es una decisión de este módulo, no un dato del
Documento Maestro: se documenta en D-032 (`docs/decisions.md`) como
propuesta a confirmar o ajustar por el docente, no como un valor oficial.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from backend.persistencia.alumnos import CCAA_CODES, CICLO_CODES, validar_curso
from backend.persistencia.modelos import ESTADOS
from backend.vigilancia.nombres import FASES

if TYPE_CHECKING:
    from backend.persistencia.alumnos import AlumnoRegistrado
    from backend.persistencia.consumo import RegistroDeConsumo
    from backend.persistencia.modelos import Almacen, EntregaRegistrada

# Los cuatro colores oficiales del §12.1, en el mismo orden y el mismo
# vocabulario que `create type semaforo as enum (...)`
# (`supabase/migrations/20260827120000_esquema_inicial.sql`). «Verde con
# alertas» no es un quinto color (D-026): sigue siendo VERDE aquí también.
COLORES_SEMAFORO: tuple[str, ...] = ("VERDE", "AMBAR", "ROJO", "GRIS")

# Los dos estados de matrícula que cuentan como «sigue en el curso» a
# efectos de perseguir una entrega que falta. `BAJA` y `TRASLADADO` no
# entran en el denominador de «sin entregar»: perseguir a alguien que ya no
# está sería un ruido que el docente no pidió, y D-025 registró
# `estado_matricula` exactamente para poder hacer esta distinción.
ESTADOS_QUE_CUENTAN_COMO_MATRICULADO: tuple[str, ...] = ("ACTIVO", "REPETIDOR")

# Bajo cuántos alumnos matriculados-activos en el ámbito filtrado se retira
# la lista nominal de `student_id` de quién no ha entregado. Ver el
# docstring del módulo y D-032 (`docs/decisions.md`): es una propuesta de
# este módulo, no una cifra que traiga el Documento Maestro ni el docente.
UMBRAL_GRUPO_PEQUENO = 10


class FiltroInformeCentro(BaseModel):
    """El ámbito que pide quien consulta el informe. Los cinco campos son
    opcionales y se combinan con Y: omitir uno agrega sobre esa dimensión
    -sin `ciclo`, el informe suma los tres ciclos; sin ningún filtro, es el
    informe del curso entero-.

    `curso` existe porque un alumno repetidor recibe una identidad nueva
    cada curso (D-027): sin este filtro, un informe que agregara varios
    cursos a la vez contaría dos veces -legítimamente, son dos matrículas
    distintas- al mismo repetidor. Se deja sin filtrar por omisión, no
    porque sea lo más frecuente, sino porque forzarlo obligaría a saber de
    antemano qué cursos hay registrados.
    """

    model_config = ConfigDict(extra="forbid")

    ccaa: str | None = None
    centro: str | None = None
    ciclo: str | None = None
    curso: str | None = None
    fase: str | None = None


class CoberturaDeFase(BaseModel):
    """Cobertura de una fase concreta dentro del ámbito filtrado."""

    model_config = ConfigDict(extra="forbid")

    fase: str
    entregados: int
    sin_entregar: int
    # `None` cuando el grupo es pequeño (`UMBRAL_GRUPO_PEQUENO`): la lista se
    # retira, el recuento no. Ver el docstring del módulo.
    sin_entregar_codigos: list[str] | None = None


class Cobertura(BaseModel):
    """Cuántos alumnos hay matriculados en el ámbito, y cómo se reparte su
    entrega fase por fase."""

    model_config = ConfigDict(extra="forbid")

    matriculados: int
    # Informativo, aparte: alguien de baja o trasladado no cuenta como
    # matriculado ni se persigue por no entregar, pero tampoco desaparece
    # sin dejar rastro de que existió en este ámbito.
    bajas_o_traslados: int
    por_fase: list[CoberturaDeFase]
    aviso_grupo_pequeno: str | None = None


class EstadoDelProceso(BaseModel):
    """Cuántas entregas del ámbito hay en cada uno de los siete estados del
    §16.1. Incluye los que valen cero: un estado ausente del diccionario
    podría leerse como «no se sabe», y aquí sí se sabe -es cero-."""

    model_config = ConfigDict(extra="forbid")

    por_estado: dict[str, int]


class DistribucionSemaforos(BaseModel):
    """El semáforo propuesto por el motor y el confirmado por el docente,
    por separado: son dos preguntas distintas (D-016), y confundirlas
    contaría mal cuánto le queda por revisar al docente."""

    model_config = ConfigDict(extra="forbid")

    propuestos: dict[str, int]
    confirmados_por_docente: dict[str, int]
    # Entregas con corrección guardada cuyo semáforo todavía no ha
    # confirmado el docente (`semaforo_aprobado` es `None`). No es un color
    # más: es la cuenta de trabajo pendiente de él.
    pendientes_de_confirmar: int


class InformeDeCoste(BaseModel):
    """Lo que pide, punto por punto, `decisiones#13-estabilidad`: «modelo
    exacto, tokens, coste por análisis principal, coste por verificación,
    coste de un segundo análisis, promedio por fase y proyección mensual y
    anual», antes de concluir que el coste no es un problema.

    «Coste por verificación» y «coste de un segundo análisis» no tienen hoy
    una fuente de datos limpia -ver `notas`-: se devuelven como `None` en
    vez de inventar una cifra, siguiendo la misma regla que ya aplica
    `backend/analisis/precios.py` cuando un modelo no tiene tarifa.
    """

    model_config = ConfigDict(extra="forbid")

    # Modelo exacto -> número de ejecuciones con ese modelo, en el ámbito.
    modelos: dict[str, int]
    tokens_entrada: int
    tokens_salida: int
    tokens_entrada_cacheados: int
    # Solo de las ejecuciones con coste calculable; ver
    # `ejecuciones_sin_coste_calculable`.
    coste_total_usd: float
    coste_medio_analisis_principal_usd: float | None
    # Siempre `None` hoy: ver la nota sobre la verificación en `notas`.
    coste_medio_verificacion_usd: float | None
    # La aproximación disponible a «coste de un segundo análisis»: el
    # promedio de toda ejecución que no es la primera guardada para su
    # entrega -un reanálisis, o un segundo intento tras un fallo-. Ver la
    # nota correspondiente en `notas`.
    coste_medio_reanalisis_usd: float | None
    promedio_por_fase_usd: dict[str, float]
    proyeccion_mensual_usd: float | None
    proyeccion_anual_usd: float | None
    ejecuciones_sin_coste_calculable: int
    periodo_observado_dias: float | None
    # Explicaciones de cada hueco o cada asunción, en el mismo texto que lee
    # el docente: por qué falta una cifra, o de qué depende la que sí se
    # muestra. Nunca un número inventado donde no hay dato.
    notas: list[str]


class InformeCentro(BaseModel):
    """El informe completo para un ámbito: cobertura, proceso, semáforos y
    coste."""

    model_config = ConfigDict(extra="forbid")

    filtro: FiltroInformeCentro
    cobertura: Cobertura
    proceso: EstadoDelProceso
    semaforos: DistribucionSemaforos
    coste: InformeDeCoste


def _validar_filtro(filtro: FiltroInformeCentro) -> None:
    if filtro.ccaa is not None and filtro.ccaa not in CCAA_CODES:
        raise ValueError(
            f"«{filtro.ccaa}» no es una comunidad autónoma reconocida. Las "
            "comunidades son: " + ", ".join(CCAA_CODES) + "."
        )
    if filtro.ciclo is not None and filtro.ciclo not in CICLO_CODES:
        raise ValueError(
            f"«{filtro.ciclo}» no es un ciclo reconocido. Los ciclos son: "
            + ", ".join(CICLO_CODES) + "."
        )
    if filtro.fase is not None and filtro.fase not in FASES:
        raise ValueError(
            f"«{filtro.fase}» no es una fase. Las fases son: "
            + ", ".join(FASES) + "."
        )
    if filtro.curso is not None:
        validar_curso(filtro.curso)


def _en_ambito(alumno: AlumnoRegistrado, filtro: FiltroInformeCentro) -> bool:
    return (
        (filtro.ccaa is None or alumno.ccaa_code == filtro.ccaa)
        and (filtro.centro is None or alumno.centro_code == filtro.centro)
        and (filtro.ciclo is None or alumno.ciclo_code == filtro.ciclo)
        and (filtro.curso is None or alumno.curso == filtro.curso)
    )


def _componer_cobertura(
    matriculados_activos: list[AlumnoRegistrado],
    entregas: list[EntregaRegistrada],
    fase: str | None,
    bajas_o_traslados: int,
) -> Cobertura:
    codigos_matriculados = {a.student_id for a in matriculados_activos}
    mostrar_lista = len(matriculados_activos) >= UMBRAL_GRUPO_PEQUENO

    por_fase: list[CoberturaDeFase] = []
    for f in ((fase,) if fase is not None else FASES):
        codigos_con_entrega = {
            e.codigo_alumno for e in entregas
            if e.fase == f and e.codigo_alumno in codigos_matriculados
        }
        sin_entregar = sorted(codigos_matriculados - codigos_con_entrega)
        por_fase.append(CoberturaDeFase(
            fase=f,
            entregados=len(codigos_con_entrega),
            sin_entregar=len(sin_entregar),
            sin_entregar_codigos=sin_entregar if mostrar_lista else None,
        ))

    aviso = None
    if matriculados_activos and not mostrar_lista:
        aviso = (
            f"Este ámbito tiene {len(matriculados_activos)} alumnos "
            f"matriculados: por debajo de {UMBRAL_GRUPO_PEQUENO}, este "
            "informe no lista los identificadores de quién no ha entregado, "
            "aunque el recuento sigue siendo exacto. En un grupo así de "
            "pequeño, un identificador -aunque no lleve nombre- puede "
            "bastar para señalar a una persona concreta si este informe "
            "sale de tus manos. Si necesitas la lista para este grupo en "
            "concreto, consulta el registro maestro en tu equipo."
        )

    return Cobertura(
        matriculados=len(matriculados_activos),
        bajas_o_traslados=bajas_o_traslados,
        por_fase=por_fase,
        aviso_grupo_pequeno=aviso,
    )


def _componer_proceso(entregas_ambito: list[EntregaRegistrada]) -> EstadoDelProceso:
    por_estado = dict.fromkeys(ESTADOS, 0)
    for entrega in entregas_ambito:
        por_estado[entrega.estado] = por_estado.get(entrega.estado, 0) + 1
    return EstadoDelProceso(por_estado=por_estado)


def _componer_semaforos(
    semaforos: list, entregas_por_id: dict[str, EntregaRegistrada],
) -> DistribucionSemaforos:
    propuestos = dict.fromkeys(COLORES_SEMAFORO, 0)
    confirmados = dict.fromkeys(COLORES_SEMAFORO, 0)
    pendientes = 0
    for semaforo in semaforos:
        if semaforo.entrega_id not in entregas_por_id:
            continue
        propuestos[semaforo.semaforo_propuesto] = (
            propuestos.get(semaforo.semaforo_propuesto, 0) + 1
        )
        if semaforo.semaforo_aprobado is None:
            pendientes += 1
        else:
            confirmados[semaforo.semaforo_aprobado] = (
                confirmados.get(semaforo.semaforo_aprobado, 0) + 1
            )
    return DistribucionSemaforos(
        propuestos=propuestos, confirmados_por_docente=confirmados,
        pendientes_de_confirmar=pendientes,
    )


def _componer_coste(
    consumos: list[RegistroDeConsumo], entregas_por_id: dict[str, EntregaRegistrada],
) -> InformeDeCoste:
    consumos_ambito = [c for c in consumos if c.entrega_id in entregas_por_id]

    por_entrega: dict[str, list[RegistroDeConsumo]] = defaultdict(list)
    for consumo in consumos_ambito:
        por_entrega[consumo.entrega_id].append(consumo)

    modelos: dict[str, int] = defaultdict(int)
    tokens_entrada = tokens_salida = tokens_cacheados = 0
    sin_coste = 0
    coste_total = 0.0
    costes_principales: list[float] = []
    costes_reanalisis: list[float] = []
    costes_por_fase: dict[str, list[float]] = defaultdict(list)

    for entrega_id, grupo in por_entrega.items():
        # Sin `creada_en` -no debería ocurrir, lo asigna el propio almacén,
        # pero un almacén de pruebas ajeno a este repositorio podría no
        # hacerlo-, se trata como la más antigua posible en vez de reventar
        # o de decidir en qué extremo cae: mismo criterio defensivo que
        # `datetime.min` de la librería estándar para «sin fecha conocida».
        ordenado = sorted(grupo, key=lambda c: c.creada_en or datetime.min)
        fase_de_la_entrega = entregas_por_id[entrega_id].fase
        for indice, consumo in enumerate(ordenado):
            modelos[consumo.modelo] += 1
            tokens_entrada += consumo.tokens_entrada or 0
            tokens_salida += consumo.tokens_salida or 0
            tokens_cacheados += consumo.tokens_entrada_cacheados or 0
            if consumo.coste_estimado_usd is None:
                sin_coste += 1
                continue
            coste_total += consumo.coste_estimado_usd
            costes_por_fase[fase_de_la_entrega].append(consumo.coste_estimado_usd)
            if indice == 0:
                costes_principales.append(consumo.coste_estimado_usd)
            else:
                costes_reanalisis.append(consumo.coste_estimado_usd)

    notas: list[str] = [
        "«Coste por verificación» no se muestra: la verificación de hoy "
        "(backend/analisis/verificacion.py) es código determinista que no "
        "llama al motor, así que no genera ningún gasto que registrar. El "
        "día que exista una verificación que sí sea una llamada al motor, "
        "aparecerá aquí con su propio coste medio.",
        "«Coste de un segundo análisis» se aproxima con el promedio de toda "
        "ejecución que no es la primera guardada para su entrega -un "
        "reanálisis, o un segundo intento tras un fallo-: es lo que "
        "`ejecucion_motor` puede distinguir hoy, no necesariamente lo mismo "
        "que «un segundo análisis completo para comparar con el primero» "
        "de `decisiones#13-estabilidad`, que todavía no es una operación "
        "propia del sistema.",
    ]
    if sin_coste:
        notas.append(
            f"{sin_coste} ejecución(es) sin coste calculable: no había "
            "tarifa vigente para su modelo en config/precios_openai.yaml en "
            "la fecha en que se ejecutaron. No entran en ningún promedio ni "
            "en la proyección; sus tokens sí se cuentan arriba."
        )

    fechas_con_coste = sorted(
        c.creada_en for c in consumos_ambito
        if c.creada_en is not None and c.coste_estimado_usd is not None
    )
    periodo_dias: float | None = None
    proyeccion_mensual: float | None = None
    proyeccion_anual: float | None = None
    if len(fechas_con_coste) >= 2:
        span = (fechas_con_coste[-1] - fechas_con_coste[0]).total_seconds() / 86400
        if span > 0:
            periodo_dias = span
            tasa_diaria = coste_total / span
            proyeccion_mensual = tasa_diaria * 30
            proyeccion_anual = tasa_diaria * 365
    if proyeccion_mensual is None:
        notas.append(
            "Sin proyección mensual ni anual: hacen falta al menos dos "
            "ejecuciones con coste calculable en fechas distintas para medir "
            "un ritmo de gasto. La proyección, cuando aparece, es una "
            "extrapolación lineal del gasto observado en este ámbito -no del "
            "calendario oficial, que sigue pendiente de fuente oficial "
            "(programacion_didactica, docs/PENDIENTE_OFICIAL.md)-: unos días "
            "de calibración intensiva no predicen un mes normal del curso, y "
            "esta cifra es un orden de magnitud, no una factura."
        )

    return InformeDeCoste(
        modelos=dict(modelos),
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        tokens_entrada_cacheados=tokens_cacheados,
        coste_total_usd=round(coste_total, 6),
        coste_medio_analisis_principal_usd=(
            round(statistics.fmean(costes_principales), 6)
            if costes_principales else None
        ),
        coste_medio_verificacion_usd=None,
        coste_medio_reanalisis_usd=(
            round(statistics.fmean(costes_reanalisis), 6)
            if costes_reanalisis else None
        ),
        promedio_por_fase_usd={
            fase_: round(statistics.fmean(valores), 6)
            for fase_, valores in costes_por_fase.items()
        },
        proyeccion_mensual_usd=(
            round(proyeccion_mensual, 6) if proyeccion_mensual is not None else None
        ),
        proyeccion_anual_usd=(
            round(proyeccion_anual, 6) if proyeccion_anual is not None else None
        ),
        ejecuciones_sin_coste_calculable=sin_coste,
        periodo_observado_dias=(
            round(periodo_dias, 3) if periodo_dias is not None else None
        ),
        notas=notas,
    )


def componer_informe_centro(
    almacen: Almacen,
    *,
    ccaa: str | None = None,
    centro: str | None = None,
    ciclo: str | None = None,
    curso: str | None = None,
    fase: str | None = None,
) -> InformeCentro:
    """El informe completo para el ámbito que describen los cinco filtros,
    todos opcionales y combinados con Y. Sin ningún filtro, es el informe
    del curso entero.

    Compone, nunca decide: no aprueba nada, no elige a quién avisar y no
    escribe en ningún almacén. Es lectura pura sobre lo que otros puntos del
    sistema ya guardaron.
    """
    filtro = FiltroInformeCentro(
        ccaa=ccaa, centro=centro, ciclo=ciclo, curso=curso, fase=fase,
    )
    _validar_filtro(filtro)

    alumnos_ambito = [
        alumno for alumno in almacen.listar_alumnos() if _en_ambito(alumno, filtro)
    ]
    codigos_ambito = {alumno.student_id for alumno in alumnos_ambito}
    matriculados_activos = [
        alumno for alumno in alumnos_ambito
        if alumno.estado_matricula in ESTADOS_QUE_CUENTAN_COMO_MATRICULADO
    ]
    bajas_o_traslados = len(alumnos_ambito) - len(matriculados_activos)

    todas_las_entregas = almacen.listar()
    entregas_del_ambito_administrativo = [
        e for e in todas_las_entregas if e.codigo_alumno in codigos_ambito
    ]
    entregas_ambito = [
        e for e in entregas_del_ambito_administrativo
        if fase is None or e.fase == fase
    ]
    entregas_por_id = {e.id: e for e in entregas_ambito}

    cobertura = _componer_cobertura(
        matriculados_activos, entregas_del_ambito_administrativo, fase,
        bajas_o_traslados,
    )
    proceso = _componer_proceso(entregas_ambito)
    semaforos = _componer_semaforos(almacen.listar_semaforos(), entregas_por_id)
    coste = _componer_coste(almacen.consumos(), entregas_por_id)

    return InformeCentro(
        filtro=filtro, cobertura=cobertura, proceso=proceso,
        semaforos=semaforos, coste=coste,
    )
