# La configuración recibe los valores que faltaban

**Fecha:** 2026-09-02
**Autor:** Marcos / colaborador técnico

## Que cambia

De los diez huecos que `config/estructura_expedientes.yaml` tenía a `null`
bajo `pendiente_de_definir`, **ocho se cierran** con el valor que fijó el
docente: extensiones y tamaño, política de identificación, versiones y
duplicados, y retención. Quedan dos: la política de reintentos y la versión
del calibrador, que él no ha tratado.

Dos de los valores nuevos son `null` **a propósito, y eso es la decisión**:

- `identificacion.umbral_de_parecido: null` — «no estableceremos un
  porcentaje de parecido para asignar automáticamente un trabajo».
- `retencion.borrar_pasados_dias: null` — «no habrá borrado automático».

Se han dejado como campos que existen y valen `null`, en vez de no
existir, para que quien los lea vea que la pregunta se hizo y la respuesta
fue que no. Un campo ausente parecería un olvido.

## Por que

Porque los pidió el documento de arquitectura y él los ha contestado. Hasta
hoy el sistema no podía validar lo que le entraba por la puerta: no sabía
qué extensiones admitir ni qué hacer con una segunda entrega.

## Fuente que lo respalda

`decisiones#5-extensiones`, `decisiones#6-identificacion`,
`decisiones#7-versiones` y `decisiones#8-retencion`.

## Que arrastra

`config/estructura_expedientes.yaml`, `backend/expedientes/estructura.py`
(cuatro bloques nuevos tipados, con tres guardas) y
`tests/expedientes/test_estructura_expedientes.py`.

Las tres guardas merecen mención, porque no son validación de forma sino de
fondo: la configuración **se niega a cargar** si alguien escribe un plazo de
borrado automático, si activa la eliminación de versiones anteriores, o si
pone un umbral de parecido con la política determinista. Las tres
contradirían una decisión suya, y las tres serían fáciles de escribir sin
darse cuenta. El sistema prefiere no arrancar a empezar a borrar trabajos de
alumnos.

## Correcciones cerradas afectadas

Ninguna. Estos valores gobiernan la entrada de archivos, que todavía no está
construida; no reinterpretan ninguna corrección ya hecha.
