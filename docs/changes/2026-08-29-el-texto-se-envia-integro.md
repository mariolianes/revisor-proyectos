# El §19 recoge que el texto se envía íntegro al proveedor

**Fecha:** 2026-08-29
**Autor:** Marcos / colaborador técnico

## Que cambia

El §19 describía que el texto de la entrega se anonimizaba antes de
transmitirse al proveedor de análisis. No es así: el circuito real envía el
texto íntegro durante el procesamiento, no lo almacena allí ni en la base de
datos, y la clave de la API reside solo en el backend local. Se sustituye la
frase por esa descripción y se añade una nota «Corregido por D-010 el
2026-08-29» junto a la ya existente «Modificado por D-001».

El resto del §19 se conserva íntegro: qué se almacena en Supabase, qué no se
almacena en ninguna parte, el límite de una evidencia citada, las
credenciales técnicas en el backend local, las cautelas de tratamiento y la
prohibición de usar entregas reales antes de cerrar `proteccion_datos`.

En `docs/decisions.md`, D-002 describía el mismo circuito con la misma
anonimización inexistente en dos frases. Se corrigen ambas y se añade una
nota de remisión a D-010, dejando el resto de D-002 —el puerto
`ProveedorAnalisis`, la clave recibida el 2026-08-28, la reserva sobre
entregas reales— intacto. Se registra la decisión nueva D-010.

## Por que

Una fuente superior no puede quedar contradiciendo al código: es el mismo
criterio que llevó a corregir el §19 y el §21.1 con D-001 al adoptar Supabase.
El §19 prometía una anonimización que el sistema no aplica; un apartado de
privacidad que describe un tratamiento que no existe es peor que no tenerlo,
porque nadie puede comprobar si el tratamiento real cumple lo que el
documento dice.

## Fuente que lo respalda

- Decisión del docente del 2026-08-29, registrada como D-010 en
  `docs/decisions.md`.
- Documento Maestro §14.1, jerarquía de fuentes y regla de conflicto: una
  fuente inferior (aquí, el comportamiento real del código) no puede
  contradecir a una superior sin que esta se corrija.

## Que arrastra

- `docs/maestro/01-documento-maestro.md` (§19).
- `docs/decisions.md`: decisión nueva D-010 y nota de corrección en D-002.
- `criteria/.sincronia.json`: se vuelve a sellar por disciplina. Ninguna
  entrada de `criteria/` cita `maestro#19-privacidad` como fuente, así que
  ninguna ancla sellada cambia de valor.

Queda pendiente, fuera del alcance de esta corrección: `proteccion_datos`
sigue en `docs/PENDIENTE_OFICIAL.md` y sigue bloqueando que una entrega real
de un alumno se envíe al proveedor.

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema, y el
cambio no toca criterio alguno.
