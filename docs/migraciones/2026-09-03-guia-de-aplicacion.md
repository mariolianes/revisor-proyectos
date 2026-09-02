# Guía para aplicar los cambios de base de datos

**Fecha:** 3 de septiembre de 2026 · **Para:** Marcos · **Cambios pendientes:** 4

Escrita a petición suya (`decisiones#14-migraciones`). Cada cambio trae su
finalidad, el SQL exacto, cómo comprobar que ha funcionado y cómo deshacerlo.

Nadie más que usted aplica esto. El sistema no tiene ninguna vía para
escribir en la base de datos por su cuenta, y es a propósito.

---

## Antes de empezar

**1. Compruebe que está en el proyecto correcto.** Abra su fichero `.env` y
mire el valor de `SUPABASE_URL`. Tiene esta forma:

    https://XXXXXXXXXXXX.supabase.co

Esas doce letras son el identificador de su proyecto. En el panel de
Supabase, arriba a la izquierda, aparece el proyecto seleccionado; entre en
**Settings → General** y compruebe que el **Reference ID** coincide con esas
doce letras. **Si no coincide, pare**: estaría modificando otro proyecto.

**2. Haga una copia de seguridad.** En el panel, **Database → Backups**.
Si su plan no ofrece copias automáticas, entre en **Database → Backups →
Download** o exporte el esquema. No es una formalidad: dos de estos cambios
crean columnas y una crea una tabla, y aunque todos son reversibles, deshacer
un cambio **borra los datos que se hayan escrito en él**.

**3. Dónde se pega el SQL.** Panel de Supabase → **SQL Editor** → **New
query**. Se pega el bloque entero, se pulsa **Run**, y se lee el resultado
antes de pasar al siguiente.

**4. Hágalos en orden.** Están numerados. El 3 depende de que el esquema
inicial exista; los demás son independientes entre sí, pero el orden numérico
es el que se ha probado.

**5. Puede repetirlos sin miedo.** Todo el SQL de esta guía está escrito para
poder ejecutarse dos veces sin romper nada: si una columna ya existe, se la
salta en vez de fallar. Si duda de si aplicó uno, aplíquelo otra vez.

---

## Cambio 1 · La corrección guarda sus dos salidas

**Fichero:** `supabase/migrations/20260829150000_correccion_guarda_sus_dos_salidas.sql`

**Para qué sirve.** Hoy la base guarda las piezas sueltas de una corrección
—cada valoración, cada evidencia— pero no el informe completo ni el borrador
de devolución tal como usted los ve en pantalla. Este cambio añade tres
columnas para guardarlos enteros.

**Qué pasa si no se aplica.** Al recargar una corrección, el informe hay que
reconstruirlo desde las piezas, y el borrador de devolución **se pierde**.

**SQL:**

```sql
alter table correccion
  add column if not exists informe jsonb not null default '{}'::jsonb,
  add column if not exists devolucion jsonb,
  add column if not exists aviso text;

alter table correccion alter column informe drop default;

comment on column correccion.informe is
  'El informe interno completo, tal como lo compone el sistema.';
comment on column correccion.devolucion is
  'El borrador de devolucion completo, o nulo si el analisis se completo sin el.';
comment on column correccion.aviso is
  'El aviso que vio el docente al guardar, si lo hubo.';
```

**Resultado esperado.** Supabase responde `Success. No rows returned`.

**Cómo comprobarlo.** Pegue esto y pulse Run:

```sql
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'correccion'
  and column_name in ('informe', 'devolucion', 'aviso')
order by column_name;
```

Debe devolver **tres filas**: `aviso`, `devolucion`, `informe`.

**Cómo deshacerlo.** Borra los informes y borradores guardados desde que se
aplicó:

```sql
alter table correccion
  drop column if exists informe,
  drop column if exists devolucion,
  drop column if exists aviso;
```

---

## Cambio 2 · Registro de consumo

**Fichero:** `supabase/migrations/20260830090000_registro_de_consumo.sql`

**Para qué sirve.** Crea la tabla donde se anota, de cada análisis, qué
modelo se usó, cuántos tokens costó, cuánto tardó y si terminó bien. **Es la
tabla que usted pide en el §13 de su respuesta** para poder ver modelo
exacto, tokens y coste por análisis antes de dar por bueno un gasto.

**Qué no guarda, y es deliberado:** ni el texto del trabajo, ni la
instrucción que se envió, ni ninguna cita. Solo cifras y estado.

**Qué pasa si no se aplica.** No hay histórico de coste. Las cifras que le
hemos dado salen de ejecuciones sueltas, no de la base.

**SQL:**

```sql
create table if not exists ejecucion_motor (
  id uuid primary key default gen_random_uuid(),
  entrega_id uuid not null references entrega(id) on delete restrict,
  modelo text not null,
  tokens_entrada integer,
  tokens_salida integer,
  tokens_entrada_cacheados integer,
  coste_estimado_usd numeric(10,6),
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
  constraint causa_de_error_si_no_fue_ok
    check (estado = 'OK' or causa_error is not null)
);

create index if not exists ejecucion_motor_entrega_id_idx
  on ejecucion_motor (entrega_id);

comment on table ejecucion_motor is
  'Coste y duracion de cada ejecucion de analisis. Nunca el texto del '
  'trabajo, la instruccion enviada ni ninguna cita: solo cifras y estado.';
```

**Resultado esperado.** `Success. No rows returned`.

**Cómo comprobarlo:**

```sql
select to_regclass('public.ejecucion_motor') as tabla;
```

Debe devolver `ejecucion_motor`. Si devuelve vacío o `null`, no se creó.

**Cómo deshacerlo.** Borra todo el histórico de consumo:

```sql
drop table if exists ejecucion_motor;
```

---

## Cambio 3 · Registro maestro de alumnos

**Fichero:** `supabase/migrations/20260831210000_registro_maestro_de_alumnos.sql`

**Para qué sirve.** Es el cambio que permite dar de alta a los 200-250
alumnos desde sus Excel. Añade a la tabla de alumnos el centro, la comunidad,
el curso, el estado de matrícula y el identificador de CESUR.

**Un detalle que cambió el 3 de septiembre.** Su decisión sobre los
repetidores —identidad nueva cada curso, conservando el ID de CESUR— chocaba
con este cambio tal como estaba escrito: llevaba un índice que exigía que
cada ID de CESUR fuese único **en toda la base**, y eso habría **rechazado a
todos los repetidores** del curso siguiente. Ya está corregido: ahora el ID
de CESUR es único **por curso**. Si tenía descargada una versión anterior de
este SQL, use esta.

**Lo que NO añade, y conviene que lo sepa:** ninguna columna para el nombre.
La correspondencia nombre-identificador se queda en su equipo, como usted
pidió, y esta migración es parte de esa garantía: no existe columna donde
guardar un nombre aunque alguien quisiera.

**Qué pasa si no se aplica.** No se puede importar ningún listado: el
importador escribiría en columnas que no existen.

**SQL:**

```sql
alter table alumno
  add column if not exists centro_code text,
  add column if not exists ccaa_code text,
  add column if not exists curso text,
  add column if not exists estado_matricula text not null default 'ACTIVO',
  add column if not exists platform_id text,
  add column if not exists matricula_anterior text;

alter table alumno drop constraint if exists ccaa_code_conocido;
alter table alumno add constraint ccaa_code_conocido
  check (ccaa_code is null or ccaa_code ~ '^(AND|MAD|CAN|MUR|ARA|EXT)$');

alter table alumno drop constraint if exists estado_matricula_conocida;
alter table alumno add constraint estado_matricula_conocida
  check (estado_matricula ~ '^(ACTIVO|BAJA|TRASLADADO|REPETIDOR)$');

drop index if exists alumno_platform_id_unico;

create unique index if not exists alumno_platform_id_unico_por_curso
  on alumno (platform_id, curso) where platform_id is not null;

create index if not exists alumno_por_curso on alumno (curso);
```

**Resultado esperado.** `Success. No rows returned`.

**Cómo comprobarlo:**

```sql
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'alumno'
  and column_name in
    ('centro_code', 'ccaa_code', 'curso', 'estado_matricula',
     'platform_id', 'matricula_anterior')
order by column_name;
```

Debe devolver **seis filas**.

**Cómo deshacerlo.** Borra el centro, la comunidad, el curso y el estado de
matrícula de todos los alumnos ya importados:

```sql
drop index if exists alumno_platform_id_unico_por_curso;
drop index if exists alumno_por_curso;
alter table alumno
  drop column if exists centro_code,
  drop column if exists ccaa_code,
  drop column if exists curso,
  drop column if exists estado_matricula,
  drop column if exists platform_id,
  drop column if exists matricula_anterior;
```

---

## Cambio 4 · La alerta sobre el verde

**Fichero:** `supabase/migrations/20260902190000_alertas_sobre_verde.sql`

**Para qué sirve.** Es la traducción de su decisión del §12: «verde con
alertas» no es un color, sino un VERDE con una marca al lado. Añade esa
marca.

**Lea esto, porque cambió sobre la marcha.** Hasta el 2 de septiembre había
aquí otra migración distinta, que **añadía un quinto color** al semáforo.
**Se ha retirado y no debe aplicarla**: si le llegó antes, no la ejecute.
El motivo es técnico y no tiene vuelta atrás — un valor añadido a un tipo
enumerado de PostgreSQL **no se puede eliminar después**. Si se hubiera
aplicado, su base de datos habría quedado con un estado que su propio
Documento Maestro no reconoce, y sin forma de quitarlo.

Esta migración, en cambio, **no toca el tipo del semáforo**: sigue con sus
cuatro valores de siempre.

**SQL:**

```sql
alter table correccion
  add column if not exists con_alertas boolean not null default false;

comment on column correccion.con_alertas is
  'VERDE que conserva defectos importantes por atender antes del cierre. '
  'No es un color: el semaforo sigue siendo uno de los cuatro oficiales.';
```

**Resultado esperado.** `Success. No rows returned`.

**Cómo comprobarlo:**

```sql
select column_name, data_type, column_default
from information_schema.columns
where table_schema = 'public' and table_name = 'correccion'
  and column_name = 'con_alertas';
```

Debe devolver **una fila**, de tipo `boolean` y con valor por omisión
`false`.

Y, de paso, compruebe que el semáforo sigue teniendo cuatro estados y no
cinco:

```sql
select enumlabel
from pg_enum
where enumtypid = 'semaforo'::regtype
order by enumsortorder;
```

Debe devolver exactamente **cuatro filas**: `VERDE`, `AMBAR`, `ROJO`,
`GRIS`. **Si aparece `VERDE_CON_ALERTAS`, avísenos**: significa que la
migración retirada llegó a aplicarse, y hay que resolverlo de otra manera
porque ese valor ya no se puede borrar.

**Cómo deshacerlo:**

```sql
alter table correccion drop column if exists con_alertas;
```

---

## Comprobación final

Cuando haya aplicado los cuatro, pegue esto una sola vez:

```sql
select
  (select count(*) from information_schema.columns
     where table_schema = 'public' and table_name = 'correccion'
       and column_name in ('informe', 'devolucion', 'aviso', 'con_alertas'))
    as columnas_de_correccion,
  (select count(*) from information_schema.columns
     where table_schema = 'public' and table_name = 'alumno'
       and column_name in ('centro_code', 'ccaa_code', 'curso',
                           'estado_matricula', 'platform_id',
                           'matricula_anterior'))
    as columnas_de_alumno,
  (select count(*) from pg_tables
     where schemaname = 'public' and tablename = 'ejecucion_motor')
    as tabla_de_consumo,
  (select count(*) from pg_enum where enumtypid = 'semaforo'::regtype)
    as estados_del_semaforo;
```

Lo correcto es:

| Columna | Valor esperado |
|---|---|
| `columnas_de_correccion` | 4 |
| `columnas_de_alumno` | 6 |
| `tabla_de_consumo` | 1 |
| `estados_del_semaforo` | **4** |

Si los cuatro números cuadran, está todo aplicado. Mándenos esa fila y lo
damos por cerrado.

## Si algo falla

Copie el mensaje de error entero y mándenoslo **sin ejecutar nada más**.
Ninguno de estos cambios borra datos existentes, así que un error a medias no
destruye nada: deja el cambio a medio aplicar, y como el SQL se puede repetir
sin daño, se corrige y se vuelve a ejecutar.
