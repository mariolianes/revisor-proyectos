# Documentos maestros

Estos tres ficheros son la fuente de verdad del sistema. El PDF del que
proceden es, desde el 2026-08-26, una copia histórica.

| Fichero | Qué responde | Destinatario |
|---|---|---|
| `01-documento-maestro.md` | Cómo se corrige | Interno |
| `02-indice-comentado.md` | Qué debe contener cada apartado | Alumnado |
| `03-guia-desarrollo.md` | Cómo se trabaja el curso | Alumnado |

## Anclas

Cada sección referenciable lleva, en la línea anterior a su encabezado, un
ancla con esta forma:

    <!-- ancla: maestro#8-dimensiones -->

Los criterios de `criteria/` apuntan a estas anclas mediante su campo
`fuente`. **Borrar o renombrar un ancla deja criterios huérfanos y el
verificador lo rechaza.** Si necesitas reorganizar un documento, cambia
primero el ancla en el YAML que la usa.

## Cómo se cambia un criterio

Se edita aquí, nunca en el YAML. Consulta `GOVERNANCE.md`.
