# El semáforo vuelve a cuatro estados: «verde con alertas» es una marca, no un color

**Fecha:** 2026-09-02
**Autor:** Marcos / colaborador técnico

## Que cambia

El docente cerró la pregunta que quedaba abierta desde el 31 de agosto
(`decisiones#12-semaforo`, `docs/maestro/05-decisiones-arquitectura.md`):

> «Verde con alertas no será un quinto estado. Se implementará como VERDE
> acompañado por alertas estructuradas o por un indicador complementario, por
> ejemplo `alerts[]` o `borderline: true`. [...] Mantener el enum de cuatro
> estados del Documento Maestro. El calibrador puede añadir alertas o
> matices, pero no crear un color oficial nuevo.»

Se revierte, por tanto, la mitad de D-019 que introducía VERDE_CON_ALERTAS
como quinto código. **No se revierte la regla que lo motivaba**, que él
mantiene: un P3 fiable sin ningún P1 ni P2 sigue sin subir a ÁMBAR. Lo que
cambia es cómo se expresa: da VERDE, y lo que queda por atender viaja al
lado.

- `criteria/v2026-2027/semaforo.yaml` pierde la entrada VERDE_CON_ALERTAS.
  La entrada VERDE recoge el matiz y gana `fuente_alertas:
  decisiones#12-semaforo`.
- `backend/analisis/verificacion.py`: `SEMAFORO_POR_PRIORIDAD` pasa a
  `P3 → VERDE`; `CODIGOS_SEMAFORO` y `SEVERIDAD_SEMAFORO` vuelven a cuatro.
  Nace `hay_alertas()`, que devuelve `True` solo sobre un VERDE con algún P3
  fiable.
- `backend/salidas/informe.py`: el `Informe` gana `con_alertas: bool`.
- `frontend/src/lib/tipos.ts` y `Revision.tsx`: mismos cuatro códigos y mismo
  mapeo, para que el anticipo de pantalla siga coincidiendo con el servidor.

## La migración que no llegó a aplicarse

`20260831093000_semaforo_verde_con_alertas.sql` **se retira sin haberse
aplicado**, y esto es lo importante del cambio: un valor añadido a un `enum`
de PostgreSQL **no se puede quitar**. Si el docente la hubiera ejecutado
antes de esta decisión, la base habría quedado con un estado que el Documento
Maestro no reconoce y que ya no habría forma de eliminar.

En su lugar entra `20260902190000_alertas_sobre_verde.sql`, que no toca el
tipo `semaforo` -sigue con sus cuatro valores del esquema inicial- y añade
`correccion.con_alertas`, un booleano con valor por omisión `false`.

## Por qué no se toca `docs/maestro/01-documento-maestro.md`

Porque nunca llegó a decir otra cosa: el §12.1 siempre enumeró VERDE, ÁMBAR,
ROJO y GRIS. El quinto nivel vivió doce días solo en el destilado y en el
código, declarado como hueco abierto. Esta decisión no corrige el Maestro:
confirma que tenía razón.

## Qué protege esto

`test_los_codigos_son_los_cuatro_oficiales_y_ninguno_mas`, en
`tests/salidas/test_informe.py`, comprueba el conjunto exacto de códigos en
las dos tablas. Es deliberadamente estricto -compara conjuntos, no
pertenencia- porque el coste de equivocarse es asimétrico: un color de más
aquí es irreversible en la base de datos.

## Por que

Porque lo decidió el docente, y porque el enum de PostgreSQL hace el error
irreversible. Su razón es de jerarquía: el Documento Maestro fija cuatro
estados oficiales, y el calibrador -nivel 5 del §14.1- puede concretar lo que
aquel deja abierto, pero no crear un color que aquel no reconoce.

## Fuente que lo respalda

`decisiones#12-semaforo`, en `docs/maestro/05-decisiones-arquitectura.md`,
documento normativo nuevo del 2026-09-02 que recoge sus respuestas a las ocho
preguntas de arquitectura. Confirma `maestro#12-errores-y-semaforo`, que
nunca enumeró más de cuatro.

## Que arrastra

`criteria/v2026-2027/semaforo.yaml`, `backend/analisis/verificacion.py`,
`backend/salidas/informe.py`, `frontend/src/lib/tipos.ts`,
`frontend/src/paginas/Revision.tsx`, `tests/salidas/test_informe.py`,
`tools/gobernanza/sincronia.py` (registra el documento nuevo),
`criteria/.sincronia.json` (resellado),
`supabase/migrations/20260831093000_semaforo_verde_con_alertas.sql`
(retirada) y `supabase/migrations/20260902190000_alertas_sobre_verde.sql`
(nueva).

## Correcciones cerradas afectadas

Ninguna. El quinto código nunca llegó a la base de datos -su migración no se
aplicó- ni existe ninguna corrección cerrada con ese valor. Las correcciones
guardadas hasta hoy llevan uno de los cuatro colores oficiales, y
`con_alertas` entra con valor por omisión `false`, así que no reinterpreta
ninguna decisión ya tomada por el docente.
