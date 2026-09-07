# Ocho decisiones para desbloquear la arquitectura

**Autor:** Marcos Castaño · **Fecha:** 2 de septiembre de 2026 · **Versión 1.0**

Respuesta del docente a las ocho preguntas del informe del 2 de septiembre.
Es prosa normativa: cierra las decisiones que dependían de él y se sitúa,
como el documento de calibración, por debajo de los tres primeros documentos
del §14.1 y sin poder contradecirlos. Donde aclara una interpretación previa
—el semáforo, las fases del banco— manda esta.

Transcripción literal de su documento. No se reescribe.

<!-- ancla: decisiones#1-decision-general -->
## 1. Decisión general

Las ocho cuestiones quedan cerradas y pueden trasladarse a configuración e
implementación. No hay que rehacer el Documento Maestro ni el Documento llave
de arquitectura. La identificación utilizará un único ID interno, las
comprobaciones de nombre se harán localmente y las reglas abiertas se
completan en este informe.

La mayor parte de los bloqueos no procede de un error de arquitectura, sino
de ejemplos antiguos, decisiones de configuración pendientes o diferencias de
interpretación. Las respuestas siguientes deben considerarse instrucciones
funcionales definitivas para esta iteración.

<!-- ancla: decisiones#2-identificador -->
## 2. Identificador y nombre del archivo

La identidad operativa única será `ALU-260001`, `ALU-260002`, etc. El ejemplo
`AF023` pertenece a una convención anterior del Documento Maestro. El
Documento llave posterior establece el sistema ALU y, según su propia
jerarquía, prevalece en cuestiones de identificadores, rutas, versionado y
nombres de archivo.

**Regla.** `AF023` no se conserva como segundo código. No habrá una tabla de
correspondencia `AF023` ↔ `ALU-260001`. El único identificador interno será
el formato ALU.

**El alumno no nombra el archivo con el ID.** No elegimos literalmente
ninguna de las dos opciones planteadas, porque parten de que el alumno debe
conocer el ID. El estudiante entrega en CESUR con el nombre que utilice
normalmente. Marcos descarga el archivo original y el sistema lo identifica.
Solo después crea el nombre normalizado.

| Momento | Ejemplo |
|---|---|
| Archivo original de CESUR | `Maria_Lopez_Entrega_2.docx` |
| Identificación local | Correspondencia confirmada con `student_id = ALU-260001` |
| Archivo normalizado | `ALU-260001_E02_v01.docx` |

El original se conserva sin sobrescribir. La copia normalizada es la que
organiza el expediente y alimenta la trazabilidad. Esta decisión desbloquea
identificación, bandejas, enrutamiento y piloto.

<!-- ancla: decisiones#3-repetidores -->
## 3. Repetidores

A efectos del sistema, un repetidor es un alumno matriculado en el curso
actual que debe realizar de nuevo el Proyecto Intermodular completo. No
necesita un flujo académico especial ni se hereda automáticamente su proyecto
anterior.

- Cada curso genera una matrícula y un ID operativo nuevo.
- Un alumno `ALU-260001` en 2026-2027 podría ser `ALU-270146` en 2027-2028.
- No se fusionan automáticamente expedientes ni entregas entre cursos.
- La coincidencia con un nombre de un curso archivado no es una incidencia.
- Solo se detienen duplicidades o contradicciones dentro del mismo curso
  activo.
- Puede existir un campo opcional `previous_enrollment_id` para consultar
  antecedentes, sin afectar al nuevo circuito.

**Implementación.** La clave de matrícula debe incluir el curso académico. No
detener la importación por encontrar a la misma persona en un curso
histórico.

<!-- ancla: decisiones#4-portada -->
## 4. Comprobación del nombre en portada

Sí debe construirse, pero exclusivamente como comprobación local previa a la
anonimización. Leer el nombre dentro del equipo no contradice la capa de
privacidad: lo que debe evitarse es enviar el nombre al servidor o incluirlo
en el texto remitido al modelo.

Secuencia requerida:

1. Leer localmente el nombre original del archivo y los metadatos disponibles
   de CESUR.
2. Consultar localmente la correspondencia nombre-ID.
3. Leer localmente la portada o las primeras páginas cuando sea necesario.
4. Confirmar el `student_id` o enviar el caso a Incidencias.
5. Eliminar, sustituir o enmascarar el nombre en el texto antes de cualquier
   llamada externa.

La portada es una evidencia auxiliar. Si falta el segundo apellido, cambia el
orden o existen pequeñas diferencias ortográficas, se aplican las reglas de
normalización. Si hay contradicción entre identificadores o más de un
candidato posible, el proceso se detiene.

<!-- ancla: decisiones#5-extensiones -->
## 5. Extensiones y tamaños

| Tipo de archivo | Extensiones admitidas | Límite y tratamiento |
|---|---|---|
| Documento del proyecto | `.pdf`, `.docx` | 20 MB por archivo. Ambos entran en el circuito de análisis. |
| Presentación de defensa | `.pdf`, `.pptx` | 20 MB por archivo. Se archiva en DEFENSA y no sustituye al proyecto final. |
| Word antiguo | `.doc` | Incidencia técnica o conversión controlada; no análisis directo por defecto. |
| Otros formatos | Cualquier otro | Incidencia por formato no admitido. |

    accepted_project_extensions: [pdf, docx]
    accepted_defense_extensions: [pdf, pptx]
    max_file_size_mb: 20
    legacy_doc_policy: incident

Si la presentación se ha preparado en Canva, Google Presentaciones u otra
aplicación, deberá archivarse una copia exportada en PDF o PPTX. Un enlace
puede guardarse como dato complementario, pero no debe ser el único soporte.

<!-- ancla: decisiones#6-identificacion -->
## 6. Política de identificación

No estableceremos un porcentaje de parecido para asignar automáticamente un
trabajo. La identificación será determinista y basada en evidencias
acumuladas. La normalización puede ignorar mayúsculas, tildes, guiones,
comas, dobles espacios y el orden «apellidos, nombre».

| Prioridad | Condición | Resultado |
|---|---|---|
| 1 | Identificador exacto de CESUR o metadato fiable disponible. | Asignación automática. |
| 2 | Nombre completo normalizado y único dentro del curso y comunidad esperados. | Asignación automática. |
| 3 | Nombre más al menos un apellido, candidato único y portada compatible. | Asignación automática. |
| 4 | Nombre parcial sin confirmación, varios candidatos o datos insuficientes. | Incidencias. |
| 5 | Contradicción entre identificador, nombre, portada o matrícula. | Incidencias siempre. |

**Configuración.** Usar `identification_policy: deterministic`. No aplicar
coincidencia difusa para resolver automáticamente un caso ambiguo.

<!-- ancla: decisiones#7-versiones -->
## 7. Versiones y duplicados

| Situación | Tratamiento |
|---|---|
| Mismo archivo y mismo hash | Registrar `DUPLICATE_EXACT`, no crear un nuevo análisis, no generar coste API y no sobrescribir el original. Mostrar aviso no bloqueante. |
| Archivo diferente para la misma fase | Conservar como `v02`, `v03`, etc.; marcar `VERSION_CONFLICT` y detener el análisis nuevo hasta que Marcos elija la versión válida. |
| Versión seleccionada | Marcarla como vigente. Las anteriores pasan a sustituida o histórica, pero nunca se eliminan. |

Esta política permite detectar una repetición sin perder información. Si la
segunda versión es la correcta, no se obliga al alumno a entregar por tercera
vez: Marcos puede validarla directamente.

<!-- ancla: decisiones#8-retencion -->
## 8. Retención y limpieza

No habrá borrado automático de proyectos, versiones, informes o evidencias.
Todo se conserva hasta autorización expresa de Marcos.

    retention_policy: manual_hold
    automatic_deletion: false
    delete_after_days: null

Al terminar el curso, la carpeta activa se moverá o copiará a
`99_ARCHIVO_CERRADO/2026-2027`, se comprobará la copia de seguridad local y
se conservará la trazabilidad necesaria. Cualquier eliminación posterior será
manual, explícita y ajena al flujo automático.

<!-- ancla: decisiones#9-carpetas -->
## 9. Carpetas del expediente

La interpretación general es correcta. Se confirman las ocho carpetas:

    ALU-260001/
      00_FICHA/  01_TEMA/  02_ENTREGA_1/  03_ENTREGA_2/  04_ENTREGA_3/
      05_ENTREGA_FINAL/  06_DEFENSA/  07_HISTORICO/

| Bloque | Función |
|---|---|
| TEMA | Propuesta y validación previa. No es una entrega evaluable. |
| ENTREGA_1 a ENTREGA_FINAL | Las cuatro entregas evaluables y acumulativas del proyecto. |
| DEFENSA | Presentación, observaciones, preguntas y valoración del tribunal. |
| FICHA e HISTORICO | Administración interna, decisiones, versiones y trazabilidad. |

Aunque el alumno suba la presentación junto con la entrega final en CESUR, el
sistema separará por tipo: el proyecto irá a `05_ENTREGA_FINAL` y la
presentación a `06_DEFENSA`.

<!-- ancla: decisiones#10-entregas -->
## 10. Proceso de entregas

Las muestras históricas no sustituyen la lógica oficial del curso. El flujo
real parte de la validación del tema y continúa con cuatro entregas
acumulativas.

| Fase | Tratamiento académico y del sistema |
|---|---|
| Tema | Registro y validación de la propuesta; no puntúa como entrega. |
| Entrega 1 | Revisión ligera y feedback breve sobre introducción, justificación, objetivos, índice, encuadre inicial y adecuación al ciclo/modalidad. |
| Entrega 2 | Primer análisis acumulativo completo: documento actual + Entrega 1 + feedback anterior. |
| Entrega 3 | Análisis acumulativo del desarrollo y comprobación de aplicación del feedback de la Entrega 2. |
| Entrega final | Revisión definitiva del proyecto completo, requisitos mínimos, coherencia, cierre y preparación de la defensa. |

**Entrega 1.** No queda sin devolución. Genera un feedback breve y
orientador, pero no requiere la profundidad ni el coste de las correcciones
acumulativas posteriores.

<!-- ancla: decisiones#11-fases-desconocidas -->
## 11. Banco P01-P09 y fases desconocidas

P01-P09 son muestras históricas para observar tipologías, calidad, formato,
profundidad y errores frecuentes. No definen el procedimiento de las entregas
del curso ni deben bloquear el piloto.

Para P01, P02, P04 y P09 no disponemos de una fase confirmada. La regla será:

- registrar `phase: UNKNOWN`;
- no utilizarlos en métricas o comparaciones sensibles a la fase;
- mantenerlos como pruebas generales de estructura, calidad y detección;
- no asumir E03 ni FINAL sin evidencia;
- no condicionar la implantación a resolver una información histórica que no
  está disponible.

En producción la fase siempre será conocida porque el archivo entrará por la
carpeta E01, E02, E03 o FINAL.

<!-- ancla: decisiones#12-semaforo -->
## 12. Semáforo oficial y «verde con alertas»

El Documento Maestro define cuatro estados oficiales: VERDE, ÁMBAR, ROJO y
GRIS. El gris representa un trabajo no evaluable o una incidencia
administrativa o técnica.

| Estado oficial | Uso |
|---|---|
| VERDE | Cumple la fase y puede avanzar; puede contener ajustes menores o alertas no bloqueantes. |
| ÁMBAR | Tiene base, pero requiere correcciones prioritarias antes de considerarse cerrado. |
| ROJO | Existe una carencia crítica o necesidad de reconducción. |
| GRIS | No evaluable: ausencia, fuera de plazo, archivo ilegible, formato bloqueado o incidencia sin resolver. |

«Verde con alertas» no será un quinto estado. Se implementará como VERDE
acompañado por alertas estructuradas o por un indicador complementario, por
ejemplo `alerts[]` o `borderline: true`. En el informe anterior utilizamos la
expresión como descripción operativa; esta aclaración conserva la jerarquía
del Documento Maestro.

**Decisión.** Mantener el enum de cuatro estados del Documento Maestro. El
calibrador puede añadir alertas o matices, pero no crear un color oficial
nuevo.

<!-- ancla: decisiones#13-estabilidad -->
## 13. Estabilidad, cifras y coste

Coincido en que una única cifra como 7/9 no debe utilizarse para ajustar el
sistema: existe variabilidad entre ejecuciones y perseguir un resultado
aislado sería calibrar contra ruido. Sin embargo, no activaremos dos análisis
completos para todos los trabajos por defecto.

Estrategia acordada:

- **Calibración:** ejecutar varias veces las muestras para medir estabilidad
  por semáforo, categoría y evidencia.
- **Producción:** una ejecución principal estructurada.
- **Verificación:** comprobar evidencias, coherencia, tono, nivel de
  exigencia y ausencia de notas en el feedback.
- **Segundo análisis completo:** solo cuando el caso sea fronterizo, la
  confianza sea baja, existan contradicciones, falten evidencias o Marcos lo
  solicite.
- **Comparación:** contrastar categorías, severidad y evidencias, no frases
  literales idénticas.

Antes de concluir que el coste no es un problema, el sistema deberá mostrar
modelo exacto, tokens, coste por análisis principal, coste por verificación,
coste de un segundo análisis, promedio por fase y proyección mensual y anual.

<!-- ancla: decisiones#14-migraciones -->
## 14. Cambios pendientes en Supabase

Confirmo que aplicaré los cuatro cambios de base de datos desde mi panel,
pero necesito recibir una guía mínima para hacerlo sin interpretar código ni
alterar el entorno equivocado.

Para cada cambio, indicar:

- nombre y finalidad;
- orden exacto de ejecución;
- SQL completo o acción exacta que debo aplicar;
- proyecto y entorno correctos;
- resultado esperado y forma de comprobarlo;
- procedimiento de reversión o recuperación si falla.

**Acción de Marcos.** Cuando reciba esas instrucciones, aplicaré las cuatro
migraciones desde el panel y devolveré la confirmación o las capturas
necesarias.

<!-- ancla: decisiones#15-cierre -->
## 15. Cierre

Con estas respuestas quedan resueltas las decisiones que dependían de mí. La
arquitectura construida es compatible con el funcionamiento docente y no
necesita replantearse. Los cambios consisten en completar la configuración,
corregir dos interpretaciones y mantener una separación clara entre
identificación local, anonimización y análisis académico.

Gracias por haber detenido el proceso antes de asumir reglas no escritas. Esa
prudencia es precisamente la que necesitamos para que el sistema pueda
automatizar mucho trabajo sin asignar un archivo a la persona equivocada ni
alterar la lógica académica. Con estas decisiones ya podemos continuar con el
piloto y revisar los primeros resultados sobre un circuito completo.

**Resultado esperado.** Un archivo descargado de CESUR entra con su nombre
original, se identifica localmente, recibe un ID único, se anonimiza antes
del análisis, queda archivado en la fase correcta y solo se detiene cuando
existe una duda real.
