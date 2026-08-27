# Revisor de Proyectos Intermodulares

Asistente interno de corrección y seguimiento de Proyectos Intermodulares de
Formación Profesional.

**Estado: hoy solo existe la capa de gobernanza.** Este repositorio contiene la
prosa normativa, su destilado en criterios y las reglas que impiden que ambos
se separen. El motor de corrección —el que lee una entrega y propone
observaciones— se construirá cuando exista la rúbrica oficial; sin ella, no hay
con qué corregir y no se va a inventar.

El sistema no califica ni comunica. Propone, evidencia y se detiene. La
valoración definitiva, la calificación y cualquier comunicación al alumno
pertenecen siempre al profesor.

## Documentación

- `GOVERNANCE.md` — las reglas del repositorio. Léelo antes de tocar criterios.
- `docs/maestro/` — la prosa normativa. Es la fuente de verdad.
- `criteria/` — el destilado ejecutable, derivado de la prosa.
- `docs/decisions.md` — por qué el sistema es como es.
- `docs/PENDIENTE_OFICIAL.md` — lo que aún no se sabe y no se inventa.

## Puesta en marcha

    python -m pip install -r requirements-dev.txt
    python tools/instalar_hooks.py
    python -m pytest
    python tools/verificar_gobernanza.py

El segundo paso no es opcional: instala el hook de pre-commit que ejecuta el
verificador. Sin él, nada vigila los criterios hasta que alguien se acuerde de
lanzar el verificador a mano.
