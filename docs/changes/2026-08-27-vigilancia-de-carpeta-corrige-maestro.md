# El Documento Maestro recoge la recepción asistida de entregas

**Fecha:** 2026-08-27
**Autor:** Marcos / colaborador técnico

## Que cambia

El §16 describía la recepción como manual: «El docente coloca o selecciona el
archivo y la ficha. La primera versión no vigila carpetas automáticamente.»
Ahora describe recepción asistida: el sistema vigila la carpeta de entregas y,
al aparecer un archivo nuevo, propone alumno y fase deducidos de su nombre; el
docente confirma o corrige; si el nombre no permite deducirlos, no se adivinan.

En el §21.1 se añade una viñeta: «Vigilancia de la carpeta de entregas, con
identificación confirmada por el docente en cada archivo (D-009)».

En el §21.2, la viñeta «Vigilancia automática de carpetas» se sustituye por
«Recogida automática de entregas sin confirmación del docente. La carpeta se
vigila (D-009), pero de quién es cada archivo y a qué fase corresponde lo
decide siempre una persona.» Lo que queda fuera de esta versión no es la
vigilancia: es que el sistema identifique al alumno por su cuenta.

No cambia nada más. En particular:

- El §16.1 no se toca. `COMUNICADO` ya decía «El docente ha registrado que
  devolvió el feedback», que es exactamente lo que cierra la decisión D-004.
- El §18.1 no se toca. «No modificar ni sobrescribir el archivo entregado»
  sigue vigente y la vigilancia lo respeta: lee el archivo y nada más, sin
  moverlo ni renombrarlo.
- El §18.2 no se toca. La condición de parada «alumno o fase no coinciden» es
  precisamente lo que la confirmación docente protege.

No cambia ningún criterio de `criteria/`. Ninguna entrada de la versión
v2026-2027 declara como fuente `maestro#16-flujo-y-estados` ni
`maestro#21-mvp-y-aplazadas`: ambos describen flujo y alcance, no criterio de
corrección. Por eso R2 no protesta y el registro de sincronía no cambia.

## Por que

El docente pidió que los trabajos permanezcan en una carpeta local y que el
programa los vaya recogiendo. La decisión D-009 lo adopta, y adoptarlo
contradecía al Documento Maestro en dos apartados. La regla del §14.1 no admite
que una fuente inferior contradiga a una superior, así que la única salida
legítima era corregir el Maestro.

La corrección no es total, y la diferencia importa. El nombre del archivo lo
pone el alumno; confiar en él habría convertido la condición de parada del
§18.2 de excepción en rutina. Por eso la vigilancia entra en la primera versión
y la identificación automática se queda fuera.

## Fuente que lo respalda

- Documento Maestro §14.1, jerarquía de fuentes y regla de conflicto.
- Documento Maestro §22.1, que ya preveía «Revisar con el colaborador técnico
  el flujo propuesto y el modelo de carpetas».
- Instrucción del docente, 2026-08-27: los trabajos permanecen en una carpeta
  local y el programa los va cogiendo.
- Decisión D-009 de `docs/decisions.md`, estado Validada, que declara
  expresamente que la contradicción obliga a corregir el §16.1 y el §21.2.

## Que arrastra

- `docs/maestro/01-documento-maestro.md` (§16, §21.1 y §21.2).
- `docs/decisions.md`: D-009 nueva, y D-004 pasa de Pendiente a Validada.

Queda fuera de este cambio, y señalado para el docente: el punto 8 del §16
menciona una «nota propuesta» que el sistema no podrá calcular mientras las
ponderaciones sigan en `PENDIENTE_OFICIAL`, porque R3 impide sustituir un dato
pendiente por una estimación. No es una contradicción del documento —describe
lo que el flujo hará cuando llegue la programación didáctica—, así que la frase
se conserva tal cual.

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema, y el
cambio no toca criterio alguno.
