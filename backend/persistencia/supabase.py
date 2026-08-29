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

from backend.persistencia.correccion import Correccion, validar_citas_acotadas
from backend.persistencia.modelos import (
    EntregaNueva,
    EntregaRegistrada,
    choca_con_lo_declarado,
    error_de_atribucion,
    validar,
    validar_estado,
    validar_fase,
)
from backend.salidas.borrador import Devolucion
from backend.salidas.informe import Informe

ESPERA = 15.0


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


class ChoqueDeAlmacen(ErrorDeAlmacen):
    """Lo que se quería guardar choca con algo que ya estaba guardado.

    Es un `ErrorDeAlmacen` porque viene de la misma costura y lleva el mismo
    tipo de mensaje, pero no es la misma clase de problema y no debe
    contestarse igual. Los demás fallos del almacén -la red caída, la clave
    caducada, RLS rechazando- son indisponibilidades: reintentar más tarde
    puede arreglarlas, y por eso la aplicación responde 503. Un choque con
    una restricción `unique` no se arregla reintentando; reintentarlo dará
    exactamente el mismo choque. Es un conflicto de datos, responde 409, y
    lo que hay que hacer lo dice el mensaje.

    La distinción no es teórica: 503 le dice al navegador -y a cualquier
    proxy o reintento automático que se ponga por delante mañana- que vuelva
    a intentarlo.
    """


# Lo que el profesor tiene que leer cuando la entrega choca con la
# restricción `unique (proyecto_id, fase, version)` de la migración. Es el
# caso más probable de todos: el alumno vuelve a entregar la misma fase con
# el mismo número de versión y otro archivo.
CHOQUE_EN_ENTREGA = (
    "Ya hay una entrega registrada de ese alumno para esa misma fase y esa "
    "misma versión. Si el alumno ha vuelto a entregar, confírmala con el "
    "número de versión siguiente. Si crees que es la misma entrega de "
    "antes, ábrela desde la lista y compruébalo antes de tocar nada."
)


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
            detalle = (
                CHOQUE_EN_ENTREGA if tabla == "entrega" else
                f"Ya hay una fila en «{tabla}» con esos mismos datos, y la "
                "base de datos no admite dos."
            )
            raise ChoqueDeAlmacen(
                f"{detalle} Respuesta de Supabase: {respuesta.text[:300]}"
            )
        if respuesta.status_code in (401, 403):
            # Decir solo que Supabase ha respondido 401 deja al docente
            # sabiendo que algo falla y sin saber qué mirar. Las tablas
            # tienen RLS activo y ninguna política, así que esto solo
            # funciona con la clave de servicio: si el 401 llega, o la clave
            # no es la que es, o ha caducado.
            raise ErrorDeAlmacen(
                f"Supabase ha rechazado la petición a «{tabla}» "
                f"({respuesta.status_code}): la clave no vale o ha caducado. "
                "Revisa SUPABASE_SERVICE_KEY en el fichero .env, que tiene "
                "que ser la clave de servicio del proyecto. Respuesta de "
                f"Supabase: {respuesta.text[:300]}"
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

    def _alumno(self, codigo: str, ciclo: str) -> tuple[str, str]:
        """El identificador del alumno y el ciclo con el que está dado de alta.

        Se devuelve el ciclo guardado, no el que se acaba de declarar,
        porque el ciclo pertenece al alumno: lo tiene la tabla `alumno` y no
        la tabla `entrega`. Devolver el declarado hacía que la ficha recién
        confirmada dijera un ciclo y la lista, al recargarla, dijera otro:
        el mismo almacén contradiciéndose consigo mismo.
        """
        existente = self._uno("alumno", codigo=f"eq.{codigo}")
        if existente:
            return existente["id"], existente.get("ciclo") or ciclo
        creado = self._pedir(
            "POST", "alumno", json={"codigo": codigo, "ciclo": ciclo}
        )
        return creado[0]["id"], creado[0].get("ciclo") or ciclo

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

    # La misma lectura, para la representación que devuelve una escritura.
    # Sin cruce interno: ahí no se filtra por ningún campo del embebido, que
    # es lo único para lo que el `!inner` hace falta.
    SELECCION_AL_ESCRIBIR = "*,proyecto(alumno(codigo,ciclo))"

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
            if choca_con_lo_declarado(ya_estaba, entrega):
                raise error_de_atribucion(ya_estaba, entrega)
            return ya_estaba

        alumno_id, ciclo = self._alumno(entrega.codigo_alumno, entrega.ciclo)
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
        # El ciclo del alumno guardado, no el declarado ahora: es el que
        # devolverán `listar` y `por_id` al leer la fila con su alumno
        # anidado, y la ficha recién confirmada tiene que decir lo mismo.
        fila["alumno"] = {"codigo": entrega.codigo_alumno, "ciclo": ciclo}
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
        # El `select` no sobra: sin él, PostgREST devuelve la fila de
        # `entrega` a secas, sin el alumno anidado, y `_componer` compone una
        # entrega con el código de alumno y el ciclo vacíos. Eso es lo que
        # devolvía este método -y lo que acababa en la ficha y en la
        # respuesta de la API- mientras AlmacenEnMemoria devolvía la entrega
        # entera. Lo encontró el test de paridad.
        #
        # Aquí el cruce va sin `!inner`, al revés que en SELECCION: el
        # `!inner` hace falta cuando se filtra por un campo del recurso
        # embebido -si no, PostgREST no filtra la tabla raíz-, y aquí el
        # filtro es por `id`, de la propia tabla. Pedir un cruce interno en
        # la representación de una escritura sería exigir a PostgREST algo
        # que no necesita hacer.
        filas = self._pedir(
            "PATCH", "entrega",
            parametros={
                "id": f"eq.{identificador}",
                "select": self.SELECCION_AL_ESCRIBIR,
            },
            json={"estado": estado, "motivo_bloqueo": motivo},
        )
        return self._componer(self._aplanar(filas[0])) if filas else None

    def guardar_correccion(
        self,
        entrega_id: str,
        informe: Informe,
        devolucion: Devolucion | None,
        motor: str,
        aviso: str | None = None,
    ) -> str:
        """Tres escrituras encadenadas: `correccion`, `valoracion_dimension`
        y `evidencia`. Si la segunda o la tercera fallan, se deshace la
        primera -y con ella, por `on delete cascade`, cualquier fila que ya
        hubiera colgado de ella- y se levanta `ErrorDeAlmacen`. Una
        corrección guardada a medias -un informe sin sus valoraciones, o
        unas valoraciones sin su evidencia- es peor que ninguna: el docente
        la vería como completa y no lo es.

        `informe` y `devolucion` se guardan enteros en las columnas `jsonb`
        que añade la migración de esta tarea -es lo que permite reconstruir
        las dos salidas completas en `correccion_de`, con fortalezas,
        indicios de autoría, reparos y dudas incluidos, que no tienen fila
        propia en ninguna tabla-. `valoracion_dimension` y `evidencia` se
        escriben además, con los mismos datos: es la parte que un futuro
        informe por dimensión necesita poder consultar con SQL, y la que
        impone en la base de datos el límite de D-001 sobre cada cita.

        Una entrega tiene una corrección -`unique (entrega_id)`-: si ya
        había una, se borra antes de insertar la nueva. Es la misma
        operación que reanalizar y que guardar una revisión del docente: las
        dos sustituyen la corrección entera, no la editan campo a campo.
        """
        validar_citas_acotadas(informe)

        existente = self._uno("correccion", entrega_id=f"eq.{entrega_id}")
        if existente is not None:
            self._pedir(
                "DELETE", "correccion", parametros={"id": f"eq.{existente['id']}"}
            )

        filas = self._pedir("POST", "correccion", json={
            "entrega_id": entrega_id,
            "version_criterios": informe.identificacion.get("criterios") or "",
            "resumen_ejecutivo": informe.resumen,
            "semaforo_propuesto": informe.semaforo,
            "accion_recomendada": informe.recomendacion,
            "informe": informe.model_dump(mode="json"),
            "devolucion": (
                devolucion.model_dump(mode="json") if devolucion is not None else None
            ),
            "aviso": aviso,
        })
        correccion_id = filas[0]["id"]

        try:
            if informe.valoraciones:
                filas_valoracion = self._pedir("POST", "valoracion_dimension", json=[
                    {
                        "correccion_id": correccion_id,
                        "dimension": v.dimension,
                        "nivel": v.nivel,
                        "prioridad": v.prioridad,
                        "observacion": v.observacion,
                    }
                    for v in informe.valoraciones
                ])
                self._pedir("POST", "evidencia", json=[
                    {
                        "valoracion_id": fila_v["id"],
                        "apartado": v.evidencia.apartado,
                        "fragmento": v.evidencia.cita,
                    }
                    for fila_v, v in zip(filas_valoracion, informe.valoraciones)
                ])
        except ErrorDeAlmacen as fallo:
            self._pedir(
                "DELETE", "correccion", parametros={"id": f"eq.{correccion_id}"}
            )
            raise ErrorDeAlmacen(
                "El análisis no se ha podido guardar del todo, así que no "
                f"se ha guardado nada: {fallo} La entrega sigue sin análisis "
                "guardado; puedes repetirlo."
            ) from fallo

        return correccion_id

    def correccion_de(self, entrega_id: str) -> Correccion | None:
        # `entrega_id` es de tipo `uuid` en la base de datos: el mismo motivo
        # que `_es_uuid` protege en `por_id`, aquí sobre la columna de
        # `correccion` en vez de sobre `entrega.id`.
        if not _es_uuid(entrega_id):
            return None
        fila = self._uno("correccion", entrega_id=f"eq.{entrega_id}")
        if fila is None:
            return None
        informe = Informe.model_validate(fila["informe"])
        devolucion = fila.get("devolucion")
        return Correccion(
            id=fila["id"],
            informe=informe,
            devolucion=Devolucion.model_validate(devolucion) if devolucion else None,
            motor=informe.motor,
            aviso=fila.get("aviso"),
        )
