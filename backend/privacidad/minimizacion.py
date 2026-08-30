"""Lo que se retira del texto antes de que salga hacia el motor de análisis.

El profesor lo pidió así: «Al motor solo va: ID, ciclo, modalidad, fase,
criterios y el contenido académico necesario». El nombre del alumno no se
manda -se sustituye por su código, que es el que ya viaja por todo el
sistema-, y tampoco correos, teléfonos, DNI ni firmas que aparezcan sueltos
en el texto del trabajo.

**Esto no es anonimización. Es minimización de mejor esfuerzo, y las dos
cosas no son lo mismo.** Anonimizar es una garantía: ningún dato personal
queda en el texto, verificable. Minimizar aquí es una regla que se aplica
sin poder demostrar que agotó los casos:

- Los correos, teléfonos y DNI se buscan con las MISMAS expresiones
  regulares de R6 (`tools/gobernanza/privacidad.py`, `PATRON_DNI`,
  `PATRON_CORREO`, `PATRON_TELEFONO`), reutilizadas tal cual y no
  reescritas: R6 ya afinó esos patrones contra los falsos positivos típicos
  de un documento real -un hash que parece teléfono, una fecha que parece
  DNI-, y llevan su propio banco de pruebas
  (`tests/gobernanza/test_privacidad.py`). Pero una expresión regular solo
  reconoce lo que encaja en su forma: un DNI escrito con espacios sueltos
  entre los dígitos, un correo partido por un salto de línea al final de
  una página, un teléfono extranjero, no encajan y pasan de largo.
- El nombre del alumno se busca por coincidencia literal contra el nombre
  que trae `listado_local.py` para su código -con margen para el orden
  «Apellidos, Nombre» de una portada-, pero eso exige dos cosas que pueden
  fallar: que el listado tenga ese código dado de alta, y que el alumno
  haya escrito su nombre en el documento exactamente como está en el
  listado. Un nombre compuesto abreviado, un apodo, una errata, un segundo
  apellido que el listado no trae, no se reconocen.
- No hay ningún patrón para «una firma»: una firma manuscrita escaneada no
  es texto -no llega aquí, PyMuPDF no la extrae-, y una firma mecanografiada
  («Fdo.: Juan Pérez») solo se retira si coincide con el nombre conocido del
  alumno, por el mismo mecanismo de arriba y con las mismas limitaciones.

Por eso este módulo nunca informa «texto limpio»: informa qué ha
sustituido y qué NO ha podido comprobar -sobre todo, si el listado local
no tenía nombre para ese código-, en `Minimizacion.avisos`. Prometer una
limpieza total que no se puede garantizar sería peor que admitir el límite:
el profesor decidió analizar entregas reales sabiendo que la herramienta es
personal y el tratamiento razonable, no que fuera infalible, y ese aviso es
la forma de que la decisión siga siendo suya, análisis a análisis, con la
información real delante -el mismo criterio que ya aplica
`AVISO_PROTECCION_DATOS` en `backend/api/analisis.py`-.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from tools.gobernanza.privacidad import PATRON_CORREO, PATRON_DNI, PATRON_TELEFONO

MARCADOR_ALUMNO = "[ALUMNO]"
MARCADOR_DNI = "[DNI-RETIRADO]"
MARCADOR_CORREO = "[CORREO-RETIRADO]"
MARCADOR_TELEFONO = "[TELEFONO-RETIRADO]"


class Minimizacion(BaseModel):
    """El texto ya minimizado, y lo que se sabe -y no se sabe- de esa limpieza.

    `texto` es lo único que debe llegar al motor y a la verificación de
    citas: ver el docstring de `backend/servicios/analisis_de_entrega.py`
    para por qué las citas se verifican contra este texto y no contra el
    original -el motor nunca vio el original, así que sus citas se refieren
    a este-.
    """

    texto: str
    nombre_conocido: bool
    veces_nombre_sustituido: int = 0
    veces_dni_sustituido: int = 0
    veces_correo_sustituido: int = 0
    veces_telefono_sustituido: int = 0

    @property
    def avisos(self) -> list[str]:
        """Lo que el profesor tiene que saber sobre esta minimización, si
        algo. Lista vacía cuando no hay nada que decir.
        """
        avisos = []
        if not self.nombre_conocido:
            avisos.append(
                "El listado local no tiene un nombre asociado a este código "
                "de alumno, así que no se ha podido buscar su nombre en el "
                "texto para sustituirlo. Si aparece escrito, ha salido tal "
                "cual hacia el motor."
            )
        return avisos

    @property
    def aviso(self) -> str:
        """Los avisos, en una sola frase, para componer con otros avisos de
        la misma entrega (mismo patrón que `FichaDeLectura.aviso`)."""
        return " ".join(self.avisos)


def _patron_del_nombre(nombre: str) -> re.Pattern[str]:
    """Un patrón que reconoce el nombre completo, en el orden en que está
    en el listado y también invertido -para cubrir el «Apellidos, Nombre»
    habitual en una portada-, sin distinguir mayúsculas de minúsculas.

    No es infalible: ver el docstring del módulo.
    """
    palabras = [re.escape(palabra) for palabra in nombre.split() if palabra]
    if not palabras:
        # Un nombre en blanco en el listado no debería poder llegar aquí
        # -`ListadoLocal.importar_csv` descarta las filas sin nombre-, pero
        # si ocurriera, un patrón que no casa con nada es más seguro que uno
        # que casa con cualquier palabra suelta del documento.
        return re.compile(r"(?!)")

    en_orden = r"\s+".join(palabras)
    formas = {en_orden}
    if len(palabras) > 1:
        formas.add(r"\s+".join(reversed(palabras)))
        # "Apellido(s), Nombre": el primer token del listado es el nombre de
        # pila -convención habitual al escribir un nombre completo en
        # castellano- y los siguientes son los apellidos.
        formas.add(r",\s*".join([r"\s+".join(palabras[1:]), palabras[0]]))

    alternativas = "|".join(sorted(formas))
    return re.compile(rf"\b(?:{alternativas})\b", re.IGNORECASE)


def minimizar(texto: str, nombre_alumno: str | None) -> Minimizacion:
    """El texto con el nombre del alumno, el DNI, el correo y el teléfono
    sustituidos por marcadores -donde se han podido reconocer-.

    El orden de las sustituciones no importa para el resultado: los cuatro
    patrones actúan sobre regiones del texto que no se solapan en la
    práctica -un correo no contiene el nombre completo separado por
    espacios, porque `\\b...\\s+...\\b` exige espacio literal entre las
    palabras del nombre y un correo no lo tiene-, así que sustituir en un
    orden u otro no puede hacer que una sustitución tape a otra.
    """
    resultado = texto
    veces_nombre = 0
    if nombre_alumno:
        resultado, veces_nombre = _patron_del_nombre(nombre_alumno).subn(
            MARCADOR_ALUMNO, resultado
        )

    resultado, veces_dni = PATRON_DNI.subn(MARCADOR_DNI, resultado)
    resultado, veces_correo = PATRON_CORREO.subn(MARCADOR_CORREO, resultado)
    resultado, veces_telefono = PATRON_TELEFONO.subn(MARCADOR_TELEFONO, resultado)

    return Minimizacion(
        texto=resultado,
        nombre_conocido=nombre_alumno is not None,
        veces_nombre_sustituido=veces_nombre,
        veces_dni_sustituido=veces_dni,
        veces_correo_sustituido=veces_correo,
        veces_telefono_sustituido=veces_telefono,
    )
