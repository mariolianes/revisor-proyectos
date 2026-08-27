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
    cd frontend && npm test
    python tools/verificar_gobernanza.py

El segundo paso no es opcional: instala el hook de pre-commit que ejecuta el
verificador. Sin él, nada vigila los criterios hasta que alguien se acuerde de
lanzar el verificador a mano.

## Editor de criterios

Para leer y modificar los documentos normativos sin salirte del
procedimiento:

    editor.cmd

Hace falta tener instalado Python y que sea accesible desde la línea de
comandos (`python` en el PATH). Node.js (`npm`) solo hace falta la primera
vez, para compilar el frontend. Si falta alguno cuando toca, `editor.cmd` lo
avisa y dice qué instalar.

Abre `http://127.0.0.1:8000` en el navegador. La primera vez compila el
frontend, lo que tarda un poco. Si ese puerto ya lo está usando otro
programa, el editor no arranca y lo dice: hay que liberarlo antes.

El editor no permite guardar un cambio sin motivo y sin fuente, y ejecuta las
reglas antes de comitear. Si alguna salta, no se guarda nada: el repositorio
queda como estaba.

Cada criterio que deriva de la sección editada se decide en el diálogo de
guardado, uno por uno: se escribe lo que pasa a decir, o se marca «lo he
revisado y no cambia». Una sección con algún criterio sin decidir no se sella,
así que R2 la sigue dando por pendiente de revisar y el guardado no pasa. No
hay forma de posponerlo desde el editor, y esa es la idea.
