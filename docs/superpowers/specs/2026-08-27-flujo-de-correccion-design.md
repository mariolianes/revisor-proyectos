# Diseño: Flujo de corrección de entregas

**Fecha:** 2026-08-27
**Estado:** Aprobado por el docente responsable
**Alcance:** desde que aparece el PDF de una entrega hasta que el docente marca que devolvió el feedback. No cubre la evaluación de la defensa, que el §6.5 del Maestro reserva a valoración humana.

---

## 1. Qué resuelve

Hoy el docente corrige a mano: abre el PDF, comprueba el formato, lo compara mentalmente con la entrega anterior, valora, redacta el feedback y lo devuelve por el Aula Virtual. Este subsistema le quita de encima lo mecánico y le deja lo que exige criterio, sin quitarle ninguna decisión.

El principio no cambia respecto al resto del sistema: **propone, evidencia y se detiene.** La valoración definitiva, la calificación y la comunicación al alumno siguen siendo suyas (§1 y §13 del Documento Maestro).

## 2. Cómo se parte

Dos entregas sucesivas, en este orden. La primera se termina y se usa sola.

**Parte A — La lectura objetiva.** Recepción, extracción, comprobaciones de formato, comparación evolutiva y ficha en Supabase. No depende del motor de análisis ni de la rúbrica oficial. Sirve desde el primer día: dice si un trabajo cumple el formato antes de que el docente se siente a leerlo.

**Parte B — El análisis y las salidas.** Las doce dimensiones, las evidencias, el informe interno, el borrador de feedback y la revisión observación por observación. Se apoya en la parte A.

Este documento diseña ambas; el plan de implementación se escribe primero para la A.

## 3. Decisiones que este diseño cierra

### D-009 · La carpeta se vigila, pero el docente confirma

El sistema observa `01_ALUMNOS/` y, cuando aparece un PDF nuevo, deduce del nombre del fichero de qué alumno y de qué fase es, y se lo presenta al docente para que lo confirme de un gesto o lo corrija.

**Contradice el §16.1 y el §21.2 del Documento Maestro**, que fijan recepción manual y sitúan la vigilancia de carpetas fuera de la primera versión. La decisión se toma con conocimiento de la contradicción y **obliga a corregir ambos apartados**.

Lo que la hace aceptable es que la vigilancia solo alcanza a *encontrar* el fichero. La identificación —de quién es y de qué fase— sigue siendo del docente, que es lo que el §18.2 protege con su condición de parada «alumno o fase no coinciden». Una recogida totalmente automática habría convertido esa parada de excepción en rutina, porque el nombre del fichero lo pone el alumno.

### D-004 · La devolución del feedback la hace el docente, y él la registra

El sistema entrega el texto aprobado listo para copiar. El docente lo pega en el Aula Virtual y vuelve a marcar que lo comunicó.

`COMUNICADO` significa exactamente eso: que el docente afirma haberlo enviado. El sistema no lo deduce ni lo comprueba, porque no puede. Encaja con el §21.2, que deja fuera el envío de correos y la integración con CESUR.

Con esto D-004 pasa de pendiente a decidida.

### D-002 · Sigue abierta, con fecha

El motor de análisis se construye contra el adaptador simulado. El puerto `ProveedorAnalisis` queda listo y cambiar de proveedor será cambiar una línea.

**Debe cerrarse antes del piloto con entregas reales.** Hasta entonces, ninguna entrega real pasa por ningún proveedor externo, lo que además satisface la condición del §19 sobre no usar entregas reales hasta confirmar las condiciones de tratamiento.

## 4. Arquitectura

Se apoya en lo que ya existe sin modificarlo: la capa de gobernanza, los criterios versionados y las nueve tablas.

```
┌──────────────────────────────────┐
│  Frontend                        │  React + Vite
│                                  │  bandeja · ficha · corregir
│                                  │  revisar · devolver
└────────────────┬─────────────────┘
                 │ HTTP, solo 127.0.0.1
┌────────────────▼─────────────────┐
│  Backend (FastAPI)               │
│                                  │
│  vigilancia/    detecta y propone│
│  extraccion/    PyMuPDF          │
│  evolucion/     compara versiones│
│  motor/         ProveedorAnalisis│
│  salidas/       informe y borrador│
│  persistencia/  las 9 tablas     │
└────────────────┬─────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼──────┐  ┌───────▼────────┐
│ 01_ALUMNOS/  │  │ Supabase       │
│ los PDF, en  │  │ fichas,        │
│ local        │  │ correcciones,  │
│              │  │ auditoría      │
└──────────────┘  └────────────────┘
```

### 4.1 El reparto, y por qué

**Lo medible se mide.** La extracción no pasa por ningún modelo de lenguaje: páginas reales de contenido excluyendo portada, índice y anexos; tipografía, cuerpo y estilo por fragmento; interlineado real; páginas en blanco y saltos artificiales; correspondencia entre los títulos del índice y los del documento con sus páginas; imágenes, resolución efectiva y superficie ocupada; y si el PDF procede de un procesador de textos o es un escaneado.

Todo eso son reglas del §6.2 del Maestro y de la lista de control del §6 del Índice comentado. Calculadas salen mejor, cuestan menos y son reproducibles. Preguntadas a un modelo salen peor y no se pueden auditar.

**La comparación evolutiva, igual.** Contraste del texto normalizado con la entrega anterior, para detectar lo que el §5.1 prohíbe: entregar solo los capítulos nuevos, repetir la versión anterior sin progreso real, o eliminar contenido ya validado.

**Lo que exige criterio se razona.** Solo eso llega al motor: valoración de las dimensiones activas, localización de evidencias, distinción entre hecho, inferencia y duda, priorización y redacción de las dos salidas.

### 4.2 La vigilancia propone, nunca decide

El vigilante lee el nombre del fichero y lo contrasta con la convención del §15.3 (`CODIGO_CICLO_FASE_FECHA_VERSION.ext`). De ahí saca una propuesta: este alumno, esta fase.

Si el nombre no encaja con el patrón, o el código no corresponde a ningún alumno registrado, o la fase no es la que toca según el estado del proyecto, **no adivina**: presenta la ficha en blanco para que la rellene el docente. Es la condición de parada del §18.2 convertida en interfaz.

El fichero **nunca se mueve, ni se renombra, ni se modifica.** El §18.1 lo exige y aquí se cumple leyendo y nada más.

### 4.3 Dónde vive la carpeta de alumnos

`01_ALUMNOS/` **está fuera del repositorio, y tiene que estarlo.** La regla R6 prohíbe que un PDF entre en el árbol versionado, y el hook de pre-commit lo bloquea: si la carpeta viviera dentro, el primer trabajo que llegara impediría cualquier commit.

Su ubicación se configura en el fichero de entorno local, que ya está en `.gitignore`, y por omisión se sitúa junto al repositorio, no dentro. El backend valida al arrancar que la ruta configurada existe, que es legible, y que **no** está bajo el directorio del repositorio; si lo está, se niega a vigilar y lo dice, en lugar de crear una trampa que reventaría al primer commit.

Los informes y borradores generados se guardan junto a la entrega que los originó, siguiendo la estructura del §15.2, y por el mismo motivo tampoco entran en el repositorio.

## 5. El flujo

Los siete estados del §16.1:

```
RECIBIDO → ANALIZADO → BORRADORES_GENERADOS → EN_REVISION_DOCENTE → APROBADO → COMUNICADO
    └──────────────────────────► BLOQUEADO
```

1. **Recepción.** Aparece un PDF; el sistema propone identificación; el docente confirma o corrige. Estado `RECIBIDO`.
2. **Validación técnica y administrativa.** Que el PDF abra, que sea legible, que el alumno y la fase correspondan, que esté dentro de plazo.
3. **Extracción.** Las comprobaciones objetivas del §4.1.
4. **Comparación evolutiva**, cuando existe entrega anterior.
5. **Análisis.** Solo las dimensiones activas para esa fase y modalidad, según `criteria/`.
6. **Síntesis.** Fortalezas, prioridades, alertas y semáforo. Estado `ANALIZADO`.
7. **Generación de las dos salidas.** Estado `BORRADORES_GENERADOS`.
8. **Revisión docente**, observación por observación. Estado `EN_REVISION_DOCENTE`.
9. **Cierre.** Estado `APROBADO`, y `COMUNICADO` cuando el docente marca que devolvió.

### 5.1 Las paradas

`BLOQUEADO` es una salida legítima y prevista, no un fallo. Se alcanza en las condiciones del §18.2, y ninguna se resuelve automáticamente:

| Condición | Respuesta |
|---|---|
| PDF ilegible, vacío o protegido | Bloquear y pedir archivo válido |
| Alumno o fase no coinciden | Bloquear y pedir identificación correcta |
| Entrega fuera de plazo | Marcar GRIS y 0; no corregir salvo instrucción docente |
| Criterios en conflicto | Alerta de resolución; se detiene el juicio afectado |
| Falta el feedback anterior cuando es necesario | Continuar sin comparación **solo con autorización expresa** |
| Indicio crítico de autoría | Nota interna prudente y escalar al profesor |
| Error técnico | Conservar la entrada, registrar el error, no crear salida aprobable |

## 6. Las dos salidas

Ambas internas. El borrador dirigido al alumno **nunca se envía ni se publica automáticamente** (§11).

**El informe técnico** lleva lo que fija el Anexo C: identificación codificada, control administrativo, resumen ejecutivo, valoración por dimensión con evidencia y prioridad, continuidad respecto al feedback anterior, dudas que requieren criterio docente, y resultado provisional.

**El borrador de devolución** sigue el Anexo D: apertura que reconozca el trabajo real sin elogio automático, una o dos fortalezas concretas, las correcciones prioritarias ordenadas, orientación sobre cómo mejorar sin redactar el contenido, qué se espera en la fase siguiente, y cierre proporcional.

**Control de coherencia**, del §17.2: si el informe marca una carencia crítica, el borrador no puede describir el proyecto como correcto; si el proyecto está sólido, el borrador no se infla con mejoras menores. Se comprueba antes de presentar ambas salidas.

**Y el borrador nunca contiene la nota interna ni las observaciones personales del docente.** La separación se aplica en el backend, no por convención en la interfaz.

## 7. Lo que este subsistema no podrá hacer todavía

**No habrá nota propuesta.** Las ponderaciones están marcadas `PENDIENTE_OFICIAL` y la regla R3 impide sustituir un dato pendiente por una estimación. Habrá dimensiones valoradas, evidencias, prioridades y semáforo; el número llega con la programación didáctica.

Esto no es una limitación técnica que se pueda rodear: es la regla funcionando. Un sistema que inventara la nota sería peor que uno que no la da.

**El análisis irá contra el simulador** hasta que se cierre D-002.

**Y sigue fuera, conforme al §21.2:** corrección por lotes, envío de correos, integración con el Aula Virtual, panel estadístico, comparación entre alumnos, detección concluyente de plagio o IA, y evaluación automática de la defensa.

## 8. Privacidad

- El PDF y el texto del trabajo **no se almacenan** en Supabase, conforme a D-001. De la entrega se guardan su nombre y su huella.
- La anonimización se realiza en el backend antes de cualquier envío al proveedor de análisis, y es una operación explícita y verificable.
- Una evidencia citada no pasa de 1.500 caracteres. La base de datos ya lo impone.
- La nota interna y las observaciones personales no viajan nunca al borrador.
- Ninguna prueba se ejecuta contra entregas reales de alumnos.

## 9. Estrategia de pruebas

- **Extracción:** contra PDFs sintéticos con desviaciones conocidas —cuerpo alterado, páginas en blanco, índice descuadrado, imágenes sobredimensionadas, escaneado—. Verificación exacta.
- **Vigilancia:** nombres que encajan, nombres que no, alumno inexistente, fase que no corresponde. Cada uno debe llevar a la ficha en blanco, nunca a una identificación inventada.
- **Comparación evolutiva:** entrega idéntica, solo capítulos nuevos, contenido eliminado, progreso real.
- **Paradas:** una prueba por cada condición del §18.2.
- **Motor:** contra el adaptador simulado, sin coste ni red.
- **Coherencia de salidas:** que un informe con carencia crítica no pueda acompañar a un borrador que diga que todo está bien.

## 10. Entregables

**Parte A:** vigilancia, extracción, comparación evolutiva, persistencia de la ficha y la entrega, y las pantallas de bandeja y ficha.

**Parte B:** motor con adaptador simulado, valoración por dimensiones, generación de las dos salidas, revisión observación por observación, y la pantalla de devolución.
