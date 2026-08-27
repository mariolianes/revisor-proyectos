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

## Editor de criterios

Para leer y modificar los documentos normativos sin salirte del
procedimiento:

    editor.cmd

Hace falta tener instalados Python y Node.js, y que ambos sean accesibles
desde la línea de comandos (`python` y `npm` en el PATH). Si falta alguno,
`editor.cmd` lo avisa y dice qué instalar.

Abre `http://127.0.0.1:8000` en el navegador. La primera vez compila el
frontend, lo que tarda un poco.

El editor no permite guardar un cambio sin motivo y sin fuente, y ejecuta las
seis reglas antes de comitear. Si alguna salta, no se guarda nada: el
repositorio queda como estaba.
