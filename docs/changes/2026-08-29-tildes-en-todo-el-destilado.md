# El resto del destilado recupera sus tildes

**Fecha:** 2026-08-29
**Autor:** Marcos

## Que cambia

Treinta y un textos de `criteria/v2026-2027/` estaban sin tildes:
`Revision docente y plan de correccion` en `semaforo.yaml`, `Avance o
valoracion general` en `feedback.yaml`, `Afirmaciones categoricas de autoria`,
`Verificacion exhaustiva de cada cifra`, y así en siete ficheros. Ahora todos
llevan la ortografía correcta.

Ningún criterio cambia de significado. No se toca ningún código, ninguna
ancla, ninguna línea `fuente:` ni ningún valor numérico: solo el texto
legible.

## Por que

Es la continuación del cambio del mismo día sobre los nombres de dimensión, y
la razón es la misma: estos textos no se quedan en el YAML. `semaforo.yaml`
alimenta el campo `recomendacion` del informe técnico, y `feedback.yaml`
alimenta la instrucción que se manda al motor y las reglas del borrador de
devolución. Un informe que le dice al profesor «Revision docente y plan de
correccion» está mal escrito en el sitio donde menos se puede permitir.

Salió a la luz al activar R8, la regla que verifica las tildes de la prosa.
Antes no existía y el verificador daba «0 infracciones» sobre un destilado
entero sin acentuar.

## Fuente que lo respalda

Ninguna novedad normativa: la prosa de `docs/maestro/` ya está correctamente
acentuada y R2 establece que el destilado la sigue. Este cambio elimina una
divergencia entre ambos, no introduce criterio nuevo.

## Que arrastra

- `criteria/v2026-2027/`: `dimensiones.yaml`, `feedback.yaml`,
  `matriz-fases.yaml`, `ponderaciones.yaml`, `prioridades.yaml`,
  `reglas-parada.yaml`, `semaforo.yaml`.
- `criteria/.sincronia.json` — resellado.
- `tests/salidas/test_informe.py` — una aserción comparaba con el texto sin
  tilde de `semaforo.yaml`; se actualiza al texto correcto.

## Correcciones cerradas afectadas

Ninguna. El sistema no ha procesado ninguna entrega real: sigue bloqueado a la
espera de confirmar las condiciones de tratamiento de datos.
