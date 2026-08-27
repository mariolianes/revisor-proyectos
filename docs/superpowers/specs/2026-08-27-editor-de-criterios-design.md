# Diseño: Editor de criterios

**Fecha:** 2026-08-27
**Estado:** Aprobado por el docente responsable
**Alcance:** la aplicación con la que el docente lee y modifica sus documentos normativos sin salirse del procedimiento de gobernanza. No cubre el flujo de corrección de entregas ni la persistencia en Supabase, que van en un diseño aparte.

---

## 1. El problema que resuelve

La capa de gobernanza construida el 2026-08-26 funciona, pero se maneja desde una consola: editar un `.md`, acordarse de mirar qué criterios derivan de él, escribir un fichero de cambio con cinco secciones obligatorias, ejecutar `--sellar`, comitear. Son seis pasos que hay que recordar en el orden correcto, y el sistema solo protesta cuando ya te has saltado uno.

Un procedimiento que se recuerda se olvida. Este editor lo convierte en el camino natural: la pantalla te lleva por él sin que tengas que saberlo.

**La regla que gobierna todo el diseño:** el editor nunca ofrece una manera de cambiar un criterio que se salte las reglas R1 a R6. No hay modo experto, no hay botón de guardar sin más, no hay "recordármelo luego". La comodidad está en que el camino correcto sea cómodo, no en que exista un atajo.

## 2. Qué no hace

- **No reimplementa ninguna regla.** El backend invoca `tools/gobernanza`, que ya existe y está probado. Si una regla cambia, el editor hereda el cambio sin tocarse.
- **No decide cómo un cambio de prosa afecta a un criterio** salvo cuando la correspondencia es literal (véase §5.2). En los demás casos muestra los criterios afectados y espera al docente.
- **No corrige entregas.** Otro subsistema.
- **No se publica en internet.** Escribe en el disco y ejecuta `git`: se sirve en `127.0.0.1` y nada más.

## 3. Arquitectura

```
┌──────────────────────────────┐
│  Frontend                    │  React + Vite + shadcn/ui
│                              │  Documentos · Editor · Estado · Pendientes
└──────────────┬───────────────┘
               │ HTTP, solo 127.0.0.1
┌──────────────▼───────────────┐
│  Backend (FastAPI)           │
│                              │
│  api/documentos.py           │  leer secciones y sus dependencias
│  api/edicion.py              │  la transacción de guardado
│  api/estado.py               │  las seis reglas, sus límites y lo pendiente
│  servicios/dependencias.py   │  qué criterio deriva de qué sección
│  servicios/propuesta.py      │  inferencia literal de valores
│  servicios/transaccion.py    │  escribir, verificar, sellar, comitear
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│  tools/gobernanza  (ya existe)│  R1-R6, sin modificar
│  docs/maestro/ · criteria/    │
└──────────────────────────────┘
```

El backend es una envoltura fina. Toda la autoridad sigue en `tools/gobernanza`.

## 4. Las cuatro pantallas

### 4.1 Documentos

Los tres documentos navegables por secciones. Junto a cada una, cuántos criterios la citan como `fuente`.

Ese número es información que hoy no está en ninguna parte y que cambia cómo se lee el documento. El §8 aparece como *citada por 12 criterios*; el §5, como *citada por ninguno*. Lo segundo significa que se puede editar sin que ninguna regla se entere, y el docente merece saberlo antes de editarlo, no después.

### 4.2 Editor

El texto de la sección a la izquierda, con medida de línea de lectura. A la derecha, los criterios que derivan de ella con su valor actual.

Al modificar el texto, el panel derecho marca qué criterios podrían verse afectados. Al guardar arranca la transacción de §5.

### 4.3 Estado

Las seis reglas con su resultado actual, y para cada una **qué vigila y qué no**. Los límites conocidos —que R2 no mira las secciones que ningún criterio cita, que ninguna regla comprueba el orden de edición, que la lista negra de R3 es corta, que hoy ningún criterio cita la Guía— salen en pantalla, no enterrados en `GOVERNANCE.md`.

Una regla que promete más de lo que hace es peor que una regla que no existe, porque genera confianza donde no la hay.

### 4.4 Pendientes

Las entradas de `docs/PENDIENTE_OFICIAL.md` con qué bloquea cada una. Cuando llegue la programación didáctica, esta pantalla dice qué desbloquea.

## 5. La transacción de guardado

El corazón del editor. O se completa entera, o el repositorio queda exactamente como estaba.

### 5.1 Pasos

1. **Detectar dependencias.** Qué criterios citan la sección editada.
2. **Proponer.** Para cada criterio, si la correspondencia es literal, proponer el valor nuevo. Si no, marcarlo como *revisar a mano*.
3. **Confirmar criterio a criterio.** El docente acepta, corrige o descarta cada propuesta. Nada se aplica sin su gesto.
4. **Pedir motivo y fuente.** Dos campos obligatorios: qué justifica el cambio y qué fuente de la jerarquía del §14.1 lo autoriza. Sin ellos no hay guardado — es el contenido que R5 exige.
5. **Escribir.** Prosa primero, YAML después. El orden importa y es el que R2 presupone.
6. **Generar el documento de cambio** en `docs/changes/`, con sus cinco secciones.
7. **Verificar.** Ejecutar las seis reglas.
8. **Sellar** el registro de sincronía.
9. **Comitear** con un mensaje que nombra el cambio.

### 5.2 Qué se puede inferir y qué no

Una propuesta automática solo se ofrece cuando el valor del criterio **aparece literalmente en el texto de la sección que lo respalda** y el cambio lo modifica de forma inequívoca. En la práctica: números y valores citados textualmente, como el mínimo de páginas o el cuerpo de letra.

Todo lo demás —cambiar la redacción de una dimensión, reordenar una matriz, añadir una condición— se marca *revisar a mano*. El editor enseña el criterio, el texto viejo y el nuevo, y espera.

Inferir de más aquí sería exactamente lo que R1 existe para impedir: un criterio cuyo valor nadie decidió conscientemente.

### 5.3 Si algo falla

Cualquier fallo entre los pasos 5 y 9 **revierte todo**: los ficheros vuelven a su contenido anterior y no queda nada a medias ni ningún commit. El editor muestra qué regla saltó, sobre qué fichero y qué dice su mensaje —el mismo texto que imprime el verificador, que ya está escrito para que lo lea un docente y no un programador—.

Un guardado a medias es peor que un guardado fallido: deja el repositorio en un estado que nadie sabe interpretar, y es justo lo que la gobernanza existe para evitar.

### 5.4 Concurrencia

Un solo usuario, un solo proceso. Antes de escribir, la transacción comprueba que el árbol de trabajo está limpio y que `HEAD` no se ha movido desde que se cargó la sección. Si algo cambió por fuera, se aborta y se pide recargar.

## 6. Seguridad

El backend escribe en el disco y ejecuta `git`. Por tanto:

- Escucha únicamente en `127.0.0.1`. Nunca en `0.0.0.0`.
- Toda ruta recibida del cliente se valida contra la lista de ficheros de `docs/maestro/` y `criteria/`. No se acepta una ruta arbitraria.
- No hay endpoint que ejecute un comando de git formado con datos del cliente.
- El editor no muestra ni escribe datos de alumnos: no los toca.

## 7. Estrategia de pruebas

- **Detección de dependencias y propuesta:** contra un repositorio temporal construido en el test, con secciones y criterios inventados.
- **La transacción:** el caso feliz, y sobre todo los de fallo. Un test por cada punto en el que puede romperse, comprobando en cada uno que el repositorio queda **byte a byte** como estaba y sin commits nuevos.
- **Reglas:** no se vuelven a probar. Ya tienen sus tests; aquí solo se comprueba que el backend las invoca y transmite su resultado.
- **Frontend:** pruebas de los componentes que deciden algo —el panel de dependencias, el formulario de motivo y fuente—. No de la maquetación.

Ninguna prueba se ejecuta contra el repositorio real ni escribe en él.

## 8. Estética

Suizo editorial. Los documentos que edita son normativos y deben leerse como tales.

- Rejilla estricta; el texto del documento a medida de línea de lectura, nunca a todo lo ancho.
- Una familia tipográfica, jerarquía por tamaño y peso. Monoespaciada solo para el YAML y los identificadores.
- Negro sobre blanco roto. **Una sola tinta**, reservada a señalar la relación entre una sección y los criterios que derivan de ella, que es la única cosa que el docente no puede deducir mirando.
- Sin sombras, sin tarjetas flotantes, sin degradados, sin animación decorativa.
- Componentes de shadcn/ui, con esa piel encima.

## 9. Entregables

1. Backend: los tres módulos de API y los tres de servicios, con sus pruebas.
2. Frontend: las cuatro pantallas y los componentes que las sirven.
3. Un `.cmd` en la raíz que levante el backend en `127.0.0.1:8000`, sirva el frontend ya compilado desde el propio FastAPI y abra el navegador. Una sola pieza que arrancar, no dos.
4. Documentación de puesta en marcha en el `README.md`.
