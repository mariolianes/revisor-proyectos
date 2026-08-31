# El semáforo pasa a cuatro niveles, con regla fronteriza, y el borrador se valida contra el color propuesto

**Fecha:** 2026-08-31
**Autor:** Marcos / colaborador técnico

## Que cambia

Dos ajustes pedidos por el docente, D-019 y D-020 en `docs/decisions.md`:

**1. El semáforo gana un cuarto nivel, VERDE_CON_ALERTAS, entre VERDE y
ÁMBAR.** `criteria/v2026-2027/semaforo.yaml` registra la nueva entrada.
`backend/salidas/informe.py` cambia el mapeo P3 → AMBAR por P3 → VERDE_
CON_ALERTAS -sin tocar P1 → ROJO ni P2 → AMBAR-, y `CODIGOS_SEMAFORO` /
`SEVERIDAD_SEMAFORO` ganan el quinto código
(`GRIS: -1, VERDE: 0, VERDE_CON_ALERTAS: 1, AMBAR: 2, ROJO: 3`).

Antes, ante la duda entre dos colores adyacentes, el sistema elegía siempre
el más severo: un P2 y un P3 llegaban los dos a AMBAR, aunque el §7 del
calibrador describe P3 como algo que «refina, pero no cambia el nivel
global». La regla fronteriza del docente lo invierte para la mitad ÁMBAR/
VERDE: «usar verde con alertas cuando todos los mínimos estén cumplidos».
La mitad ROJO/ÁMBAR no exigía cambio de código: ROJO ya solo sale de un P1
fiable -verificado contra `evidencia_localizada`-, y un P1 fiable ES la
«carencia crítica demostrable» que la regla exige para ROJO.

**Hueco que queda abierto, a propósito.** «VERDE_CON_ALERTAS» no existe como
nivel formal en el §12.1 del Documento Maestro (`maestro#12-errores-y-
semaforo`) ni en el §9 del calibrador (`calibracion#9-semaforo`): los dos
siguen enumerando solo VERDE, ÁMBAR, ROJO y GRIS. La palabra sí aparece,
aplicada al caso P05, en el banco de casos del §6 del calibrador
(`calibracion#6-banco-de-casos`). El nuevo criterio usa esa sección como
`fuente` -es un ancla real, y el término está en la prosa, no inventado-,
pero dos campos de la entrada (`fuente_pendiente_en_maestro` y el `calibrado`
de la propia entrada) dicen sin adornarlo que el nivel no está formalizado
en el §12.1 ni en el §9. No se toca `docs/maestro/` en este cambio: el
docente pidió expresamente no rehacerlo, y decidir si formaliza el nivel
allí queda para él. Ver el informe de esta tarea
(`.superpowers/sdd/2026-08-31-ajustes-del-docente/semaforo-coherencia-report.md`).

**2. `backend/salidas/borrador.py` rechaza un borrador cuyo semáforo
propuesto dice más de lo que sostienen, por sí solas, las prioridades que van
a generar sus `acciones`.** Nueva comprobación,
`_semaforo_y_acciones_incoherentes`, hermana de `_viola_una_regla_dura` pero
estructural, no textual: compara `semaforo_por_valoraciones(analisis.
valoraciones)` contra la nueva `color_sostenido_por_prioridades(elegidas)`
(`backend/salidas/informe.py`). Se aplica antes de llamar al motor. También
se añade `_calibrado_por_color`, que inyecta en `instruccion_de_devolucion`
el texto `calibrado` del color ya calculado -reutilizado de
`semaforo.yaml`, no inventado-, para que el motor redacte sobre esa
severidad en vez de inferirla.

## Por que

**(1)** Instrucción directa del docente, dada como regla literal en esta
tarea: los cuatro niveles y la regla fronteriza citada arriba, cerrando
además con «la prudencia no significa elegir siempre el color más bajo».

**(2)** Objeción del docente sobre un caso real: un borrador de ejemplo para
P07 (ROJO) hablaba de «avance sólido», «fase de afinado» y «cuatro
retoques» -lenguaje de ámbar alto o de verde con alertas, no de una
insuficiencia global-. Pidió un validador que compruebe, antes de liberar el
borrador, que apertura, prioridades, cierre y semáforo cuentan la misma
historia.

## Fuente que lo respalda

Instrucción directa del docente en esta tarea (2026-08-31), análoga en
naturaleza a la decisión del 2026-08-28 que ya registra este mismo fichero
(«se mantiene AMBAR»): una instrucción dada en conversación con el
responsable del proyecto, no todavía trasladada a `docs/maestro/`. Para el
término «verde con alertas» en sí, la fuente documental existente es
`calibracion#6-banco-de-casos` (caso P05), tal como queda registrado en el
criterio.

## Que arrastra

- `criteria/v2026-2027/semaforo.yaml` (YAML; sin tocar prosa)
- `backend/salidas/informe.py`
- `backend/salidas/borrador.py`
- `frontend/src/lib/tipos.ts`
- `frontend/src/paginas/Revision.tsx`
- `supabase/migrations/20260831093000_semaforo_verde_con_alertas.sql`
  (escrita en este cambio; la aplica el docente desde el panel, no un token
  personal — ver `docs/decisions.md` D-001 y la instrucción permanente sobre
  Supabase)
- `docs/decisions.md` (D-019, D-020)
- `criteria/.sincronia.json` (resellado con `--sellar` tras este cambio)

## Correcciones cerradas afectadas

Ninguna. `criteria/v2026-2027/` no está congelada todavía (no existe
`criteria/v2026-2027/.congelada`): no hay ninguna corrección aprobada con
esta versión de criterios cuyo semáforo pudiera quedar retroactivamente
distinto.
