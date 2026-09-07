# Un borrador demasiado largo ya no tira el informe entero

**Fecha:** 2026-09-04
**Autor:** Marcos / colaborador técnico

## Que cambia

Cuando el motor redacta una línea del borrador por encima de su límite, el
informe **se guarda igual** y lo que falta es solo el borrador, con un aviso
que lo explica. Antes se revertía la entrega entera a RECIBIDO y no quedaba
nada.

Y la respuesta de la API se compone ahora **con lo que de verdad se ha
guardado**, no con lo que se intentó guardar.

## Por que

Se encontró recorriendo el circuito completo con el motor real, sobre un
trabajo de verdad. La primera pasada murió así:

> El motor de análisis ha devuelto un texto que no cabe en su límite: una
> acción de la devolución tiene 423 caracteres, y el límite es 400.

El análisis había salido bien y estaba pagado. Se tiró entero por una línea
de más en el texto que ni siquiera es el informe.

`backend/servicios/analisis_de_entrega.py` ya declaraba el invariante: «no
hay forma de que la redacción del borrador invalide un informe que ya es
correcto». **Lo cumplía la redacción, pero no la escritura**: la validación
de longitudes no distinguía de qué mitad venía el texto largo, así que un
fallo del borrador arrastraba al informe.

La segunda mitad del arreglo apareció al escribir el test: con solo lo
anterior, el informe se guardaba sin borrador pero la respuesta seguía
anunciando el borrador. La pantalla habría dicho una cosa y una recarga otra,
que es peor que el fallo original.

## Fuente que lo respalda

Ninguna nueva. Es el invariante que ya declaraba
`backend/servicios/analisis_de_entrega.py`, que no se cumplía en la capa de
persistencia.

## Que arrastra

`backend/persistencia/correccion.py` (`TextoFueraDeLimite` gana
`de_la_devolucion`), `backend/api/analisis.py` (`_guardar_o_fallar` devuelve
lo guardado; nace `_aviso_de_borrador_demasiado_largo`) y
`tests/backend/test_api_analisis.py`.

El límite contrario se mantiene y tiene su propio test: si lo que se pasa de
largo es del **informe**, no hay nada que salvar y se revierte entero.

## Correcciones cerradas afectadas

Ninguna guardada. Sí explica, hacia atrás, cualquier análisis que se haya
intentado y muriera con un 503 de desbordamiento: aquel informe era válido y
se perdió.
