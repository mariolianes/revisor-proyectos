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
transmite íntegro al proveedor durante el procesamiento. No se almacena allí
ni en Supabase. Quien mantenga el sistema debe conocerlo para no alterar el
circuito por descuido.

**Corregido por D-010 el 2026-08-29:** este párrafo decía que el texto se
anonimizaba antes de enviarse; no es así, nunca se ha aplicado esa
anonimización. Ver D-010.

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
el procesamiento, no lo almacena allí ni en la base de datos, y la clave de
la API reside solo en el backend local.

Una fuente superior no puede quedar contradiciendo al código: es el mismo
criterio que llevó a corregir el §19 y el §21.1 con D-001 al adoptar
Supabase. Se corrige la prosa del §19 y las dos frases de D-002 que repetían
la misma inexactitud, cada una con su nota de remisión a esta decisión.

**Sigue en pie** que ninguna entrega real de un alumno se envía al proveedor
hasta que se cierre `proteccion_datos`. Tener la llave de la API no autoriza
a usarla con el trabajo de un alumno.

**Arrastra:** el §19 del Documento Maestro quedó corregido en este mismo
cambio, con su documento `docs/changes/2026-08-29-el-texto-se-envia-integro.md`.
