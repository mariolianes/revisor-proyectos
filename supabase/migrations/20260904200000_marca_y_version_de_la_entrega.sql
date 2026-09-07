-- Lo que la admisión decide sobre una entrega, con sitio donde guardarse.
--
-- `backend/servicios/admision.py` ya calcula estas tres cosas y hasta ahora
-- no tenían columna: se perdían en cuanto la respuesta salía de memoria.
--
-- Las tres salen de decisiones#7-versiones y decisiones#2-identificador:
--
--   «Mismo archivo y mismo hash: registrar DUPLICATE_EXACT, no crear un
--   nuevo análisis, no generar coste API y no sobrescribir el original.»
--   «Archivo diferente para la misma fase: conservar como v02, v03...;
--   marcar VERSION_CONFLICT y detener el análisis nuevo hasta que Marcos
--   elija la versión válida.»
--   «Versión seleccionada: marcarla como vigente. Las anteriores pasan a
--   sustituida o histórica, pero nunca se eliminan.»
--
-- `estado_version` entra con 'VIGENTE' por omisión: una entrega que existía
-- antes de esta migración es, por definición, la única de su fase, y llamarla
-- de cualquier otra cosa sería inventar un histórico que no ocurrió.
--
-- `ruta_expediente` guarda dónde quedó la copia normalizada, relativa a la
-- raíz de expedientes. Nunca una ruta absoluta: esa lleva el nombre de
-- usuario del equipo del docente, y este sistema no manda a la base nada
-- que identifique a una persona si puede evitarlo.
--
-- Aplicación: desde el panel de Supabase, o por la API de gestión.

alter table entrega
  add column if not exists marca_admision text,
  add column if not exists estado_version text not null default 'VIGENTE',
  add column if not exists ruta_expediente text;

alter table entrega drop constraint if exists marca_de_admision_conocida;
alter table entrega add constraint marca_de_admision_conocida
  check (marca_admision is null
         or marca_admision in ('DUPLICATE_EXACT', 'VERSION_CONFLICT'));

alter table entrega drop constraint if exists estado_de_version_conocido;
alter table entrega add constraint estado_de_version_conocido
  check (estado_version in ('VIGENTE', 'SUSTITUIDA', 'HISTORICA'));

comment on column entrega.marca_admision is
  'DUPLICATE_EXACT o VERSION_CONFLICT, del 7 de la respuesta del docente del 2026-09-02. Nulo cuando la entrega entró sin incidencia.';
comment on column entrega.estado_version is
  'VIGENTE, SUSTITUIDA o HISTORICA. Ninguna se elimina nunca: lo dijo el docente expresamente.';
comment on column entrega.ruta_expediente is
  'Donde quedo la copia normalizada, relativa a la raiz de expedientes. Nunca absoluta: esa llevaria el nombre de usuario del equipo.';
