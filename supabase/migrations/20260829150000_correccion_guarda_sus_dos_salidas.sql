-- Amplía `correccion` para poder reconstruir sus dos salidas enteras.
--
-- Task 12 guarda el análisis en las tres tablas que el esquema inicial ya
-- preveía: `correccion`, `valoracion_dimension` y `evidencia`. Esas tres
-- bastan para la parte estructurada del Anexo C -las doce dimensiones, cada
-- una con su cita capada a 1.500 caracteres por D-001-, pero el informe
-- lleva más bloques que el esquema inicial no dio dónde guardar: fortalezas
-- e indicios de autoría (cada uno con su propia cita), dudas para el
-- docente, reparos, dimensiones ausentes, si una valoración quedó marcada
-- como no localizada, y el Anexo D -la devolución para el alumno- entero.
-- Sin guardarlos, recargar la ficha después de analizar perdía justo lo que
-- el docente tiene que revisar: las prioridades y el borrador.
--
-- La solución no es siete tablas nuevas para siete listas de solo lectura:
-- es guardar el informe y la devolución completos, tal como los componen
-- `salidas/informe.py` y `salidas/borrador.py`, en dos columnas `jsonb`.
-- `valoracion_dimension` y `evidencia` se siguen escribiendo igual -es lo
-- estructurado, lo que un futuro informe por dimensión necesita consultar
-- con SQL, y lo que impone el límite de D-001 con un CHECK que un `jsonb`
-- no puede aplicar por sí solo-, pero dejan de ser lo único: son el
-- resumen consultable, no la fuente que se relee.
--
-- Ninguna columna nueva lleva el texto del trabajo del alumno ni el PDF
-- (§19): `informe` y `devolucion` son lo que el motor compuso sobre ese
-- texto -juicios, citas breves, prosa para el alumno-, nunca el texto en
-- sí. El límite de las citas, y el de la prosa que las acompaña -el
-- resumen, cada observación, las dudas, los reparos, y si la hay, la
-- devolución entera-, se comprueban en código antes de escribir
-- (backend/persistencia/correccion.py:validar_textos_acotados), por igual
-- en los dos almacenes, precisamente porque un `jsonb` no lleva ningún
-- CHECK. Sin el límite de la prosa, el de la cita se rodearía con
-- verbosidad: una observación sin tope podría llevar lo que la cita no
-- puede.

alter table correccion
  add column informe jsonb not null default '{}'::jsonb,
  add column devolucion jsonb,
  add column aviso text;

alter table correccion alter column informe drop default;

comment on column correccion.informe is
  'El Anexo C completo, tal como lo compone salidas/informe.py (Task 12). '
  'valoracion_dimension y evidencia guardan su parte estructurada aparte; '
  'esta columna es la que se relee para reconstruirlo entero.';
comment on column correccion.devolucion is
  'El Anexo D completo, o nulo si el análisis se completó sin borrador: '
  'informe válido, redacción fallida (InformeSinBorrador).';
comment on column correccion.aviso is
  'El aviso que vio el docente al guardar, si lo hubo -por ejemplo, que el '
  'borrador no se pudo completar-. Para que una recarga de la ficha lo siga '
  'diciendo igual, sin inventar uno nuevo a partir de una causa que ya no '
  'está en memoria.';
