"""El informe técnico interno, según el Anexo C del Documento Maestro.

Es la salida donde SI aparece todo: los P4, las observaciones cuya evidencia
no se pudo localizar, los reparos de la verificación, las dudas que el motor
reserva al docente y los indicios de autoría. Al alumno le llega un resumen
(Task 8); al docente, el trabajo entero. Esa es la diferencia entre las dos
salidas, y no es de formato: este documento no llega jamas al alumno, y por
eso puede ser franco donde el borrador tiene que ser prudente.

No hay campo para la nota. El Anexo C la menciona -"Semaforo, nota y
recomendacion"- porque el Maestro la preve para cuando exista la rúbrica
oficial con sus ponderaciones; mientras esas ponderaciones sigan
PENDIENTE_OFICIAL, R3 impide inventarlas y aquí no existe ni el hueco. El
semaforo y la recomendacion si tienen hueco: los dos proponen -un estado
provisional y una accion sugerida, calibrados en
`criteria/<version>/semaforo.yaml`-, y ninguno de los dos califica.

Ningun indicio de autoría se presenta como un veredicto. `verificar()` ya le
pone a cada uno el aviso del §13 (un `Reparo` con `regla:
"autoria_es_indicio"`, incondicional, en `analisis.reparos`); este modulo no
repite ni suaviza ese aviso, se limita a no esconderlo: `indicios` y
`reparos` viajan juntos en el mismo informe.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from backend.analisis.verificacion import (
    AnalisisVerificado,
    FortalezaVerificada,
    IndicioDeAutoriaVerificado,
    Reparo,
    ValoracionVerificada,
)
from backend.persistencia.modelos import EntregaRegistrada
from backend.salidas.seleccion import seleccionar_prioridades
from backend.servicios.lectura_objetiva import FichaDeLectura

# El §9 del calibrador, calibrado en `criteria/<version>/semaforo.yaml`: un
# P1 es carencia critica (ROJO); un P2 o P3, mejora pendiente (AMBAR); sin
# ninguno de los tres, correcto para la fase (VERDE). GRIS no se calcula
# aqui: es el color de una incidencia administrativa -archivo ausente, fuera
# de plazo, ilegible-, y esas se deciden en la Parte A, antes de que exista
# un `AnalisisVerificado` sobre el que razonar. Este modulo solo resume lo
# que el análisis, ya verificado, dice sobre el contenido.
_SEMAFORO_POR_PRIORIDAD = {"P1": "ROJO", "P2": "AMBAR", "P3": "AMBAR"}

# Si `semaforo.yaml` no existiera. Los mismos textos que ese fichero declara
# hoy bajo `accion`, para que la ausencia del fichero degrade sin romper y no
# para inventar un texto que el criterio no ha fijado.
_RECOMENDACION_POR_OMISION = {
    "VERDE": "Mantener fortalezas y aplicar ajustes menores",
    "AMBAR": "Aplicar cambios antes de cerrar la siguiente fase",
    "ROJO": "Revisión docente y plan de corrección",
    "GRIS": "Resolver incidencia; no emitir juicio académico automático",
}


class Informe(BaseModel):
    """Los bloques del Anexo C que este modulo sabe componer.

    Quedan fuera dos bloques de la plantilla del Maestro: "Continuidad"
    -depende del feedback aplicado en la fase anterior, un dato que todavia
    no le llega a `componer_informe`- y "Revisión del profesor" -es el
    resultado de que el docente use este informe, no un dato que el informe
    pueda llevar sobre si mismo-. Ninguno de los dos se inventa aquí.
    """

    model_config = ConfigDict(extra="forbid")

    identificacion: dict[str, str]
    control_administrativo: list[str]
    resumen: str
    valoraciones: list[ValoracionVerificada]
    fortalezas: list[FortalezaVerificada]
    prioridades: list[ValoracionVerificada]
    prioridades_descartadas: list[ValoracionVerificada]
    dudas: list[str]
    indicios: list[IndicioDeAutoriaVerificado]
    reparos: list[Reparo]
    dimensiones_ausentes: list[str]
    semaforo: str | None
    recomendacion: str | None
    motor: str


def _semaforo(analisis: AnalisisVerificado) -> str | None:
    """El peor de los estados que se desprenden de las valoraciones fiables.

    Solo cuentan las valoraciones cuya evidencia se localizo en el
    documento. No es un matiz menor: si el motor devolviera diez P1 y
    ninguna de sus citas existiera en el texto -las diez inventadas-, un
    semaforo calculado sobre la prioridad en bruto diria ROJO con la misma
    confianza que si las diez estuvieran bien fundadas. Aquí no se computa
    sobre lo que el motor afirmo, sino sobre lo que la verificación ya dio
    por localizable; el resto se queda en `valoraciones` -entero, para que
    el docente lo vea- pero no decide el color.

    Y si no queda ninguna valoración fiable -porque no hubo ninguna, o
    porque las que hubo no se localizaron- no se devuelve color: no hay
    estado que resumir, y un verde por defecto diria que el trabajo esta
    bien cuando lo que pasa es que no se ha podido valorar nada. Ese
    silencio (`None`) es visible en el informe porque `dimensiones_ausentes`
    y `reparos` siguen ahi para explicar por que.
    """
    fiables = [v for v in analisis.valoraciones if v.evidencia_localizada]
    if not fiables:
        return None
    for codigo in ("P1", "P2", "P3"):
        if any(v.prioridad == codigo for v in fiables):
            return _SEMAFORO_POR_PRIORIDAD[codigo]
    return "VERDE"


def _recomendaciones_por_color(raiz: Path, version: str) -> dict[str, str]:
    """La accion calibrada de cada color, leida de `semaforo.yaml`.

    No se escribe un texto nuevo aqui: se reutiliza la columna `accion` que
    ese fichero ya declara para cada código, con su propia `fuente` al
    Documento Maestro. Inventar una redacción distinta en este modulo
    duplicaria una decisión que ya vive, versionada, en `criteria/`.
    """
    fichero = raiz / "criteria" / version / "semaforo.yaml"
    if not fichero.is_file():
        return dict(_RECOMENDACION_POR_OMISION)
    catalogo = yaml.safe_load(fichero.read_text(encoding="utf-8")) or []
    return {
        c["codigo"]: c["accion"]
        for c in catalogo
        if isinstance(c, dict) and "codigo" in c and "accion" in c
    }


def componer_informe(
    raiz: Path,
    version: str,
    entrega: EntregaRegistrada,
    ficha: FichaDeLectura | None,
    analisis: AnalisisVerificado,
    motor: str,
) -> Informe:
    """Compone el Anexo C. `ficha` es la lectura objetiva, o `None` si no la hay.

    Llama a `seleccionar_prioridades` una sola vez: es una funcion pura que
    no deja marca en `analisis`, y sus dos listas -`elegidas` y
    `descartadas`- son justo `prioridades` y `prioridades_descartadas` de
    este informe. Volver a llamarla no cambiaria el resultado, pero
    duplicaria el trabajo sin motivo.
    """
    control: list[str] = []
    if ficha is not None and ficha.medidas is not None:
        control.append(f"{ficha.medidas.total_paginas} paginas en total.")
        contadas = ficha.medidas.estructura.paginas_de_contenido
        control.append(
            f"{contadas} paginas de contenido." if contadas is not None
            else "No se ha podido contar el contenido: no se localizo el indice."
        )
        for c in ficha.comprobaciones:
            if c.veredicto == "NO_CUMPLE":
                control.append(f"{c.criterio}: {c.medido}")

    seleccion = seleccionar_prioridades(raiz, version, analisis)
    color = _semaforo(analisis)

    return Informe(
        identificacion={
            "alumno": entrega.codigo_alumno,
            "ciclo": entrega.ciclo,
            "fase": entrega.fase,
            "version": str(entrega.version),
            "archivo": entrega.nombre_archivo,
            "criterios": entrega.version_criterios,
        },
        control_administrativo=control,
        resumen=(
            analisis.fortalezas[0].descripcion
            if analisis.fortalezas
            else "Sin resumen del motor."
        ),
        valoraciones=analisis.valoraciones,
        fortalezas=analisis.fortalezas,
        prioridades=seleccion.elegidas,
        prioridades_descartadas=seleccion.descartadas,
        dudas=analisis.dudas_para_el_docente,
        indicios=analisis.indicios_de_autoria,
        reparos=analisis.reparos,
        dimensiones_ausentes=analisis.dimensiones_ausentes,
        semaforo=color,
        recomendacion=(
            _recomendaciones_por_color(raiz, version).get(color)
            if color is not None
            else None
        ),
        motor=motor,
    )
