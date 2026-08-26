# El Documento Maestro recoge el circuito de datos real

**Fecha:** 2026-08-26
**Autor:** Marcos / colaborador técnico

## Que cambia

El §19 describía la privacidad dando por supuesto un sistema estrictamente
local. Ahora empieza declarando el circuito de datos real: qué se guarda en
Supabase, qué no se guarda en ninguna parte, qué límite tiene una evidencia
citada, qué sale hacia el proveedor de análisis y dónde viven las credenciales.

Se retira del §19 la viñeta «Guardar las credenciales técnicas en variables
seguras, nunca dentro de documentos o scripts compartidos», que presuponía un
sistema de scripts locales. La sustituye, dentro del circuito, «Las
credenciales técnicas residen en el backend local, nunca en el frontend».

El resto del §19 se conserva íntegro: códigos de alumno, supresión de datos
identificativos, separación de las observaciones personales, registro mínimo
del §19.1, copias de seguridad y la prohibición de usar entregas reales antes
de la calibración.

Se añade una sola frase que no es del docente: «Las cautelas de tratamiento se
mantienen íntegras:», que encabeza esa lista conservada. Es redacción nueva, y
solo de estructura: sin ella el apartado quedaba con dos listas de viñetas
seguidas sin rótulo y no se leía que la segunda sigue vigente. No altera
ningún criterio. Queda señalada aquí para que el docente la adopte como suya o
la cambie por la suya.

En el §21.1, la viñeta «Historial local sencillo y recuperación de errores»
pasa a ser dos: «Aplicación con interfaz web local, backend en el equipo del
docente y persistencia en Supabase (D-001)» e «Historial consultable y
recuperación de errores».

No cambia ningún criterio de `criteria/`. Ninguna entrada de la versión
v2026-2027 declara como fuente `maestro#19-privacidad` ni
`maestro#21-mvp-y-aplazadas`: el §19 y el §21 describen arquitectura y alcance,
no criterio de corrección. Por eso R2 no protesta y el sellado no cambia el
registro de sincronía.

## Por que

La decisión D-001 adopta Supabase como persistencia. Contradice al Documento
Maestro, que es fuente superior, y la regla del §14.1 no admite que una fuente
inferior contradiga a una superior. La única salida legítima era corregir el
Maestro, no dejar la contradicción viva.

Además, un apartado de privacidad que describe un sistema que no existe es
peor que no tenerlo: nadie puede comprobar si el tratamiento real cumple lo
que el documento promete.

## Fuente que lo respalda

- Documento Maestro §14.1, jerarquía de fuentes y regla de conflicto.
- Decisión D-001 de `docs/decisions.md`, estado Validada, que declara
  expresamente que la contradicción obliga a corregir el §19 y el §21.1.

## Que arrastra

- `docs/maestro/01-documento-maestro.md` (§19 y §21.1).
- `criteria/v2026-2027/.sincronia.json`: se vuelve a sellar por disciplina,
  aunque ninguna ancla sellada cambia.

Queda pendiente, fuera del alcance de D-001: la etapa 4 de la hoja de ruta del
§22 sigue diciendo «Aplicación mínima local». D-001 acota su corrección al §19
y al §21.1, así que esa fila no se toca aquí. El docente decide si la etapa 4
debe redactarse de nuevo o si describe bien un hito intermedio ya superado.

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema, y el
cambio no toca criterio alguno.
