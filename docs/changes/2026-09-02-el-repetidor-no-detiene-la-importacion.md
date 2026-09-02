# El repetidor no detiene la importación

**Fecha:** 2026-09-02
**Autor:** Marcos / colaborador técnico

## Que cambia

Una fila cuyo ID de CESUR ya existía en un curso anterior deja de mandarse a
revisión. Entra como alta nueva, con identidad nueva, y se anota en
`matricula_anterior` de dónde viene. El motivo `REPETIDOR_POSIBLE` desaparece
del importador.

El índice único sobre `platform_id` pasa a ser único sobre
`(platform_id, curso)`.

## Por que

Porque lo cerró el docente. Y porque, con 200-250 alumnos, detener y
preguntar por cada repetidor convertía en trabajo suyo justo lo que el
sistema existe para ahorrarle.

## Fuente que lo respalda

`decisiones#3-repetidores`, en `docs/maestro/05-decisiones-arquitectura.md`.

## Que arrastra

`backend/persistencia/alumnos.py`, `backend/persistencia/memoria.py`,
`backend/persistencia/supabase.py`,
`backend/servicios/importacion_alumnos.py`,
`supabase/migrations/20260831210000_registro_maestro_de_alumnos.sql`,
`tests/servicios/test_importacion_alumnos.py`,
`tests/persistencia/test_paridad.py`,
`docs/migraciones/2026-09-03-guia-de-aplicacion.md`.

## Correcciones cerradas afectadas

Ninguna. No hay ningún listado importado todavía contra la base real -las
migraciones siguen sin aplicarse-, así que no existe ningún alumno cuyo
tratamiento cambie de forma retroactiva.
