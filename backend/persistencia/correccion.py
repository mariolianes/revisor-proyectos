"""El análisis, ya guardado, y la regla de D-001 sobre lo que lleva dentro.

Vive en su propio módulo y no en `modelos.py` porque necesita `Informe` y
`Devolucion` de verdad -no solo como anotación de tipo, sino para construir
instancias- y `salidas/informe.py` ya importa `EntregaRegistrada` desde
`modelos.py`. Meter el import contrario ahí crearía un ciclo; aquí no hay
ninguno, porque nada en `salidas/` importa de este módulo.
"""

from pydantic import BaseModel, ConfigDict

from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe

# D-001: el mismo límite que impone `evidencia.fragmento` en la migración.
LIMITE_DE_CITA = 1500


def validar_citas_acotadas(informe: Informe) -> None:
    """Ninguna cita del informe pasa de 1.500 caracteres.

    Valoraciones, fortalezas e indicios de autoría llevan cada uno su propia
    evidencia (`ValoracionVerificada.evidencia`, `FortalezaVerificada.evidencia`,
    `IndicioDeAutoriaVerificado.evidencia`), y solo la de las valoraciones
    tiene una fila propia en la tabla `evidencia`, con su CHECK
    `fragmento_acotado`. Esta función aplica la MISMA regla, en código y por
    igual en los dos almacenes, sobre cualquier cita que el sistema vaya a
    guardar -tenga o no una fila en la base de datos-: `correccion.informe`
    guarda el informe entero en una columna `jsonb`, que no lleva ningún
    CHECK de la base de datos consigo.

    Se llama antes de escribir nada, en los dos almacenes: un análisis con
    una cita fuera de límite no debe dejar ni una fila a medias.
    """
    citas = (
        [v.evidencia.cita for v in informe.valoraciones]
        + [f.evidencia.cita for f in informe.fortalezas]
        + [i.evidencia.cita for i in informe.indicios]
    )
    for cita in citas:
        if len(cita) > LIMITE_DE_CITA:
            raise ValueError(
                f"Una cita del análisis tiene {len(cita)} caracteres; D-001 "
                f"limita las citas guardadas a {LIMITE_DE_CITA}. Esto "
                "indica un fallo del motor, no un dato del alumno que "
                "recortar: revisa el análisis antes de guardarlo."
            )


class Correccion(BaseModel):
    """El análisis tal como queda en el almacén: sus dos salidas y el motor.

    `devolucion` puede ser `None`: es el caso de `InformeSinBorrador` -el
    informe es válido y ya está guardado, y la redacción del borrador no se
    completó-. Forzar aquí una `Devolucion` vacía confundiría ese caso con el
    que ya produce una vacía a propósito -sin fortalezas ni prioridades de
    las que redactar nada-, el mismo motivo por el que `ResultadoAnalisis` de
    la API (`backend/api/analisis.py`) hace la misma distinción.

    `aviso` es el texto que vio el docente al guardar, si lo hubo. No es un
    dato del análisis: es lo que compuso la API sobre él (por ejemplo, que el
    borrador no se pudo completar). Se guarda tal cual para que una recarga
    de la ficha diga lo mismo, sin recomponerlo a partir de una causa -la
    excepción original- que ya no existe fuera de la petición que la lanzó.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    informe: Informe
    devolucion: Devolucion | None
    motor: str
    aviso: str | None = None
