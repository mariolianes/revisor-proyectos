"""Lo medido contra lo exigido en criteria/<version>/formato.yaml.

Este módulo no sabe abrir un PDF y el de extracción no sabe qué exige el
Maestro. Esa separación es lo que permite cambiar un criterio sin tocar la
medición, y medir mejor sin revisar ningún criterio.

Ningún valor de criterio está escrito aquí: todos se leen del fichero en
cada llamada. Copiarlos al código habría creado un segundo dueño del
criterio, que es lo que la regla R1 existe para impedir.
"""

import unicodedata
from pathlib import Path

import yaml
from pydantic import BaseModel

from backend.extraccion.medidas import Medidas

CUMPLE = "CUMPLE"
NO_CUMPLE = "NO_CUMPLE"
NO_VERIFICABLE = "NO_VERIFICABLE"

# Un texto justificado alinea a la derecha todas las líneas menos la última
# de cada párrafo. Las dos bandas son anchas a propósito: entre ellas la
# medida no distingue, y decir «no lo sé» es más útil que acertar a medias.
JUSTIFICADO_DESDE = 0.75
JUSTIFICADO_HASTA = 0.25

NOTA_INTERLINEADO = (
    "Un PDF no guarda «1,5 líneas»: guarda la distancia entre líneas base. "
    "La equivalencia entre esa distancia y el valor elegido en el procesador "
    "de textos depende de la fuente —para Arial 11 a 1,5 el ratio ronda "
    "1,73— y no está fijada en ninguna fuente oficial. Se enseña lo medido "
    "y lo juzga el docente."
)

NOTA_IMAGENES = (
    "Comprobar numeración, título, fuente y mención en el texto exige leer "
    "el documento y relacionar cada imagen con lo que se dice de ella. "
    "Corresponde a la segunda parte del flujo."
)


class Comprobacion(BaseModel):
    """Un criterio de formato contrastado con lo medido.

    `esperado` y `medido` van como texto porque los lee el docente. `fuente`
    es la sección del Maestro que respalda el criterio: sin ella la
    comprobación no se emite.
    """

    criterio: str
    veredicto: str
    esperado: str
    medido: str
    fuente: str
    nota: str = ""


class _FicheroInservible(Exception):
    """El fichero de criterios no se ha podido usar, con qué decirle al docente.

    Lleva ya redactado lo que verá en la `Comprobacion` de repuesto:
    `medido` es qué le pasa al fichero, y `nota` qué hacer para arreglarlo.
    """

    def __init__(self, medido: str, nota: str) -> None:
        super().__init__(medido)
        self.medido = medido
        self.nota = nota


def _cargar(raiz: Path, version: str) -> dict:
    """El fichero de criterios como diccionario, o por qué no se puede usar.

    Las tres formas de que no se pueda usar acaban en `_FicheroInservible`,
    porque el docente edita este fichero a mano y las tres son cosas que le
    pueden pasar de verdad:

    - Guardarlo con el Bloc de notas en la codificación de Windows en vez
      de en UTF-8: la primera tilde deja de leerse y `read_text` revienta.
    - Escribir un YAML que no se puede interpretar.
    - Escribir un YAML válido que no es un mapa de criterios -una lista,
      por ejemplo-, con lo que `criterios.items()` no existe.

    Los tres escapaban como 500 y tumbaban la ficha entera, en un módulo
    cuyo docstring promete justo lo contrario.
    """
    ruta = f"criteria/{version}/formato.yaml"
    fichero = raiz / "criteria" / version / "formato.yaml"
    if not fichero.is_file():
        return {}

    try:
        texto = fichero.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise _FicheroInservible(
            "el fichero no está guardado en UTF-8",
            f"{ruta} tiene caracteres que no son UTF-8 ({error.reason}, en el "
            f"byte {error.start}). Vuelve a guardarlo en UTF-8: si lo editas "
            "con el Bloc de notas, en «Guardar como» hay una lista de "
            "codificación y hay que elegir UTF-8. Mientras tanto no se puede "
            "comprobar ningún criterio de formato.",
        ) from error

    try:
        criterios = yaml.safe_load(texto)
    except yaml.YAMLError as error:
        raise _FicheroInservible(
            "el fichero no se ha podido interpretar",
            f"{ruta} no se ha podido leer como YAML: {error}. Corrígelo para "
            "que el resto de la comprobación pueda ejecutarse.",
        ) from error

    if criterios is None:
        return {}
    if not isinstance(criterios, dict):
        raise _FicheroInservible(
            f"el fichero es un YAML válido, pero no es un mapa de criterios "
            f"(es {type(criterios).__name__})",
            f"{ruta} tiene que ser una lista de criterios con nombre, cada "
            "uno con sus valores debajo -«tipografia:», «margenes:»...-, no "
            "una lista de guiones ni un valor suelto. Compáralo con la "
            "versión anterior del fichero.",
        )
    return criterios


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar el valor de un criterio sin
    que una mayúscula o un acento decidan el veredicto."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.strip().lower()


def _texto(valor: object) -> str:
    """Convierte cualquier valor a texto sin que la conversión pueda fallar.

    El nombre y la `fuente` de un bloque de criterios llegan tal cual los
    escribió quien editó el YAML a mano: no tienen por qué ser una cadena
    -`fuente` podría ser un diccionario, una lista, un número-. Se usan aquí
    para construir la `Comprobacion` de repuesto cuando algo ya ha fallado,
    así que no pueden volver a fallar por el mismo motivo: si un campo
    crudo del bloque se pasa sin convertir a un `Comprobacion(...)` de
    repuesto, Pydantic lo rechaza y esa segunda excepción escapa sin que
    nadie la capture. Cualquier valor que en el futuro se tome directamente
    de un bloque para un mensaje de repuesto debe pasar por aquí primero.
    """
    try:
        return str(valor)
    except Exception:
        return "<valor no representable>"


def _extension(bloque: dict, medidas: Medidas) -> Comprobacion:
    minimo = bloque["minimo_paginas_contenido"]
    contadas = medidas.estructura.paginas_de_contenido
    if contadas is None:
        return Comprobacion(
            criterio="extension",
            veredicto=NO_VERIFICABLE,
            esperado=f"{minimo} páginas de contenido como mínimo",
            medido=f"{medidas.total_paginas} páginas en total",
            fuente=bloque["fuente"],
            nota="No se ha localizado el índice, así que no se sabe dónde "
                 "empieza el contenido ni dónde acaban los anexos. Indica el "
                 "reparto y se cuenta.",
        )
    return Comprobacion(
        criterio="extension",
        veredicto=CUMPLE if contadas >= minimo else NO_CUMPLE,
        esperado=f"{minimo} páginas de contenido como mínimo",
        medido=f"{contadas} páginas de contenido "
               f"(de {medidas.total_paginas} en total)",
        fuente=bloque["fuente"],
    )


def _tipografia(bloque: dict, medidas: Medidas) -> Comprobacion:
    familia = str(bloque["familia"])
    cuerpo = float(bloque["cuerpo"])
    tolerancia = float(bloque.get("tolerancia_cuerpo", 0))
    medido = medidas.texto

    # Esta salida cubre también el `cuerpo_dominante` a None: los dos
    # salen de la misma rama de `medir_texto` -no hay ni un fragmento de
    # texto del que sacar familia ni cuerpo-, así que una familia vacía y
    # un cuerpo nulo van siempre juntos. Si alguna vez dejaran de ir
    # juntos, la resta de abajo daría un TypeError, que el `try/except` de
    # `comprobar` convierte en un NO_VERIFICABLE con el motivo a la vista:
    # se vería, no se inventaría un veredicto.
    if not medido.familia_dominante:
        return Comprobacion(
            criterio="tipografia",
            veredicto=NO_VERIFICABLE,
            esperado=f"{familia} {cuerpo:g}",
            medido="el documento no tiene texto extraíble",
            fuente=bloque["fuente"],
        )

    coincide = (
        medido.familia_dominante.lower() == familia.lower()
        and abs(medido.cuerpo_dominante - cuerpo) <= tolerancia
    )
    return Comprobacion(
        criterio="tipografia",
        veredicto=CUMPLE if coincide else NO_CUMPLE,
        esperado=f"{familia} {cuerpo:g} (tolerancia {tolerancia:g})",
        medido=f"{medido.familia_dominante} {medido.cuerpo_dominante:g}, "
               f"en el {medido.proporcion_cuerpo_dominante:.0%} del texto",
        fuente=bloque["fuente"],
    )


def _interlineado(bloque: dict, medidas: Medidas) -> Comprobacion:
    """Siempre NO_VERIFICABLE. Ver NOTA_INTERLINEADO."""
    ratio = medidas.texto.ratio_interlineado
    return Comprobacion(
        criterio="interlineado",
        veredicto=NO_VERIFICABLE,
        esperado=f"{bloque['valor']} líneas",
        medido=(f"ratio medido {ratio:.2f} entre líneas base y cuerpo"
                if ratio is not None else "no hay líneas suficientes para medirlo"),
        fuente=bloque["fuente"],
        nota=NOTA_INTERLINEADO,
    )


def _alineacion(bloque: dict, medidas: Medidas) -> Comprobacion:
    """Solo se falla o se aprueba cuando el criterio pide «justificado».

    La proporción de líneas que llegan al margen derecho distingue un texto
    justificado de uno que no lo está, pero no sabe decir si un texto no
    justificado queda alineado a la izquierda, a la derecha o centrado.
    Juzgarlo con esa medida haría que un documento que cumple exactamente lo
    que se le pide —«alineado a la izquierda», por ejemplo— recibiera
    NO_CUMPLE por tener pocas líneas al margen derecho, que es justo lo que
    se espera de él.
    """
    proporcion = medidas.texto.proporcion_lineas_al_margen_derecho
    esperado = str(bloque["valor"])
    fuente = bloque["fuente"]

    if _normalizar(esperado) != "justificado":
        medido = (
            f"el {proporcion:.0%} de las líneas llega al margen derecho"
            if proporcion is not None
            else "el documento no tiene texto extraíble"
        )
        return Comprobacion(
            criterio="alineacion", veredicto=NO_VERIFICABLE, esperado=esperado,
            medido=medido, fuente=fuente,
            nota="La proporción de líneas que llegan al margen derecho "
                 "distingue un texto justificado de uno que no lo está, pero "
                 "no dice si un texto no justificado queda alineado a la "
                 "izquierda, a la derecha o centrado. Míralo en el "
                 "documento.",
        )

    if proporcion is None:
        return Comprobacion(
            criterio="alineacion", veredicto=NO_VERIFICABLE, esperado=esperado,
            medido="el documento no tiene texto extraíble", fuente=fuente,
        )

    medido = f"el {proporcion:.0%} de las líneas llega al margen derecho"
    if proporcion >= JUSTIFICADO_DESDE:
        return Comprobacion(criterio="alineacion", veredicto=CUMPLE,
                            esperado=esperado, medido=medido, fuente=fuente)
    if proporcion <= JUSTIFICADO_HASTA:
        return Comprobacion(criterio="alineacion", veredicto=NO_CUMPLE,
                            esperado=esperado, medido=medido, fuente=fuente)
    return Comprobacion(
        criterio="alineacion", veredicto=NO_VERIFICABLE, esperado=esperado,
        medido=medido, fuente=fuente,
        nota="Entre el 25 % y el 75 % la medida no distingue un texto "
             "justificado de uno alineado a la izquierda con líneas largas. "
             "Míralo en el documento.",
    )


def _margenes(bloque: dict, medidas: Medidas) -> Comprobacion:
    esperado_cm = float(bloque["centimetros"])
    tolerancia = float(bloque.get("tolerancia", 0))
    medido = medidas.texto
    lados = {
        "izquierdo": medido.margen_izquierdo_cm,
        "derecho": medido.margen_derecho_cm,
        "superior": medido.margen_superior_cm,
        "inferior": medido.margen_inferior_cm,
    }
    if any(valor is None for valor in lados.values()):
        return Comprobacion(
            criterio="margenes", veredicto=NO_VERIFICABLE,
            esperado=f"{esperado_cm:g} cm", medido="no hay texto que medir",
            fuente=bloque["fuente"],
        )

    incumplen = {
        lado for lado, valor in lados.items()
        if abs(valor - esperado_cm) > tolerancia
    }
    # Los cuatro valores quedan a la vista -son informativos- pero el que
    # incumple se señala: sin eso el docente tenía que restar cada uno
    # contra la tolerancia a mano para saber cuál es el problema.
    medido = ", ".join(
        f"{lado} {valor:.2f} cm" + (" [incumple]" if lado in incumplen else "")
        for lado, valor in lados.items()
    )
    return Comprobacion(
        criterio="margenes",
        veredicto=CUMPLE if not incumplen else NO_CUMPLE,
        esperado=f"{esperado_cm:g} cm (tolerancia {tolerancia:g})",
        medido=medido,
        fuente=bloque["fuente"],
        nota="" if not incumplen else
             "Los márgenes superior e inferior se miden sobre todo el texto "
             "de la página: un encabezado o un pie los reducen.",
    )


def _archivo(bloque: dict, medidas: Medidas) -> Comprobacion:
    admite = bool(bloque.get("admite_escaneado", False))
    return Comprobacion(
        criterio="archivo",
        veredicto=NO_CUMPLE if (medidas.escaneado and not admite) else CUMPLE,
        esperado=f"{bloque.get('formato', 'PDF')} generado desde el original"
                 + ("" if admite else ", no escaneado"),
        medido="PDF escaneado, sin texto extraíble" if medidas.escaneado
               else "PDF con texto extraíble",
        fuente=bloque["fuente"],
    )


def _paginas_en_blanco(bloque: dict, medidas: Medidas) -> Comprobacion:
    permitidas = bool(bloque.get("permitidas", False))
    hay = medidas.paginas_en_blanco
    return Comprobacion(
        criterio="paginas_en_blanco",
        veredicto=NO_CUMPLE if (hay and not permitidas) else CUMPLE,
        esperado="ninguna página en blanco" if not permitidas
                 else "se admiten páginas en blanco",
        medido="ninguna" if not hay
               else "páginas " + ", ".join(str(numero) for numero in hay),
        fuente=bloque["fuente"],
    )


def _imagenes(bloque: dict, medidas: Medidas) -> Comprobacion:
    """Siempre NO_VERIFICABLE en esta parte. Ver NOTA_IMAGENES."""
    return Comprobacion(
        criterio="imagenes",
        veredicto=NO_VERIFICABLE,
        esperado="numeradas, tituladas, con fuente si son ajenas y citadas "
                 "en el texto",
        medido=f"{len(medidas.imagenes)} imágenes colocadas",
        fuente=bloque["fuente"],
        nota=NOTA_IMAGENES,
    )


def _indice_paginado(bloque: dict, medidas: Medidas) -> Comprobacion:
    estructura = medidas.estructura
    if estructura.pagina_del_indice is None:
        return Comprobacion(
            criterio="indice_paginado", veredicto=NO_VERIFICABLE,
            esperado="títulos y páginas del índice coinciden con el documento",
            medido="no se ha localizado el índice", fuente=bloque["fuente"],
        )

    problemas = list(estructura.paginas_declaradas_incorrectas)
    problemas += [
        f"«{titulo}» aparece en el índice pero no se encuentra en el documento."
        for titulo in estructura.titulos_no_encontrados
    ]
    return Comprobacion(
        criterio="indice_paginado",
        veredicto=CUMPLE if not problemas else NO_CUMPLE,
        esperado="títulos y páginas del índice coinciden con el documento",
        medido=" ".join(problemas) if problemas
               else f"{len(estructura.entradas_de_indice)} entradas, todas correctas",
        fuente=bloque["fuente"],
    )


# Cada criterio del fichero con la función que lo comprueba. Un criterio que
# no esté aquí simplemente no se comprueba: no se inventa un veredicto.
COMPROBADORES = {
    "extension": _extension,
    "tipografia": _tipografia,
    "interlineado": _interlineado,
    "alineacion": _alineacion,
    "margenes": _margenes,
    "archivo": _archivo,
    "paginas_en_blanco": _paginas_en_blanco,
    "imagenes": _imagenes,
    "indice_paginado": _indice_paginado,
}


def comprobar(raiz: Path, version: str, medidas: Medidas) -> list[Comprobacion]:
    """Un resultado por criterio de formato presente en el fichero.

    El orden es el del fichero de criterios, que es el que el docente
    conoce. El profesor edita ese YAML a mano: un fichero que no se puede
    interpretar, o un criterio mal escrito dentro de uno que sí se
    interpreta, no tiran abajo la comprobación de los demás. Cada fallo se
    convierte en su propio NO_VERIFICABLE, con el motivo a la vista, y el
    resto sigue su curso.
    """
    try:
        criterios = _cargar(raiz, version)
    except _FicheroInservible as fallo:
        return [Comprobacion(
            criterio="fichero_de_criterios",
            veredicto=NO_VERIFICABLE,
            esperado="un YAML válido en criteria/<version>/formato.yaml",
            medido=fallo.medido,
            fuente=f"criteria/{version}/formato.yaml",
            nota=fallo.nota,
        )]

    resultado = []
    for nombre, bloque in criterios.items():
        if not isinstance(bloque, dict):
            continue

        # R1: sin fuente trazable, o con una fuente vacía, el criterio no
        # existe, así que tampoco existe su comprobación.
        fuente = bloque.get("fuente")
        if not fuente:
            continue

        comprobador = COMPROBADORES.get(nombre)
        if comprobador is None:
            nombre_txt = _texto(nombre)
            resultado.append(Comprobacion(
                criterio=nombre_txt,
                veredicto=NO_VERIFICABLE,
                esperado="una comprobación programada para este criterio",
                medido="el criterio está declarado en el fichero pero el "
                       "sistema todavía no sabe comprobarlo",
                fuente=_texto(fuente),
                nota=f"«{nombre_txt}» no coincide con ningún comprobador "
                     f"conocido en criteria/{version}/formato.yaml. Si es "
                     "una errata en el nombre, corrígela; si es un criterio "
                     "nuevo, falta programar su comprobación.",
            ))
            continue

        try:
            resultado.append(comprobador(bloque, medidas))
        except Exception as error:  # noqa: BLE001 - un bloque mal escrito, o un fallo interno, no debe tumbar los demás
            # No se sabe si el fallo viene de un bloque mal escrito o de un
            # error del programa al operar sobre lo medido: el mismo
            # try/except envuelve las dos cosas y no hay forma fiable de
            # distinguirlas desde aquí. Se ofrecen las dos posibilidades sin
            # afirmar cuál es -lo que no se sabe, no se afirma-, igual que
            # con cualquier otro juicio de este módulo.
            nombre_txt = _texto(nombre)
            resultado.append(Comprobacion(
                criterio=nombre_txt,
                veredicto=NO_VERIFICABLE,
                esperado="un criterio comprobable",
                medido="no se ha podido comprobar",
                fuente=_texto(fuente),
                nota=f"No se ha podido comprobar el criterio «{nombre_txt}» "
                     f"({type(error).__name__}: {error}). Puede deberse a un "
                     f"error en criteria/{version}/formato.yaml -sobre todo "
                     "si se acaba de editar- o a un fallo del programa; con "
                     "lo que se sabe aquí no se puede distinguir cuál de las "
                     "dos es. El resto de criterios sí se ha comprobado.",
            ))
    return resultado
