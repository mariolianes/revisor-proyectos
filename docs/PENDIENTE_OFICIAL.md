# Pendiente de cierre oficial

Lo que este sistema **no sabe** y **no va a inventar**. Recoge el Anexo H del
Documento Maestro.

Esta lista es el catálogo completo de lo que falta, no un reflejo de lo que el
verificador vigila. Solo algunas entradas tienen hoy contrapartida en
`criteria/` con `estado: PENDIENTE_OFICIAL` —`ponderaciones` y `calendario`—;
las demás están aquí porque el dato no existe, aunque ningún fichero de
criterios las nombre todavía.

La parada automática ante un juicio que necesite uno de estos datos será
comportamiento del motor de corrección, conforme al §18.2 del Maestro, cuando
ese motor se construya. Hoy no hay motor: nada se detiene solo. Que
`proteccion_datos` o `politica_ia` figuren aquí no bloquea mecánicamente nada;
lo que hacen es constar.

## Pendientes

- **banco_calibracion** — *Recibido el 2026-08-28.* El docente entregó el
  documento de calibración inicial, incorporado como
  `docs/maestro/04-calibracion.md`. Aporta los niveles de prioridad P1-P4, la
  regla de economía pedagógica, la lectura calibrada del semáforo, el banco de
  casos P01-P09 y once pruebas de aceptación. **No aporta ponderaciones,
  rúbrica ni calendario**, que siguen pendientes más abajo. La propia
  calibración señala que la muestra no cubre la primera ni la segunda entrega,
  ni las modalidades de investigación y revisión documental: se ampliará con
  segundas entregas reales del curso.

- **ponderaciones** — reparto definitivo entre las cuatro entregas y la presentación. El Maestro §10 propone 20 % cada componente como modelo provisional, expresamente configurable hasta validarlo con la programación oficial. Se espera de la programación didáctica.
- **calendario** — fechas de validación del tema, de las cuatro entregas, de recuperación y de defensa. Se espera de la programación didáctica y del centro.
- **rubrica** — criterios oficiales, niveles, mínimos y causas de no superación. Se espera de la programación didáctica.
- **programacion_didactica** — programación aplicable por centro, sede, modalidad y comunidad autónoma. Es la fuente de la que cuelgan casi todas las demás entradas de esta lista, y hasta que llegue no se sabe siquiera cuál de las versiones en circulación rige. Anexo H, punto 47.
- **formato_definitivo** — formato, extensión y sistema de citas oficiales, si difieren de los de la guía. `criteria/v2026-2027/formato.yaml` trabaja hoy con los valores de la guía y del §6.2 del Maestro: Arial 11, interlineado 1,5, justificado, márgenes de 2,5 cm y un mínimo de 20 páginas de contenido. Si la programación fija otros, mandan los suyos. Anexo H, punto 51.
- **resultados_aprendizaje** — resultados y criterios de evaluación oficiales vinculados al Proyecto Intermodular. Se espera de la normativa del ciclo.
- **defensa** — duración, soporte, composición del tribunal y procedimiento de evaluación de la exposición. Se espera del centro.
- **politica_ia** — política institucional sobre autoría, uso de IA y evidencias admitidas. La Guía y el Índice comentado ya fijan la norma para el alumnado; falta la posición institucional que la respalde.

- **tolerancias_formato** — cuánta desviación se admite al comprobar el formato de un PDF antes de darlo por incumplido. `criteria/v2026-2027/formato.yaml` trabaja con ±0,5 puntos en el cuerpo de letra, ±0,1 en el interlineado y ±0,5 cm en los márgenes. Solo la de los márgenes tiene apoyo en la prosa, en el «aproximadamente 2,5 cm» del §6.2; las otras dos las puso quien destiló el YAML para que un PDF real no incumpla por redondeo. La del cuerpo de letra decide si un documento maquetado a 11,5 cumple o no, y esa es una decisión del docente. Registradas en `docs/changes/2026-08-27-interpretaciones-de-formato-dimensiones-y-fases.md`. Se espera del docente.
- **tutorias** — procedimiento de tutorías, correcciones y plazos de respuesta. Se espera del centro.
- **casos_especiales** — reglas para retrasos, cambios de tema y recuperación. Se espera del centro.
- **canal_devolucion** — cómo llega el feedback aprobado al alumno y qué marca exactamente el estado COMUNICADO. Decisión D-004, pendiente del docente.
- **equivalencia_interlineado** — a qué distancia entre líneas base
  corresponde el «1,5» que exige el §6.2. Un PDF no guarda el valor elegido
  en el procesador de textos, sino la separación real, y la conversión
  depende de la fuente: para Arial 11 a 1,5 líneas el ratio ronda 1,73. Hasta
  fijarlo, la comprobación del interlineado se emite como `NO_VERIFICABLE`
  con el ratio medido a la vista. Se espera del banco de calibración del §20.

## Resueltas

Lo que estuvo en la lista y ya no lo está. No se borra: saber que algo
estuvo pendiente, y por qué dejó de estarlo, es parte de poder reconstruir
con qué criterio se corrigió a un alumno.

- **proteccion_datos** — *Resuelta el 2026-08-30 por decisión del docente.* Ya no bloquea. El sistema se usa como herramienta personal del docente, en su equipo, sobre trabajos descargados legítimamente, y la protección se resuelve minimizando lo que sale en vez de deteniendo el desarrollo: identificador del alumno en lugar del nombre, correspondencia solo en local, y retirada de nombre, correo, teléfono y DNI antes de cada llamada. Ver D-013 y el §4 de la respuesta del docente del 2026-08-30. Si algún día la herramienta se comparte con el centro u otros docentes, su gobernanza vuelve a revisarse.

## Qué hacer cuando llegue uno

1. Se incorpora el dato a la prosa de `docs/maestro/`.
2. Si tiene contrapartida en `criteria/`, se le retira `estado:
   PENDIENTE_OFICIAL` y se pone el valor real. Si no la tiene, se crea el
   criterio que ahora ya se puede escribir.
3. Se borra la entrada de esta lista.
4. Se registra en `docs/changes/` y, si cambia una decisión, en `docs/decisions.md`.

El orden importa: primero la prosa, después el YAML.
