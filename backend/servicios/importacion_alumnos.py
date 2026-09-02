"""Del Excel de una comunidad al registro maestro, y del registro maestro a
la correspondencia local nombre-student_id.

El docente lo dijo así: los Excel «pueden proceder directamente de CESUR y
no tienen que conservar la misma estructura entre comunidades». Este módulo
no asume ninguna estructura fija -mapea columnas por alias, no por posición
ni por un nombre exacto-, y tampoco adivina lo que no puede saber con
certeza: cuando una fila es dudosa -sin centro, con un centro que no está en
el catálogo, con un ciclo o un estado que no se reconocen, repetida dentro
del propio listado, o con un nombre que coincide con otra fila o con un
alumno ya conocido- se detiene y lo dice, en vez de decidir por su cuenta.
Es la traducción concreta del principio del docente: «la automatización
puede detenerse; lo que no puede hacer es asignar silenciosamente un
trabajo al alumno equivocado». Aquí el trabajo es una identidad, no una
entrega, pero el riesgo -y la regla- son los mismos.

Ninguna fila dudosa se escribe en ningún almacén. El sistema no inventa un
`student_id` para una fila que no puede resolver con seguridad: prefiere
dejar a un alumno sin registrar un día más a arriesgarse a mezclarlo con
otro. La fila queda en `ResultadoImportacion.pendientes`, con el número de
fila del Excel y el motivo, nunca con el nombre -el nombre no sale de este
módulo hacia ningún sitio que no sea `ListadoLocal`, ni siquiera en un
mensaje que el docente lee en su propia terminal: es la misma cautela,
"cero avisos innecesarios", que ya aplica
`backend/privacidad/listado_local.py`-.

Emparejar por `platform_id` -el ID de CESUR- es preferible a emparejar por
nombre, y aquí es literalmente lo único que se usa para decidir en
automático que dos filas de dos importaciones son la misma persona: sin
`platform_id`, una fila que coincide en nombre con un alumno ya conocido no
se fusiona nunca sola, se manda a revisión (ver `COINCIDENCIA_DE_NOMBRE`
más abajo). Y un `platform_id` que ya pertenecía a un `student_id` de OTRO
curso no se reutiliza en automático tampoco -sería decidir, sin que nadie lo
haya dicho, que es un repetidor y no un alumno nuevo-: se manda a revisión
como `REPETIDOR_POSIBLE`. Ver D-025 en `docs/decisions.md`.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml
from pydantic import BaseModel

from backend.persistencia.alumnos import (
    CICLO_CODES,
    ESTADO_MATRICULA_INICIAL,
    ESTADOS_MATRICULA,
    AlumnoNuevo,
)
from backend.privacidad.listado_local import ListadoLocal

# --- mapeo de columnas ------------------------------------------------------

# Un campo puede llamarse de formas distintas según la comunidad, y el
# docente lo advirtió expresamente. Se añaden alias aquí, nunca una
# suposición nueva en el código que los use. Se escriben con sus tildes
# normales -"código", "matrícula", "situación"- porque `mapear_cabecera` los
# pasa por `_normalizar_texto` antes de comparar, igual que la cabecera real
# del Excel: escribirlos ya sin tilde no ganaría nada en la comparación y sí
# perdería la R8 (`tools/gobernanza/ortografia.py`), que lee estas cadenas
# como prosa en cuanto encadenan tres palabras o más.
ALIAS_COLUMNAS: dict[str, tuple[str, ...]] = {
    "nombre_apellidos": (
        "nombre y apellidos", "nombre apellidos", "apellidos y nombre",
        "alumno", "alumno a", "nombre completo", "nombre del alumno",
        "nombre", "apellidos y nombre del alumno",
    ),
    "centro_code": (
        "centro", "código centro", "cod centro", "centro código",
        "código del centro", "cod del centro",
    ),
    "ciclo_code": (
        "ciclo", "código ciclo", "cod ciclo", "ciclo formativo",
        "código del ciclo", "ciclo código",
    ),
    "estado_matricula": (
        "estado", "estado matrícula", "situación", "matrícula",
        "situación matrícula", "estado de matrícula",
    ),
    "platform_id": (
        "id cesur", "id plataforma", "platform id", "código cesur",
        "id alumno cesur", "id", "id alumno",
    ),
}

# Sin estas tres columnas -con cualquiera de sus alias- no hay con qué
# registrar a nadie con seguridad: falta saber quién es, o dónde estudia, o
# en qué ciclo. `estado_matricula` y `platform_id` son opcionales.
CAMPOS_OBLIGATORIOS = ("nombre_apellidos", "centro_code", "ciclo_code")


def _normalizar_texto(texto: str) -> str:
    """Minúsculas, sin acentos, sin dobles espacios. Sirve tanto para
    comparar cabeceras de columna como nombres de alumno: los dos son texto
    libre que puede venir con distinta capitalización o acentuación entre
    comunidades."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    con_espacios = "".join(c if c.isalnum() else " " for c in sin_acentos.lower())
    return " ".join(con_espacios.split())


class ColumnasNoMapeadas(ValueError):
    """El Excel no trae, con ningún alias reconocido, alguna columna
    obligatoria."""


def mapear_cabecera(cabecera: list[str]) -> dict[str, str]:
    """Campo canónico -> nombre de columna real del Excel, o
    `ColumnasNoMapeadas` si falta alguna obligatoria.

    Se compara la cabecera entera de una vez -no fila a fila- porque es un
    fallo de todo el fichero, no de una fila concreta: sin saber en qué
    columna vive el centro no hay ninguna fila que se pueda registrar con
    seguridad, así que la importación entera se detiene aquí, antes de leer
    ni una fila de datos.
    """
    normalizados = {_normalizar_texto(c): c for c in cabecera if c}
    mapa: dict[str, str] = {}
    for campo, alias in ALIAS_COLUMNAS.items():
        for candidato in alias:
            candidato_normalizado = _normalizar_texto(candidato)
            if candidato_normalizado in normalizados:
                mapa[campo] = normalizados[candidato_normalizado]
                break

    faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if campo not in mapa]
    if faltantes:
        raise ColumnasNoMapeadas(
            "No se ha encontrado columna para: " + ", ".join(faltantes) + ". "
            "Cabecera del Excel: "
            + (", ".join(c for c in cabecera if c) if any(cabecera) else "(vacía)")
            + ". Cambia el nombre de esa columna en el Excel a uno reconocido, "
            "o añade el alias en ALIAS_COLUMNAS "
            "(backend/servicios/importacion_alumnos.py) si es un nombre "
            "legítimo y nuevo."
        )
    return mapa


# --- resultado ---------------------------------------------------------------

SIN_CENTRO = "SIN_CENTRO"
CENTRO_DESCONOCIDO = "CENTRO_DESCONOCIDO"
SIN_CICLO = "SIN_CICLO"
CICLO_DESCONOCIDO = "CICLO_DESCONOCIDO"
ESTADO_DESCONOCIDO = "ESTADO_DESCONOCIDO"
FILA_DUPLICADA = "FILA_DUPLICADA"
COINCIDENCIA_DE_NOMBRE = "POSIBLE_COINCIDENCIA_DE_NOMBRE"
REPETIDOR_POSIBLE = "REPETIDOR_POSIBLE"
ERROR_AL_REGISTRAR = "ERROR_AL_REGISTRAR"


class FilaPendiente(BaseModel):
    """Una fila que no se ha registrado, y por qué.

    `detalle` nunca lleva el nombre del alumno -se identifica por el número
    de fila del Excel, que el docente puede localizar sin que el nombre
    tenga que pasar por ningún sitio más que el propio Excel y
    `ListadoLocal`-.
    """

    fila: int
    motivo: str
    detalle: str


class ResultadoImportacion(BaseModel):
    """Lo que ha pasado al importar un listado. Sin nombres."""

    total_filas: int
    en_blanco: int
    nuevas: int
    actualizadas: int
    pendientes: list[FilaPendiente]


def cargar_centros_conocidos(ruta: Path, ccaa_code: str) -> set[str] | None:
    """Los códigos de centro conocidos para esa comunidad, o `None` si no
    hay ninguno con el que comparar.

    `None` -no un conjunto vacío- es la señal de «no hay catálogo para esta
    comunidad todavía»: sin él, NINGÚN centro se puede verificar, así que
    toda fila con centro queda pendiente de revisión en vez de aceptarse a
    ciegas. Es el fallo seguro: mejor parar por falta de catálogo que
    registrar 200 alumnos con un centro que nadie ha comprobado.
    """
    if not ruta.is_file():
        return None
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    if not isinstance(datos, dict):
        return None
    centros = datos.get(ccaa_code)
    if not centros:
        return None
    return {str(centro).strip().upper() for centro in centros}


def importar(
    filas: list[dict[str, str]],
    cabecera: list[str],
    *,
    ccaa_code: str,
    curso: str,
    almacen,
    listado_local: ListadoLocal,
    centros_conocidos: set[str] | None,
) -> ResultadoImportacion:
    """Mapea, valida, registra lo seguro y detiene lo dudoso.

    `filas` son diccionarios `{columna_original: valor}`, ya leídos del
    Excel -este módulo no sabe leer un `.xlsx`: eso lo hace
    `tools/importar_listado_alumnos.py`, para que la lógica de aquí se
    pruebe sin necesitar nunca un fichero real-. `almacen` es cualquier
    `Almacen` (`backend/persistencia/modelos.py`): memoria o Supabase, con
    el mismo resultado.
    """
    mapa = mapear_cabecera(cabecera)

    en_blanco = 0
    nuevas = 0
    actualizadas = 0
    pendientes: list[FilaPendiente] = []

    nombres_locales = listado_local.todos()
    filas_por_nombre_local: dict[str, list[str]] = {}
    for student_id, nombre in nombres_locales.items():
        filas_por_nombre_local.setdefault(_normalizar_texto(nombre), []).append(student_id)

    pares_de_nombre: dict[str, str] = {}

    # --- primera pasada: qué fila es cuál, sin registrar nada todavía -----
    #
    # Hace falta conocer el listado ENTERO antes de decidir si un nombre es
    # dudoso: si la fila 2 y la fila 5 comparten nombre, las dos son dudosas
    # -no solo la segunda que se encuentra-, y eso no se puede saber al
    # llegar a la fila 2 sin haber mirado todavía la fila 5. Registrar la
    # fila 2 antes de ver la 5 sería, precisamente, "asignar en silencio"
    # antes de tener toda la información para dudar.
    procesadas: list[dict | None] = []  # None = fila en blanco
    vistos_en_este_lote: dict[tuple, int] = {}
    for indice, fila in enumerate(filas, start=2):  # la fila 1 es la cabecera
        nombre = (fila.get(mapa["nombre_apellidos"]) or "").strip()
        if not nombre:
            procesadas.append(None)
            continue

        centro = (fila.get(mapa["centro_code"]) or "").strip().upper()
        ciclo = (fila.get(mapa["ciclo_code"]) or "").strip().upper()
        estado_bruto = (
            (fila.get(mapa["estado_matricula"]) or "").strip().upper()
            if "estado_matricula" in mapa else ""
        )
        platform_id = (
            (fila.get(mapa["platform_id"]) or "").strip()
            if "platform_id" in mapa else ""
        ) or None
        estado = estado_bruto or ESTADO_MATRICULA_INICIAL
        clave_nombre = _normalizar_texto(nombre)
        clave_duplicado = (
            (platform_id, clave_nombre, centro, ciclo) if platform_id
            else (clave_nombre, centro, ciclo)
        )
        es_duplicado = clave_duplicado in vistos_en_este_lote
        fila_original = vistos_en_este_lote.get(clave_duplicado)
        if not es_duplicado:
            vistos_en_este_lote[clave_duplicado] = indice

        procesadas.append(dict(
            indice=indice, nombre=nombre, clave_nombre=clave_nombre,
            centro=centro, ciclo=ciclo, estado_bruto=estado_bruto,
            estado=estado, platform_id=platform_id,
            es_duplicado=es_duplicado, fila_original=fila_original,
        ))

    # Cuántas filas DISTINTAS -sin contar duplicados exactos, que son la
    # misma fila repetida por error, no dos personas- comparten nombre. Un
    # nombre que aparece una sola vez entre las filas no duplicadas no es
    # una coincidencia con nadie.
    filas_por_nombre_en_lote: dict[str, list[int]] = {}
    for info in procesadas:
        if info is not None and not info["es_duplicado"]:
            filas_por_nombre_en_lote.setdefault(info["clave_nombre"], []).append(info["indice"])

    # --- segunda pasada: validar y registrar lo seguro ---------------------
    for info in procesadas:
        if info is None:
            # Una fila en blanco al final del Excel es normal, no un error.
            en_blanco += 1
            continue

        indice = info["indice"]
        nombre = info["nombre"]
        clave_nombre = info["clave_nombre"]
        centro = info["centro"]
        ciclo = info["ciclo"]
        estado_bruto = info["estado_bruto"]
        estado = info["estado"]
        platform_id = info["platform_id"]

        if info["es_duplicado"]:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=FILA_DUPLICADA,
                detalle=f"Fila {indice}: repite exactamente la fila "
                        f"{info['fila_original']} de este listado. "
                        "No se registra dos veces.",
            ))
            continue

        if not centro:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=SIN_CENTRO,
                detalle=f"Fila {indice}: no tiene centro. No se registra sin él.",
            ))
            continue
        if centros_conocidos is None:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=CENTRO_DESCONOCIDO,
                detalle=f"Fila {indice}: el centro «{centro}» no se puede "
                        "verificar: config/centros.yaml no tiene ningún "
                        "centro para esta comunidad todavía. Añade primero "
                        "los centros reales de la comunidad antes de "
                        "importar.",
            ))
            continue
        if centro not in centros_conocidos:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=CENTRO_DESCONOCIDO,
                detalle=f"Fila {indice}: el centro «{centro}» no está en "
                        "config/centros.yaml para esta comunidad. Añádelo si "
                        "es correcto, o corrígelo si es un error de tecleo.",
            ))
            continue
        if not ciclo:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=SIN_CICLO,
                detalle=f"Fila {indice}: no tiene ciclo. No se registra sin él.",
            ))
            continue
        if ciclo not in CICLO_CODES:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=CICLO_DESCONOCIDO,
                detalle=f"Fila {indice}: «{ciclo}» no es un ciclo reconocido "
                        f"({', '.join(CICLO_CODES)}).",
            ))
            continue
        if estado not in ESTADOS_MATRICULA:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=ESTADO_DESCONOCIDO,
                detalle=f"Fila {indice}: «{estado_bruto}» no es un estado de "
                        f"matrícula reconocido ({', '.join(ESTADOS_MATRICULA)}).",
            ))
            continue

        otras_filas_con_este_nombre = [
            i for i in filas_por_nombre_en_lote.get(clave_nombre, ()) if i != indice
        ]
        if otras_filas_con_este_nombre:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=COINCIDENCIA_DE_NOMBRE,
                detalle=f"Fila {indice}: coincide en nombre con la fila "
                        + " y la fila ".join(str(i) for i in otras_filas_con_este_nombre)
                        + " de este mismo listado. El sistema no decide si "
                        "es la misma persona: ninguna de las dos se "
                        "registra hasta que lo revises a mano.",
            ))
            continue

        student_id: str | None = None
        if platform_id is not None:
            existentes = almacen.alumnos_por_platform_id(platform_id)
            del_mismo_curso = [a for a in existentes if a.curso == curso]
            de_otro_curso = [a for a in existentes if a.curso != curso]
            if del_mismo_curso:
                student_id = del_mismo_curso[0].student_id
            elif de_otro_curso:
                otro = de_otro_curso[0]
                pendientes.append(FilaPendiente(
                    fila=indice, motivo=REPETIDOR_POSIBLE,
                    detalle=f"Fila {indice}: este ID de plataforma ya "
                            f"existe con el student_id {otro.student_id}, "
                            f"del curso {otro.curso}. ¿Es un repetidor? "
                            "Decide si conserva ese student_id o si es un "
                            "alta nueva, y reimporta esta fila con lo que "
                            "corresponda -el sistema no lo decide solo-.",
                ))
                continue
            # Si no hay ninguno, sigue en None: alta nueva.
        else:
            candidatos_locales = filas_por_nombre_local.get(clave_nombre, [])
            if candidatos_locales:
                pendientes.append(FilaPendiente(
                    fila=indice, motivo=COINCIDENCIA_DE_NOMBRE,
                    detalle=f"Fila {indice}: el nombre ya está en la "
                            "correspondencia local y esta fila no trae ID "
                            "de plataforma con el que confirmarlo. Añade el "
                            "ID de CESUR si existe, o confirma a mano si es "
                            "la misma persona antes de reimportar.",
                ))
                continue

        alumno_nuevo = AlumnoNuevo(
            student_id=student_id, curso=curso, ccaa_code=ccaa_code,
            centro_code=centro, ciclo_code=ciclo, estado_matricula=estado,
            platform_id=platform_id,
        )
        try:
            registrado = almacen.dar_de_alta_alumno(alumno_nuevo)
        except ValueError as fallo:
            pendientes.append(FilaPendiente(
                fila=indice, motivo=ERROR_AL_REGISTRAR,
                detalle=f"Fila {indice}: {fallo}",
            ))
            continue

        if student_id is None:
            nuevas += 1
        else:
            actualizadas += 1
        pares_de_nombre[registrado.student_id] = nombre

    if pares_de_nombre:
        listado_local.importar_pares(pares_de_nombre)

    return ResultadoImportacion(
        total_filas=len(filas), en_blanco=en_blanco,
        nuevas=nuevas, actualizadas=actualizadas, pendientes=pendientes,
    )
