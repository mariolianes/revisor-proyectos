# Los informes por centro y el conflicto de versión, con pantalla

**Fecha:** 2026-09-07
**Autor:** Marcos / colaborador técnico

## Que cambia

Dos cosas que estaban construidas, probadas y a las que el docente no podía
llegar:

- **La pestaña Informes.** El módulo del punto 7 componía cobertura, estado
  del proceso, semáforos y coste desde hacía días, y no tenía puerta.
- **El botón para elegir versión**, en la ficha de una entrega con conflicto.

## Por que

El segundo era peor de lo que parece. Si al docente le llegaban dos versiones
de la misma entrega, el análisis **se detenía** -correcto, es su regla del §7-
y **no tenía forma de desbloquearlo**: la entrega se quedaba muerta y solo se
podía resolver tocándole la base de datos.

Un endpoint sin pantalla no es una funcionalidad a medias: para quien usa el
programa, es una funcionalidad que no existe.

## Tres cosas que la pantalla dice y conviene que diga

- **Que ninguna versión se elimina.** Es lo que le permite elegir sin miedo a
  perder la otra.
- **Por qué está detenido**: analizar la que luego descarte cuesta dinero y
  produce un informe que habría que tirar.
- **Separa lo que propuso el sistema de lo que confirmó él.** En el bloque de
  semáforos son dos recuentos distintos, no uno: la propuesta del sistema no
  es una decisión.

Y en el informe, dos que vienen de decisiones ya tomadas: el aviso de grupo
pequeño se pinta con la tinta `senal` -es algo que espera que él lo lea-, y
los análisis sin coste calculable se dicen con su número y con el motivo, «el
sistema no inventa un precio».

## Fuente que lo respalda

`decisiones#7-versiones` para el conflicto, y el documento de arquitectura
para el informe por centro. Ninguna nueva.

## Que arrastra

`frontend/src/paginas/Informes.tsx` (nueva),
`frontend/src/paginas/Ficha.tsx`, `frontend/src/App.tsx`,
`frontend/src/lib/api.ts`, `frontend/src/lib/tipos.ts`, y sus pruebas.
Ningún cambio en el backend: ya estaba todo.

## Correcciones cerradas afectadas

Ninguna.
