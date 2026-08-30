"""`recortar_cita`: la evidencia buena que sobrevive a lo que el motor añadió.

Nace de la calibración del 2026-08-30 con los nueve casos del banco: subir
del 50 % al 69 % de citas localizadas reforzando la instrucción no bastó, y
los casos que quedan son siempre la misma forma -el motor copia bien el
principio y luego se sale del texto-, no una cita inventada del todo. Los
tres casos de abajo reproducen esa forma con texto inventado, no con datos
de un trabajo real: dos que sí tienen un tramo real que recortar, y uno que
no tiene ninguno y sigue descartándose.
"""

from backend.analisis.verificacion import (
    CITA_MINIMA,
    PROPORCION_MINIMA_DE_RECORTE,
    cita_localizada,
    normalizar_para_buscar,
    recortar_cita,
)

TRABAJO = """
3. Metodología

El equipo aplicó una metodología ágil basada en sprints quincenales
revisados por el tutor y el resto del grupo en reuniones periódicas de
seguimiento.

4. Resultados

Los resultados obtenidos confirman que el sistema reduce el tiempo de
gestión de reservas en un cuarenta por ciento respecto al proceso manual
previo, según las pruebas realizadas con usuarios reales del taller.

6. Evaluación

El presupuesto inicial asciende a 4.500 euros, repartidos entre licencias,
formación y difusión.
"""


# --- Los tres casos reales de la calibración, con la misma forma ---

def test_caso_1_cita_con_vinetas_se_recorta_al_prefijo_real() -> None:
    """El motor cita bien las primeras doce palabras y luego añade dos
    viñetas con contenido que no está en el trabajo."""
    prefijo_real = (
        "El equipo aplicó una metodología ágil basada en sprints "
        "quincenales revisados por"
    )
    assert len(prefijo_real.split()) == 12

    cita_del_motor = (
        f"{prefijo_real}\n"
        "• Con retroalimentación diaria del cliente final\n"
        "• Con integración continua automatizada en cada entrega"
    )

    # La cita entera no se localiza: esto es justo el caso que el aviso del
    # instructor no consigue evitar.
    assert not cita_localizada(cita_del_motor, TRABAJO)

    recorte = recortar_cita(cita_del_motor, TRABAJO)

    assert recorte == prefijo_real
    assert cita_localizada(recorte, TRABAJO)


def test_caso_2_cita_con_puntos_suspensivos_se_recorta_al_primer_tramo() -> None:
    """El motor une con "..." un tramo real y uno que no está: el trozo de
    después del "..." no aparece en ningún sitio del trabajo."""
    primer_tramo = (
        "Los resultados obtenidos confirman que el sistema reduce el "
        "tiempo de gestión de reservas en un cuarenta por ciento respecto "
        "al proceso manual previo"
    )
    cita_del_motor = (
        f"{primer_tramo} ... y sitúa al taller entre los más eficientes de "
        "la provincia según el ranking sectorial publicado este año"
    )

    assert not cita_localizada(cita_del_motor, TRABAJO)

    recorte = recortar_cita(cita_del_motor, TRABAJO)

    assert recorte == primer_tramo
    assert cita_localizada(recorte, TRABAJO)
    # El "..." no sobrevive al recorte: lo que queda es un tramo seguido,
    # tal cual está en el documento, no la unión con puntos suspensivos que
    # la instrucción ya prohíbe.
    assert "..." not in recorte


def test_caso_3_ausencia_descrita_no_tiene_nada_que_recortar() -> None:
    """El límite que separa recortar de hacer trampa: aquí no hay ningún
    prefijo real, así que no hay nada que conservar."""
    cita_del_motor = (
        "No se localizan referencias a la incorporación de feedback o "
        "evolución entre versiones."
    )

    assert not cita_localizada(cita_del_motor, TRABAJO)
    assert recortar_cita(cita_del_motor, TRABAJO) is None


# --- Cuánto tiene que quedar para que el recorte valga ---

def test_un_recorte_que_es_una_esquirla_se_descarta() -> None:
    """El ejemplo de manual: una cita larga de la que solo se localiza un
    fragmento mínimo no es una evidencia recortada, es casi ninguna
    evidencia, aunque ese fragmento ya supere `CITA_MINIMA` por sí solo."""
    documento = "El proyecto es viable y sostenible a medio plazo para el taller."
    cita_larga = (
        "El proyecto es viable y además resulta perfectamente compatible "
        "con la normativa vigente sobre proteccion de datos y con los "
        "plazos administrativos previstos por el centro educativo para "
        "la entrega final de toda la documentacion del curso"
    )
    fragmento_localizable = "El proyecto es viable"
    assert len(normalizar_para_buscar(fragmento_localizable)) >= CITA_MINIMA
    assert cita_localizada(fragmento_localizable, documento)

    # El fragmento localizable es real, pero es una fracción mínima de lo
    # que el motor propuso como evidencia: no llega a un tercio.
    proporcion = len(normalizar_para_buscar(fragmento_localizable)) / len(
        normalizar_para_buscar(cita_larga)
    )
    assert proporcion < PROPORCION_MINIMA_DE_RECORTE

    assert recortar_cita(cita_larga, documento) is None


def test_un_recorte_justo_en_el_limite_de_la_proporcion_se_acepta() -> None:
    """El umbral es un mínimo inclusivo, igual que `CITA_MINIMA`."""
    documento = (
        "El sistema de reservas del taller reduce notablemente los "
        "tiempos de espera para el cliente final del negocio."
    )
    prefijo = (
        "El sistema de reservas del taller reduce notablemente los "
        "tiempos de espera"
    )
    len_prefijo = len(normalizar_para_buscar(prefijo))
    objetivo_total = len_prefijo * 3
    # Relleno que no está en el documento -"z" no forma ninguna palabra real
    # ahí-, ajustado para que el total normalizado sea exactamente el
    # triple del prefijo: el prefijo queda justo en
    # PROPORCION_MINIMA_DE_RECORTE, ni un carácter por encima.
    relleno = "z" * (objetivo_total - len_prefijo - 1)
    cita = f"{prefijo} {relleno}"
    assert len(normalizar_para_buscar(cita)) == objetivo_total

    assert recortar_cita(cita, documento) == prefijo


def test_un_recorte_justo_por_debajo_del_limite_se_descarta() -> None:
    """Un carácter por debajo del umbral, y el recorte deja de valer, igual
    que una cita de diecinueve caracteres normalizados deja de valer."""
    documento = (
        "El sistema de reservas del taller reduce notablemente los "
        "tiempos de espera para el cliente final del negocio."
    )
    prefijo = (
        "El sistema de reservas del taller reduce notablemente los "
        "tiempos de espera"
    )
    len_prefijo = len(normalizar_para_buscar(prefijo))
    objetivo_total = len_prefijo * 3 + 1
    relleno = "z" * (objetivo_total - len_prefijo - 1)
    cita = f"{prefijo} {relleno}"
    assert len(normalizar_para_buscar(cita)) == objetivo_total

    assert recortar_cita(cita, documento) is None


# --- Nunca a mitad de palabra ---

def test_el_recorte_nunca_corta_a_mitad_de_palabra() -> None:
    """Una cita que acabara en «el presupuesto asc» sería peor que ninguna.
    Aquí el documento y la cita comparten el prefijo de caracteres «El
    presupuesto asc», pero divergen dentro de la misma palabra -"asciende"
    contra "ascendental"-: un recorte por caracteres se quedaría con ese
    fragmento roto; el recorte por palabras completas no encuentra ningún
    prefijo de palabra entera que sea real y devuelve `None`."""
    documento = "El presupuesto asciende a cuatro mil quinientos euros."
    cita_del_motor = (
        "El presupuesto ascendental hasta cifras que no constan en el "
        "documento del proyecto"
    )

    recorte = recortar_cita(cita_del_motor, documento)

    assert recorte is None


def test_el_recorte_cuando_existe_es_siempre_un_prefijo_de_palabras_completas() -> None:
    """Comprobación estructural: si hay recorte, es exactamente la unión de
    las primeras N palabras de la cita del motor -nunca un trozo de una."""
    documento = "El equipo documentó cada decisión de diseño en el repositorio."
    cita_del_motor = (
        "El equipo documentó cada decisión de diseño en el repositorio "
        "y además incorporó un historial de cambios que no figura en "
        "ninguna parte de este trabajo"
    )

    recorte = recortar_cita(cita_del_motor, documento)

    assert recorte is not None
    palabras_originales = cita_del_motor.split()
    n = len(recorte.split())
    assert recorte == " ".join(palabras_originales[:n])
