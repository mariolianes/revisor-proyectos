# El destilado recupera las tildes de la prosa maestra

**Fecha:** 2026-08-29
**Autor:** Marcos

## Que cambia

Los doce nombres de dimensión de `criteria/v2026-2027/dimensiones.yaml`
estaban sin tildes —«Fundamentacion y fuentes»— mientras la tabla del §8 del
Documento Maestro los tiene acentuados —«Fundamentación y fuentes»—. Lo mismo
en el campo `observa` de ocho dimensiones, y en dos campos de
`prioridades.yaml` frente a la tabla del §7 del documento de calibración
(«Critico», «coste pedagogico»).

Ahora los dieciocho campos coinciden carácter por carácter con su fuente.
Ningún código, ninguna ancla y ninguna línea `fuente:` cambia: solo el texto
legible.

## Por que

R2 establece que la prosa manda sobre el destilado. El destilado se había
desviado, y la desviación no se quedaba en el fichero: estos nombres entran
en la instrucción que se manda al modelo, y de ahí pasan al informe técnico
que lee el profesor y al borrador que lee el alumno. Un informe de corrección
que escribe «Redaccion y presentacion» al valorar la redacción de un trabajo
académico se desautoriza solo.

Salió a la luz al leer la instrucción generada por el módulo nuevo de la
Parte B, que es la primera vez que estos nombres se ven fuera del YAML.

## Fuente que lo respalda

Las dos fuentes ya vigentes, sin novedad normativa: la tabla de dimensiones
del §8 del Documento Maestro (`maestro#8-dimensiones`) y la tabla de niveles
de prioridad del §7 del documento de calibración
(`calibracion#7-prioridades`). Los valores se han tomado de ellas, no
escritos a mano.

## Que arrastra

- `criteria/v2026-2027/dimensiones.yaml` — diez campos.
- `criteria/v2026-2027/prioridades.yaml` — dos campos.
- `criteria/.sincronia.json` — resellado.
- `tests/analisis/test_instruccion.py` — tres tests afirmaban los nombres sin
  tilde y fallaron al hacer el cambio. Es la alarma funcionando: esos tests
  leen los criterios reales para que un cambio en ellos no pase inadvertido.
  Actualizados a los nombres correctos.

## Correcciones cerradas afectadas

Ninguna. No hay ninguna corrección aprobada todavía: el sistema no ha
procesado ninguna entrega real, que sigue bloqueado a la espera de confirmar
las condiciones de tratamiento de datos.
