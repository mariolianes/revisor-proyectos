# La admisión: de la bandeja al expediente

**Fecha:** 2026-09-04
**Autor:** Marcos / colaborador técnico

## Que cambia

Nace `backend/servicios/admision.py`, que toma un archivo de la bandeja y lo
deja en el expediente del alumno con su nombre normalizado, o en Incidencias
con el motivo. Valida extensión y tamaño, calcula la huella, identifica,
reconoce duplicados y conflictos de versión, y crea el expediente con la
primera entrega.

Tres cambios de apoyo:

- `backend/identificacion/nombres.py` gana `nombra_a` y
  `nombra_parcialmente_a`, para comparar un nombre contra un texto que lo
  contiene.
- `config/estructura_expedientes.yaml` separa el código de fase (`E1`) del
  nombre de su carpeta en la bandeja (`E01`).
- Las carpetas del expediente declaran qué fase reciben.

## Por que

Porque la identificación estaba construida y no la llamaba nadie. Y porque al
unir las piezas aparecieron tres fallos que ninguna prueba de unidad podía
ver, el primero de ellos grave: **con la comparación de nombres anterior,
ningún archivo real se habría identificado nunca.**

## Fuente que lo respalda

`decisiones#4-portada` para el orden de los pasos, `decisiones#6-identificacion`
para la escalera, `decisiones#7-versiones` para duplicados y versiones,
`decisiones#9-carpetas` para dónde va cada cosa, y `decisiones#2-identificador`
para el nombre normalizado.

## Que arrastra

`backend/servicios/admision.py`, `backend/identificacion/nombres.py`,
`backend/identificacion/determinista.py`, `backend/expedientes/estructura.py`,
`config/estructura_expedientes.yaml`, `tests/servicios/test_admision.py`,
`tests/expedientes/test_estructura_expedientes.py`.

## Correcciones cerradas afectadas

Ninguna. La admisión no ha corrido sobre ningún archivo real y todavía no la
llama nadie.
