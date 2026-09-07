# Manual de conexión para un agente

Para cualquier agente de código —Codex, Claude, el que sea— que llegue a este
repositorio a sacar una actualización. Léelo entero antes de tocar nada: son
cinco minutos y te ahorra romper cosas que no dan ningún error.

Si solo lees una frase, que sea esta:

> **El sistema propone, evidencia y se detiene.** La valoración definitiva, la
> calificación y cualquier comunicación al alumno son siempre del profesor.

Todo lo demás sale de ahí.

## Qué es esto

Un sistema de corrección de Proyectos Intermodulares de Formación Profesional.
Lee el PDF que entrega un alumno, lo analiza contra doce dimensiones, exige una
cita literal para cada observación, **comprueba que esa cita existe de verdad
en el documento**, y compone dos salidas: un informe interno para el profesor y
un borrador de devolución que él revisa antes de que llegue a nadie.

Se usa en el equipo del profesor. Para la beta va empaquetado en un `.exe` que
él abre con doble clic: ver `docs/INSTALACION.md`.

## Lo primero que tienes que entender: la prosa manda

Este repositorio tiene una jerarquía y no es negociable.

| Nivel | Qué es |
|---|---|
| `docs/maestro/` | **La fuente de verdad.** Prosa normativa del profesor. Cinco documentos. |
| `criteria/` | Destilado ejecutable. **Derivado, nunca original.** |
| El código | Aplica el destilado. No decide nada. |

**No edites `criteria/` sin editar antes `docs/maestro/`.** Al revés rompe R2 y
la comprobación lo detecta. Y no reescribas la prosa del profesor: se corrige
cuando él lo pide, con su documento de cambio, no «se mejora» de oficio.

Las ocho reglas están en `GOVERNANCE.md`. Estas cuatro son las que más se
incumplen sin querer:

- **R1** — ningún criterio existe sin `fuente: documento#ancla` apuntando a la
  prosa.
- **R3** — lo que no se sabe va a `docs/PENDIENTE_OFICIAL.md`. **Nunca se
  rellena con un valor razonable.** Un `null` declarado es una respuesta; un
  valor inventado es una mentira que nadie volverá a revisar.
- **R5** — todo cambio de criterio lleva su fichero en `docs/changes/`,
  copiando `docs/changes/PLANTILLA.md` y rellenándola entera.
- **R8** — todo en castellano **con tildes correctas**: identificadores,
  comentarios, mensajes de error. Los lee un profesor, no un programador.

## Antes de dar nada por terminado

```
python -m pytest
cd frontend && npm test
python tools/verificar_gobernanza.py
```

Los tres en verde o el trabajo no está hecho. **No anuncies que algo funciona
sin haber visto la salida.**

## Lo que no se hace nunca

- **No metas datos de alumnos.** Ni PDFs, ni nombres, ni ejemplos reales. Los
  ejemplos usan códigos tipo `AF023` o `ALU-260001` y nombres inventados.
- **No implementes que el sistema decida algo del §13.** Aprobar una nota,
  valorar autoría, dar por apto un documento, comunicar feedback: propone y se
  detiene.
- **No apliques migraciones.** Se escriben en `supabase/migrations/` y las
  aplica él desde su panel. Si hace falta una, escríbela y dilo.
- **No toques una versión de criterios congelada.** Se crea la siguiente.

## Las trampas que ya han mordido

Todas estas ocurrieron de verdad. Un agente que llega nuevo las repite.

**El proveedor simulado es más permisivo que el real.** Cuatro fallos han
sobrevivido a más de mil pruebas porque todas usaban el simulado: una llamada
con el campo de texto vacío, un valor de enumeración que la columna no admite,
un parámetro que los modelos de razonamiento rechazan, y una entrega que decía
estar analizada sin estarlo. **Si tocas el camino del análisis, ejecútalo
contra el motor real una vez.** Cuesta un céntimo y medio.

**Las pruebas de unidad no ven las costuras.** Al unir la identificación con la
admisión aparecieron tres fallos que ninguna pieza suelta podía mostrar; el
peor: la comparación de nombres exigía igualdad exacta, y **ningún archivo real
se habría identificado nunca**, con los 31 tests de identificación en verde.

**Empaquetado, las rutas cambian.** `backend/empaquetado.py` separa los
recursos del programa (dentro del `.exe`) de la carpeta de trabajo del profesor
(al lado). Confundirlas hace que su `.env` se pierda en cada actualización o
que los criterios no aparezcan.

**Un `git add -A` se lleva lo que no debe.** Ya coló un fichero temporal al
repositorio publicado.

**Cuidado con los agentes en paralelo.** Han colisionado tres veces numerando
decisiones (`D-0NN`) y una vez fusionando código que git unió sin protestar
dejando una escala de cinco niveles en cuatro. Si lanzas varios, revisa
`docs/decisions.md` al fusionar.

## Cómo se saca una actualización

1. Rama nueva desde `arquitectura-de-expedientes`. **Nunca sobre `main`.**
2. El cambio, con sus pruebas. Rompe lo tuyo a propósito y comprueba que algún
   test se entera: en este proyecto ha pasado más de quince veces que un
   mecanismo importante funcionaba y nada lo protegía.
3. Su fichero en `docs/changes/` si toca criterios, y su entrada en
   `docs/decisions.md` si es una decisión de diseño con un porqué.
4. Los tres comandos de arriba, en verde.
5. `python tools/empaquetar.py` deja `dist/RevisorDeProyectos.exe`.
6. Al profesor se le manda **solo el `.exe`**. Su `.env`, su
   `config/centros.yaml` y su carpeta de trabajos se quedan como están: por eso
   viven fuera.

## Lo que está abierto ahora mismo

- La convención de nombre de archivo: el sistema asigna `ALU-260001` y el §15.3
  espera `AF023`. **Bloquea la identificación automática.** Es la pregunta 1 de
  `docs/` → informe de las ocho preguntas.
- El umbral de diez alumnos para ocultar la lista nominal en un informe de
  centro (D-032) es una propuesta nuestra, no una cifra suya.
- Los estados posteriores a `ANALIZADO` existen en la base y **no los escribe
  nadie**: una entrega revisada se queda en «analizada».
- Las entregas acumulativas del §11 de su respuesta: el sistema compara con la
  anterior a partir de lo ya medido, no volviendo a mandarle los dos documentos
  al motor. Está sin decidir si quiere lo segundo, que cuesta el doble.

## Dónde mirar

| Ruta | Qué es |
|---|---|
| `GOVERNANCE.md` | Las ocho reglas, enteras. |
| `CLAUDE.md` | El resumen operativo. |
| `docs/maestro/` | La prosa normativa. Cinco documentos; el orden importa. |
| `docs/decisions.md` | Por qué el sistema es como es. Treinta y dos decisiones. |
| `docs/changes/` | Un fichero por cambio de criterio. |
| `docs/PENDIENTE_OFICIAL.md` | Lo que no se sabe y no se inventa. |
| `docs/INSTALACION.md` | Cómo se empaqueta y qué recibe el profesor. |
| `tools/verificar_gobernanza.py` | Lo comprueba todo. Un módulo por regla. |
