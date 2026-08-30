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

**Fecha:** 2026-08-29 · **Estado:** Provisional, a la espera de que Marcos la
valide · **Propuesta desde la implementación**

> A diferencia de las anteriores, esta decisión no la ha tomado el docente:
> se propone desde la implementación al corregir un defecto, y se registra
> aquí para que él la vea y decida. Mientras siga *Provisional*, lo que
> gobierna es lo que dice el §17.1, no esta entrada.

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
