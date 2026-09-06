# El registro de auditoría del §19.1 empieza a escribirse

**Fecha:** 2026-09-06
**Autor:** Marcos / colaborador técnico

## Que cambia

Registrar una entrega, cambiarle el estado o guardar una corrección dejan
ahora su línea en la tabla `registro`. Antes no la escribía nadie.

## Por que

Porque el §19.1 lo exige y la tabla llevaba desde el primer día vacía. Se
encontró mirando la base después del primer recorrido completo del circuito
contra infraestructura real.

## Fuente que lo respalda

`maestro#19-privacidad`, §19.1 «Registro mínimo», que enumera los seis datos
que hay que poder reconstruir.

## Que arrastra

`backend/persistencia/auditoria.py`, `backend/persistencia/memoria.py`,
`backend/persistencia/supabase.py`, `backend/persistencia/modelos.py`,
`tests/conftest.py`, `tests/persistencia/test_paridad.py`,
`tests/persistencia/test_supabase.py`.

Dos tests contaban peticiones y se han actualizado con su porqué: lo que
protegen no es el número, sino que las escrituras **no crezcan con el número
de dimensiones**. La de auditoría es una, siempre.

## Correcciones cerradas afectadas

Ninguna. Lo hecho antes de hoy no tiene histórico y no se puede reconstruir
hacia atrás: el registro empieza aquí.
