"""PDFs sintéticos con desviaciones conocidas.

Se construyen aquí y viven en tmp_path. Ninguna prueba de este proyecto
toca una entrega real de un alumno, y ningún PDF entra en el repositorio.
"""

import re
from pathlib import Path

import pymupdf
import pytest

# insert_text sitúa la línea base en el punto dado. El interlineado medido
# será la distancia entre líneas base consecutivas.
IZQUIERDA = 72.0
PRIMERA_LINEA = 100.0

# Los criterios de formato reales, con el mínimo de páginas rebajado a 4 y la
# familia puesta en Helvetica, que es la que PyMuPDF incrusta con «helv».
CRITERIOS_DE_PRUEBA = """
extension:
  minimo_paginas_contenido: 4
  excluye: [portada, indice, anexos]
  fuente: maestro#6-estandar-academico

tipografia:
  familia: Helvetica
  cuerpo: 11
  tolerancia_cuerpo: 0.5
  fuente: maestro#6-estandar-academico

interlineado:
  valor: 1.5
  tolerancia: 0.1
  fuente: maestro#6-estandar-academico

alineacion:
  valor: justificado
  fuente: maestro#6-estandar-academico

margenes:
  centimetros: 2.5
  tolerancia: 0.5
  fuente: maestro#6-estandar-academico

archivo:
  formato: PDF
  generado_desde_original: true
  admite_escaneado: false
  fuente: indice#6-formato-y-control

paginas_en_blanco:
  permitidas: false
  fuente: indice#6-formato-y-control

imagenes:
  requiere_numeracion: true
  requiere_titulo: true
  requiere_fuente_si_ajena: true
  requiere_mencion_en_texto: true
  fuente: indice#6-formato-y-control

indice_paginado:
  titulos_coinciden_con_documento: true
  paginas_actualizadas: true
  fuente: indice#6-formato-y-control
"""


def escribir_pdf(
    ruta: Path,
    paginas: list[list[str]],
    cuerpo: float = 11.0,
    salto: float = 19.0,
    fuente: str = "helv",
    izquierda: float = IZQUIERDA,
) -> Path:
    """Un PDF con las líneas indicadas, una lista de líneas por página."""
    documento = pymupdf.open()
    for lineas in paginas:
        pagina = documento.new_page()
        y = PRIMERA_LINEA
        for linea in lineas:
            pagina.insert_text((izquierda, y), linea, fontname=fuente, fontsize=cuerpo)
            y += salto
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture(name="escribir_pdf")
def _escribir_pdf():
    """El constructor de PDFs, para las pruebas que necesitan uno a medida.

    Se expone como fixture y no se importa directamente porque los
    directorios de prueba no son paquetes: un módulo de prueba no puede
    importar de otro.
    """
    return escribir_pdf


@pytest.fixture
def criterios_de_formato(tmp_path: Path) -> Path:
    """Una raíz con solo criteria/v2026-2027/formato.yaml.

    Los valores son los reales salvo el mínimo de páginas, rebajado a 4 para
    que un PDF de prueba pueda cumplirlo. Vive aquí y no en cada carpeta de
    pruebas porque lo usan las de formato, las del servicio y las de la API.
    """
    raiz = tmp_path / "repo"
    carpeta = raiz / "criteria" / "v2026-2027"
    carpeta.mkdir(parents=True)
    (carpeta / "formato.yaml").write_text(CRITERIOS_DE_PRUEBA, encoding="utf-8")
    return raiz


@pytest.fixture
def criterios_alterados(tmp_path: Path):
    """Una raíz de criterios con un valor cambiado, para probar el fallo.

    Devuelve la función que hace la sustitución: cada prueba altera lo que
    necesita sin repetir el fichero entero.
    """
    def alterar(viejo: str, nuevo: str) -> Path:
        raiz = tmp_path / "alterado"
        carpeta = raiz / "criteria" / "v2026-2027"
        carpeta.mkdir(parents=True)
        (carpeta / "formato.yaml").write_text(
            CRITERIOS_DE_PRUEBA.replace(viejo, nuevo), encoding="utf-8"
        )
        return raiz

    return alterar


@pytest.fixture
def pdf_simple(tmp_path: Path) -> Path:
    """Dos páginas con texto, ninguna vacía."""
    return escribir_pdf(
        tmp_path / "simple.pdf",
        [["Primera linea.", "Segunda linea."], ["Tercera linea."]],
    )


@pytest.fixture
def pdf_con_pagina_en_blanco(tmp_path: Path) -> Path:
    """Tres páginas; la segunda, vacía."""
    return escribir_pdf(
        tmp_path / "con-blanco.pdf",
        [["Texto de la primera."], [], ["Texto de la tercera."]],
    )


@pytest.fixture
def pdf_escaneado(tmp_path: Path) -> Path:
    """Una imagen a página completa y ni un carácter de texto."""
    documento = pymupdf.open()
    pagina = documento.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 850), False)
    pixmap.set_rect(pixmap.irect, (240, 240, 235))
    pagina.insert_image(pagina.rect, pixmap=pixmap)
    ruta = tmp_path / "escaneado.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_cuerpo_mezclado(tmp_path: Path) -> Path:
    """Mucho texto a cuerpo 11 y un titular a 20: el dominante es el 11."""
    documento = pymupdf.open()
    pagina = documento.new_page()
    pagina.insert_text((IZQUIERDA, 80.0), "TITULO", fontname="helv", fontsize=20.0)
    y = PRIMERA_LINEA + 30
    for _ in range(8):
        pagina.insert_text(
            (IZQUIERDA, y),
            "Linea larga del cuerpo del trabajo con bastante texto.",
            fontname="helv",
            fontsize=11.0,
        )
        y += 19.0
    ruta = tmp_path / "mezclado.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_alineado_izquierda(tmp_path: Path) -> Path:
    """Cinco líneas de longitudes muy distintas en una misma página.

    Es lo que se ve en un texto alineado a la izquierda: cada línea acaba
    donde acaba su última palabra.
    """
    return escribir_pdf(
        tmp_path / "izquierda.pdf",
        [[
            "Una linea francamente larga que ocupa casi todo el ancho util.",
            "Otra bastante mas corta.",
            "Mediana, ni corta ni larga del todo.",
            "Brevisima.",
            "Y una ultima de longitud intermedia para cerrar.",
        ]],
    )


@pytest.fixture
def pdf_justificado(tmp_path: Path) -> Path:
    """Cuatro líneas que acaban en el mismo borde derecho y una corta.

    Es lo que distingue el texto justificado: todas las líneas menos la
    última de cada párrafo terminan exactamente en el margen.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()
    y = PRIMERA_LINEA
    for _ in range(4):
        pagina.insert_text(
            (IZQUIERDA, y), "Linea que llega al margen.", fontname="helv", fontsize=11.0
        )
        y += 19.0
    pagina.insert_text((IZQUIERDA, y), "Corta.", fontname="helv", fontsize=11.0)
    ruta = tmp_path / "justificado.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_con_indice(tmp_path: Path) -> Path:
    """Portada, índice, tres apartados y un anexo.

    Las páginas declaradas en el índice son correctas salvo la del tercer
    apartado, que dice 5 estando en la 6. Es el fallo más común: se añade
    contenido y no se actualiza el índice.
    """
    return escribir_pdf(
        tmp_path / "con-indice.pdf",
        [
            ["PROYECTO INTERMODULAR", "Ciclo DAM", "Curso 2026-2027"],
            ["INDICE", "1. Introduccion .... 3", "2. Objetivos .... 4",
             "3. Desarrollo .... 5", "ANEXOS .... 7"],
            ["1. Introduccion", "Texto de la introduccion del trabajo."],
            ["2. Objetivos", "Texto de los objetivos del trabajo."],
            ["Continuacion de los objetivos, que ocupan dos paginas."],
            ["3. Desarrollo", "Texto del desarrollo del trabajo."],
            ["ANEXOS", "Anexo I. Codigo fuente."],
        ],
    )


@pytest.fixture
def pdf_con_imagenes(tmp_path: Path) -> Path:
    """Dos imágenes: una nítida y otra de 40x30 px estirada a 200x150 pt.

    La segunda queda a 14,4 ppp efectivos: es la captura de pantalla
    ampliada que se ve borrosa impresa.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()

    nitida = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 450), False)
    nitida.set_rect(nitida.irect, (30, 60, 120))
    pagina.insert_image(pymupdf.Rect(72, 72, 272, 222), pixmap=nitida)

    borrosa = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), False)
    borrosa.set_rect(borrosa.irect, (200, 120, 60))
    pagina.insert_image(pymupdf.Rect(72, 300, 272, 450), pixmap=borrosa)

    ruta = tmp_path / "con-imagenes.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_con_imagen_en_pagina_girada(tmp_path: Path) -> Path:
    """Una imagen de 300x60 px en un rectángulo nativo de 60x300 pt, en una
    página girada 90°.

    `get_image_rects` da ese rectángulo en coordenadas anteriores a
    `/Rotate`: en la página impresa el ancho y el alto quedan
    intercambiados. Es una imagen nítida -se imprime a 72 ppp- que sin
    deshacer ese cruce se confundiría con una captura de pantalla estirada.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 300, 60), False)
    pixmap.set_rect(pixmap.irect, (10, 20, 30))
    pagina.insert_image(
        pymupdf.Rect(72, 72, 132, 372),  # 60 x 300 pt, en coordenadas nativas
        pixmap=pixmap,
        keep_proportion=False,
    )
    pagina.set_rotation(90)
    ruta = tmp_path / "girada.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_con_imagen_estirada_de_forma_asimetrica(tmp_path: Path) -> Path:
    """Una imagen de 400x100 px en un rectángulo de 100x100 pt, sin
    conservar la proporción.

    Da 288 ppp en horizontal y 72 en vertical: el caso de arrastrar solo una
    esquina de la imagen. `insert_image` conserva la proporción por
    defecto, así que una imagen normal siempre da el mismo dpi en los dos
    ejes y no sirve para distinguir `min` de `max`; esta sí.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 100), False)
    pixmap.set_rect(pixmap.irect, (200, 50, 10))
    pagina.insert_image(
        pymupdf.Rect(72, 72, 172, 172),  # 100 x 100 pt
        pixmap=pixmap,
        keep_proportion=False,
    )
    ruta = tmp_path / "estirada-asimetrica.pdf"
    documento.save(ruta)
    documento.close()
    return ruta


@pytest.fixture
def pdf_con_imagen_sin_colocacion(tmp_path: Path) -> Path:
    """Una imagen en el catálogo de recursos de la página, sin ningún
    operador en el contenido que la coloque.

    Se inserta una imagen normal y luego se retira a mano, del flujo de
    contenido, el operador `Do` que la dibuja -dejando intacta la entrada
    del recurso XObject-. Es lo que dejan algunos exportadores descuidados
    o una capa oculta: `get_image_rects` no devuelve ningún rectángulo para
    ese recurso.
    """
    documento = pymupdf.open()
    pagina = documento.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 50, 50), False)
    pixmap.set_rect(pixmap.irect, (10, 10, 10))
    pagina.insert_image(pymupdf.Rect(72, 72, 122, 122), pixmap=pixmap)

    xref_contenido = pagina.get_contents()[0]
    contenido = documento.xref_stream(xref_contenido)
    contenido_sin_colocacion = re.sub(rb"/\S+\s+Do\s*\n?", b"", contenido)
    documento.update_stream(xref_contenido, contenido_sin_colocacion)

    ruta = tmp_path / "sin-colocacion.pdf"
    documento.save(ruta)
    documento.close()
    return ruta
