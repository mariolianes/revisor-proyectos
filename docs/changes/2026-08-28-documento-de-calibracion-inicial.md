# Entra el documento de calibración inicial como cuarta fuente

**Fecha:** 2026-08-28
**Autor:** Marcos / colaborador técnico

## Que cambia

El docente entregó el «Documento de calibración inicial del sistema de
corrección y seguimiento», en `.docx`. Se incorpora convertido a Markdown como
`docs/maestro/04-calibracion.md`, con catorce anclas, y se registra en la lista
blanca de `tools/gobernanza/sincronia.py` con la clave `calibracion`.

La prosa es del docente y no se ha tocado: solo se han añadido las anclas, sin
las cuales ningún criterio podría citarlo. La conversión se verificó frase a
frase contra el original; el único texto que se perdió en un primer intento
—el recuadro de portada, el que dice que la calibración no modifica el
Documento Maestro— se recuperó antes de instalarlo.

El `.docx` original **no entra en el repositorio**: `.gitignore` lo excluye,
como a cualquier binario de ofimática.

### Criterios nuevos

**`criteria/v2026-2027/prioridades.yaml`.** Los cuatro niveles P1-P4 del §7 del
calibrador, con su efecto y con lo que cada uno puede llegar al alumno.

Esto resuelve además una infracción latente de R1 que nadie había detectado: el
tipo `prioridad` de la migración tiene cuatro valores —`CRITICA`, `ALTA`,
`MEDIA`, `BAJA`— mientras que el §7 del Documento Maestro solo habla de tres,
«carencias críticas, correcciones importantes y mejoras secundarias». El cuarto
valor estaba en la base de datos sin prosa que lo respaldara. El calibrador se
la da: P4, «no compensa el coste pedagógico», que no debe cargarse al alumno.

La correspondencia entre P1-P4 y el enum de la base de datos vive en ese
fichero y en ningún otro sitio. El criterio habla como el docente; la tabla
conserva su vocabulario.

**`criteria/v2026-2027/feedback.yaml`.** Los límites que la devolución no puede
cruzar: la regla de economía pedagógica —tres o cuatro prioridades como máximo,
aunque haya diez errores—, la forma de la devolución, lo que nunca puede
aparecer en el texto dirigido al alumno, los rasgos de estilo que conservar y
evitar, y lo que el sistema no debe exigir.

No describe cómo se redacta, que es criterio del docente. Describe los límites,
que sí son comprobables sobre el texto ya generado.

### Criterios ampliados

**`criteria/v2026-2027/semaforo.yaml`.** Cada color recibe la lectura calibrada
del §9, que precisa el significado sin sustituirlo, y se añade la advertencia
de que un trabajo puede estar verde en formato y ámbar en rigor cuantitativo:
la lectura por dimensiones se conserva y una apariencia impecable no arrastra
toda la valoración.

### Una discrepancia de nomenclatura, resuelta

El calibrador llama **AMARILLO** a lo que el Documento Maestro llama **ÁMBAR**.
Es el mismo estado con otro nombre. Por la regla de conflicto del §14.1, manda
la fuente superior. **Decisión del docente, 2026-08-28: se mantiene ÁMBAR**, y
el fichero de criterios deja constancia de cómo lo llama él.

### Gobernanza

`tools/gobernanza/criterios.py` acepta ahora `calibracion` como documento
válido en un ancla y en una fuente, junto a `maestro`, `indice` y `guia`. El
mensaje de infracción de R1 lo enumera.

El registro de sincronía se ha vuelto a sellar: pasa de ocho a doce secciones
selladas, las cuatro nuevas del calibrador.

## Por que

El §20 del Documento Maestro preveía un banco de calibración y el §14.1 le
reserva expresamente el quinto nivel de la jerarquía de fuentes: «Manual
docente, banco de feedback y casos calibrados». Este documento ocupa ese hueco.

No contradice ninguna fuente superior. Al contrario: su propia jerarquía
interna coincide punto por punto con la del §14.1, y su recuadro de apertura
declara que no modifica el Documento Maestro ni crea criterios académicos
nuevos. Lo que aporta es concreción de principios que ya existían —la
«Proporción» del §7 se vuelve un máximo de tres o cuatro prioridades— y una
fuente para el cuarto nivel de prioridad, que la base de datos ya usaba sin
tenerla.

## Fuente que lo respalda

- Documento Maestro §14.1, que reserva el nivel 5 de la jerarquía a
  «Manual docente, banco de feedback y casos calibrados».
- Documento Maestro §20, que prevé el banco de calibración.
- El propio documento de calibración, entregado por el docente el 2026-08-28.
- Decisión del docente sobre ÁMBAR frente a AMARILLO, misma fecha.

## Que arrastra

- `docs/maestro/04-calibracion.md` (nuevo).
- `criteria/v2026-2027/prioridades.yaml` y `feedback.yaml` (nuevos).
- `criteria/v2026-2027/semaforo.yaml` (ampliado, sin cambiar significados).
- `tools/gobernanza/sincronia.py` y `criterios.py` (aceptan el documento nuevo).
- `criteria/.sincronia.json` (resellado, de 8 a 12 secciones).

**Lo que NO arrastra, y conviene decirlo:** las ponderaciones, la rúbrica y el
calendario siguen en `docs/PENDIENTE_OFICIAL.md`. Este documento calibra el
criterio, no lo cuantifica. **Sigue sin haber nota propuesta**, y el
interlineado sigue sin poder juzgarse.

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema.
