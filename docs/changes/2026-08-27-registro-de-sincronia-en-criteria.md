# El registro de sincronía de R2 pasa a `criteria/`

**Fecha:** 2026-08-27
**Autor:** Marcos / colaborador técnico

## Que cambia

El registro que R2 usa para detectar que la prosa cambió sin revisar su
derivado deja de vivir dentro de una versión de criterios.

- Antes: `criteria/v2026-2027/.sincronia.json`
- Ahora: `criteria/.sincronia.json`

El fichero se mueve, no se duplica: el contenido y los hashes son los mismos.
No cambia ningún criterio ni ninguna cifra.

## Por que

`FICHERO_SINCRONIA` estaba fijado a la única versión existente, pero la
función que decide qué anclas sellar recorre `criteria/` entero. Mientras solo
hubiera una versión, ambas cosas coincidían por casualidad.

En cuanto exista una segunda —y crear la siguiente versión es exactamente el
remedio que R4 prescribe para cualquier cambio— el sellado escribiría la unión
de las anclas de todas las versiones dentro de la carpeta de una de ellas, que
además será normalmente la congelada. Una versión congelada es la prueba de
con qué criterio se corrigió a un alumno: escribir dentro de ella, aunque el
sello `.congelada` solo vigile los `*.yaml` y no proteste, es exactamente lo
que R4 existe para impedir.

Se ha elegido un registro único en `criteria/` en lugar de uno por versión
porque es la opción que hace coincidir el alcance del fichero con el alcance
del recorrido, sin añadir maquinaria: la pregunta que R2 responde —¿ha
cambiado alguna sección de prosa de la que dependa algún criterio vivo?— es
una pregunta del repositorio, no de una versión. Un registro por versión
habría exigido, además, decidir qué hacer al sellar una versión cerrada, que
es una decisión que no debería existir.

## Fuente que lo respalda

Acuerdo interno documentado: R4 del propio `GOVERNANCE.md`, que prohíbe
alterar una versión congelada. Ninguna fuente académica superior interviene:
es una corrección de la maquinaria, no del criterio.

## Que arrastra

- `criteria/v2026-2027/.sincronia.json` → `criteria/.sincronia.json`
- `tools/gobernanza/sincronia.py`
- `GOVERNANCE.md`

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema, y los
hashes registrados son los mismos que antes del movimiento.
