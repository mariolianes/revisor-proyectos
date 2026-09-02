# El verde con alerta recibe menos acciones que un ámbar

**Fecha:** 2026-09-03
**Autor:** Marcos / colaborador técnico

## Que cambia

`criteria/v2026-2027/feedback.yaml` gana una entrada `VERDE: 2` en
`prioridades_maximas_por_semaforo`.

## Por que

Es una regresión que introdujo el cambio del semáforo del 2 de septiembre, y
conviene contarla entera porque es el tipo de fallo que no da ningún error.

Hasta el 31 de agosto, un P3 sin ningún P1 ni P2 daba ÁMBAR. Después pasó a
dar VERDE_CON_ALERTAS, que tenía su propia entrada. Al retirar ese quinto
color, ese mismo caso pasó a dar **VERDE** —correctamente, es lo que el
docente pide—, pero VERDE nunca había tenido entrada en el mapa de límites,
porque hasta entonces **no podía tener ninguna observación de la que partir**.

Resultado: caía en el tope absoluto de cuatro. Un trabajo que «cumple la fase
y puede avanzar» le habría mandado al alumno **más acciones que uno que
necesita correcciones prioritarias**. Ni un test fallaba: el límite estaba
bien, el color estaba bien, y la combinación de los dos no.

Dos, y no tres, porque él describe ese verde como «ajustes menores o alertas
no bloqueantes»: menos que el ámbar, que es donde empiezan las «correcciones
prioritarias antes de considerarse cerrado».

## Fuente que lo respalda

`decisiones#12-semaforo` para la descripción de VERDE, y
`calibracion#7-economia-pedagogica` para la regla del límite, que no cambia.

## Que arrastra

`criteria/v2026-2027/feedback.yaml`, `backend/salidas/seleccion.py` (el
docstring de `_maximo` decía que VERDE no llegaba a usarse, y ya no es
cierto) y `tests/salidas/test_seleccion.py`.

## Correcciones cerradas afectadas

Ninguna. Entre el cambio del semáforo y esta corrección no se ha analizado
ningún trabajo real.
