"""Las imágenes del documento, medidas sin mirar su contenido.

Aquí no se juzga si una imagen está numerada, titulada o citada en el
texto: eso exige leer y relacionar, y es trabajo de la segunda parte. Aquí
solo hay geometría y píxeles.

Dos límites conocidos, documentados y no resueltos, porque
`proporcion_de_pagina` hoy no decide nada por sí sola -el criterio de
imágenes sale NO_VERIFICABLE en la comprobación de formato, porque juzgar
numeración y cita en el texto exige leer el documento- y arreglarlos exige
parsear el flujo de contenido de la página, lo que no compensa por ahora:

- Recorte por clip. Si el PDF muestra solo un trozo de una imagen mediante
  un recorte -lo que hace Word al «recortar imagen»-, `proporcion_de_pagina`
  cuenta el rectángulo entero de colocación, no la parte visible: puede
  sobrestimar en más de un orden de magnitud (31,9 % medido frente a 2,0 %
  real en un caso de prueba). `dpi_efectivo` en cambio sigue siendo correcto
  bajo recorte: la densidad de píxeles por punto es uniforme en toda el área
  que mapea la matriz de transformación, se vea entera la imagen o no.
- Imagen sin colocación localizable. Si una imagen figura en el catálogo de
  recursos de la página pero `get_image_rects` no devuelve ningún
  rectángulo para ella -un recurso huérfano que deja algún exportador
  descuidado, una capa oculta-, el bucle interior no itera ninguna vez y esa
  imagen no aparece en el resultado, sin error ni aviso.
"""

import pymupdf

from backend.extraccion.medidas import Imagen

PUNTOS_POR_PULGADA = 72.0


def leer_imagenes(documento: pymupdf.Document) -> list[Imagen]:
    """Una entrada por cada colocación de imagen, en orden de página.

    Una misma imagen repetida en varias páginas produce una entrada por
    página: lo que importa es cómo se ve en cada sitio donde aparece, y el
    mismo archivo puede estar bien dimensionado en una página y estirado en
    otra.
    """
    imagenes = []
    for numero, pagina in enumerate(documento, start=1):
        area_pagina = pagina.rect.get_area()
        # get_image_rects() da el rectángulo en coordenadas nativas del
        # MediaBox, anteriores a aplicar /Rotate. En una página girada 90 o
        # 270 grados, ese rectángulo trae el ancho y el alto intercambiados
        # respecto a como se ve de verdad la página impresa: hay que
        # deshacer el cruce antes de dividir entre píxeles, o el dpi
        # horizontal queda calculado contra el lado que en el papel es
        # vertical, y viceversa. Con 0 y 180 no hay cruce de ejes que
        # deshacer.
        pagina_de_lado = pagina.rotation in (90, 270)
        for referencia in pagina.get_images(full=True):
            xref, _, ancho_px, alto_px = referencia[0], referencia[1], referencia[2], referencia[3]
            for rectangulo in pagina.get_image_rects(xref):
                if rectangulo.width <= 0 or rectangulo.height <= 0:
                    continue
                ancho_impreso_pt = rectangulo.height if pagina_de_lado else rectangulo.width
                alto_impreso_pt = rectangulo.width if pagina_de_lado else rectangulo.height
                dpi_horizontal = ancho_px / (ancho_impreso_pt / PUNTOS_POR_PULGADA)
                dpi_vertical = alto_px / (alto_impreso_pt / PUNTOS_POR_PULGADA)
                imagenes.append(Imagen(
                    pagina=numero,
                    ancho_px=ancho_px,
                    alto_px=alto_px,
                    # El lado peor mandado es el que se ve borroso.
                    dpi_efectivo=min(dpi_horizontal, dpi_vertical),
                    proporcion_de_pagina=(
                        rectangulo.get_area() / area_pagina if area_pagina else 0.0
                    ),
                ))
    return imagenes
