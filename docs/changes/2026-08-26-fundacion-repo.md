# Fundación del repositorio y de la capa de gobernanza

**Fecha:** 2026-08-26
**Autor:** Marcos / colaborador técnico

## Que cambia

El sistema pasa de existir como tres documentos PDF sueltos a tener un
repositorio con la prosa normativa en Markdown, su destilado ejecutable en
YAML y un verificador que comprueba las reglas R1 a R6.

Desde hoy, `docs/maestro/` es la fuente de verdad. Los PDF originales pasan a
ser copia histórica.

## Por que

Los tres documentos se solapan a propósito y ninguno era la fuente de verdad
de los otros. Un criterio podía cambiar en la Guía y no en el Maestro, y el
sistema habría acabado corrigiendo con un criterio que ya no era el del
docente. El §1 del Maestro plantea exactamente ese riesgo.

## Fuente que lo respalda

Documento Maestro §14.1, jerarquía de fuentes y regla de conflicto.

## Que arrastra

- `docs/maestro/01-documento-maestro.md`
- `docs/maestro/02-indice-comentado.md`
- `docs/maestro/03-guia-desarrollo.md`
- `criteria/v2026-2027/` completo
- `docs/PENDIENTE_OFICIAL.md`
- `docs/decisions.md`
- `tools/gobernanza/`

## Correcciones cerradas afectadas

Ninguna. No se ha corregido todavía ninguna entrega con este sistema.

## Interpretación registrada

La dimensión D05 (fundamentación y fuentes) se activa desde la segunda
entrega, no desde la primera. El §9.2 no exige bibliografía completa en E1,
solo "primeras fuentes o datos que permitan investigar", y esa comprobación la
cubre D02, que observa la evidencia de partida. Si el criterio del docente es
otro, se corrige en `criteria/v2026-2027/dimensiones.yaml` con su documento de
cambio.
