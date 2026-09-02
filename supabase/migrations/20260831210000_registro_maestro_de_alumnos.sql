-- Registro maestro de alumnos: importación de listados por comunidad.
--
-- El punto 2 del orden de implantación del docente pide poder dar de alta a
-- los 200-250 alumnos de un curso ANTES de que llegue ninguna entrega, con
-- centro, ciclo, comunidad autónoma y estado de matrícula -y el ID de
-- CESUR, cuando el centro lo facilita, que el docente pidió preferir al
-- nombre para emparejar-.
--
-- La tabla `alumno` ya existe (20260827120000_esquema_inicial.sql) y ya es,
-- por diseño, la identidad anónima del alumno: esta migración AMPLÍA esa
-- tabla, no crea una segunda. `codigo` sigue siendo la columna del
-- identificador -desde esta tarea con forma ALU-AANNNN
-- (backend/persistencia/alumnos.py) en vez de la que elegía a mano cada
-- alumno en el nombre de su archivo (AF023, AF024...)- y `ciclo` sigue
-- siendo la misma columna de siempre, ahora también con el vocabulario
-- cerrado que pide el docente (MYP, CIN, AYF). Ver D-024 en
-- docs/decisions.md, incluida la pregunta que queda abierta: si un alumno
-- repetidor conserva su student_id de un curso anterior.
--
-- Ninguna columna nueva admite un nombre. La correspondencia con el nombre
-- real sigue viviendo únicamente en el equipo del docente
-- (backend/privacidad/listado_local.py); esta migración no cambia eso, lo
-- confirma: nada de lo que aquí se guarda permite reconstruir un nombre.

alter table alumno
  add column centro_code text,
  add column ccaa_code text
    constraint ccaa_code_conocido check (ccaa_code ~ '^(AND|MAD|CAN|MUR|ARA|EXT)$'),
  add column curso text,
  add column estado_matricula text not null default 'ACTIVO'
    constraint estado_matricula_conocida check (estado_matricula ~ '^(ACTIVO|BAJA|TRASLADADO|REPETIDOR)$'),
  add column platform_id text;

comment on column alumno.codigo is
  'El student_id: ALU-AANNNN desde esta migración (AA = curso, NNNN = secuencia). Estable dentro de un curso e independiente del centro y la comunidad, por decisión del docente. Alumnos anteriores a esta tarea pueden seguir llevando el código que traía el nombre de su archivo (p.ej. AF023): las dos formas conviven en la misma columna.';
comment on column alumno.ciclo is
  'El ciclo_code: MYP, CIN o AYF (backend/persistencia/alumnos.py, CICLO_CODES). NULL en alumnos dados de alta antes de esta tarea sin ciclo declarado.';
comment on column alumno.centro_code is
  'Código del centro, p.ej. AND-MAL-01. Se valida en la aplicación contra config/centros.yaml, no contra un enum de la base de datos: el catálogo de centros crece sin que eso sea una migración.';
comment on column alumno.ccaa_code is
  'Comunidad autónoma del centro: AND, MAD, CAN, MUR, ARA o EXT.';
comment on column alumno.curso is
  'Curso académico, p.ej. 2026-2027. Determina el prefijo del student_id (backend/persistencia/alumnos.py, generar_student_id).';
comment on column alumno.estado_matricula is
  'Activo, baja, trasladado o repetidor. Por omisión, activo: un alta sin este dato en el listado no debe leerse como baja.';
comment on column alumno.platform_id is
  'ID de CESUR, cuando el centro lo facilita. Preferible al nombre para emparejar entre importaciones -lo pidió así el docente-. NULL cuando no hay ID de plataforma.';

-- Un ID de plataforma no puede pertenecer a dos identidades. Parcial porque
-- muchos centros no lo facilitan: dos NULL no chocan entre sí -es el
-- comportamiento estándar de NULL en un índice unique de Postgres-, y se
-- declara `where platform_id is not null` explícitamente para que quien lea
-- la migración no tenga que recordar esa regla para saber qué hace este
-- índice.
--
-- La aplicación ya comprueba esto antes de escribir
-- (AlmacenSupabase.dar_de_alta_alumno, backend/persistencia/supabase.py),
-- con el mismo mensaje en los dos almacenes
-- (backend/persistencia/alumnos.py, error_de_platform_id_duplicado); este
-- índice es la segunda línea de defensa, para cualquier escritura que no
-- pase por esa vía.
create unique index alumno_platform_id_unico on alumno (platform_id)
  where platform_id is not null;

create index alumno_por_curso on alumno (curso);
