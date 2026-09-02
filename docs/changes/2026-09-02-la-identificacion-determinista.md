# La identificación determinista, con la portada como evidencia auxiliar

**Fecha:** 2026-09-02
**Autor:** Marcos / colaborador técnico

## Que cambia

Nace `backend/identificacion/`, con la escalera de cinco prioridades del
docente. Se construye la comprobación del nombre en portada, que el 31 de
agosto habíamos decidido no construir.

## Por que

Porque él lo revocó, y con razón: la minimización protege contra *enviar* el
nombre, no contra *leerlo* en el equipo. El orden correcto es leer,
identificar y después enmascarar.

## Fuente que lo respalda

`decisiones#4-portada` y `decisiones#6-identificacion`.

## Que arrastra

`backend/identificacion/nombres.py`,
`backend/identificacion/determinista.py`,
`tests/identificacion/test_determinista.py`. Ninguno toca lo ya construido:
es una pieza nueva que todavía no está conectada al flujo de entrada.

## Correcciones cerradas afectadas

Ninguna. Nada de esto se ha ejecutado sobre ningún trabajo real.
