-- Esquema inicial del Revisor de Proyectos Intermodulares.
--
-- Deriva del §15.1 del Documento Maestro (las siete entidades mínimas) y de
-- la decisión D-001, que acota qué se almacena aquí y qué no.
--
-- NO SE ALMACENA EN NINGUNA TABLA:
--   - El PDF de la entrega del alumno.
--   - El texto completo del trabajo.
-- Solo viven aquí las fichas, las correcciones, las evidencias citadas, el
-- feedback aprobado y la auditoría.

-- ---------------------------------------------------------------------------
-- Tipos
-- ---------------------------------------------------------------------------

-- Fases del §5 y del §9. TEMA no puntúa como entrega; DEFENSA se valora a mano.
create type fase as enum ('TEMA', 'E1', 'E2', 'E3', 'FINAL', 'DEFENSA');

-- Modalidades del §3.
create type modalidad as enum ('PROFESIONAL', 'INVESTIGACION', 'REVISION');

-- Estados de ejecución del §16.1.
create type estado_entrega as enum (
  'RECIBIDO',
  'BLOQUEADO',
  'ANALIZADO',
  'BORRADORES_GENERADOS',
  'EN_REVISION_DOCENTE',
  'APROBADO',
  'COMUNICADO'
);

-- Semáforo del §12.1.
create type semaforo as enum ('VERDE', 'AMBAR', 'ROJO', 'GRIS');

-- Escala de valoración del §8.1.
create type nivel_dimension as enum (
  'SOLIDO',
  'ADECUADO',
  'EN_DESARROLLO',
  'INSUFICIENTE',
  'NO_APLICABLE',
  'NO_VERIFICABLE'
);

-- Prioridad de una observación, del §7.
create type prioridad as enum ('CRITICA', 'ALTA', 'MEDIA', 'BAJA');

-- Estado de comunicación del feedback. COMUNICADO existe pero no se usa
-- todavía: la decisión D-004 sobre el canal de devolución sigue abierta.
create type estado_feedback as enum ('BORRADOR', 'REVISADO', 'APROBADO', 'COMUNICADO');

-- ---------------------------------------------------------------------------
-- Alumno
-- ---------------------------------------------------------------------------
-- El §19 exige códigos anónimos. Aquí NO se guardan nombres, DNI, correos ni
-- teléfonos: solo el código con el que el docente identifica a cada alumno en
-- sus propios registros.

create table alumno (
  id uuid primary key default gen_random_uuid(),
  codigo text not null unique,
  ciclo text not null,
  grupo text,
  -- Reservadas al docente. Nunca se convierten en feedback (§10.2).
  observaciones_docentes text,
  creado_en timestamptz not null default now(),

  constraint codigo_sin_espacios check (codigo = btrim(codigo) and codigo <> '')
);

comment on table alumno is
  'Alumno identificado por código anónimo. Sin datos personales: §19.';
comment on column alumno.observaciones_docentes is
  'Reservado al docente. No se traslada nunca al feedback del alumno.';

-- ---------------------------------------------------------------------------
-- Proyecto
-- ---------------------------------------------------------------------------

create table proyecto (
  id uuid primary key default gen_random_uuid(),
  alumno_id uuid not null references alumno(id) on delete restrict,
  titulo text,
  tema_validado boolean not null default false,
  tema_validado_en date,
  modalidad modalidad,
  version_criterios text not null,
  creado_en timestamptz not null default now(),

  -- Un alumno tiene un proyecto por curso; la versión de criterios lo fecha.
  unique (alumno_id, version_criterios),
  constraint validacion_coherente
    check (tema_validado = false or tema_validado_en is not null)
);

comment on column proyecto.version_criterios is
  'Versión de criterios vigente al validar el tema, p.ej. v2026-2027.';

-- ---------------------------------------------------------------------------
-- Entrega
-- ---------------------------------------------------------------------------
-- El fichero NO se guarda. Se registra su nombre y su huella para poder
-- identificar cuál se corrigió, sin conservar su contenido (D-001).

create table entrega (
  id uuid primary key default gen_random_uuid(),
  proyecto_id uuid not null references proyecto(id) on delete restrict,
  fase fase not null,
  version integer not null default 1,
  recibida_en timestamptz not null default now(),
  fecha_limite date,
  dentro_de_plazo boolean,
  nombre_archivo text,
  huella_archivo text,
  estado estado_entrega not null default 'RECIBIDO',
  motivo_bloqueo text,
  version_criterios text not null,

  unique (proyecto_id, fase, version),
  constraint bloqueo_con_motivo
    check (estado <> 'BLOQUEADO' or motivo_bloqueo is not null)
);

comment on table entrega is
  'Una versión de una entrega. El PDF no se almacena: solo su nombre y huella.';
comment on column entrega.huella_archivo is
  'Huella del fichero entregado, para identificarlo sin conservarlo (§19.1).';

-- ---------------------------------------------------------------------------
-- Corrección
-- ---------------------------------------------------------------------------
-- La nota propuesta y la aprobada son campos distintos a propósito: el §13
-- reserva al profesor la aprobación de cualquier calificación.

create table correccion (
  id uuid primary key default gen_random_uuid(),
  entrega_id uuid not null references entrega(id) on delete restrict,
  version_criterios text not null,
  resumen_ejecutivo text,
  semaforo_propuesto semaforo,
  semaforo_aprobado semaforo,
  nota_propuesta numeric(4,2),
  nota_aprobada numeric(4,2),
  accion_recomendada text,
  aprobada_en timestamptz,
  aprobada_por text,
  creada_en timestamptz not null default now(),

  unique (entrega_id),
  constraint nota_propuesta_en_rango
    check (nota_propuesta is null or (nota_propuesta >= 0 and nota_propuesta <= 10)),
  constraint nota_aprobada_en_rango
    check (nota_aprobada is null or (nota_aprobada >= 0 and nota_aprobada <= 10)),
  -- Una nota aprobada exige constancia de quién y cuándo la aprobó.
  constraint aprobacion_con_firma
    check (nota_aprobada is null or (aprobada_en is not null and aprobada_por is not null))
);

comment on column correccion.nota_propuesta is
  'Propuesta del sistema. Interna y provisional hasta que el docente la apruebe (§10.1).';
comment on column correccion.nota_aprobada is
  'Calificación validada por el docente. Solo él puede escribirla (§13).';

-- ---------------------------------------------------------------------------
-- Valoración por dimensión
-- ---------------------------------------------------------------------------
-- Las doce dimensiones del §8, una fila por dimensión valorada.

create table valoracion_dimension (
  id uuid primary key default gen_random_uuid(),
  correccion_id uuid not null references correccion(id) on delete cascade,
  dimension text not null,
  nivel nivel_dimension not null,
  prioridad prioridad,
  observacion text,
  decision_docente text,

  unique (correccion_id, dimension),
  constraint dimension_conocida check (dimension ~ '^D(0[1-9]|1[0-2])$'),
  constraint decision_docente_valida
    check (decision_docente is null
           or decision_docente in ('ACEPTADA', 'EDITADA', 'DESCARTADA'))
);

comment on column valoracion_dimension.decision_docente is
  'Aceptar, editar o descartar. Solo lo aprobado pasa al histórico (§13).';

-- ---------------------------------------------------------------------------
-- Evidencia citada
-- ---------------------------------------------------------------------------
-- D-001 fija el límite en 1.500 caracteres y dice que es una restricción del
-- sistema, no una recomendación: impide que la suma de evidencias acabe
-- reconstruyendo el trabajo del alumno dentro de la base de datos.

create table evidencia (
  id uuid primary key default gen_random_uuid(),
  valoracion_id uuid not null references valoracion_dimension(id) on delete cascade,
  apartado text,
  pagina integer,
  fragmento text not null,

  constraint fragmento_acotado check (char_length(fragmento) <= 1500),
  constraint pagina_positiva check (pagina is null or pagina > 0)
);

comment on constraint fragmento_acotado on evidencia is
  'D-001: 1.500 caracteres como máximo. El límite es del sistema, no un consejo.';

-- ---------------------------------------------------------------------------
-- Feedback
-- ---------------------------------------------------------------------------

create table feedback (
  id uuid primary key default gen_random_uuid(),
  correccion_id uuid not null references correccion(id) on delete restrict,
  borrador text,
  texto_aprobado text,
  estado estado_feedback not null default 'BORRADOR',
  aprobado_en timestamptz,
  comunicado_en timestamptz,

  unique (correccion_id),
  constraint aprobado_con_texto
    check (estado not in ('APROBADO', 'COMUNICADO') or texto_aprobado is not null),
  -- COMUNICADO no se usa mientras D-004 siga abierta: qué marca ese estado y
  -- por qué canal llega el feedback al alumno está sin decidir.
  constraint comunicado_con_fecha
    check (estado <> 'COMUNICADO' or comunicado_en is not null)
);

comment on table feedback is
  'Borrador y versión aprobada. Nunca contiene la nota interna (§18.1).';

-- ---------------------------------------------------------------------------
-- Defensa
-- ---------------------------------------------------------------------------
-- El §6.5 dice que el sistema no evalúa una defensa en directo: la valoración
-- la introduce el docente.

create table defensa (
  id uuid primary key default gen_random_uuid(),
  proyecto_id uuid not null references proyecto(id) on delete restrict,
  fecha date,
  soporte text,
  preguntas text,
  valoracion text,
  nota numeric(4,2),
  registrada_por text,

  unique (proyecto_id),
  constraint nota_defensa_en_rango
    check (nota is null or (nota >= 0 and nota <= 10))
);

comment on table defensa is
  'Valoración introducida a mano por el docente. El sistema no la evalúa (§6.5).';

-- ---------------------------------------------------------------------------
-- Registro de auditoría
-- ---------------------------------------------------------------------------
-- El §19.1 fija el registro mínimo: reconstruir qué ocurrió, con qué criterios
-- y quién decidió.

create table registro (
  id uuid primary key default gen_random_uuid(),
  ocurrido_en timestamptz not null default now(),
  usuario text not null,
  accion text not null,
  entidad text,
  entidad_id uuid,
  version_criterios text,
  detalle jsonb
);

create index registro_por_fecha on registro (ocurrido_en desc);
create index registro_por_entidad on registro (entidad, entidad_id);

comment on table registro is
  'Auditoría del §19.1. Permite reconstruir qué se hizo y con qué criterios.';

-- ---------------------------------------------------------------------------
-- Consultas frecuentes
-- ---------------------------------------------------------------------------

create index entrega_por_proyecto on entrega (proyecto_id, fase);
create index correccion_por_entrega on correccion (entrega_id);
create index valoracion_por_correccion on valoracion_dimension (correccion_id);
create index evidencia_por_valoracion on evidencia (valoracion_id);

-- ---------------------------------------------------------------------------
-- Seguridad a nivel de fila
-- ---------------------------------------------------------------------------
-- RLS activo en todas las tablas y SIN políticas todavía. Con esta
-- configuración nadie accede salvo la clave de servicio, que es lo correcto
-- mientras no se decida cómo se autentica el docente: es preferible que no
-- entre nadie a que entre cualquiera.
--
-- Cuando se decida la autenticación, las políticas van en su propia migración
-- y con su documento de cambio.

alter table alumno                enable row level security;
alter table proyecto              enable row level security;
alter table entrega               enable row level security;
alter table correccion            enable row level security;
alter table valoracion_dimension  enable row level security;
alter table evidencia             enable row level security;
alter table feedback              enable row level security;
alter table defensa               enable row level security;
alter table registro              enable row level security;
