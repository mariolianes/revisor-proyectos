# Conectar Codex a este repositorio

Para que un agente de código pueda sacar actualizaciones del programa sin que
haya alguien delante todo el rato.

## Lo que hace falta una vez

**1. Tener el repositorio.**

    git clone https://github.com/mariolianes/revisor-proyectos.git
    cd revisor-proyectos

**2. Las dependencias.**

    python -m pip install -r requirements-dev.txt
    cd frontend && npm install && cd ..

`requirements-dev.txt` trae también las herramientas de desarrollo. El
`requirements.txt` a secas es lo que necesita el programa para funcionar, y es
el que se usa al empaquetar.

**3. El `.env`.** No está en el repositorio y no debe estarlo: son claves.
Cópialo del equipo donde ya funcione, o créalo con las variables que enumera
`docs/INSTALACION.md`.

**4. Abrir Codex en esa carpeta.** Lo primero que lee es `AGENTS.md`, en la
raíz: ahí está todo lo que un agente necesita saber para no romper nada. No
hace falta explicárselo tú.

## Cómo se le pide algo

Codex trabaja mejor con un encargo concreto y un criterio de terminado. Este
repositorio ya tiene los dos escritos, así que basta con apuntarle a ellos.

Un encargo bien hecho:

> Lee `AGENTS.md` antes de nada. Quiero que [lo que sea]. Cuando termines, los
> tres comandos de «Antes de dar nada por terminado» tienen que estar en verde.

Y uno mal hecho:

> Arregla esto.

La diferencia no es de cortesía: sin el criterio de terminado, un agente
declara hecho lo que compila.

## Lo que hay que exigirle siempre

**Que rompa lo suyo a propósito.** En este proyecto ha ocurrido más de quince
veces que un mecanismo importante funcionaba y ningún test lo protegía. Pídele
que estropee lo que acaba de escribir y compruebe que algún test se entera. Si
no salta ninguno, el test no vale.

**Que no invente ningún criterio.** Si un dato no está en `docs/maestro/`, va a
`docs/PENDIENTE_OFICIAL.md`. Un valor razonable inventado es peor que un hueco
declarado: nadie vuelve a revisarlo.

**Que ejecute contra el motor real si toca el análisis.** Cuatro fallos han
sobrevivido a más de mil pruebas porque todas usaban el proveedor simulado, más
permisivo que el real. Cuesta un céntimo y medio comprobarlo.

**Que no aplique migraciones.** Las escribe y las aplica el profesor desde su
panel.

## Cómo se comprueba lo que ha hecho

Sin leer código:

    python -m pytest
    cd frontend && npm test
    python tools/verificar_gobernanza.py

Los tres en verde. El tercero es el que comprueba que no se ha inventado un
criterio, que la prosa y el destilado siguen cuadrando y que no se ha colado
un texto sin tildes.

Y después:

    git log --oneline -10
    git diff main --stat

Si un cambio toca `criteria/` y no hay un fichero nuevo en `docs/changes/`, la
verificación de gobernanza ya habrá protestado. Si toca `docs/maestro/` sin que
el profesor lo haya pedido, eso no lo detecta ninguna herramienta: míralo tú.

## Cómo se le manda la actualización al profesor

    python tools/empaquetar.py

Deja `dist/RevisorDeProyectos.exe`. Se le manda **ese fichero y nada más**: su
`.env`, su `config/centros.yaml` y su carpeta de trabajos viven fuera del
programa precisamente para que una actualización no se los lleve por delante.

## Dos cosas que conviene no perder de vista

**El agente no decide qué es correcto pedagógicamente.** Puede escribir código,
tests y documentación; no puede decidir si un trabajo merece ámbar o si una
observación es justa. Eso es del profesor, y el sistema entero está construido
para no quitárselo.

**Los cambios de criterio se le consultan a él.** Un agente que ajusta un
umbral porque «mejora las cifras» está optimizando contra ruido: una tanda de
calibración es una tirada, no una medición. Está explicado en las observaciones
acumuladas para el docente.
