"""La lectura objetiva de una entrega, de principio a fin.

Une las seis piezas y no añade criterio propio: mide, contrasta con los
criterios, compara con la anterior y devuelve la ficha. No valora, no
puntúa y no redacta nada para el alumno; eso es la segunda parte del flujo.

La comparación evolutiva vuelve a medir el archivo anterior desde la
carpeta. No se guarda ni el PDF ni su texto —lo fija D-001—, así que la
única forma de comparar es que el archivo anterior siga donde estaba. Si no
está, no se compara y se dice: el §18.2 no admite seguir como si nada
cuando falta el material anterior.

Tampoco se compara si a alguno de los dos documentos le falta texto
extraíble. Comparar exige palabras a los dos lados; sin ellas la
comparación devuelve sus valores por omisión, y una cifra por omisión
enseñada como medida es peor que decir que no se ha comparado.
"""

from pathlib import Path

from pydantic import BaseModel

from backend.evolucion.comparacion import Evolucion, comparar, normalizar
from backend.extraccion import medir
from backend.extraccion.lectura import PdfIlegible
from backend.extraccion.medidas import Medidas
from backend.formato.comprobacion import Comprobacion, comprobar
from backend.persistencia.modelos import (
    BLOQUEADO,
    ESTADO_INICIAL,
    Almacen,
    EntregaRegistrada,
)


class FichaDeLectura(BaseModel):
    """Todo lo objetivo que se sabe de una entrega.

    `medidas` es `None` cuando el archivo no se ha podido leer. En ese caso
    la entrega queda en BLOQUEADO con su motivo, que es una salida prevista
    del §18.2 y no un fallo del sistema. Y al revés: si una entrega que
    estaba bloqueada se lee entera, el bloqueo se levanta, porque la propia
    lectura acaba de demostrar que su motivo ya no se sostiene.

    `aviso` no es solo para la comparación que no se pudo hacer: también lo
    usa `api/entregas.py` para decir que la entrega que se acaba de
    confirmar ya estaba registrada de antes -mismos datos declarados-, que
    es el caso legítimo de un archivo que el docente movió de carpeta y
    volvió a ver como pendiente.
    """

    entrega: EntregaRegistrada
    medidas: Medidas | None = None
    comprobaciones: list[Comprobacion] = []
    evolucion: Evolucion | None = None
    comparada_con: str | None = None
    aviso: str = ""


def _bloquear(almacen: Almacen, entrega: EntregaRegistrada, motivo: str) -> FichaDeLectura:
    bloqueada = almacen.cambiar_estado(entrega.id, BLOQUEADO, motivo) or entrega
    return FichaDeLectura(entrega=bloqueada)


def _desbloquear(almacen: Almacen, entrega: EntregaRegistrada) -> EntregaRegistrada:
    """Quita el bloqueo cuando la lectura acaba de demostrar que no se sostiene.

    Una entrega se bloquea porque el archivo no está o no se puede abrir. Si
    la siguiente lectura lo mide entero, ese motivo ya no es cierto, y
    dejarlo puesto hacía que la ficha enseñara las medidas completas junto
    al aviso «El archivo ya no está en la carpeta de entregas», en tinta de
    señal. Un motivo falso pintado como incumplimiento es peor que no
    avisar de nada.

    Vuelve a RECIBIDO, que es el estado del que salió: ANALIZADO lo pone el
    docente, y esta función no decide nada del §13.
    """
    if entrega.estado != BLOQUEADO:
        return entrega
    return almacen.cambiar_estado(entrega.id, ESTADO_INICIAL, None) or entrega


def leer(
    raiz: Path,
    carpeta: Path,
    version_criterios: str,
    almacen: Almacen,
    entrega: EntregaRegistrada,
) -> FichaDeLectura:
    """Mide la entrega, la contrasta con los criterios y la compara."""
    ruta = localizar(carpeta, entrega.nombre_archivo)
    if ruta is None:
        return _bloquear(
            almacen, entrega,
            f"El archivo «{entrega.nombre_archivo}» ya no está en la carpeta "
            "de entregas. Vuelve a dejarlo donde estaba o corrige la ficha.",
        )

    try:
        medidas = medir(ruta)
    except PdfIlegible as fallo:
        return _bloquear(almacen, entrega, str(fallo))

    entrega = _desbloquear(almacen, entrega)
    ficha = FichaDeLectura(
        entrega=entrega,
        medidas=medidas,
        comprobaciones=comprobar(raiz, version_criterios, medidas),
    )

    anterior = almacen.anterior_de(
        entrega.codigo_alumno, entrega.fase, entrega.version
    )
    if anterior is None:
        return ficha

    ruta_anterior = localizar(carpeta, anterior.nombre_archivo)
    if ruta_anterior is None:
        ficha.aviso = (
            f"No se ha comparado con la entrega anterior: el archivo "
            f"«{anterior.nombre_archivo}» ya no está en la carpeta. Devuélvelo "
            "y vuelve a abrir la ficha, o sigue sin comparación sabiendo que "
            "no se comprueba el progreso."
        )
        return ficha

    try:
        texto_anterior = medir(ruta_anterior).texto_plano
    except PdfIlegible as fallo:
        ficha.aviso = f"No se ha comparado con la entrega anterior: {fallo}"
        return ficha

    # Comparar exige texto a los dos lados. Sin él, `comparar` devuelve una
    # Evolucion con proporcion_conservada 0.0 y proporcion_nueva 0.0 -sus
    # valores por omisión, no una medida-, y la pantalla lo lee como «se
    # conserva el 0 % de lo anterior»: dos cifras inventadas presentadas
    # como medidas. Con la entrega nueva sin texto es peor todavía, porque
    # salta el aviso más severo del módulo -«la entrega no parece incluir el
    # trabajo anterior»- por un hecho puramente técnico.
    #
    # El criterio es `normalizar`, no `medidas.escaneado`, porque
    # `normalizar` es exactamente lo que la comparación usa para construir
    # sus firmas: si no devuelve ni una palabra, no hay nada que comparar,
    # lo diga o no la bandera de escaneado. `escaneado` es «no hay ni un
    # carácter de texto», que es más estricto: un PDF cuyo único texto
    # fueran guiones o números de página no sería escaneado y aun así no
    # daría ni una firma. Que el archivo sea un escaneado ya lo reporta por
    # su cuenta el criterio «archivo» de formato; aquí solo importa si hay
    # palabras con las que comparar.
    sin_texto_anterior = not normalizar(texto_anterior)
    sin_texto_nuevo = not normalizar(medidas.texto_plano)
    if sin_texto_anterior or sin_texto_nuevo:
        if sin_texto_anterior and sin_texto_nuevo:
            cual = (
                "ni esta entrega ni la anterior "
                f"(«{anterior.nombre_archivo}») tienen texto extraíble"
            )
        elif sin_texto_nuevo:
            cual = "esta entrega no tiene texto extraíble"
        else:
            cual = (
                f"la entrega anterior («{anterior.nombre_archivo}») no tiene "
                "texto extraíble"
            )
        ficha.aviso = (
            f"No se ha comparado el progreso con la entrega anterior: {cual}. "
            "Sin texto a los dos lados no hay nada que comparar, así que no "
            "se dice cuánto se conserva ni cuánto es nuevo."
        )
        return ficha

    ficha.evolucion = comparar(texto_anterior, medidas.texto_plano)
    ficha.comparada_con = anterior.nombre_archivo
    return ficha


def localizar(carpeta: Path, nombre: str) -> Path | None:
    """Localiza el archivo por su ruta relativa a la carpeta de entregas.

    `mirar` (Task 9) ya entrega esa ruta relativa -incluida la subcarpeta
    del alumno cuando la hay-, así que localizar es sencillamente unir la
    carpeta con ella. Solo si esa ruta directa no existe -el docente ha
    movido el archivo desde que se registró la entrega o desde que se vio
    como pendiente- se cae al respaldo: buscarlo en todo el árbol por su
    nombre de archivo, sin la ruta.
    """
    directa = carpeta / nombre
    if directa.is_file():
        return directa
    # El respaldo busca por `Path(nombre).name` -solo el nombre de archivo-
    # y no por `nombre` entero. Lo que puede haber cambiado es la
    # subcarpeta, no el nombre: buscar con `rglob(nombre)` seguiría
    # exigiendo la misma ruta relativa completa, así que un archivo movido
    # de una subcarpeta a otra no aparecería, y es exactamente el
    # movimiento que este respaldo existe para cubrir. Si esta línea vuelve
    # a `rglob(nombre)`, un trabajo confirmado dentro de una subcarpeta
    # reaparece como pendiente para siempre en cuanto el docente lo mueve.
    return next(
        (ruta for ruta in carpeta.rglob(Path(nombre).name) if ruta.is_file()),
        None,
    )
