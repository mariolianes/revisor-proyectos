# Instalable para la beta: un solo fichero que el docente abre

**Fecha:** 2026-09-07
**Autor:** Marcos / colaborador técnico

## Que cambia

`python tools/empaquetar.py` construye `dist/RevisorDeProyectos.exe`: un solo
fichero de unos 70 MB que el docente abre con doble clic. Sin instalar
Python, sin instalar Node, sin consola.

Tres cambios de apoyo:

- `backend/empaquetado.py` separa **los recursos del programa** -criterios,
  prosa normativa, configuración, interfaz compilada, que viajan dentro- de
  **la carpeta de trabajo** -donde vive su `.env`, al lado del ejecutable-.
- El programa busca el primer puerto libre a partir del 8000.
- `requirements.txt` separa lo que el programa necesita de las herramientas
  de desarrollo.

## Por que

Tres fallos que le habrían aparecido a él, no a nosotros:

1. **`editor.cmd` no instalaba las dependencias.** Con un Python recién
   instalado, lo primero que habría visto es un `ModuleNotFoundError` de
   fastapi. Ya las instala.
2. **Si el puerto 8000 estaba ocupado, el programa se negaba a arrancar.**
   Para alguien que abre un `.exe` con doble clic, eso es un programa que no
   funciona y ninguna forma de averiguar por qué. Ahora busca otro y dice
   cuál.
3. **El `.env` dentro del ejecutable se habría perdido en cada
   actualización**, y habría repartido su clave de OpenAI con cualquiera que
   recibiera el fichero. Va al lado, nunca dentro.

## Fuente que lo respalda

Ninguna nueva: es empaquetado, no criterio. La prosa normativa no cambia.

## Que arrastra

`backend/empaquetado.py` (nuevo), `tools/empaquetar.py` (nuevo),
`requirements.txt` (nuevo), `docs/INSTALACION.md` (nuevo),
`backend/__main__.py`, `backend/app.py`, `backend/configuracion.py`,
`editor.cmd`, `.gitignore`.

**Probado como lo recibiría él**: el ejecutable copiado a una carpeta limpia
fuera del repositorio, con un `.env` al lado, arrancó, eligió el puerto 8002
-el 8000 y el 8001 estaban ocupados-, sirvió la interfaz, leyó los cinco
documentos normativos desde dentro del propio fichero y vigiló la carpeta de
entregas.

## Correcciones cerradas afectadas

Ninguna. No cambia ningún criterio ni ninguna corrección.
