"""La entrega nueva contra la anterior, comparando por n-gramas de palabras.

El corpus sintético de más abajo se construye con un generador seudo-
aleatorio de semilla fija, así que las mismas ejecuciones dan siempre los
mismos números. El vocabulario es intencionadamente amplio para que dos
párrafos no coincidan por azar en una firma de ocho palabras.
"""

import random
import time
from collections import Counter

from backend.evolucion.comparacion import (
    CONSERVADO_MINIMO,
    RECONOCIDO_MINIMO,
    _firmas,
    comparar,
    normalizar,
)

# Plantilla verbatim: la frase que se copia sin cambiar ni una palabra para
# probar el caso que solo detecta el multiconjunto.
PLANTILLA = (
    "El grupo de trabajo completo la fase de pruebas siguiendo el "
    "protocolo establecido por el equipo docente y no se detectaron "
    "incidencias relevantes."
)

# ---------------------------------------------------------------------
# Construcción del corpus sintético
# ---------------------------------------------------------------------

_VOCABULARIO = [
    "taller", "reserva", "cliente", "vehiculo", "cita", "diagnostico",
    "mantenimiento", "averia", "presupuesto", "factura", "mecanico",
    "recambio", "motor", "neumatico", "freno", "aceite", "revision",
    "garantia", "inspeccion", "itv", "bateria", "correa", "filtro",
    "suspension", "chapa", "pintura", "electricidad", "climatizacion",
    "cambio", "embrague", "direccion", "escape", "radiador", "alternador",
    "arranque", "carroceria", "matricula", "seguro", "peritaje",
    "siniestro", "grua", "recogida", "entrega", "plazo", "incidencia",
    "satisfaccion", "encuesta", "fidelizacion", "campana", "descuento",
    "promocion", "temporada", "stock", "proveedor", "pedido", "almacen",
    "turno", "agenda", "calendario", "notificacion", "recordatorio",
    "confirmacion", "cancelacion", "reprogramacion", "historial",
    "expediente", "kilometraje", "modelo", "marca", "version", "combustible",
    "hibrido", "electrico", "diesel", "gasolina", "transmision", "manual",
    "automatico", "tapiceria", "sensor", "camara", "asistencia", "carretera",
    "urgencia", "diagnosis", "software", "actualizacion", "recall",
    "campanya", "homologacion", "normativa", "emisiones", "ruido",
    "vibracion", "ajuste", "calibracion", "balanceo", "alineacion",
]

_VOCABULARIO_AJENO = [
    "receta", "horno", "levadura", "harina", "cosecha", "vendimia",
    "bodega", "ganaderia", "pastoreo", "huerto", "invernadero", "riego",
    "abono", "semilla", "floracion", "poda", "injerto", "vivero",
    "senderismo", "cumbre", "refugio", "mochila", "brujula", "acampada",
    "hoguera", "cordada", "escalada", "rapel", "arnes", "piolet",
    "orquesta", "partitura", "batuta", "solista", "coro", "ensayo",
    "escenario", "telon", "vestuario", "utileria", "guion", "rodaje",
    "montaje", "edicion", "subtitulo", "doblaje", "estreno", "taquilla",
    "biblioteca", "archivo", "manuscrito", "encuadernacion", "imprenta",
    "tipografia", "acuarela", "oleo", "lienzo", "paleta", "boceto",
    "escultura", "ceramica", "torno", "esmalte", "cesteria", "telar",
    "bordado", "ganchillo", "tejido", "hilatura", "sastreria", "patron",
]


def _parrafo(rng: random.Random, vocabulario: list[str], palabras: int = 150) -> str:
    return " ".join(rng.choice(vocabulario) for _ in range(palabras)) + "."


def _documento(n_parrafos: int, vocabulario: list[str] | None = None, semilla: int = 1) -> str:
    rng = random.Random(semilla)
    vocabulario = vocabulario if vocabulario is not None else _VOCABULARIO
    parrafos = [_parrafo(rng, vocabulario) for _ in range(n_parrafos)]
    return "\n\n".join(parrafos)


N_PARRAFOS = 200

ANTERIOR = _documento(N_PARRAFOS, semilla=1)


# ---------------------------------------------------------------------
# normalizar
# ---------------------------------------------------------------------


def test_normalizar_da_palabras_en_minusculas_sin_tildes_ni_puntuacion() -> None:
    palabras = normalizar("¡Hola! Ánimo, va bien el Proyecto-2.")

    assert palabras == ["hola", "animo", "va", "bien", "el", "proyecto", "2"]


def test_normalizar_ignora_los_saltos_de_linea_y_los_espacios_de_sobra() -> None:
    palabras = normalizar("Uno   Dos\n\n\nTres  \n Cuatro")

    assert palabras == ["uno", "dos", "tres", "cuatro"]


def test_normalizar_de_texto_vacio_es_lista_vacia() -> None:
    assert normalizar("") == []


# ---------------------------------------------------------------------
# _firmas
# ---------------------------------------------------------------------


def test_firmas_de_texto_vacio_es_multiconjunto_vacio() -> None:
    assert _firmas([]) == Counter()


def test_firmas_de_menos_de_ocho_palabras_da_una_sola_firma() -> None:
    assert _firmas(["hola", "que", "tal"]) == Counter({("hola", "que", "tal"): 1})


def test_firmas_de_exactamente_ocho_palabras_da_una_sola_firma() -> None:
    palabras = [f"p{i}" for i in range(8)]

    assert _firmas(palabras) == Counter({tuple(palabras): 1})


def test_firmas_de_nueve_palabras_da_dos_firmas_solapadas() -> None:
    palabras = [f"p{i}" for i in range(9)]

    assert _firmas(palabras) == Counter(
        {tuple(palabras[0:8]): 1, tuple(palabras[1:9]): 1}
    )


def test_firmas_cuenta_repeticiones_no_solo_presencia() -> None:
    """La razón de ser del multiconjunto: contar, no solo marcar presencia."""
    palabras = ["a"] * 16

    firmas = _firmas(palabras)

    assert firmas[("a",) * 8] == 9  # 16 - 8 + 1 posiciones, todas la misma firma


# ---------------------------------------------------------------------
# comparar: los ocho casos de la revisión
# ---------------------------------------------------------------------


def test_entrega_identica_avisa_de_falta_de_progreso() -> None:
    evolucion = comparar(ANTERIOR, ANTERIOR)

    assert evolucion.proporcion_conservada == 1.0
    assert evolucion.proporcion_nueva == 0.0
    assert evolucion.avisos == [
        "La entrega llega sin cambios respecto a la anterior: no se "
        "aprecia progreso."
    ]


def test_parrafos_reordenados_no_disparan_avisos() -> None:
    """Cambiar el orden de los apartados no es perder contenido."""
    parrafos = ANTERIOR.split("\n\n")
    rng = random.Random(2)
    rng.shuffle(parrafos)
    reordenado = "\n\n".join(parrafos)

    evolucion = comparar(ANTERIOR, reordenado)

    assert evolucion.proporcion_conservada >= RECONOCIDO_MINIMO
    assert evolucion.avisos == []


def test_cada_parrafo_partido_en_dos_no_dispara_avisos() -> None:
    """Partir un párrafo en dos, la edición que rompía la versión anterior.

    Se acompaña de un retoque de una palabra para que el documento no sea
    una copia literal: si lo fuera, el aviso correcto sería justo el de
    «sin cambios» (probado aparte), no el de contenido perdido.
    """
    parrafos = ANTERIOR.split("\n\n")
    partidos = []
    for parrafo in parrafos:
        palabras = parrafo.split(" ")
        mitad = len(palabras) // 2
        partidos.append(" ".join(palabras[:mitad]))
        partidos.append(" ".join(palabras[mitad:]))
    primeras_palabras = partidos[0].split(" ")
    primeras_palabras[0] = "excepcionalmente"
    partidos[0] = " ".join(primeras_palabras)
    partido = "\n\n".join(partidos)

    evolucion = comparar(ANTERIOR, partido)

    assert evolucion.proporcion_conservada >= RECONOCIDO_MINIMO
    assert evolucion.avisos == []


def test_texto_sin_lineas_en_blanco_entre_parrafos_se_compara_igual_de_bien() -> None:
    """El caso real de nuestra propia extraccion: PyMuPDF no siempre deja
    parrafos separados por una linea en blanco, y el texto llega como un
    unico bloque. Aun asi, una entrega que progresa de verdad se reconoce:
    lo anterior sigue contando como conservado y lo añadido cuenta como
    nuevo."""
    anterior_sin_saltos = "\n".join(ANTERIOR.split("\n\n"))
    extra = _documento(round(N_PARRAFOS * 0.2), semilla=5)
    nuevo_sin_saltos = anterior_sin_saltos + "\n" + extra

    evolucion = comparar(anterior_sin_saltos, nuevo_sin_saltos)

    assert evolucion.proporcion_conservada >= RECONOCIDO_MINIMO
    assert evolucion.proporcion_nueva > 0.0
    assert evolucion.avisos == []


def test_entrega_ampliada_no_avisa_de_nada() -> None:
    extra = _documento(round(N_PARRAFOS * 0.3), semilla=3)
    ampliada = ANTERIOR + "\n\n" + extra

    evolucion = comparar(ANTERIOR, ampliada)

    assert evolucion.proporcion_conservada >= RECONOCIDO_MINIMO
    assert evolucion.proporcion_nueva > 0.0
    assert evolucion.avisos == []


def test_entrega_que_solo_trae_lo_nuevo_se_avisa() -> None:
    """Solo los capítulos nuevos, sin el trabajo anterior: §5.1."""
    solo_nuevo = _documento(N_PARRAFOS, vocabulario=_VOCABULARIO_AJENO, semilla=4)

    evolucion = comparar(ANTERIOR, solo_nuevo)

    assert evolucion.proporcion_conservada == 0.0
    assert any("documento completo" in aviso for aviso in evolucion.avisos)


def test_entrega_recortada_a_la_mitad_avisa_de_contenido_no_reconocido() -> None:
    """El §5.1 lo prohíbe: no se quita lo ya validado."""
    parrafos = ANTERIOR.split("\n\n")
    mitad = len(parrafos) // 2
    recortada = "\n\n".join(parrafos[:mitad])

    evolucion = comparar(ANTERIOR, recortada)

    assert CONSERVADO_MINIMO <= evolucion.proporcion_conservada < RECONOCIDO_MINIMO
    assert any("no se reconoce" in aviso for aviso in evolucion.avisos)


def test_un_retoque_de_una_palabra_no_dispara_avisos() -> None:
    """Cambiar una palabra no convierte el documento en otro distinto."""
    parrafos = ANTERIOR.split("\n\n")
    palabras = parrafos[0].split(" ")
    palabras[0] = "excepcionalmente"
    parrafos[0] = " ".join(palabras)
    retocado = "\n\n".join(parrafos)

    evolucion = comparar(ANTERIOR, retocado)

    assert evolucion.proporcion_conservada >= RECONOCIDO_MINIMO
    assert evolucion.avisos == []


def test_plantilla_repetida_recortada_a_la_mitad_avisa_de_contenido_no_reconocido() -> None:
    """El caso que un conjunto no ve: cuarenta copias verbatim de la misma
    plantilla, recortadas a veinte. Como conjunto, veinte copias idénticas
    producen las mismas firmas que cuarenta, y la pérdida de la mitad de
    las filas quedaría invisible. Este test falla si `_firmas` vuelve a
    ser un `set` en vez de un `Counter`.
    """
    anterior = "\n\n".join([PLANTILLA] * 40)
    recortado = "\n\n".join([PLANTILLA] * 20)

    evolucion = comparar(anterior, recortado)

    assert CONSERVADO_MINIMO <= evolucion.proporcion_conservada < RECONOCIDO_MINIMO
    assert 0.45 <= evolucion.proporcion_conservada <= 0.55
    assert any("no se reconoce" in aviso for aviso in evolucion.avisos)


# ---------------------------------------------------------------------
# Casos límite
# ---------------------------------------------------------------------


def test_sin_entrega_anterior_no_se_compara() -> None:
    evolucion = comparar("", ANTERIOR)

    assert evolucion.avisos == []
    assert evolucion.proporcion_conservada == 0.0
    assert evolucion.parrafos_antes == 0
    assert evolucion.parrafos_despues == N_PARRAFOS


def test_entrega_nueva_vacia_avisa_de_falta_de_contenido() -> None:
    evolucion = comparar(ANTERIOR, "")

    assert evolucion.proporcion_conservada == 0.0
    assert evolucion.proporcion_nueva == 0.0
    assert any("documento completo" in aviso for aviso in evolucion.avisos)


def test_parrafos_antes_y_despues_son_informativos() -> None:
    evolucion = comparar(ANTERIOR, ANTERIOR)

    assert evolucion.parrafos_antes == N_PARRAFOS
    assert evolucion.parrafos_despues == N_PARRAFOS


# ---------------------------------------------------------------------
# Rendimiento
# ---------------------------------------------------------------------


def test_comparar_seiscientos_parrafos_es_rapido() -> None:
    """No debe volver al coste cuadrático del diseño por párrafos."""
    grande_anterior = _documento(600, semilla=10)
    grande_nuevo = _documento(600, semilla=11)

    inicio = time.perf_counter()
    comparar(grande_anterior, grande_nuevo)
    duracion = time.perf_counter() - inicio

    assert duracion < 2.0


def test_comparar_mil_doscientos_parrafos_es_rapido() -> None:
    """El multiconjunto (`Counter`) sigue siendo lineal, igual que el
    conjunto que sustituye."""
    grande_anterior = _documento(1200, semilla=20)
    grande_nuevo = _documento(1200, semilla=21)

    inicio = time.perf_counter()
    comparar(grande_anterior, grande_nuevo)
    duracion = time.perf_counter() - inicio

    assert duracion < 2.0
