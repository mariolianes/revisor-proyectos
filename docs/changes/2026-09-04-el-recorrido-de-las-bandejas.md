# El recorrido de las bandejas

**Fecha:** 2026-09-04
**Autor:** Marcos / colaborador técnico

## Que cambia

Nace `backend/servicios/bandejas.py`: recorre las carpetas `PENDIENTES` de
cada comunidad y fase y pasa por la admisión lo que encuentra. Es lo que
enchufa la admisión, que hasta hoy no llamaba nadie.

## Por que

Porque sin esto la arquitectura del docente y el corrector eran dos sistemas
separados que no se hablaban.

Tres decisiones que merecen constar:

- **Solo se miran las carpetas `PENDIENTES`.** Es la regla que él escribió, y
  tiene una consecuencia práctica que conviene decir en voz alta: si se
  vigilara `INCIDENCIAS`, lo que la admisión aparta por no poder
  identificarlo volvería a entrar en el circuito en cada pasada, una y otra
  vez.
- **La comunidad y la fase salen de la ruta.** Un trabajo en
  `AND_ANDALUCIA/E02/PENDIENTES` es de Andalucía y de la segunda entrega
  porque el docente lo dejó ahí. Es un dato suyo, no una deducción sobre el
  nombre del fichero, y por eso aquí no hay ninguna heurística de fase.
- **La lista de admitidas crece dentro del bucle**, no se calcula una vez al
  empezar. Dos versiones del mismo trabajo en la misma bandeja tienen que
  salir como versión 1 y 2; con una foto tomada al principio, las dos serían
  la versión 1 y la segunda sobrescribiría a la primera en disco.

**No registra nada en el almacén.** Devuelve lo que ha pasado con cada
archivo. Quién decide registrar una entrega, y cuándo, sigue siendo del
docente: esa frontera es de las que no conviene mover sin que él lo pida.

## Fuente que lo respalda

`decisiones#9-carpetas` y el documento de arquitectura del docente para la
estructura de la bandeja; `decisiones#6-identificacion` y
`decisiones#7-versiones` a través de la admisión.

## Que arrastra

`backend/servicios/bandejas.py` y `tests/servicios/test_bandejas.py`. Nada
de lo existente cambia.

## Correcciones cerradas afectadas

Ninguna. Todavía no lo llama ninguna pantalla ni ningún endpoint.
