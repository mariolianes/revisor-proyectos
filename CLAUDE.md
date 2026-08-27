# Instrucciones para el agente

Sistema de corrección de Proyectos Intermodulares. Antes de tocar nada, lee
`GOVERNANCE.md`.

## Lo que no se hace nunca

- **No inventes un criterio.** Si un dato no está en `docs/maestro/` ni en una
  fuente oficial, va a `docs/PENDIENTE_OFICIAL.md` con `estado:
  PENDIENTE_OFICIAL`. Nunca se rellena con un valor razonable.
- **No edites `criteria/` sin editar antes `docs/maestro/`.** El YAML es un
  derivado. Al revés rompe R2.
- **No toques una versión de criterios congelada.** Se crea la siguiente.
- **No metas datos de alumnos.** Ni PDFs, ni nombres, ni ejemplos con datos
  reales. Los ejemplos usan códigos tipo `AF023`.
- **No reescribas la prosa del docente.** Los documentos de `docs/maestro/` son
  normativos. Se corrigen cuando él lo pide, con su documento de cambio; no se
  "mejoran" de oficio.
- **No implementes que el sistema decida algo del §13.** Aprobar nota, valorar
  autoría, autorizar cambio de tema, dar por apto un documento, comunicar
  feedback: el sistema propone y se detiene.

## Antes de dar por terminado un cambio

```
python -m pytest
cd frontend && npm test
python tools/verificar_gobernanza.py
```

Los tres en verde, o el trabajo no está terminado. No anuncies que algo
funciona sin haber visto la salida. Los tests del frontend cuentan igual que
los demás: la pantalla del editor es donde el docente decide qué dice cada
criterio.

## Idioma

Todo en castellano: identificadores, comentarios, mensajes de error,
documentación y commits. Los mensajes de infracción los lee el docente, no un
programador: han de decir qué pasa y qué hacer, sin jerga.

## Estructura

| Ruta | Qué es |
|---|---|
| `docs/maestro/` | La fuente de verdad. Prosa normativa. |
| `criteria/` | Destilado ejecutable. Derivado, nunca original. |
| `docs/decisions.md` | Por qué el sistema es como es. |
| `docs/PENDIENTE_OFICIAL.md` | Lo que no se sabe y no se inventa. |
| `docs/changes/` | Un fichero por cambio de criterio. |
| `tools/gobernanza/` | Un módulo por regla. |
