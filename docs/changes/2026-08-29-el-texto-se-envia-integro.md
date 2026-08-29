# El §19 recoge que el texto se envía íntegro al proveedor

**Fecha:** 2026-08-29
**Autor:** Marcos / colaborador técnico

## Que cambia

El §19 describía que el texto de la entrega se anonimizaba antes de
transmitirse al proveedor de análisis. No es así: el circuito real envía el
texto íntegro durante el procesamiento. Se sustituye la frase por esa
descripción y se añade una nota «Corregido por D-010 el 2026-08-29» junto a
la ya existente «Modificado por D-001».

Una primera redacción de ese mismo párrafo, el mismo día, decía además que el
texto «no se almacena allí ni en la base de datos», dando por hecho, sin
haberlo verificado, el comportamiento de retención del proveedor. Se corrige
en una segunda pasada: el párrafo separa ahora lo que el sistema garantiza
—no guarda copia, como ya decía la prosa dos frases antes— de lo que depende
de las condiciones del proveedor, sin confirmar, y remite a la cautela ya
existente del apartado que exige confirmarlas antes de usar entregas reales,
en vez de repetirla suelta.

El resto del §19 se conserva íntegro: qué se almacena en Supabase, qué no se
almacena en ninguna parte, el límite de una evidencia citada, las
credenciales técnicas en el backend local, las cautelas de tratamiento y la
prohibición de usar entregas reales antes de cerrar `proteccion_datos`.

En `docs/decisions.md`, D-002 describía el mismo circuito con las mismas dos
imprecisiones: la anonimización que no se aplica y la certeza no verificada
sobre la retención del proveedor. Se corrigen ambas con una nota de remisión
a D-010, dejando el resto de D-002 —el puerto `ProveedorAnalisis`, la clave
recibida el 2026-08-28, la reserva sobre entregas reales— intacto. Se
registra la decisión nueva D-010, que recoge también, en su propio texto, la
misma corrección de la segunda pasada.

## Por que

Una fuente superior no puede quedar contradiciendo al código: es el mismo
criterio que llevó a corregir el §19 y el §21.1 con D-001 al adoptar Supabase.
El §19 prometía una anonimización que el sistema no aplica; un apartado de
privacidad que describe un tratamiento que no existe es peor que no tenerlo,
porque nadie puede comprobar si el tratamiento real cumple lo que el
documento dice.

La misma razón alcanza a la retención del proveedor: R3 (`GOVERNANCE.md`)
exige marcar lo que no se sabe en vez de inventarlo, y esa exigencia no
distingue entre un dato que nadie ha fijado y un dato que nadie ha
verificado. Un apartado normativo sobre tratamiento de datos de alumnos no
puede dar por hecho el comportamiento de retención de un proveedor externo:
ese proveedor no está bajo el control de este sistema, y lo habitual en
proveedores de este tipo es retener por un plazo de control de abuso, así
que la afirmación retirada no solo era inverificable sino probablemente
incorrecta.

## Fuente que lo respalda

- Decisión del docente del 2026-08-29, registrada como D-010 en
  `docs/decisions.md`.
- Documento Maestro §14.1, jerarquía de fuentes y regla de conflicto: una
  fuente inferior (aquí, el comportamiento real del código) no puede
  contradecir a una superior sin que esta se corrija.
- `GOVERNANCE.md`, R3: lo pendiente, o lo no verificado, se marca y no se
  inventa.

## Que arrastra

- `docs/maestro/01-documento-maestro.md` (§19).
- `docs/decisions.md`: decisión nueva D-010 y notas de corrección en D-002.
- `criteria/.sincronia.json`: se vuelve a sellar por disciplina. Ninguna
  entrada de `criteria/` cita `maestro#19-privacidad` como fuente, así que
  ninguna ancla sellada cambia de valor.

Queda pendiente, fuera del alcance de esta corrección: `proteccion_datos`
sigue en `docs/PENDIENTE_OFICIAL.md` y sigue bloqueando que una entrega real
de un alumno se envíe al proveedor.

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema, y el
cambio no toca criterio alguno.

## Tercera pasada: redacción

La frase quedó como «Qué retiene el proveedor con el texto una vez recibido lo
rigen sus propias condiciones», que no concuerda: el sujeto es singular y el
verbo, plural. Se reescribe como «Lo que el proveedor retenga se rige por sus
propias condiciones» en el §19 y en las dos apariciones paralelas de
`docs/decisions.md`.

El significado no cambia. Se registra porque R5 no distingue entre cambiar lo
que dice la prosa maestra y cambiar cómo lo dice, y esa indistinción es
deliberada: quien audite el documento debe poder ver toda mano que lo tocó.
