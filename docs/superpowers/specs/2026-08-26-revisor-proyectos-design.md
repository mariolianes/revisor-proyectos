# Diseño: Revisor de Proyectos Intermodulares

**Fecha:** 2026-08-26
**Estado:** Aprobado por el docente responsable
**Alcance de este documento:** cimientos de gobernanza, estructura documental y esqueleto técnico. No cubre el motor de corrección, que se especificará cuando existan la programación didáctica y la rúbrica oficiales.

---

## 1. Qué es este sistema

Un asistente local de corrección y seguimiento de Proyectos Intermodulares de Formación Profesional. Lee la entrega de un alumno, la contrasta con los criterios vigentes y produce dos salidas internas: un informe técnico para el docente y un borrador de feedback para el alumno.

El sistema no califica ni comunica. Propone, evidencia y se detiene. La valoración definitiva, la calificación y cualquier comunicación al alumno pertenecen siempre al profesor.

Este principio no es una preferencia de diseño: es la decisión central del Documento Maestro (§1) y condiciona toda la arquitectura que sigue.

## 2. De dónde sale todo

Existen tres documentos maestros previos a este sistema, redactados por el docente:

| Documento | Función | Destinatario |
|---|---|---|
| Documento Maestro | Cómo se corrige: dimensiones, matriz, semáforo, salidas | Interno |
| Índice comentado | Qué debe contener cada apartado del proyecto | Alumnado |
| Guía de desarrollo | Cómo se trabaja el curso: entregas, plazos, feedback | Alumnado |

Los tres se solapan deliberadamente, y ese solape es el riesgo principal del proyecto: si un criterio cambia en un documento y no en los otros, el sistema corregirá con un criterio que ya no es el del profesor. La capa de gobernanza de la sección 5 existe para impedirlo.

## 3. Decisiones de arquitectura

Tres decisiones se han tomado en la sesión de diseño y quedan registradas en `docs/decisions.md`.

### D-001 · Supabase como persistencia

El Documento Maestro (§19, §21.1) especifica un sistema estrictamente local. Se adopta Supabase para persistencia, historial y trazabilidad, lo que contradice esa especificación.

La decisión se toma con conocimiento de la contradicción y **obliga a corregir el §19 y el §21.1 del Documento Maestro**, no a ignorarlos. Se acota su alcance así:

- **Sí se almacena:** fichas de alumno y proyecto, criterios versionados, correcciones por dimensión, evidencias citadas, semáforo, nota interna, feedback aprobado y registro de auditoría. Una evidencia citada es la referencia al apartado y la página, más un fragmento literal de **1.500 caracteres como máximo**, holgura suficiente para reproducir un párrafo completo y justificar con solvencia cualquier observación. El límite es una restricción del sistema, verificada en el backend, no una recomendación: existe para que la suma de evidencias no acabe reconstruyendo el trabajo entero dentro de la base de datos.
- **No se almacena, ni en Storage ni en tablas:** el PDF de la entrega, ni el texto completo del trabajo del alumno.

### D-002 · OpenAI tras adaptador intercambiable

El análisis académico lo realiza la API de OpenAI. El backend define un puerto único `ProveedorAnalisis` con implementaciones sustituibles sin tocar el resto del sistema.

Esta decisión fija el proveedor, no su implementación. En esta fase solo se construye el puerto y el adaptador simulado; el adaptador de OpenAI se implementa cuando exista la matriz de criterios cerrada (véase §10).

Característica del sistema, a efectos de arquitectura: el texto de la entrega, ya anonimizado según §4.2, se transmite a OpenAI para su análisis. No se almacena allí ni en Supabase, pero sí sale del equipo durante el procesamiento. Quien mantenga este sistema debe conocerlo para no alterar por descuido el circuito de datos.

La clave de la API reside únicamente en el backend local. Nunca en el frontend.

### D-003 · PyMuPDF para extracción

Se elige PyMuPDF por ser la herramienta más capaz para las comprobaciones objetivas que exigen el §6.2 del Maestro y la lista de control del Índice comentado.

Limitación registrada: PyMuPDF se distribuye bajo AGPL. Para uso interno no supone restricción. Una eventual distribución o comercialización exigiría licencia comercial, o migrar a pdfplumber, de licencia permisiva y algo menos preciso en tipografía.

### D-004 · Canal de devolución del feedback — PENDIENTE

El §10 del Maestro establece que el alumno recibe feedback pero no necesariamente la calificación numérica de cada fase. El sistema respeta esa separación, pero no está definido **cómo** llega el feedback aprobado al alumno ni qué marca exactamente el estado `COMUNICADO`: si el docente lo copia manualmente en el Aula Virtual y lo registra después, o si existe algún paso intermedio.

Queda abierta y debe cerrarse antes de implementar la transición a `COMUNICADO`. Hasta entonces, ese estado se modela pero no se activa.

## 4. Arquitectura

```
┌─────────────────────┐
│  Frontend           │  React + Vite, en localhost
│                     │  ficha · análisis · revisión · aprobación
└──────────┬──────────┘
           │ HTTP
┌──────────▼──────────┐
│  Backend            │  FastAPI, en el equipo del docente
│                     │
│  extraccion/        │  PyMuPDF: evidencia objetiva
│  criterios/         │  carga y valida los YAML vigentes
│  motor/             │  puerto ProveedorAnalisis
│  dominio/           │  las 7 entidades del §15.1
└─────┬───────────┬───┘
      │           │
      │           └──────────────► OpenAI  (texto en tránsito)
      │
┌─────▼───────────────┐
│  Supabase           │  Postgres + RLS
│                     │  resultados, historial, auditoría
└─────────────────────┘
```

### 4.1 Reparto de responsabilidades

La división obedece a un criterio único: **lo que es medible se mide, lo que exige criterio se razona.**

**Extracción (PyMuPDF, determinista).** Todo lo que se puede comprobar sin juicio: páginas reales de contenido excluyendo portada, índice y anexos; tipografía, cuerpo y estilo por fragmento; interlineado real; páginas en blanco y saltos artificiales; correspondencia entre los títulos del índice y los del documento con sus páginas; imágenes, resolución efectiva y superficie ocupada; si el PDF procede de un procesador de textos o es un escaneado.

Estas comprobaciones no se delegan al modelo de lenguaje. Salen peor, cuestan dinero y no son reproducibles.

**Comparación evolutiva (Python, determinista).** Contraste entre la entrega actual y la anterior sobre texto normalizado, para detectar lo que el §5.1 prohíbe: entregar solo capítulos nuevos, repetir la versión anterior sin progreso real, o eliminar contenido ya validado.

**Análisis académico (modelo de lenguaje).** Solo lo que exige criterio: valoración de las dimensiones activas, localización de evidencias, distinción entre hecho, inferencia y duda, priorización de carencias y redacción de las dos salidas.

### 4.2 Anonimización

El PDF que entrega el alumno lleva su nombre en la portada. El §19 exige trabajar con códigos anónimos. La supresión de datos identificativos se realiza en el backend, antes de cualquier envío al proveedor de análisis, y es una operación explícita y verificable, no un efecto colateral.

## 5. Gobernanza

Siete reglas, derivadas de la jerarquía de fuentes del §14.1 del Maestro y de su regla de conflicto: una fuente inferior no puede contradecir a una superior.

**R1 · Ningún criterio sin origen.** Cada entrada de los YAML de `criteria/` lleva un campo `fuente` que apunta a la sección exacta del Markdown de la que procede. Sin él, el verificador falla y el commit no pasa.

**R2 · La prosa manda.** El YAML se deriva del Markdown, nunca al revés. Cada sección del Markdown lleva un hash; si cambia sin que se revise su YAML derivado, el verificador señala la desincronización.

**R3 · Lo pendiente se marca, no se inventa.** Los criterios aún no publicados llevan `estado: PENDIENTE_OFICIAL`. Si el sistema necesita uno para emitir un juicio, se detiene, conforme al §18.2. Nunca lo sustituye por una estimación razonable.

**R4 · Los criterios se versionan y se congelan.** Cada corrección registra con qué versión de criterios se realizó. Una versión ya empleada en una corrección aprobada no se modifica: se crea la siguiente. Esto permite reconstruir, tiempo después, con qué criterio exacto se corrigió a un alumno.

**R5 · Un fichero por cambio.** Todo cambio de criterio deja constancia en `docs/changes/`: qué cambia, por qué, qué fuente lo respalda, qué YAML arrastra y a qué correcciones cerradas afecta.

**R6 · Nada personal entra en el repositorio.** Ni PDFs, ni texto de entregas, ni nombres de alumnos. Los tests se ejecutan contra el banco de calibración anonimizado del §20. Un hook de pre-commit bloquea la entrada de PDFs y de patrones con apariencia de dato identificativo.

**R7 · Las reservas del profesor son bloqueos reales.** Las nueve decisiones del §13 se implementan como estados que el backend no puede atravesar por sí mismo: aprobar una nota, valorar autoría, autorizar un cambio de tema, dar por apto un documento final, comunicar feedback. El sistema propone y se detiene.

### 5.1 Procedimiento de cambio de criterio

```
1. Editar   docs/maestro/<documento>.md          la prosa
2. Ajustar  criteria/vAAAA-AAAA/<fichero>.yaml   el derivado
3. Escribir docs/changes/AAAA-MM-DD-<asunto>.md
4. Anotar   docs/decisions.md                    si es una decisión, no un ajuste
5. Ejecutar tools/verificar_gobernanza.py        pasa, o no hay commit
```

## 6. Modelo de datos

Las siete entidades del §15.1 del Maestro, en Postgres con RLS activo:

| Entidad | Contenido esencial |
|---|---|
| `alumno` | código anónimo, ciclo, grupo, observaciones docentes |
| `proyecto` | título, tema validado, modalidad, estado, versión de criterios |
| `entrega` | fase, fecha, plazo, versión, estado administrativo |
| `correccion` | dimensiones, evidencias, semáforo, nota propuesta, decisiones |
| `feedback` | borrador, versión aprobada, fecha, estado de comunicación |
| `defensa` | fecha, soporte, valoración manual, preguntas, nota |
| `registro` | usuario, acción, versión, fecha, cambio |

Dos campos no viajan nunca al frontend del alumno ni al borrador de feedback: la nota interna y las observaciones personales del docente. La separación se aplica en el backend, no por convención en la interfaz.

## 7. Estados y paradas

Los siete estados del §16.1 gobiernan cada entrega:

```
RECIBIDO → ANALIZADO → BORRADORES_GENERADOS → EN_REVISION_DOCENTE → APROBADO → COMUNICADO
    └────────────────────────► BLOQUEADO
```

`BLOQUEADO` no es un error del sistema: es una salida legítima y prevista. Se alcanza en las condiciones del §18.2 —PDF ilegible, alumno o fase que no corresponden, entrega fuera de plazo, criterios en conflicto, indicio de autoría, fallo técnico— y ninguna de ellas se resuelve automáticamente.

De `EN_REVISION_DOCENTE` a `APROBADO` solo se pasa por acción explícita del profesor sobre cada observación: aceptar, editar o descartar.

## 8. Manejo de errores

| Situación | Respuesta |
|---|---|
| PDF ilegible, vacío o protegido | `BLOQUEADO`, se conserva la entrada intacta |
| Criterio necesario `PENDIENTE_OFICIAL` | Se detiene ese juicio concreto, no la corrección entera |
| Criterios en conflicto | Alerta de resolución; el juicio afectado se suspende |
| Fallo del proveedor de análisis | Se conserva la entrada, se registra el error, no se genera salida aprobable |
| Falta la entrega anterior | Continúa sin comparación evolutiva, dejando constancia |

Regla transversal: **el archivo entregado no se modifica ni se sobrescribe nunca.**

## 9. Estrategia de pruebas

- **Extracción:** contra PDFs sintéticos construidos para el caso, con desviaciones conocidas —cuerpo de letra alterado, páginas en blanco, índice descuadrado, imágenes sobredimensionadas—. Verificación exacta, sin tolerancia.
- **Criterios:** validación de esquema, presencia obligatoria de `fuente`, coherencia entre Markdown y YAML.
- **Gobernanza:** el propio verificador tiene pruebas que confirman que detecta las infracciones de R1 a R6.
- **Motor:** contra el adaptador simulado, sin coste ni red.
- **Calibración (§20):** aplazada hasta disponer del banco anonimizado de 9 a 12 proyectos.

Ninguna prueba se ejecuta contra entregas reales de alumnos.

## 10. Qué queda fuera de esta fase

El motor de corrección no se implementa todavía. La razón la da el propio Maestro en el §22: la matriz de evaluación no puede cerrarse hasta que existan la programación didáctica y la rúbrica oficiales, que aún no están disponibles.

Construir ahora el motor significaría fijar ponderaciones y umbrales inventados que la normativa oficial probablemente desmienta en semanas. Lo que sí se construye es todo aquello sobre lo que la normativa no influye: la gobernanza, la estructura documental, la extracción objetiva y el esqueleto.

Aplazado igualmente, conforme al §21.2: vigilancia de carpetas, corrección por lotes, envío de correos, integración con el Aula Virtual, panel estadístico, comparación entre alumnos, detección concluyente de plagio o IA y evaluación automática de la defensa.

## 11. Entregables de esta fase

1. `CLAUDE.md` y `GOVERNANCE.md` con las reglas R1 a R7.
2. Los tres documentos maestros convertidos a Markdown, con secciones estables y hash.
3. `criteria/v2026-2027/` con lo estable destilado y lo pendiente marcado.
4. `docs/decisions.md` con D-001, D-002 y D-003.
5. `docs/PENDIENTE_OFICIAL.md` con el Anexo H.
6. `tools/verificar_gobernanza.py` operativo y con pruebas, más el hook de pre-commit que lo ejecuta y que bloquea la entrada de datos personales (R6).
7. Esqueleto de backend: dominio, carga de criterios, extracción con PyMuPDF, puerto de análisis con adaptador simulado.
8. Esqueleto de frontend y migraciones de Supabase con RLS.
9. `docs/changes/2026-08-26-fundacion-repo.md`.
