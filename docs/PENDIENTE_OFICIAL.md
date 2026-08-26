# Pendiente de cierre oficial

Lo que este sistema **no sabe** y **no va a inventar**. Recoge el Anexo H del
Documento Maestro.

Cada entrada de esta lista se corresponde con una clave marcada
`estado: PENDIENTE_OFICIAL` en `criteria/`. Mientras siga aquí, el sistema se
detiene ante cualquier juicio que la necesite, conforme al §18.2 del Maestro.

## Pendientes

- **ponderaciones** — reparto definitivo entre las cuatro entregas y la presentación. El Maestro §10 propone 20 % cada componente como modelo provisional, expresamente configurable hasta validarlo con la programación oficial. Se espera de la programación didáctica.
- **calendario** — fechas de validación del tema, de las cuatro entregas, de recuperación y de defensa. Se espera de la programación didáctica y del centro.
- **rubrica** — criterios oficiales, niveles, mínimos y causas de no superación. Se espera de la programación didáctica.
- **resultados_aprendizaje** — resultados y criterios de evaluación oficiales vinculados al Proyecto Intermodular. Se espera de la normativa del ciclo.
- **defensa** — duración, soporte, composición del tribunal y procedimiento de evaluación de la exposición. Se espera del centro.
- **politica_ia** — política institucional sobre autoría, uso de IA y evidencias admitidas. La Guía y el Índice comentado ya fijan la norma para el alumnado; falta la posición institucional que la respalde.
- **proteccion_datos** — condiciones de tratamiento aplicables y régimen de uso de herramientas externas. Bloquea el piloto con entregas reales.
- **tutorias** — procedimiento de tutorías, correcciones y plazos de respuesta. Se espera del centro.
- **casos_especiales** — reglas para retrasos, cambios de tema y recuperación. Se espera del centro.
- **canal_devolucion** — cómo llega el feedback aprobado al alumno y qué marca exactamente el estado COMUNICADO. Decisión D-004, pendiente del docente.

## Qué hacer cuando llegue uno

1. Se incorpora el dato a la prosa de `docs/maestro/`.
2. Se retira `estado: PENDIENTE_OFICIAL` del YAML y se pone el valor real.
3. Se borra la entrada de esta lista.
4. Se registra en `docs/changes/` y, si cambia una decisión, en `docs/decisions.md`.

El orden importa: primero la prosa, después el YAML.
