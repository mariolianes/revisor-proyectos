-- «Verde con alertas» deja de ser un color y pasa a ser una marca sobre VERDE.
--
-- El docente lo decidió el 2026-09-02 (docs/maestro/05-decisiones-arquitectura.md,
-- §12): «Verde con alertas no será un quinto estado. Se implementará como
-- VERDE acompañado por alertas estructuradas o por un indicador
-- complementario. Mantener el enum de cuatro estados del Documento Maestro.
-- El calibrador puede añadir alertas o matices, pero no crear un color
-- oficial nuevo.»
--
-- Por eso NO se toca el tipo `semaforo`: sigue teniendo exactamente los
-- cuatro valores del esquema inicial (VERDE, AMBAR, ROJO, GRIS). Se retiró
-- la migración que iba a añadirle un quinto valor antes de aplicarla; un
-- valor de un enum de PostgreSQL no se puede quitar una vez añadido, así
-- que aplicarla habría dejado en la base un estado que el Documento Maestro
-- no reconoce y que ya no se podría eliminar.
--
-- Lo que sí se añade es la marca. `con_alertas` acompaña al semáforo
-- propuesto: es VERDE, avanza, pero conserva algo que conviene atender
-- antes del cierre -en la práctica, algún hallazgo P3 fiable sin ningún P1
-- ni P2-. Se deja en el semáforo propuesto y no en el aprobado porque la
-- marca la calcula el sistema; lo que el docente aprueba es el color.
--
-- Aplicación: la ejecuta el docente desde el panel de Supabase, nunca un
-- token personal (instrucción permanente del proyecto).

alter table correccion
  add column if not exists con_alertas boolean not null default false;

comment on column correccion.con_alertas is
  'VERDE que conserva defectos importantes por atender antes del cierre. '
  'No es un color: el semáforo sigue siendo uno de los cuatro oficiales. '
  'Ver docs/maestro/05-decisiones-arquitectura.md, §12.';
