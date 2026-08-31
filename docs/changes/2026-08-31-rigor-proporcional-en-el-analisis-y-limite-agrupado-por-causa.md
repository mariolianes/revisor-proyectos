# El rigor proporcional llega a la instrucción de análisis y el límite se agrupa por causa

**Fecha:** 2026-08-31
**Autor:** Marcos / colaborador técnico

## Que cambia

Dos ajustes de calibración, pedidos por el docente a partir de un caso real
(proyecto de importación textil, ver `docs/decisions.md`, D-019 para el
razonamiento completo):

1. `backend/analisis/instruccion.py` ahora lee `no_exigir` y
   `priorizar_siempre` de `criteria/<version>/feedback.yaml` y se lo dice al
   motor con ejemplos concretos -indicadores de logro, flujo de caja, ratios
   financieros, análisis de sensibilidad-. Antes, esos dos bloques solo se
   usaban al redactar el borrador (`backend/salidas/borrador.py`), después de
   que el motor ya hubiera podido generar un hallazgo P1/P2 pidiéndolos como
   requisito general.

2. `backend/salidas/seleccion.py` ya no elige las cuatro observaciones de
   mayor prioridad sin más: agrupa las candidatas por la causa raíz que
   `agrupacion_de_causa` (nuevo, en `feedback.yaml`) asigna a cada dimensión,
   colapsa cada grupo a su hallazgo de mayor prioridad, y solo entonces
   aplica el límite. El límite mismo deja de ser fijo: `_maximo` ahora
   calcula el semáforo del análisis (`semaforo_por_valoraciones`, movida de
   `backend/salidas/informe.py` a `backend/analisis/verificacion.py`) y
   busca en `prioridades_maximas_por_semaforo` -AMBAR: 3, ROJO: 4- antes de
   caer en el `prioridades_maximas` de siempre.

Efecto secundario, no pedido pero descubierto al resellar R2 tras el punto 2:
`tools/gobernanza/sincronia.py` no reconocía `calibracion` como prefijo
válido de "la siguiente ancla", así que dentro de `04-calibracion.md` -que
solo lleva anclas `calibracion#...`- el cuerpo de cada sección se extendía
hasta el final del fichero. Se corrige y se añade un test de regresión.

## Por que

El docente, con el ejemplo de un proyecto real, señaló que el sistema pedía
indicadores de logro, flujo de caja, ratios (ROI, margen neto) y análisis de
sensibilidad como si fueran exigencias generales, y que las cuatro
prioridades trasladadas al alumno eran cuatro hallazgos aislados en vez de
las causas que más explican la calidad global del trabajo. Pidió también que
el límite de cuatro no sea fijo: dos o tres en un trabajo sólido, tres o
cuatro en uno con carencias más profundas, bien agrupadas.

## Fuente que lo respalda

- `docs/maestro/04-calibracion.md` §2 (ampliado en este mismo cambio, con la
  petición del docente del 2026-08-31): §2.2 (qué no debe exigir el
  sistema), §2.3 (economía pedagógica, ahora con el límite variable), §2.4
  (qué debe priorizarse siempre) y §2.5 (agrupación por causa raíz), nuevos
  o ampliados.
- El ejemplo real de corrección que el docente aportó como motivo del
  cambio, sobre un proyecto de importación textil.

## Que arrastra

- `docs/maestro/04-calibracion.md` (§2.2-2.5 nuevos o ampliados; fila P07 del
  §6, con más detalle sobre el mismo caso).
- `criteria/v2026-2027/feedback.yaml` (`no_exigir` ampliado con las
  herramientas financieras avanzadas; `priorizar_siempre` y
  `agrupacion_de_causa`, nuevos; `economia_pedagogica` con
  `prioridades_maximas_por_semaforo`).
- `backend/analisis/instruccion.py` (lee `priorizar_siempre` y `no_exigir`).
- `backend/analisis/verificacion.py` (`semaforo_por_valoraciones`,
  `CODIGOS_SEMAFORO`, `SEVERIDAD_SEMAFORO`, movidas desde
  `backend/salidas/informe.py` para que `seleccion.py` las pueda importar sin
  crear un ciclo).
- `backend/salidas/informe.py` (reexporta los tres nombres anteriores; nada
  de su comportamiento cambia).
- `backend/salidas/seleccion.py` (agrupación por causa raíz y límite
  variable por semáforo).
- `tools/gobernanza/sincronia.py` (`PATRON_CUALQUIER_ANCLA` reconoce
  `calibracion` como prefijo de ancla válido).
- `criteria/.sincronia.json` (resellado).
- Tests: `tests/analisis/test_instruccion.py`,
  `tests/salidas/test_seleccion.py`, `tests/salidas/test_informe.py`,
  `tests/salidas/test_borrador.py`, `tests/gobernanza/test_sincronia.py`.

**Lo que NO arrastra:** ninguna nota, ponderación ni rúbrica -siguen
`PENDIENTE_OFICIAL`-. Este cambio no toca `calcular_nota_interna` ni ninguna
otra pieza reservada al §13.

## Correcciones cerradas afectadas

Ninguna. La versión `v2026-2027` no está congelada (no se ha aprobado
ninguna corrección todavía con ella).
