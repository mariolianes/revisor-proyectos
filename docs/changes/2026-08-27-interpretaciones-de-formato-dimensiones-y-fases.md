# Se registran tres interpretaciones que el YAML presentaba como derivadas

**Fecha:** 2026-08-27
**Autor:** Marcos / colaborador técnico

## Que cambia

Ningún criterio cambia de valor. Lo que cambia es que tres decisiones que
estaban en `criteria/v2026-2027/` sin decir que eran decisiones quedan
registradas como lo que son: interpretación de quien destiló la prosa, no
prosa del docente.

Son las tolerancias de formato (`tolerancia_cuerpo`, `interlineado.tolerancia`
y `margenes.tolerancia`), el reparto completo de `activa_en` en
`dimensiones.yaml` y el `TEMA: evaluable: false` de `matriz-fases.yaml`.

Las tres siguen en el YAML con el mismo valor y la misma `fuente`. Este
documento no las corrige: las hace visibles.

## Por que

La regla madre del §14.1 es que una fuente inferior no contradiga a una
superior. Presentar como derivado del Maestro algo que el Maestro no dice es
una forma silenciosa de contradecirlo: quien lea el YAML dentro de un año dará
por hecho que esas cifras las escribió el docente, y no es así.

R1 comprueba que el ancla citada existe, no que la sección diga lo que el
criterio afirma. Ese hueco solo se tapa por escrito.

## Fuente que lo respalda

Ninguna fuente de la jerarquía del §14.1 respalda estos tres valores: por eso
son interpretación y no criterio. El acuerdo interno que las sostiene mientras
tanto es este documento, y las tolerancias quedan además anotadas en
`docs/PENDIENTE_OFICIAL.md` para que el docente las confirme o las cambie.

## Que arrastra

- `docs/PENDIENTE_OFICIAL.md` (entrada nueva `tolerancias_formato`)
- Ningún fichero de `criteria/`: los valores no se tocan.

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema.

## Interpretación registrada

**1. Las tres tolerancias de `formato.yaml`.** El §6.2 del Maestro da valores
exactos —Arial 11, interlineado 1,5, texto justificado— y solo admite margen
en los márgenes: «regulares, aproximadamente 2,5 cm». Las tres tolerancias del
YAML citan `maestro#6-estandar-academico`, pero dos de ellas no salen de ahí.

Existen porque la comprobación se hace sobre un PDF y un PDF no devuelve nunca
un valor redondo: el cuerpo de letra extraído de un documento maquetado en
Arial 11 sale a 10,98 o a 11,04 según la fuente incrustada y el redondeo del
extractor, y el interlineado se declara como múltiplo del alto de línea, que
depende de la métrica de la familia. Sin ninguna tolerancia el sistema marcaría
como incumplimiento un documento correcto, que es peor error que el contrario.

- `tipografia.tolerancia_cuerpo: 0.5` es la más discutible y la que más decide.
  Medio punto no es ruido de medición: deja pasar un documento maquetado a
  11,5, que es una desviación deliberada y visible. Se mantiene por prudencia
  —el sistema propone y no califica— pero es exactamente la clase de cifra que
  el docente debería fijar él.
- `interlineado.tolerancia: 0.1` cubre la diferencia entre un 1,5 declarado y
  el alto de línea efectivo. Es ruido de medición y poco más.
- `margenes.tolerancia: 0.5` (cm) es la única con apoyo en la prosa: el
  «aproximadamente» del §6.2 pide un margen, aunque no diga cuánto.

Mientras `tolerancias_formato` siga en `docs/PENDIENTE_OFICIAL.md`, estas tres
cifras son provisionales y quien las lea debe saberlo.

**2. El `activa_en` de `dimensiones.yaml`.** Las doce dimensiones citan
`maestro#8-dimensiones`, y el §8 es en efecto de donde salen el código, el
nombre y qué observa cada una. Pero el §8 declina fijar en qué fases está
activa cada dimensión: dice que «su peso y profundidad se configuran por fase,
modalidad y programación» y que una dimensión puede estar activa, ser
orientativa o no corresponder todavía. No hay tabla.

El reparto que está en el YAML se deriva de otra parte: de los §9.2 a §9.5,
que enumeran qué debe existir en cada entrega, y del §5, que establece que la
validación del tema no puntúa. D05 y D06 empiezan en E2 porque la metodología
y la bibliografía aparecen en el listado de la segunda entrega y el §9.2
excluye expresamente la bibliografía completa en E1; D08 y D09 empiezan en E3
porque resultados y conclusiones aparecen ahí; D10 empieza en E2 porque antes
no hay entrega anterior con la que comparar; D12 llega a DEFENSA porque el
§9.6 observa la capacidad de justificar decisiones.

La `fuente` sigue apuntando al §8, que es donde vive la dimensión. La
correspondencia fase por fase es de quien destiló, y si el criterio del docente
es otro se corrige con su documento de cambio.

**3. El `TEMA: evaluable: false` de `matriz-fases.yaml`.** El bloque `TEMA`
cita `maestro#9-matriz-entregas`, y el §9.1 sí es la fuente de su
`debe_existir`. Pero el §9.1 no dice si el tema puntúa; quien lo dice es el §5:
«la elección del tema es una validación previa y no una entrega evaluable», y
la tabla del ciclo de vida lo remacha con «no puntúa como entrega».

El campo `evaluable` de ese bloque viene, por tanto, del §5 y no del §9. Se
deja la `fuente` en el §9 porque el resto del bloque sale de allí, y se anota
aquí de dónde sale el campo que no. Es la misma clase de préstamo que el punto
anterior, y conviene que se vea antes de que alguien cambie el §5 dando por
hecho que el §9 lo protege: no lo hace, porque R2 vigila la sección citada, no
la sección de la que realmente se dedujo el valor.
