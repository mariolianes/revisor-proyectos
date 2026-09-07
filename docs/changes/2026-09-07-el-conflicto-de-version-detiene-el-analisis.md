# Un conflicto de versión detiene el análisis hasta que el docente elige

**Fecha:** 2026-09-07
**Autor:** Marcos / colaborador técnico

## Que cambia

Una entrega marcada `VERSION_CONFLICT` no se puede analizar. Nace
`POST /api/entregas/{id}/version-elegida`, con el que el docente elige cuál
vale: las otras pasan a sustituidas y se borra la marca, que es lo que vuelve
a permitir el análisis.

## Por que

Porque lo pide el §7 de su respuesta, y porque analizar la versión que luego
se descarta cuesta dinero y produce un informe que hay que tirar. La guarda
va antes de llamar al motor, no después.

## Fuente que lo respalda

`decisiones#7-versiones`.

## Que arrastra

`backend/api/analisis.py`, `backend/api/entregas.py`,
`backend/persistencia/modelos.py`, `backend/persistencia/memoria.py`,
`backend/persistencia/supabase.py`, `tests/persistencia/test_paridad.py`,
`tests/backend/test_api_analisis.py`.

## Correcciones cerradas afectadas

Ninguna. No hay ninguna entrega con conflicto guardada: la base está vacía.
