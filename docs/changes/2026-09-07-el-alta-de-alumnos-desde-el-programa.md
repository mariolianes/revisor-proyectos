# El alta de alumnos, desde el programa

**Fecha:** 2026-09-07
**Autor:** Marcos / colaborador técnico

## Que cambia

Nace la pestaña **Alumnos**: el docente elige uno de sus Excel de
`00_LISTADOS_ALUMNOS`, la comunidad y el curso, y lo importa. Con endpoint
propio (`backend/api/alumnos.py`) y la lectura del Excel mudada de `tools/`
al paquete que sí viaja dentro del ejecutable.

Y el catálogo de centros pasa a ser suyo: `backend/empaquetado.py` lo busca
primero al lado del ejecutable y se cae al de dentro si no está.

## Por que

Porque el importador existía, funcionaba y tenía sus pruebas, pero **solo
como orden de consola**, y `tools/` no viaja dentro del ejecutable. Para la
beta eso significaba que el docente no podía dar de alta a sus propios
alumnos sin que alguien le ejecutara un comando. Y sin alumnos dados de alta
no hay a quién asignar un trabajo, ni nombre que tachar antes de mandar el
texto al motor.

**El catálogo de centros era el mismo problema, una capa más abajo**, y se
descubrió importando un listado de verdad desde el ejecutable ya construido:
las dos filas se rechazaron por un catálogo vacío que no había forma de
rellenar, porque estaba dentro del `.exe`. Los centros son suyos -cambian
cuando abre uno nuevo-, así que tienen que poder editarse sin esperar a una
versión nueva del programa.

## Tres decisiones

- **Los Excel no se suben: se eligen.** Mismo trato que los trabajos: una
  carpeta suya que el programa mira. Un listado con los nombres de 250
  alumnos no tiene por qué atravesar nada, ni siquiera dentro de su equipo.
- **La respuesta no lleva ningún nombre.** Las filas que quedan sin
  registrar se identifican por su número de fila del Excel -el que él ve al
  abrirlo-. Hay un test que lo comprueba.
- **El nombre del fichero se recorta a su nombre.** Sin eso, un
  `../../algo.xlsx` habría leído un Excel de cualquier parte de su disco.

## Fuente que lo respalda

`decisiones#3-repetidores` y `decisiones#6-identificacion` para el alta;
ninguna nueva: es la misma importación que ya existía, con otra puerta.

## Que arrastra

`backend/api/alumnos.py` (nuevo), `backend/empaquetado.py` (`config`),
`backend/servicios/importacion_alumnos.py` (`leer_excel`), `backend/app.py`,
`tools/importar_listado_alumnos.py`, `frontend/src/paginas/Alumnos.tsx`
(nueva), `frontend/src/App.tsx`, `frontend/src/lib/api.ts`,
`frontend/src/lib/tipos.ts`, y sus pruebas.

**Probado desde el ejecutable**, con un Excel de dos filas -una buena y una
de centro inventado-: la pantalla vio el listado, importó, devolvió las dos
filas pendientes con su número y su motivo, y ni un nombre en la respuesta.

## Correcciones cerradas afectadas

Ninguna.
