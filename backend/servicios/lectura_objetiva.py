"""La lectura objetiva de una entrega, de principio a fin.

Une las seis piezas y no añade criterio propio: mide, contrasta con los
criterios, compara con la anterior y devuelve la ficha. No valora, no
puntúa y no redacta nada para el alumno; eso es la segunda parte del flujo.

La comparación evolutiva vuelve a medir el archivo anterior desde la
carpeta. No se guarda ni el PDF ni su texto —lo fija D-001—, así que la
única forma de comparar es que el archivo anterior siga donde estaba. Si no
está, no se compara y se dice: el §18.2 no admite seguir como si nada
cuando falta el material anterior.
"""

from pathlib import Path

from pydantic import BaseModel

from backend.evolucion.comparacion import Evolucion, comparar
from backend.extraccion import medir
from backend.extraccion.lectura import PdfIlegible
from backend.extraccion.medidas import Medidas
from backend.formato.comprobacion import Comprobacion, comprobar
from backend.persistencia.modelos import Almacen, EntregaRegistrada


class FichaDeLectura(BaseModel):
    """Todo lo objetivo que se sabe de una entrega.

    `medidas` es `None` cuando el archivo no se ha podido leer. En ese caso
    la entrega queda en BLOQUEADO con su motivo, que es una salida prevista
    del §18.2 y no un fallo del sistema.

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
    bloqueada = almacen.cambiar_estado(entrega.id, "BLOQUEADO", motivo) or entrega
    return FichaDeLectura(entrega=bloqueada)


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
