"""Lo que se puede deducir del nombre de un archivo.

La convención del §15.3 es CODIGO_CICLO_FASE_FECHA_VERSION.ext, por ejemplo
AF023_DAM_E2_20260115_v1.pdf.

Este módulo deduce y se detiene. No corrige nombres parecidos, no elige el
alumno más probable y no supone la fase por la fecha. El nombre del archivo
lo escribe el alumno, y confiar en él convertiría la condición de parada del
§18.2 —«alumno o fase no coinciden»— de excepción en rutina. Lo que sale de
aquí es una propuesta que el docente confirma.
"""

import re
from datetime import date

from pydantic import BaseModel, computed_field

FASES: tuple[str, ...] = ("TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA")

EJEMPLO = "AF023_DAM_E2_20260115_v1.pdf"

PATRON = re.compile(
    r"^(?P<codigo>[A-Za-z]{1,4}\d{1,5})"
    r"_(?P<ciclo>[A-Za-z]{2,8})"
    r"_(?P<fase>[A-Za-z0-9]{1,8})"
    r"_(?P<fecha>\d{8})"
    r"(?:_[vV](?P<version>\d{1,2}))?$"
)


class PropuestaDeIdentificacion(BaseModel):
    """De quién y de qué fase parece ser el archivo.

    Un campo a `None` significa que no se ha podido deducir, nunca que se
    haya deducido un valor por omisión.
    """

    codigo_alumno: str | None = None
    ciclo: str | None = None
    fase: str | None = None
    fecha: date | None = None
    version: int | None = None
    motivo: str = ""

    @computed_field
    @property
    def completa(self) -> bool:
        """Si el docente puede confirmarla de un clic, sin escribir nada.

        Va como `computed_field` porque el frontend la lee para decidir si
        enseña el botón de confirmar o el formulario. Una propiedad normal
        de Pydantic no se serializa, y llegaría ausente al navegador.
        """
        return all((
            self.codigo_alumno, self.ciclo, self.fase, self.fecha, self.version
        ))


def deducir(nombre_archivo: str) -> PropuestaDeIdentificacion:
    """Lee el nombre y propone. Lo que no encaja se queda a None con motivo."""
    tronco = nombre_archivo.rsplit(".", 1)[0]
    encaje = PATRON.match(tronco)
    if encaje is None:
        return PropuestaDeIdentificacion(
            motivo=f"El nombre «{nombre_archivo}» no sigue la convención "
                   f"CODIGO_CICLO_FASE_FECHA_VERSION, por ejemplo {EJEMPLO}. "
                   "Indica tú de quién es y de qué fase."
        )

    partes = encaje.groupdict()
    motivos = []

    fase = partes["fase"].upper()
    if fase not in FASES:
        motivos.append(
            f"«{partes['fase']}» no es una fase conocida. Las fases son: "
            + ", ".join(FASES) + "."
        )
        fase = None

    try:
        fecha = date(
            int(partes["fecha"][:4]), int(partes["fecha"][4:6]), int(partes["fecha"][6:])
        )
    except ValueError:
        motivos.append(f"«{partes['fecha']}» no es una fecha válida (AAAAMMDD).")
        fecha = None

    version = int(partes["version"]) if partes["version"] else None
    if version is None:
        motivos.append(
            f"El nombre no indica la versión. Se espera _v1, _v2… como en {EJEMPLO}."
        )

    return PropuestaDeIdentificacion(
        codigo_alumno=partes["codigo"].upper(),
        ciclo=partes["ciclo"].upper(),
        fase=fase,
        fecha=fecha,
        version=version,
        motivo=" ".join(motivos),
    )
