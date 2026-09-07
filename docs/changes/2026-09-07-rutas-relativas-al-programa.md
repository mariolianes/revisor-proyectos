# Las rutas del `.env` pueden ser relativas al programa

**Fecha:** 2026-09-07
**Autor:** Marcos / colaborador técnico

## Que cambia

`REVISOR_CARPETA_ENTREGAS`, `REVISOR_RAIZ_EXPEDIENTES` y
`REVISOR_DATOS_LOCALES` admiten una ruta relativa, que se resuelve contra la
carpeta donde vive el programa.

## Por que

Porque el `.env` que se le manda al docente llevaba escritas las rutas del
equipo donde se preparó (`C:\Users\conta\Desktop\...`). Al descomprimirlo en
su carpeta, **el programa no habría encontrado nada** y el primer arranque
habría fallado sin que se supiera por qué. Se vio revisando la carpeta de
entrega justo antes de mandársela.

**Contra la carpeta del programa, no contra el directorio actual.** Quien
abre un `.exe` con doble clic no controla desde dónde se lanza: resolver
contra el directorio actual haría que la misma configuración funcionara o no
según cómo se hubiera abierto.

## Fuente que lo respalda

Ninguna: es configuración, no criterio.

## Que arrastra

`backend/configuracion.py` (`_resolver`) y
`tests/backend/test_configuracion.py`.

**Probado moviendo la carpeta entera a otra ruta y arrancando el ejecutable
desde `C:\Windows`** -el caso peor-: encontró su bandeja, su carpeta de
expedientes y sus datos locales.

## Correcciones cerradas afectadas

Ninguna. Una ruta absoluta sigue funcionando igual que antes.
