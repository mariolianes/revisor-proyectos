"""PDFs sintéticos con desviaciones conocidas.

Se construyen aquí y viven en tmp_path. Ninguna prueba de este proyecto
toca una entrega real de un alumno, y ningún PDF entra en el repositorio.
"""

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
