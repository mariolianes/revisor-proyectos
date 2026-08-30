-- Registro de consumo: lo que ha costado cada ejecución de análisis.
--
-- El profesor lo pidió para poder decidir si corregir con esta herramienta
-- compensa: para eso hace falta saber cuánto cuesta cada corrección, no solo
-- que el sistema funciona. Una fila por ejecución (`POST /entregas/{id}/
-- analisis`), no por llamada individual al proveedor: una ejecución puede
-- hacer hasta dos llamadas reales -el análisis y la redacción del
-- borrador-, y hasta dos intentos de cada una si la primera respuesta no
-- encaja; `tokens_entrada`, `tokens_salida`, `duracion_ms` e `intentos` son
-- la suma de todo eso, no de una sola llamada
-- (backend/persistencia/consumo.py, backend/servicios/analisis_de_entrega.py).
--
-- NO SE ALMACENA EN ESTA TABLA, por la misma razón que en el resto del
-- esquema (§19, D-001): ni el texto del trabajo, ni la instrucción que se le
-- envió al motor, ni ninguna cita. Solo cifras y etiquetas -tokens, coste,
-- duración, estado- y el código de entrega, que ya es anónimo.

create table ejecucion_motor (
  id uuid primary key default gen_random_uuid(),
  entrega_id uuid not null references entrega(id) on delete restrict,
  modelo text not null,
  tokens_entrada integer,
  tokens_salida integer,
  tokens_entrada_cacheados integer,
  coste_estimado_usd numeric(10,6),
  -- Qué fila de config/precios_openai.yaml se aplicó ("modelo@fecha"), o
  -- nulo si no había ninguna tarifa vigente -y por eso tampoco hay coste-.
  -- Sin este dato, un coste guardado hoy sería irreproducible en cuanto la
  -- tabla de precios cambiara: sirve para poder responder "¿con qué tarifa
  -- se calculó esto?" dentro de un año.
  tarifa_aplicada text,
  duracion_ms integer not null,
  estado text not null,
  intentos integer not null default 1,
  causa_error text,
  paginas integer,
  caracteres_texto integer,
  reutilizado boolean not null default false,
  creada_en timestamptz not null default now(),

  constraint estado_de_ejecucion_conocido
    check (estado in ('OK', 'PARCIAL', 'ERROR')),
  constraint intentos_positivos check (intentos >= 1),
  constraint duracion_no_negativa check (duracion_ms >= 0),
  constraint tokens_no_negativos
    check (
      (tokens_entrada is null or tokens_entrada >= 0)
      and (tokens_salida is null or tokens_salida >= 0)
      and (tokens_entrada_cacheados is null or tokens_entrada_cacheados >= 0)
    ),
  constraint coste_no_negativo
    check (coste_estimado_usd is null or coste_estimado_usd >= 0),
  constraint paginas_no_negativas check (paginas is null or paginas >= 0),
  constraint caracteres_no_negativos
    check (caracteres_texto is null or caracteres_texto >= 0),
  -- Un estado ERROR o PARCIAL sin decir por qué deja al profesor sin poder
  -- distinguir "el motor tardó" de "la clave caducó" al mirar el histórico.
  constraint causa_de_error_si_no_fue_ok
    check (estado = 'OK' or causa_error is not null)
);

comment on table ejecucion_motor is
  'Coste y duración de cada ejecución de análisis. Nunca el texto del '
  'trabajo, la instrucción enviada ni ninguna cita: solo cifras y estado.';
comment on column ejecucion_motor.modelo is
  'El proveedor y el modelo, tal como los guarda correccion.informe.motor '
  '(por ejemplo "openai:gpt-4.1"), para poder cruzar una ejecución con la '
  'corrección que produjo, si la produjo.';
comment on column ejecucion_motor.tarifa_aplicada is
  'Qué fila de config/precios_openai.yaml se usó para el coste ("modelo@'
  'fecha"), o nulo si no había tarifa vigente para ese modelo.';
comment on column ejecucion_motor.reutilizado is
  'Si esta ejecución sirvió un resultado ya guardado en vez de llamar al '
  'proveedor. Hoy siempre es false: el sistema no tiene todavía ninguna vía '
  'que reutilice un resultado anterior sin volver a llamarlo.';

create index ejecucion_motor_entrega_id_idx on ejecucion_motor (entrega_id);
