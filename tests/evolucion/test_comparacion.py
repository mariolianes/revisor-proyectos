"""La entrega nueva contra la anterior."""

from backend.evolucion.comparacion import comparar, normalizar

ANTERIOR = """
1. Introduccion

Este trabajo estudia la gestion de reservas en talleres.

2. Objetivos

El objetivo general es reducir el tiempo de atencion.

3. Metodologia

Se emplea un enfoque incremental por iteraciones.
"""


def test_normalizar_reduce_espacios_y_mayusculas() -> None:
    """El párrafo de prueba supera el mínimo de caracteres a propósito:
    por debajo de CARACTERES_MINIMOS se descarta por corto, y eso es lo
    que comprueba test_normalizar_ignora_los_parrafos_muy_cortos.
    """
    parrafos = normalizar(
        "  UN   Parrafo  con  bastante  contenido  para  pasar  el  minimo.  "
        "\n\n\n Otro   Párrafo  tambien  con  bastante  contenido  util. "
    )

    assert parrafos == [
        "un parrafo con bastante contenido para pasar el minimo.",
        "otro parrafo tambien con bastante contenido util.",
    ]


def test_normalizar_ignora_los_parrafos_muy_cortos() -> None:
    """Numeraciones sueltas y encabezados de una palabra no son contenido."""
    parrafos = normalizar("3\n\nEste parrafo si tiene contenido suficiente.\n\nx")

    assert parrafos == ["este parrafo si tiene contenido suficiente."]


def test_entrega_identica_avisa_de_falta_de_progreso() -> None:
    evolucion = comparar(ANTERIOR, ANTERIOR)

    assert evolucion.proporcion_conservada == 1.0
    assert evolucion.proporcion_nueva == 0.0
    assert any("sin cambios" in aviso for aviso in evolucion.avisos)


def test_entrega_ampliada_no_avisa_de_nada() -> None:
    nuevo = ANTERIOR + """
4. Desarrollo

Se implementa el modulo de reservas con sus pruebas.

5. Resultados

El tiempo de atencion baja de doce a siete minutos.
"""

    evolucion = comparar(ANTERIOR, nuevo)

    assert evolucion.parrafos_nuevos == 2
    assert evolucion.parrafos_eliminados == 0
    assert evolucion.avisos == []


def test_contenido_eliminado_se_avisa() -> None:
    """El §5.1 lo prohíbe: no se quita lo ya validado."""
    recortado = """
1. Introduccion

Este trabajo estudia la gestion de reservas en talleres.
"""

    evolucion = comparar(ANTERIOR, recortado)

    assert evolucion.parrafos_eliminados > 0
    assert any("desaparecido" in aviso for aviso in evolucion.avisos)


def test_entrega_que_solo_trae_lo_nuevo_se_avisa() -> None:
    """Solo los capítulos nuevos, sin el trabajo anterior: §5.1."""
    solo_nuevo = """
4. Desarrollo

Se implementa el modulo de reservas con sus pruebas.

5. Resultados

El tiempo de atencion baja de doce a siete minutos.
"""

    evolucion = comparar(ANTERIOR, solo_nuevo)

    assert evolucion.proporcion_conservada == 0.0
    assert any("documento completo" in aviso for aviso in evolucion.avisos)


def test_sin_entrega_anterior_no_se_compara() -> None:
    evolucion = comparar("", ANTERIOR)

    assert evolucion.avisos == []
    assert evolucion.proporcion_conservada == 0.0
    assert evolucion.parrafos_eliminados == 0


def test_un_retoque_menor_cuenta_como_conservado() -> None:
    """Cambiar una palabra no convierte el párrafo en otro distinto."""
    retocado = ANTERIOR.replace("reducir el tiempo", "acortar el tiempo")

    evolucion = comparar(ANTERIOR, retocado)

    assert evolucion.proporcion_conservada == 1.0
    assert evolucion.parrafos_eliminados == 0


def test_un_retoque_menor_no_se_confunde_con_falta_de_progreso() -> None:
    """El aviso de «sin cambios» exige texto idéntico, no parecido.

    Con el umbral de parecido, un párrafo retocado cuenta como conservado y
    no cuenta como nuevo, así que juzgar el progreso por esas proporciones
    marcaría como estancada una entrega que sí se ha corregido.
    """
    retocado = ANTERIOR.replace("reducir el tiempo", "acortar el tiempo")

    assert comparar(ANTERIOR, retocado).avisos == []
