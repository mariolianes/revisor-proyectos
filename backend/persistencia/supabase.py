"""El almacén contra las tablas reales, por PostgREST.

Se usa httpx directamente y no un cliente de Supabase: son cuatro llamadas
HTTP con dos cabeceras, y añadir una dependencia para eso solo traería su
propio ciclo de versiones.

Las tablas tienen RLS activo y ninguna política, así que esto solo funciona
con la clave de servicio. Es lo que se pretende mientras no esté decidido
cómo se autentica el docente: es preferible que no entre nadie a que entre
cualquiera.
"""

import uuid
from datetime import datetime

import httpx

from backend.persistencia.modelos import (
    EntregaNueva,
    EntregaRegistrada,
    validar,
    validar_estado,
    validar_fase,
)

ESPERA = 15.0

# Lo declarado se compara en estos campos para decidir si una huella
# repetida es de verdad el mismo archivo confirmado dos veces. El nombre o
# la ruta quedan fuera a propósito: es dónde está el fichero, no de quién
# es, y moverlo de subcarpeta no debe dar error. Ver memoria.py, que hace
# la misma comprobación: los dos almacenes tienen que comportarse igual.
_CAMPOS_DE_IDENTIDAD = ("codigo_alumno", "ciclo", "fase", "version")


def _choca_con_lo_declarado(
    existente: EntregaRegistrada, nueva: EntregaNueva
) -> bool:
    return any(
        getattr(existente, campo) != getattr(nueva, campo)
        for campo in _CAMPOS_DE_IDENTIDAD
    )


def _es_uuid(identificador: str) -> bool:
    """Si no tiene forma de UUID, ni se pregunta.

    `entrega.id` es de tipo `uuid` en la base de datos: mandarle a Postgres
    algo que no lo es no da «no existe», da un 400 -«invalid input syntax
    for type uuid»-, porque Postgres rechaza la consulta antes de mirar si
    hay una fila así. Sin esta guarda, un identificador inventado en una
    URL (por ejemplo, `GET /api/entregas/no-existe`) se convertiría en un
    error del servidor en vez de en el «no existe esa entrega» que da
    AlmacenEnMemoria al no encontrarlo en su diccionario. Los dos almacenes
    tienen que responder igual a lo mismo.
    """
    try:
        uuid.UUID(identificador)
        return True
    except ValueError:
        return False


class ErrorDeAlmacen(Exception):
    """No se ha podido hablar con la base de datos."""


class AlmacenSupabase:
    """Las nueve tablas, vistas por las tres que esta parte usa."""

    def __init__(
        self, url: str, clave: str, cliente: httpx.Client | None = None
    ) -> None:
        self._base = url.rstrip("/") + "/rest/v1"
        self._cliente = cliente or httpx.Client(timeout=ESPERA)
        self._cabeceras = {
            "apikey": clave,
            "Authorization": f"Bearer {clave}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    @property
    def es_duradero(self) -> bool:
        return True

    def _pedir(
        self, metodo: str, tabla: str, *, parametros: dict | None = None, json=None
    ) -> list[dict]:
        try:
            respuesta = self._cliente.request(
                metodo,
                f"{self._base}/{tabla}",
                headers=self._cabeceras,
                params=parametros,
                json=json,
            )
        except httpx.HTTPError as fallo:
            raise ErrorDeAlmacen(
                "No se ha podido conectar con Supabase. Comprueba la conexión "
                "y que SUPABASE_URL es correcta."
            ) from fallo
        if respuesta.status_code == 409:
            # PostgREST devuelve 409 cuando la fila choca con una restricción
            # `unique`. En `entrega` la restricción es
            # `unique (proyecto_id, fase, version)`, y el choque tiene una
            # causa concreta y frecuente que conviene nombrar: el alumno
            # reentrega la misma fase con el mismo número de versión y otro
            # archivo. Sin esto, el caso más probable de todos llegaba como
            # un volcado de PostgREST en inglés.
            raise ErrorDeAlmacen(
                f"Supabase ha rechazado guardar en «{tabla}» porque choca con "
                "algo que ya está registrado. En una entrega ocurre cuando ya "
                "hay una de ese alumno para la misma fase y la misma versión: "
                "si es una reentrega, confírmala con el número de versión "
                f"siguiente. Respuesta de Supabase: {respuesta.text[:300]}"
            )
        if respuesta.status_code >= 400:
            raise ErrorDeAlmacen(
                f"Supabase ha respondido {respuesta.status_code} al acceder a "
                f"«{tabla}»: {respuesta.text[:300]}"
            )
        cuerpo = respuesta.json()
        return cuerpo if isinstance(cuerpo, list) else [cuerpo]

    def _uno(self, tabla: str, **filtros) -> dict | None:
        filas = self._pedir(
            "GET", tabla, parametros={**filtros, "select": "*", "limit": "1"}
        )
        return filas[0] if filas else None

    def _alumno(self, codigo: str, ciclo: str) -> str:
        existente = self._uno("alumno", codigo=f"eq.{codigo}")
        if existente:
            return existente["id"]
        creado = self._pedir(
            "POST", "alumno", json={"codigo": codigo, "ciclo": ciclo}
        )
        return creado[0]["id"]

    def _proyecto(self, alumno_id: str, version_criterios: str) -> str:
        existente = self._uno(
            "proyecto",
            alumno_id=f"eq.{alumno_id}",
            version_criterios=f"eq.{version_criterios}",
        )
        if existente:
            return existente["id"]
        creado = self._pedir("POST", "proyecto", json={
            "alumno_id": alumno_id, "version_criterios": version_criterios,
        })
        return creado[0]["id"]

    def _componer(self, fila: dict) -> EntregaRegistrada:
        """Una fila de `entrega` más su alumno, tal como la usa el sistema."""
        alumno = fila.get("alumno") or {}
        return EntregaRegistrada(
            id=fila["id"],
            codigo_alumno=alumno.get("codigo", ""),
            ciclo=alumno.get("ciclo", ""),
            fase=fila["fase"],
            version=fila["version"],
            nombre_archivo=fila.get("nombre_archivo") or "",
            huella=fila.get("huella_archivo") or "",
            recibida_en=datetime.fromisoformat(fila["recibida_en"]),
            estado=fila["estado"],
            motivo_bloqueo=fila.get("motivo_bloqueo"),
            version_criterios=fila["version_criterios"],
        )

    # PostgREST devuelve el alumno anidado atravesando las dos claves ajenas:
    # así se lee la entrega y su código de alumno en una sola llamada.
    #
    # El `!inner` no es opcional. Sin él, un filtro sobre un recurso embebido
    # no filtra la tabla raíz: devuelve TODAS las entregas, con el embebido a
    # null en las que no casan. En anterior_de eso significaría traerse las
    # entregas de todos los alumnos. Como toda entrega tiene proyecto y todo
    # proyecto tiene alumno —ambas claves son NOT NULL—, el cruce interno no
    # descarta ninguna fila legítima.
    #
    # httpx transmite el `!` de aquí percent-codificado (`%21`) al construir
    # la query string a partir de `params=`. Eso no cambia nada: el servidor
    # (Warp/WAI, en el que corre PostgREST) hace percent-decoding de la query
    # string antes de que el parser de filtros de PostgREST vea el valor de
    # `select`, así que `%21inner` y `!inner` llegan como la misma cadena. Es
    # el comportamiento estándar de cualquier framework HTTP al partir una
    # query string, no una particularidad de PostgREST.
    SELECCION = "*,proyecto!inner(alumno!inner(codigo,ciclo))"

    def _aplanar(self, fila: dict) -> dict:
        anidado = (fila.get("proyecto") or {}).get("alumno") or {}
        return {**fila, "alumno": anidado}

    def registrar(self, entrega: EntregaNueva) -> EntregaRegistrada:
        validar(entrega)
        ya_estaba = self.por_huella(entrega.huella)
        if ya_estaba is not None:
            # Misma huella es el mismo archivo, aunque lo hayan renombrado.
            # Pero si lo que se declara ahora no coincide con la ficha bajo
            # la que ya está, es un error de atribución: no se resuelve en
            # silencio a favor del primero que llegó. Mismo criterio que
            # AlmacenEnMemoria.registrar.
            if _choca_con_lo_declarado(ya_estaba, entrega):
                raise ValueError(
                    f"El archivo «{entrega.huella}» ya está registrado como "
                    f"{ya_estaba.codigo_alumno}/{ya_estaba.ciclo}/"
                    f"{ya_estaba.fase} v{ya_estaba.version} (ficha "
                    f"{ya_estaba.id}), pero ahora se declara como "
                    f"{entrega.codigo_alumno}/{entrega.ciclo}/{entrega.fase} "
                    f"v{entrega.version}. Si es el mismo trabajo, corrige el "
                    "dato que no coincide antes de confirmarlo."
                )
            return ya_estaba

        alumno_id = self._alumno(entrega.codigo_alumno, entrega.ciclo)
        proyecto_id = self._proyecto(alumno_id, entrega.version_criterios)
        filas = self._pedir("POST", "entrega", json={
            "proyecto_id": proyecto_id,
            "fase": entrega.fase,
            "version": entrega.version,
            "nombre_archivo": entrega.nombre_archivo,
            "huella_archivo": entrega.huella,
            "version_criterios": entrega.version_criterios,
        })
        fila = filas[0]
        fila["alumno"] = {"codigo": entrega.codigo_alumno, "ciclo": entrega.ciclo}
        return self._componer(fila)

    def listar(self) -> list[EntregaRegistrada]:
        filas = self._pedir("GET", "entrega", parametros={
            "select": self.SELECCION, "order": "recibida_en.desc",
        })
        return [self._componer(self._aplanar(fila)) for fila in filas]

    def por_id(self, identificador: str) -> EntregaRegistrada | None:
        if not _es_uuid(identificador):
            return None
        filas = self._pedir("GET", "entrega", parametros={
            "id": f"eq.{identificador}", "select": self.SELECCION, "limit": "1",
        })
        return self._componer(self._aplanar(filas[0])) if filas else None

    def por_huella(self, huella: str) -> EntregaRegistrada | None:
        filas = self._pedir("GET", "entrega", parametros={
            "huella_archivo": f"eq.{huella}", "select": self.SELECCION, "limit": "1",
        })
        return self._componer(self._aplanar(filas[0])) if filas else None

    def anterior_de(
        self, codigo_alumno: str, fase: str, version: int = 1
    ) -> EntregaRegistrada | None:
        """La más reciente de las entregas que preceden a esta.

        El orden de fases no es alfabético ni cronológico, así que el
        filtrado se hace aquí y no en la consulta: son pocas entregas por
        alumno y la alternativa sería codificar el orden de las fases dentro
        de una cadena de consulta.
        """
        validar_fase(fase)
        from backend.vigilancia.nombres import FASES

        filas = self._pedir("GET", "entrega", parametros={
            "select": self.SELECCION,
            "proyecto.alumno.codigo": f"eq.{codigo_alumno}",
        })
        candidatas = [
            self._componer(self._aplanar(fila)) for fila in filas
        ]
        orden_actual = (FASES.index(fase), version)
        previas = [
            entrega for entrega in candidatas
            if entrega.codigo_alumno == codigo_alumno
            and entrega.fase in FASES
            and (FASES.index(entrega.fase), entrega.version) < orden_actual
        ]
        if not previas:
            return None
        return max(previas, key=lambda e: (FASES.index(e.fase), e.version))

    def cambiar_estado(
        self, identificador: str, estado: str, motivo: str | None
    ) -> EntregaRegistrada | None:
        # Primero el estado: un estado inválido es el error más informativo
        # de los dos, y debe verse aunque el identificador tampoco valga.
        validar_estado(estado, motivo)
        if not _es_uuid(identificador):
            return None
        filas = self._pedir(
            "PATCH", "entrega",
            parametros={"id": f"eq.{identificador}"},
            json={"estado": estado, "motivo_bloqueo": motivo},
        )
        return self._componer(self._aplanar(filas[0])) if filas else None
