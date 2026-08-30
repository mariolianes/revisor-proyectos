# Registro de decisiones

Por qué el sistema es como es. Formato del Anexo G del Documento Maestro.

Una decisión entra aquí cuando condiciona la arquitectura, contradice una
fuente superior o no puede deducirse leyendo el código. Los ajustes ordinarios
de criterio van a `docs/changes/`, no aquí.

**Estados:** `Provisional` (adoptada, revisable) · `Validada` (confirmada por el
docente) · `Pendiente` (identificada, sin resolver) · `Revertida`.

---

## D-001 · Supabase como persistencia, en lugar de sistema estrictamente local

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

El Documento Maestro §19 y §21.1 especifican un sistema estrictamente local.
Se adopta Supabase para persistencia, historial y trazabilidad.

**La contradicción es consciente y obliga a corregir el §19 y el §21.1**, no a
ignorarlos. Motivo: una aplicación puramente local no da historial consultable
ni acceso desde varios equipos, y el docente ya trabaja con este stack.

Alcance acotado:

- **Se almacena:** fichas, criterios versionados, correcciones por dimensión,
  evidencias citadas, semáforo, nota interna, feedback aprobado y auditoría.
- **No se almacena:** el PDF de la entrega ni el texto completo del trabajo.
- Evidencia citada: referencia a apartado y página más un fragmento de 1.500
  caracteres como máximo, verificado en el backend.

**Arrastra:** el §19 y el §21.1 del Documento Maestro quedaron corregidos en
el commit `305c78d`, con su documento de cambio
`docs/changes/2026-08-26-supabase-corrige-maestro.md`.

**Queda abierto:** la etapa 4 de la hoja de ruta del §22 sigue describiendo el
prototipo como «Aplicación mínima local», en contradicción con lo que ahora
dicen el §19 y el §21.1. Esta decisión acota su alcance a esos dos apartados y
no se ha tocado el §22 de oficio. Pendiente de que el docente decida si esa
fila se redacta de nuevo, si se amplía el alcance de D-001 o si describe bien
un hito intermedio ya superado y se deja como está.

## D-002 · OpenAI como proveedor de análisis, tras adaptador intercambiable

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

El análisis académico lo realiza la API de OpenAI. El backend define un puerto
`ProveedorAnalisis` con implementaciones sustituibles.

Circuito de datos, a efectos de arquitectura: el texto de la entrega se
transmite íntegro al proveedor durante el procesamiento. Por parte del
sistema no se guarda copia: ni en Supabase, ni en el repositorio. Lo que el
proveedor retenga se rige por sus propias condiciones, sin confirmar. Quien mantenga el sistema debe conocer este
circuito para no alterarlo por descuido.

**Corregido por D-010 el 2026-08-29:** este párrafo dijo dos cosas que no
podía sostener: que el texto se anonimizaba antes de enviarse, y que no se
almacenaba «allí» —en el proveedor—, dando por hecho su comportamiento de
retención sin haberlo verificado. Queda separado arriba lo que el sistema
garantiza de lo que depende de las condiciones del proveedor, sin confirmar.
Ver D-010.

La clave de la API reside únicamente en el backend local, nunca en el frontend.

**Clave recibida el 2026-08-28.** La facilitó el profesor y vive en el fichero
`.env` de la raíz, que `.gitignore` excluye. Se comprobó que no aparece en
ningún fichero versionado ni en el historial de commits. Con esto queda
cumplida la condición que la decisión tenía pendiente.

Sigue en pie lo que exige el §19: **ninguna entrega real de un alumno se envía
al proveedor** hasta que se confirmen las condiciones de tratamiento. Hasta
entonces se prueba con documentos propios (corregido por D-010 el
2026-08-29: no hay anonimizado en el backend antes del envío, porque no se
aplica ninguno).

## D-003 · PyMuPDF para la extracción

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

Es la herramienta más capaz para las comprobaciones objetivas del §6.2 y de la
lista de control del Índice comentado: tipografía y cuerpo por fragmento,
interlineado real, páginas en blanco, correspondencia del índice, resolución y
superficie de las imágenes, origen del PDF.

**Limitación:** licencia AGPL. Sin restricción para uso interno. Una eventual
distribución exigiría licencia comercial o migrar a pdfplumber.

## D-004 · La devolución la hace el docente, y él la registra

**Fecha:** 2026-08-26 · **Decidida:** 2026-08-27 · **Estado:** Validada ·
**Responsable:** Marcos

El sistema entrega el texto aprobado listo para copiar. El docente lo pega en
el Aula Virtual y vuelve a marcar que lo comunicó.

`COMUNICADO` significa exactamente eso: que el docente afirma haber devuelto el
feedback. El sistema no lo deduce ni lo comprueba, porque no puede. Se
descartó automatizar el envío: el §21.2 lo deja fuera de esta versión, y un
estado que el sistema pusiera solo diría que se disparó un envío, no que el
alumno recibiera nada.

**Desbloquea:** la transición a `COMUNICADO`.

## D-005 · La prosa manda sobre el destilado

**Fecha:** 2026-08-26 · **Estado:** Validada · **Responsable:** Marcos

Los criterios ejecutables de `criteria/` se derivan de `docs/maestro/`, nunca
al revés. Un criterio sin fuente trazable no existe.

Se descartó que el motor leyera la prosa directamente: impedía validar la
existencia de un criterio, versionar ponderaciones y medir la calibración
del §20.

**Arrastra:** reglas R1 y R2 de `GOVERNANCE.md`.

## D-006 · El editor no ofrece ningún atajo al procedimiento

**Fecha:** 2026-08-27 · **Estado:** Validada · **Responsable:** Marcos

El editor de criterios no tiene modo experto, ni botón de guardar sin motivo,
ni opción de posponer el documento de cambio. Guardar una edición exige indicar
por qué se cambia y qué fuente lo respalda, y el guardado ejecuta las seis
reglas antes de comitear.

Se descartaron dos alternativas. Un editor libre que avisara después: un aviso
que se puede posponer se pospone siempre, y en unos meses la prosa y los
criterios habrían dejado de decir lo mismo sin que nadie se enterara. Y un
editor de solo lectura, que no resolvía el problema que lo originó.

La comodidad está en que el camino correcto sea cómodo, no en que exista un
atajo. Quien mantenga esto encontrará una función que no existe: **no existe a
propósito.**

## D-007 · La propuesta automática solo se hace cuando la correspondencia es literal

**Fecha:** 2026-08-27 · **Estado:** Validada · **Responsable:** Marcos

Al cambiar la prosa, el editor propone actualizar un criterio derivado **solo**
cuando su valor es un número que aparece textualmente una sola vez en el texto
anterior, ha dejado de aparecer en el nuevo, y hay un único candidato ocupando
su mismo lugar, identificado por las palabras que lo precedían. En cualquier
otro caso muestra el criterio marcado para revisión manual, con el motivo
escrito para el docente.

La restricción es deliberada y más estrecha de lo que sería técnicamente
posible. Inferir de más significaría fabricar un criterio que nadie decidió
conscientemente, que es exactamente lo que R1 impide. Durante la construcción
se comprobó: una versión menos restrictiva llegaba a proponer el número de una
subsección como mínimo de páginas de un trabajo.

**Límite conocido:** si una reescritura conserva las palabras previas al valor
pero cambia el sujeto de la frase, la propuesta puede ser errónea. Requiere que
el arranque sobreviva literal, así que es estrecho, pero está ahí.

## D-008 · El valor de un criterio se escribe sobre el árbol del fichero, no sobre su texto

**Fecha:** 2026-08-27 · **Estado:** Validada · **Responsable:** Marcos

Cuando el editor actualiza el valor de un criterio, localiza el nodo por su
ruta dentro del árbol del fichero YAML y lo modifica ahí, conservando
comentarios y formato. No busca la clave por coincidencia de texto.

La decisión se tomó tras cuatro rondas de correcciones sobre búsqueda textual.
Cada una cerró una forma del mismo fallo y destapó la siguiente: reescribir el
criterio equivocado cuando dos comparten nombre de clave, comerse el primer
elemento de una lista, confundir un comentario con un valor, y elegir una clave
anidada en lugar de la correcta. Todas producían lo mismo: un criterio
corrompido y un mensaje diciendo que el cambio se había guardado y verificado.
Una de ellas, además, borraba silenciosamente un comentario del fichero.

La raíz era estructural. Un patrón de texto sabe encontrar `clave:` pero no
distingue una clave propia del criterio de otra igual en su subárbol, porque
eso es estructura y no texto.

**Arrastra:** la dependencia `ruamel.yaml`, fijada en `requirements-dev.txt`.

## D-009 · La carpeta de entregas se vigila, pero el docente confirma quién y qué fase

**Fecha:** 2026-08-27 · **Estado:** Validada · **Responsable:** Marcos

El sistema observa la carpeta de entregas y, cuando aparece un PDF nuevo,
deduce del nombre del fichero de qué alumno y de qué fase es. Esa deducción es
una propuesta: el docente la confirma de un gesto o la corrige. Si el nombre no
encaja con la convención del §15.3, o el código no corresponde a ningún alumno
registrado, o la fase no es la que toca, el sistema no adivina: presenta la
ficha en blanco.

**Contradice el §16.1 y el §21.2 del Documento Maestro**, que fijan recepción
manual y sitúan la vigilancia de carpetas fuera de la primera versión. La
decisión se toma sabiéndolo y obliga a corregir ambos apartados.

Se descartó la recogida totalmente automática. El nombre del fichero lo pone el
alumno, así que confiar en él habría convertido la condición de parada del
§18.2 —«alumno o fase no coinciden»— de excepción en rutina. La vigilancia
alcanza a encontrar el fichero; la identificación sigue siendo del docente.

El fichero nunca se mueve, ni se renombra, ni se modifica: el §18.1 lo exige y
aquí se cumple leyendo y nada más. La carpeta vive **fuera del repositorio**,
porque R6 impide que un PDF entre en el árbol versionado.

**Arrastra:** corrección del §16.1 y del §21.2 de `docs/maestro/`.

## D-010 · El texto se envía íntegro al proveedor de análisis, sin anonimización previa

**Fecha:** 2026-08-29 · **Estado:** Validada · **Responsable:** Marcos

Decisión del docente del 2026-08-29. El §19 del Documento Maestro y D-002
describían el circuito de análisis dando por supuesta una anonimización
previa al envío al proveedor. Esa anonimización no se aplica y nunca se ha
aplicado: el circuito real transmite el texto íntegro de la entrega durante
el procesamiento. Por parte del sistema no se guarda copia: ni en Supabase,
ni en el repositorio. Lo que el proveedor retenga se rige por sus propias
condiciones, que no están confirmadas; confirmarlas sigue siendo, como ya
fijaba el §19, condición previa a usar entregas reales.
La clave de la API reside solo en el backend local.

Una fuente superior no puede quedar contradiciendo al código: es el mismo
criterio que llevó a corregir el §19 y el §21.1 con D-001 al adoptar
Supabase. Se corrige la prosa del §19 y las dos frases de D-002 que repetían
la misma inexactitud sobre la anonimización, cada una con su nota de
remisión a esta decisión.

Una primera redacción de esta misma decisión, el mismo día, daba por buena
—sin haberla verificado— la retención del proveedor sobre el texto recibido.
Se corrige aquí, en el §19 y en D-002: R3 no distingue entre un dato que
nadie ha fijado y un dato que nadie ha verificado, y un apartado normativo
sobre tratamiento de datos de alumnos no puede dar por hecho el
comportamiento de retención de un tercero.

**Sigue en pie** que ninguna entrega real de un alumno se envía al proveedor
hasta que se cierre `proteccion_datos`. Tener la llave de la API no autoriza
a usarla con el trabajo de un alumno.

**Arrastra:** el §19 del Documento Maestro quedó corregido en este mismo
cambio, con su documento `docs/changes/2026-08-29-el-texto-se-envia-integro.md`.

## D-011 · El resumen del informe interno es un recuento verificado, no la síntesis del §17.1

**Fecha:** 2026-08-29 · **Estado:** Resuelta el 2026-08-30 (ver D-017) ·
**Propuesta desde la implementación**

> A diferencia de las anteriores, esta decisión no la ha tomado el docente:
> se propuso desde la implementación al corregir un defecto, y se registró
> aquí para que él la viera y decidiera. La decidió: D-017 pide la síntesis
> provisional que esta entrada dejaba pendiente, y con eso el hueco que
> sigue describiendo el resto de esta entrada queda cerrado, no vigente. Lo
> que sigue se conserva tal cual se escribió -por qué `resumen` no podía ser
> esa síntesis- porque la razón sigue siendo cierta; lo que cambia es que ya
> no hace falta esperar a que el docente decida: ya lo hizo.

`backend/salidas/informe.py` componía el «Resumen» del Anexo C con
`analisis.fortalezas[0].descripcion` -la primera fortaleza que hubiera, sin
pasar por el filtro de evidencia localizada que sí aplica `_semaforo`-. Una
fortaleza con la cita inventada podía titular el informe entero, sin cita y
sin la tinta de señal que sí llevan las dudas, los indicios y las
observaciones no localizadas.

Se sustituye por `_resumen()`, que compone el campo a partir de piezas ya
verificadas del mismo informe: el semáforo, cuántas prioridades llegan al
alumno y de qué gravedad, cuántas quedaron fuera solo por el límite de la
economía pedagógica, si alguna dimensión activa quedó sin valorar y si la
verificación dejó reparos. Ninguna de esas piezas es una interpretación
nueva: cada una se puede contrastar con otro bloque del mismo informe.

Eso deja un hueco que el profesor debe conocer, y esta decisión lo deja
constar en vez de disimularlo. El §17.1 pide «estado general en cinco o seis
líneas» y el §11.1 un «resumen ejecutivo del estado del proyecto»: los dos
piden una síntesis interpretativa -no solo enumerar lo verificado, sino decir
qué significa en su conjunto-, y eso es una lectura del trabajo que el §13
reserva al profesor, no un dato que el sistema pueda calcular por sí mismo.
Pedírselo de nuevo al motor como texto libre reabriría el problema que esta
misma decisión cierra. Se descarta también inventar aquí una interpretación
razonable: iría contra R3 tanto como una fortaleza sin cita.

No se ha creado una entrada nueva en `docs/PENDIENTE_OFICIAL.md`: ese catálogo
recoge datos oficiales que faltan y que llegarán -rúbrica, ponderaciones,
calendario-, no un límite permanente de diseño. Este hueco no se cierra
cuando llegue un dato nuevo, se cierra si el docente decide que quiere que el
sistema interprete, y esa es una decisión de alcance, no un dato pendiente.

**Sigue en pie** que el resumen factual conviva con el semáforo, las
prioridades, las dimensiones ausentes y los reparos, todos visibles en el
mismo informe: el profesor tiene delante las mismas piezas con las que
podría escribir él la síntesis que el §17.1 describe.

**Arrastra:** `backend/salidas/informe.py` (`_resumen`) y
`frontend/src/paginas/Revision.tsx`, donde el bloque «Resumen» sigue
mostrando el campo tal cual llega del backend.

---

## D-012 · La continuidad se deriva de lo ya medido, no se le pide al motor

**Fecha:** 2026-08-30 · **Estado:** Provisional, a la espera de que Marcos la
valide · **Propuesta desde la implementación**

> A diferencia de las anteriores, esta decisión no la ha tomado el docente:
> él pidió construir el bloque «Continuidad» y clasificar cada feedback
> anterior en aplicado, parcialmente aplicado, pendiente o no verificable,
> pero dejó abierto CÓMO clasificarlo. Se propone desde la implementación y
> se registra aquí para que la valide.

El §17.1 pide, en el informe interno, un bloque «Continuidad» con el
«feedback anterior aplicado, pendiente o no verificable»; el docente amplió
el vocabulario a cuatro estados, añadiendo «parcialmente aplicado», y dio
dos instrucciones concretas: desde la segunda entrega, recuperar el último
feedback aprobado y clasificarlo; y no fingir continuidad en la primera,
donde no hay antecedente.

Clasificar si una prioridad anterior se aplicó exige comparar lo que se le
dijo al alumno con lo que ha hecho, y eso es un juicio. Había dos caminos:

1. Pedírselo al motor -la observación anterior y el texto nuevo, y que
   diga si se aplicó-. Es exactamente el tipo de afirmación que el resto
   del sistema no se cree sin comprobar (`backend/analisis/verificacion.py`
   existe entero por eso), y aquí no hay con qué verificarla: sería texto
   libre sobre un cambio entre dos documentos, sin ninguna cita que
   contrastar.
2. Derivarlo de lo que el sistema ya mide, sin pedir un juicio nuevo:
   `comparar()` (`backend/evolucion/comparacion.py`), que ya calcula cuánto
   cambia una entrega frente a la anterior con n-gramas, sin semántica; y
   `cita_localizada()` (`backend/analisis/verificacion.py`), que ya decide
   si un fragmento exacto sigue en un texto, con el mismo criterio que
   verifica cada cita del motor.

Se elige el segundo. El resultado es más conservador que las cuatro
categorías que pide el docente: `clasificar_continuidad()`
(`backend/evolucion/continuidad.py`) solo emite PENDIENTE -cuando la cita
que motivó la observación anterior sigue apareciendo literal en la entrega
nueva, certeza mecánica de que no se ha tocado- o NO_VERIFICABLE -en
cualquier otro caso, incluido cuando la comparación global no es de fiar o
no se pudo hacer-. APLICADO y PARCIALMENTE_APLICADO quedan declarados en el
vocabulario del bloque, porque son parte del contrato del §17.1, pero
ninguna medida de este sistema hoy distingue «se corrigió» de «se rehízo
sin corregirlo» sin leer y entender el trabajo, y NO_VERIFICABLE es la
respuesta honesta cuando esa distinción no se puede sostener. El docstring
de `backend/evolucion/continuidad.py` explica el criterio completo, caso
por caso.

«El último feedback aprobado» se lee como `Informe.prioridades` de la
corrección guardada para la entrega anterior -lo que `revisar()`
(`backend/api/analisis.py`) llama, en su propio docstring, «lo que el §13
llama revisión docente»-, porque hoy no existe ningún estado distinto de
«aprobado» en el flujo implementado: ni `entrega.estado` llega nunca a
`APROBADO`, ni `correccion.aprobada_en`/`aprobada_por` se escriben desde
ningún endpoint. Es la mejor aproximación disponible a lo que pide el
docente, no una lectura literal de una columna que hoy nadie rellena.

Lo que el docente pide y este cambio **no** entrega: «cuando exista un
registro de comunicación, conservar también esa fecha». La tabla
`feedback.comunicado_en` existe en la migración, pero D-004 -qué canal usa
la devolución al alumno- sigue sin decidirse, y ningún endpoint escribe esa
columna. Añadir un campo que siempre leería vacío sería decorar el informe
con una promesa sin nada detrás; se deja pendiente de D-004, no inventado.

**Arrastra:** `backend/evolucion/continuidad.py` (nuevo),
`backend/salidas/informe.py` (`componer_informe`, campo `continuidad`),
`backend/servicios/analisis_de_entrega.py` (recupera la entrega y la
corrección anteriores) y `frontend/src/paginas/Revision.tsx` (el bloque
«Continuidad»).
## D-013 · Minimización de mejor esfuerzo, no anonimización, antes de la llamada externa

**Fecha:** 2026-08-30 · **Estado:** Provisional, a la espera de que Marcos la
valide · **Responsable:** Marcos, condiciones concretas a cambio de levantar
el bloqueo de `proteccion_datos`

El docente levantó el bloqueo de protección de datos a cambio de medidas
concretas: un ID por alumno (reutiliza `codigo_alumno`, ya alfanumérico y ya
no personal, en vez de crear un segundo identificador numérico en paralelo
-ver el docstring de `backend/privacidad/listado_local.py` para el porqué-),
la correspondencia nombre-código solo en local
(`backend/privacidad/listado_local.py`, fuera de Supabase, de la API y de
cualquier informe), y que el nombre del alumno, el DNI, el correo y el
teléfono se retiren del texto ANTES de que salga hacia el proveedor
(`backend/privacidad/minimizacion.py`).

**Esto no se vende como anonimización.** Los correos, teléfonos y DNI se
retiran con las mismas expresiones regulares de R6
(`tools/gobernanza/privacidad.py`), reutilizadas y no reescritas -mismo
criterio que ya seguía D-001 con otras piezas de la Parte A-, pero una
expresión regular no agota los casos: un DNI escrito distinto, un correo
partido por un salto de página, no encajan. El nombre se busca por
coincidencia literal contra el que trae el listado local para ese código, y
solo si el listado lo tiene: un apodo, una errata o un nombre que el listado
no conoce no se reconocen. Prometer una limpieza total que no se puede
garantizar sería peor que admitir el límite -la instrucción explícita de
Marcos al encargar esta tarea-, así que el sistema nunca informa «texto
limpio»: informa qué ha sustituido y qué no ha podido comprobar. Ver el
docstring de `backend/privacidad/minimizacion.py` para el detalle completo.

El sistema NO bloquea el análisis cuando el nombre no se puede verificar
como retirado -sería un segundo bloqueo donde el docente ya decidió asumir
el riesgo de una herramienta personal, sobre su propio equipo, con trabajos
descargados legítimamente-. Lo que hace es avisar, cada vez, cuando el
proveedor no es el simulado: el mismo criterio de honestidad por petición
que ya usa `AVISO_PROTECCION_DATOS` en `backend/api/analisis.py`.

**Sigue en pie** que la entrada `proteccion_datos` de
`docs/PENDIENTE_OFICIAL.md` no se retira con este cambio: es lo único que
hoy hace saltar la confirmación explícita antes de enviar un trabajo real
(`AVISO_PROTECCION_DATOS`), y quitarla antes de que esta minimización esté
fusionada y verificada dejaría al sistema mandando nombres sin avisar. La
retira Marcos cuando dé por buena esta tarea.

Además, `ProveedorOpenAI.analizar()` llama a la API de Responses con
`store: false`, para que OpenAI no conserve un objeto persistente de la
llamada en su lado -el profesor lo pidió expresamente, del mismo apartado-.

**Arrastra:** `backend/privacidad/`, `backend/servicios/
analisis_de_entrega.py` (la minimización se aplica antes de
`proveedor.analizar`, y el texto verificado y citado a partir de ahí es
siempre el minimizado, nunca el original -el motor no vio el original-),
`backend/analisis/openai.py` (`store=False`), `tools/importar_listado.py`
(la CLI que carga el listado local) y `.env.example`
(`REVISOR_DATOS_LOCALES`).

## D-014 · Registro de consumo, con una tabla de precios fechada y no escrita en Python

**Fecha:** 2026-08-30 · **Estado:** Provisional, a la espera de que Marcos la
valide · **Responsable:** Marcos

Del mismo encargo que D-013: para una herramienta que se paga por uso, saber
cuánto cuesta corregir una entrega es parte de decidir si compensa. Se
añade `ejecucion_motor`
(`supabase/migrations/20260830090000_registro_de_consumo.sql`), una fila por
llamada a `POST /entregas/{id}/analisis` -no por llamada individual al
proveedor: una ejecución puede hacer hasta dos llamadas reales, con hasta
dos intentos cada una-, con modelo, tokens de entrada/salida/cacheados,
coste estimado, duración, estado, intentos, causa de error, páginas,
volumen de texto y si se reutilizó un resultado anterior. Nunca el texto,
la instrucción ni ninguna cita: la misma frontera que D-001 ya traza para
`Correccion`.

El coste se calcula con `backend/analisis/precios.py`, contra una tabla
fechada en `config/precios_openai.yaml` -no un número en Python: las
tarifas de OpenAI cambian sin avisar, y una fila nueva con su propia
`vigente_desde` no reescribe el coste de un análisis ya hecho con el precio
de ayer-. Si un modelo no tiene tarifa vigente para la fecha del análisis,
el coste se deja como `None` -no calculable-, nunca en cero: R3 no
distingue entre inventar un criterio de corrección y inventar un precio.

`registrar_consumo` no es un método obligatorio del `Protocol` `Almacen`
(`backend/persistencia/modelos.py`): se llama por `getattr` con degradado
en silencio si el almacén -o un doble de prueba- no lo implementa. Hacerlo
obligatorio habría exigido tocar cada doble de prueba existente en el
repositorio para un dato de telemetría que no debe poder tumbar un análisis
que sí se completó.

**Arrastra:** `backend/persistencia/consumo.py`, `backend/analisis/
precios.py`, `config/precios_openai.yaml`,
`supabase/migrations/20260830090000_registro_de_consumo.sql`, y
`ConsumoDeLlamada`/`numero_de_llamadas`/`modelo` en
`backend/analisis/proveedor.py` y `backend/analisis/openai.py`.

**Resuelta por D-017**, que añade `sintesis_provisional` sin tocar
`resumen`: los dos campos conviven, tal como pedía el párrafo «Sigue en
pie» de arriba.

## D-015 · La nota interna es una estimación que calcula el sistema a partir de una rúbrica oficial, nunca una que propone el motor

**Fecha:** 2026-08-30 · **Estado:** Validada · **Responsable:** Marcos

Hasta esta decisión, «no existe la nota en ninguna parte» era literal: ni en
el formulario que rellena el motor (`backend/analisis/contrato.py`), ni en
el informe (`backend/salidas/informe.py`), ni en la pantalla de revisión.
El §13 reserva al profesor «aprobar o modificar cualquier calificación»
(`maestro#13-reservas-del-profesor`), y la forma de respetarlo era que la
operación no existiera.

El docente pide ahora que el sistema proponga una nota. No es una
contradicción con lo anterior -el §13 reserva *aprobar y modificar*, no
*calcular*-, pero exige una distinción que el código tiene que sostener, no
solo la prosa: la nota no la propone el motor -eso seguiría siendo R3 y R7
rotos, un modelo de lenguaje inventando un juicio sin evidencia
verificable-, la calcula el sistema, de forma determinista, a partir de la
rúbrica oficial cuando existe. `backend/analisis/contrato.py` no cambia:
`AnalisisDelMotor` sigue con `extra="forbid"` y sin ningún campo de nota, y
si el motor devolviera una, `esquema_estricto()` y la validación de Pydantic
la siguen rechazando antes de que nadie la vea. Esto se ha comprobado
rompiendo la regla a propósito -ver el informe de esta tarea en
`.superpowers/sdd/2026-08-30-respuesta-del-docente/`- y viendo caer
`tests/analisis/test_contrato.py::test_el_analisis_no_admite_campos_de_mas`.

Los campos nuevos, todos en `Informe` (`backend/salidas/informe.py`):

- `nota_propuesta_sistema`: el número, o `None`.
- `estado_nota`: `pendiente_de_rubrica` / `propuesta` / `modificada` /
  `aprobada` / `no_aplicable`. Nace `no_aplicable` en TEMA y DEFENSA -no
  llevan nota de corrección por este camino: TEMA no puntúa como entrega, y
  DEFENSA se valora a mano por el §6.5-, y `pendiente_de_rubrica` en el
  resto mientras no haya rúbrica. Solo pasa a `propuesta` cuando
  `calcular_nota_interna` calcula un número, y a `aprobada` o `modificada`
  cuando el docente decide en `revisar()`.
- `version_rubrica` y `ponderaciones_nota`: de qué rúbrica salió el número y
  con qué peso por dimensión, para que se pueda auditar sin adivinar.
- `nota_final_docente`: lo que el docente aprueba o modifica. Nunca lo
  escribe el motor -no hay ninguna vía por la que un valor del motor llegue
  a este campo-, y `revisar()` lo rechaza si `estado_nota` no admite
  ninguna decisión todavía (`pendiente_de_rubrica`, `no_aplicable`).
- `motivo_modificacion_nota`: opcional, y solo tiene sentido cuando la nota
  queda `modificada`, nunca cuando queda `aprobada` tal cual -un motivo ahí
  sería ruido, y `revisar()` lo descarta aunque llegue-.

**Hoy no hay rúbrica oficial**: `rubrica` y `ponderaciones` siguen
`PENDIENTE_OFICIAL` en `docs/PENDIENTE_OFICIAL.md`, y
`criteria/v2026-2027/ponderaciones.yaml` ya declara con sus propias
palabras que bloquea `nota_final` y `nota_propuesta`
(`bloquea: [nota_final, nota_propuesta]`). `rubrica_pendiente()`
(`backend/salidas/informe.py`) comprueba las dos entradas -no basta con
cerrar una sola-, con el mismo patrón que
`tools.calibrar.proteccion_datos_pendiente`. Mientras siga así,
`estado_nota` no puede valer otra cosa que `pendiente_de_rubrica` -o
`no_aplicable`- y `nota_propuesta_sistema` se queda en `None`: R3 impide
inventar la rúbrica, así que el sistema informa de la ausencia y no rellena
un valor razonable. Lo que se ha construido en esta tarea es la estructura
completa y la vía por la que entrará una rúbrica real -`calcular_nota_interna`
lee `criteria/<version>/rubrica.yaml` si existe, con una forma de ejemplo
documentada en el propio código, no un valor inventado-, probada con una
rúbrica de prueba en `tests/salidas/test_informe.py`, nunca con la oficial,
que no existe.

**Sobre el motivo de modificación.** El docente lo pidió «opcional y no
sensible», que es él avisando de que ahí no deben acabar datos personales
del alumno -circunstancias familiares, salud, lo que sea-. El sistema no
puede impedirlo del todo -es texto libre, y ninguna comprobación automática
distingue un criterio académico de una circunstancia personal-, pero puede
no invitarlo: el campo se pide explícitamente sobre «qué criterio de
corrección pesó en el cambio», nunca sobre el alumno, tanto en el docstring
de `Revision.motivo_modificacion_nota` (`backend/api/analisis.py`) como en
el texto que ve el docente junto al campo en
`frontend/src/paginas/Revision.tsx`. Ni el nombre del campo ni su
descripción mencionan al alumno en ningún momento, a propósito: la
prudencia depende de quien escribe, pero el sistema no le da ninguna razón
para pensar que ahí cabe otra cosa. R6 sigue aplicando igual que a
cualquier otro campo de texto libre del repositorio.

**No se ha necesitado ninguna migración de esquema.** La migración inicial
(`supabase/migrations/20260827120000_esquema_inicial.sql`) ya declaraba
`nota_propuesta`, `nota_aprobada`, `aprobada_en` y `aprobada_por` en la
tabla `correccion`, sin usar. Esta tarea no las rellena: la nota interna
entera vive en la columna `informe` (`jsonb`), que ya se relee entera en
`correccion_de` (`backend/persistencia/supabase.py`). No se escribe en las
columnas estructuradas porque la restricción `aprobacion_con_firma` exige
`aprobada_por` en cuanto hay `nota_aprobada`, y este sistema no tiene
todavía ninguna identidad de docente que escribir ahí -no hay
autenticación-: inventar un valor para poder rellenar esas columnas sería
inventar un dato, y R3/R6 lo prohíben igual que cualquier otro. Cuando
exista autenticación, una migración futura puede empezar a escribirlas de
verdad, con su propio documento de cambio.

**Arrastra:** `backend/analisis/contrato.py` (sin tocar, a propósito),
`backend/salidas/informe.py` (`calcular_nota_interna`, `rubrica_pendiente`),
`backend/api/analisis.py` (`Revision`, `revisar()`),
`backend/persistencia/correccion.py` (`LIMITE_DE_MOTIVO_NOTA`) y
`frontend/src/paginas/Revision.tsx`.

## D-016 · Doble semáforo: propuesto, inalterable, y final del docente, que no puede quedar por debajo de lo aprobado

**Fecha:** 2026-08-30 · **Estado:** Validada · **Responsable:** Marcos

Antes de esta decisión, `Informe` llevaba un único campo, `semaforo`: el
que calculaba `_semaforo` al analizar, y `revisar()` no lo tocaba nunca -el
comentario que lo decía ya existía-, pero tampoco había ningún campo donde
constara que el docente lo hubiera confirmado. El docente pide ahora dos
campos distintos, y los dos guardan algo que el otro no puede: `semaforo_
propuesto` -el mismo cálculo de siempre, renombrado, y ahora explícitamente
inalterable después del análisis, útil para auditoría- y
`semaforo_final_docente` -el que confirma al cerrar la revisión, `None`
mientras no lo haga-.

La parte difícil no es guardar dos campos: es qué hacer cuando el docente
intenta cerrar con un color que ya no cuadra con lo que sigue aprobado.
Tres reglas, tal como las pidió:

1. **`semaforo_propuesto` no se recalcula nunca**, ni siquiera en
   `revisar()`. Es la prueba de auditoría de lo que el sistema propuso antes
   de que nadie revisara nada, y recalcularlo confundiría «lo que se
   propuso» con «lo que queda después de editar», que es justo la distinción
   que este campo existe para conservar.
2. **No se modifica nada en silencio.** Si el docente descarta la única
   observación crítica, `semaforo_final_docente` no cambia solo: sigue
   valiendo lo que el docente puso, y es la interfaz -no el backend- quien
   avisa de que el color mínimo compatible puede haber cambiado
   (`colorMinimo` en `frontend/src/paginas/Revision.tsx`, recalculado en
   cada render sobre las decisiones actuales).
3. **No se puede cerrar con un semáforo incompatible con lo aprobado.**

La tercera es la que exigía decidir qué cuenta como «incompatible» y qué
hace el sistema entonces, y la pista que dio el docente -bloquear sin
explicar es lo peor de ambos mundos- fija el criterio: **incompatible es
proponer un color menos severo del que sostienen las observaciones fiables
que siguen aprobadas**, nunca al revés. `semaforo_por_valoraciones`
(`backend/salidas/informe.py`, la misma función que ya usaba `_semaforo`,
ahora pública y reutilizada) calcula ese color mínimo sobre las valoraciones
que quedan tras aplicar la decisión de esta misma petición de `revisar()`.
Ir más allá del mínimo -cerrar en ROJO cuando bastaría AMBAR- es prudencia
del docente y se acepta siempre: nadie pierde nada por ser más cauto que el
sistema. Quedarse corto -VERDE cuando queda un P1 aprobado- se rechaza con
un 400 que nombra el color mínimo y las dos salidas reales: descartar lo que
ya no se sostiene, o elegir un color acorde
(`_mensaje_semaforo_incompatible`, `backend/api/analisis.py`). No se guarda
nada de esa petición, ni siquiera las decisiones sobre observaciones que sí
eran válidas: es la misma garantía de todo-o-nada que ya tenía
`TextoFueraDeLimite`.

GRIS entra en la misma escala de severidad, no aparte: `SEVERIDAD_SEMAFORO`
lo pone por debajo de VERDE. Eso tiene dos efectos, los dos deliberados: si
no queda ninguna valoración fiable, cualquier color final es compatible -el
docente está ejerciendo un juicio que el sistema no pudo verificar, y eso es
exactamente lo que el §13 le reserva-, pero si sí queda algo fiable y
aprobado, cerrar en GRIS -«no evaluable»- también se rechaza: no se puede
esconder una observación real detrás de una incidencia que ya no existe.

Se ha comprobado rompiendo la comparación a propósito -invirtiendo el
operador en `revisar()`- y viendo caer tres tests de golpe:
`test_revisar_acepta_un_semaforo_final_mas_severo_que_el_minimo`,
`test_revisar_rechaza_un_semaforo_final_menos_severo_que_el_minimo` y
`test_revisar_evalua_la_compatibilidad_sobre_las_decisiones_de_esta_peticion`
(`tests/backend/test_api_analisis.py`).

**Arrastra:** `backend/salidas/informe.py` (`semaforo_por_valoraciones`,
`CODIGOS_SEMAFORO`, `SEVERIDAD_SEMAFORO`), `backend/api/analisis.py`
(`Revision.semaforo_final_docente`, la comprobación en `revisar()`,
`_mensaje_semaforo_incompatible`), `backend/persistencia/supabase.py`
(columna `semaforo_aprobado`, ya prevista sin usar en el esquema inicial) y
`frontend/src/paginas/Revision.tsx` (la sección «Semáforo final» y el
aviso de `colorMinimo`).

## D-017 · La síntesis provisional la compone el sistema desde piezas verificadas; nunca se cierra sola

**Fecha:** 2026-08-30 · **Estado:** Validada · **Responsable:** Marcos

D-011 dejó constancia de un hueco: el §17.1 pide un «Resumen» de «estado
general en cinco o seis líneas», y el §11.1 un «resumen ejecutivo», y los
dos piden una síntesis interpretativa -no solo enumerar lo verificado, sino
decir qué significa en su conjunto- que un sistema que se detiene antes de
interpretar no puede dar sin, o bien inventar una lectura que nadie ha
verificado, o bien pedírsela de nuevo al motor y reabrir el problema de la
fortaleza con la cita inventada que ese mismo cambio cerró.

El docente responde pidiendo la síntesis, pero **provisional y editable**,
«rotulada como síntesis provisional para revisión docente», y «nunca cerrar
automáticamente». Eso cambia el equilibrio que describía D-011: un texto que
el docente va a revisar y reescribir no es lo mismo que un texto que se da
por bueno, y D-011 razonaba sobre lo segundo. Pero el criterio de fondo de
D-011 no se abandona: **si la redactara el motor, volvería el problema de
las citas inventadas** -una síntesis con una lectura que suena bien y no
está sostenida por ninguna otra pieza del informe sería tan peligrosa como
la fortaleza sin cita que abrió esta discusión-. La solución no es pedirle
al motor un texto libre nuevo: es que el sistema componga, desde las mismas
piezas ya verificadas que usa `componer_resumen`, un borrador más largo y
más explícito -`componer_sintesis_provisional`,
`backend/salidas/informe.py`-, con una línea por bloque (semáforo,
prioridades nombradas con su código y su gravedad, lo descartado por el
límite, las fortalezas fiables, las dimensiones sin valorar, los reparos).
Sale rígido, pero es cierto: cada línea se puede contrastar con otro bloque
del mismo informe, igual que ya podía hacerse con `resumen`. Sobre eso
escribe el docente la lectura que el sistema no puede dar por sí mismo.

**El recuento factual se conserva.** `resumen` no desaparece ni se fusiona
con la síntesis: sigue siendo el campo fijo, de una frase, que permite
comprobar la síntesis provisional de un vistazo -si la síntesis dice algo
que `resumen` no sostiene, hay algo que revisar-. `revisar()` sigue
recomponiendo `resumen` en cada revisión, exactamente como antes.

**`sintesis_provisional` no se recompone en `revisar()`.** Es la diferencia
de fondo con `resumen`: en cuanto el sistema la compone por primera vez, es
del docente. `revisar()` la guarda tal cual la envíe -reescrita entera, a
medias, o sin tocar-, y si la petición no la incluye, conserva la que ya
hubiera. Recalcularla ahí borraría cualquier edición que el docente ya
hubiera hecho, que es justo la clase de modificación silenciosa que D-016
prohíbe para el semáforo y que aquí se evita por el mismo motivo. Que nunca
se cierre sola no es un estado que el sistema imponga -no hay ningún
`estado_sintesis` que pase a «cerrada»-: es, sencillamente, que no existe
ninguna operación que la marque como definitiva. El rótulo «síntesis
provisional para revisión docente» vive en la pantalla
(`frontend/src/paginas/Revision.tsx`), no en el texto compuesto, con el
mismo criterio que ya usan «Semáforo propuesto» o «Resumen»: la etiqueta es
del encabezado, no del contenido.

**Arrastra:** `backend/salidas/informe.py` (`Informe.sintesis_provisional`,
`componer_sintesis_provisional`), `backend/api/analisis.py`
(`Revision.sintesis_provisional`, `revisar()`),
`backend/persistencia/correccion.py` (`LIMITE_DE_SINTESIS`) y
`frontend/src/paginas/Revision.tsx` (la sección «Síntesis provisional para
revisión docente»).

## D-018 · El bloque de capacidad vive en el informe de calibración, no en un sistema de alertas nuevo

**Fecha:** 2026-08-30 · **Estado:** Provisional, a la espera de que Marcos la
valide · **Responsable:** Marcos

El docente pidió, tras ejecutar los nueve casos de calibración, un resumen
con coste total, coste medio, mediana, máximo, tokens medios y proyección
para 50, 100 y 200 análisis, más alertas de presupuesto al 50 %, 75 % y
90 %, y que un análisis marcado para reintento al agotar un límite no
pierda el PDF, la ficha ni el estado de la revisión. Los nueve casos son,
literalmente, lo que ejecuta `tools/calibrar.py`, así que este bloque se
compone ahí -`_resumen_de_consumo`, al final de `ejecutar()`- y no en un
sistema de monitorización nuevo: no hay dónde más leerlo hoy sin inventar
una infraestructura que nadie ha pedido.

El bloque no llama al proveedor una segunda vez ni recalcula nada por su
cuenta: lee `almacen.consumos()`, la misma tabla que ya deja
`analizar_entrega` por cada ejecución real (D-014), tras el mismo
`AlmacenEnMemoria` compartido por los nueve casos de la tanda.

**La mediana viaja siempre junto a la media.** Los nueve casos del banco
van de 4.000 a 12.600 palabras -dispersión real, no teórica-, y una media
sola no dice si el gasto se concentra en unos pocos trabajos largos.
`_lectura_de_consumo` compara los dos valores en prosa -sin inventar un
umbral de «cuánta diferencia es demasiada»- y deja el juicio al docente.

**La proyección no se presenta como precio.** `proyeccion_usd` multiplica
el coste medio de la tanda por 50, 100 y 200, con la tarifa vigente hoy
-`config/precios_openai.yaml`, D-014-, y tanto la prosa compuesta como el
texto final repiten que es una estimación sobre nueve casos, no una
promesa. Incluye los intentos que llegaron a llamar al proveedor y
fallaron después de gastar tokens -«un análisis fallido también
consume»-, porque esos registros están en `almacen.consumos()` igual que
los que terminaron bien; no incluye los casos saltados por un archivo
ilegible o ausente, que nunca llegan a costar nada. La estimación del
curso completo queda fuera a propósito: hace falta el número real de
alumnos y entregas, que nadie ha dado todavía, y este módulo no lo
inventa (R3).

**Las alertas de presupuesto son un mecanismo, no un número.** El docente
pidió avisar al 50 %, 75 % y 90 %, pero no ha fijado ningún presupuesto
todavía. `PRESUPUESTO_CALIBRACION` (`REVISOR_PRESUPUESTO_USD`, por entorno
o `.env`) y `--presupuesto-usd` en la línea de órdenes son las dos vías por
las que ese número podrá entrar; mientras ninguna lo traiga,
`ResumenDeConsumo.presupuesto_configurado` queda en `False` y el informe
lo dice sin calcular ningún porcentaje sobre un límite inventado. Un
presupuesto a cero o en negativo -un `.env` mal escrito, un signo
equivocado- se trata igual que ausente, no como un presupuesto real de
cero. Este es exactamente el mismo patrón que ya usa `CARPETA_CALIBRACION`
para la carpeta de los PDF.

**La cola o el reintento marcado, sin perder el PDF ni la ficha, queda
fuera.** Hoy, si un análisis falla, la entrega vuelve a `RECIBIDO` -no se
guarda nada a medias- y se puede volver a pedir a mano; el PDF y la ficha
nunca se tocan porque `analizar_entrega` no llega a escribir nada cuando
falla. Encolar automáticamente o marcar una entrega para reintento es
alcance nuevo -un estado nuevo en el flujo, o un disparador que hoy no
existe- y el docente pidió decidirlo él mismo, no que se construyera de
oficio. El informe de calibración lo dice explícitamente, para que quede
constancia de qué se pidió y qué no se ha construido todavía.

**Arrastra:** `tools/calibrar.py`
(`ResumenDeConsumo`, `AlertaDePresupuesto`, `_resumen_de_consumo`,
`_lectura_de_consumo`, `PRESUPUESTO_CALIBRACION`, `UMBRALES_DE_ALERTA_PCT`,
`PROYECCIONES_DE_ANALISIS`, `--presupuesto-usd`) y
`tests/tools/test_calibrar.py`.
