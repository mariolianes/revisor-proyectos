# Lo que la admisión decide llega ya a la entrega

**Fecha:** 2026-09-06
**Autor:** Marcos / colaborador técnico

## Que cambia

`EntregaNueva` y `EntregaRegistrada` ganan `marca_admision`,
`estado_version` y `ruta_expediente`, los dos almacenes las guardan y las
releen, y nace `entrega_desde()` en la admisión, que convierte una admisión
en la entrega que se registra.

## Por que

Porque la migración del 4 de septiembre creó las columnas y nada las
escribía: la admisión calculaba las tres y se perdían al salir de memoria.

Tres guardas nuevas, y las tres rechazan al construir, no al guardar, para
que no dependan de qué almacén haya detrás:

- una marca de admisión que no sea una de las dos del docente,
- un estado de versión que no sea uno de los tres,
- y **una ruta absoluta**, porque lleva el nombre de usuario del equipo del
  docente y eso es un dato personal en una columna que no debe llevarlos.

## Dos cosas que se vieron probando contra la base real

**Un conflicto de versión entra como VIGENTE igualmente.** El docente
todavía no ha elegido cuál vale, y marcarla ya como sustituida sería decidir
por él. Lo que hace el conflicto es detener el análisis, no degradar la
entrega.

**La ruta se guardaba con las barras invertidas de Windows.** Una ruta así es
ilegible desde cualquier otro sitio y se rompe al partirla por el separador.
Lo que va a la base es una ruta de texto, no una ruta de este sistema
operativo: ahora se guarda con barras normales. No lo vio ningún test hasta
que se miró la primera fila de verdad.

## Fuente que lo respalda

`decisiones#7-versiones` y `decisiones#2-identificador`.

## Que arrastra

`backend/persistencia/modelos.py`, `backend/persistencia/supabase.py`,
`backend/servicios/admision.py`, `tests/servicios/test_admision.py`.

## Correcciones cerradas afectadas

Ninguna. La base está vacía: los datos del circuito de prueba se retiraron a
petición del responsable.
