# Las fases que el docente no confirma dejan de contar como si lo estuvieran

**Fecha:** 2026-09-02
**Autor:** Marcos / colaborador técnico

## Que cambia

P01, P02, P04 y P09 pasan de `fase: E3` —que era una suposición nuestra— a
`fase: DESCONOCIDA`. El arnés de calibración los sigue ejecutando, pero **su
color no se compara con nada** y no entra en el recuento de semáforos.

Lo que no depende de la fase —evidencias localizadas, incidencias por
taxonomía, frases que no deberían aparecer— sigue contando en ellos: él pidió
mantenerlos «como pruebas generales de estructura, calidad y detección».

El informe dice, cuando ocurre, cuántos casos quedaron fuera del recuento y
por qué. Un recuento sobre menos casos de los que se ejecutaron se lee como
si fueran todos, si no se avisa.

## Por que

Porque el sistema activa dimensiones distintas según la fase. Comparar el
color de un trabajo cuya fase nadie ha confirmado **no mide el sistema: mide
nuestra suposición**. Todas las cifras de semáforo que le hemos dado hasta
hoy incluían esos cuatro casos.

## Fuente que lo respalda

`decisiones#11-fases-desconocidas`: «registrar phase: UNKNOWN», «no
utilizarlos en métricas o comparaciones sensibles a la fase», «no asumir E03
ni FINAL sin evidencia», «no condicionar la implantación a resolver una
información histórica que no está disponible».

## Que arrastra

`tools/calibrar.py` (`FASE_DESCONOCIDA`, `ResultadoDeCaso.fase_desconocida`,
`InformeDeCalibracion.sin_fase_confirmada`, y el recuento acotado a los
comparables), `docs/calibracion/casos.example.yaml` y
`tests/tools/test_calibrar.py`.

**Una decisión que conviene explicar.** El motor no sabe analizar «sin
fase»: hay que darle una. Un caso de fase desconocida se ejecuta con la vara
de la entrega final, que es la única que no deja ninguna dimensión fuera, y
así el caso sigue sirviendo para lo que él lo quiere. Eso **no** es asumir
que sea la entrega final —lo que él prohíbe—: es elegir cómo ejecutarlo, y
precisamente por eso su semáforo no se compara con nada.

## Correcciones cerradas afectadas

Ninguna en la base de datos. Sí quedan afectadas, hacia atrás, todas las
cifras de coincidencia de semáforo que se le han comunicado: se calcularon
sobre nueve casos y cuatro de ellos no eran comparables. La próxima
calibración dará la cifra sobre cinco, y lo dirá.
