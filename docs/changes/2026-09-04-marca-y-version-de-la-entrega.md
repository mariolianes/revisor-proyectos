# La entrega guarda lo que la admisión decide sobre ella

**Fecha:** 2026-09-04
**Autor:** Marcos / colaborador técnico

## Que cambia

`entrega` gana tres columnas: `marca_admision`, `estado_version` y
`ruta_expediente`.

## Por que

Porque `backend/servicios/admision.py` ya calculaba las tres y no tenían
dónde guardarse: se perdían en cuanto la respuesta salía de memoria. Un
duplicado exacto detectado hoy volvía a detectarse mañana desde cero, y la
copia normalizada quedaba en disco sin que nada apuntara a ella.

`estado_version` entra con `VIGENTE` por omisión: una entrega anterior a esta
migración es, por definición, la única de su fase, y llamarla de otra cosa
sería inventar un histórico que no ocurrió.

`ruta_expediente` guarda una ruta **relativa** a la raíz de expedientes,
nunca absoluta: la absoluta lleva el nombre de usuario del equipo del
docente, y a la base no va nada que identifique a una persona si se puede
evitar.

## Fuente que lo respalda

`decisiones#7-versiones` para las dos marcas y los tres estados de versión,
y `decisiones#2-identificador` para el nombre normalizado al que apunta
`ruta_expediente`.

## Que arrastra

`supabase/migrations/20260904200000_marca_y_version_de_la_entrega.sql`.
Ningún módulo de Python todavía: la admisión calcula estos valores pero
quien registra una entrega sigue sin escribirlos, y conectarlo es el paso
siguiente.

## Correcciones cerradas afectadas

Ninguna. La base no tenía ninguna entrega salvo la del recorrido de prueba
del circuito completo.
