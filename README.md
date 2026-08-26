# Revisor de Proyectos Intermodulares

Asistente interno de correccion y seguimiento de Proyectos Intermodulares de
Formacion Profesional.

El sistema no califica ni comunica. Propone, evidencia y se detiene. La
valoracion definitiva, la calificacion y cualquier comunicacion al alumno
pertenecen siempre al profesor.

## Documentacion

- `GOVERNANCE.md` — las reglas del repositorio. Leelo antes de tocar criterios.
- `docs/maestro/` — la prosa normativa. Es la fuente de verdad.
- `criteria/` — el destilado ejecutable, derivado de la prosa.
- `docs/decisions.md` — por que el sistema es como es.
- `docs/PENDIENTE_OFICIAL.md` — lo que aun no se sabe y no se inventa.

## Puesta en marcha

    python -m pip install -r requirements-dev.txt
    python -m pytest
    python tools/verificar_gobernanza.py
