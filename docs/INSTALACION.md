# Instalación para la beta

Para que el docente pueda probar el sistema en su equipo sin instalar nada.

## Lo que él recibe

**Dos ficheros**, en la misma carpeta:

    RevisorDeProyectos.exe
    .env

Y nada más. No instala Python, no instala Node, no abre una consola. Abre el
`.exe` con doble clic y el navegador se abre solo.

**El `.env` va al lado del ejecutable, nunca dentro.** Son sus claves y la
ruta de sus entregas, y tienen que sobrevivir cuando se le mande una versión
nueva del programa: si viajaran dentro, cada actualización se las llevaría
por delante, y además cualquiera que recibiera el ejecutable se llevaría su
clave de OpenAI. Ver `backend/empaquetado.py`.

## Qué poner en su `.env`

    REVISOR_CARPETA_ENTREGAS=C:\Users\marcos\CESUR_2026-2027\01_ENTRADA_TRABAJOS
    REVISOR_VERSION_CRITERIOS=v2026-2027
    REVISOR_MODELO_ANALISIS=gpt-5.6-luna
    REVISOR_ESFUERZO_ANALISIS=high
    OPENAI_API_KEY=
    SUPABASE_URL=
    SUPABASE_SERVICE_KEY=

Sin `OPENAI_API_KEY` el programa arranca igual y avisa de que el análisis es
simulado. Sin las dos de Supabase también arranca, y avisa de que lo que
registre se pierde al cerrar. **Los dos avisos se ven en pantalla**: no hay
forma de creerse que está corrigiendo de verdad cuando no lo está.

## Cómo se construye

    python tools/empaquetar.py

Compila la interfaz y deja `dist/RevisorDeProyectos.exe`, unos 70 MB. Dentro
van los criterios, la prosa normativa del docente, la configuración y la
interfaz compilada: los cuatro son el programa y se actualizan con él.

La interfaz se compila **siempre**, no solo cuando falta. Una interfaz vieja
con un backend nuevo no da ningún error: solo pantallas que no cuadran y la
conclusión razonable de que esto no funciona.

## El puerto

El programa usa el 8000. Si está ocupado, prueba el siguiente hasta el 8019 y
dice cuál ha elegido. **Nunca comparte puerto con nadie**: si se arrancara
sobre uno ocupado, el navegador se abriría contra otro programa.

Hasta el 7 de septiembre de 2026 se negaba a arrancar si el 8000 estaba
ocupado. Para alguien que abre un `.exe` con doble clic, eso es un programa
que no funciona y ninguna forma de averiguar por qué.

## Para desarrollar, no para la beta

`editor.cmd` arranca desde el repositorio: instala las dependencias, compila
la interfaz y lanza el programa. Necesita Python y Node instalados, así que
**no** es lo que se le da al docente.

## Lo que falta antes de dársela

- **Las cuatro migraciones aplicadas** en su Supabase. Sin eso el programa
  arranca, pero no guarda nada: hay una guía en
  `docs/migraciones/2026-09-03-guia-de-aplicacion.md`.
- **Sus listados de alumnos importados.** No es una comodidad: la capa que
  quita el nombre del texto antes de mandarlo al motor solo funciona cuando
  sabe qué nombre tachar. Primero los listados, después las entregas.
- **Decidir la convención de nombre de archivo**, que sigue abierta desde el
  informe de las ocho preguntas.
