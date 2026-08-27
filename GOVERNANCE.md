# Gobernanza del repositorio

Este sistema decide sobre el trabajo de personas. Estas reglas existen para
que, dentro de un año, se pueda reconstruir con qué criterio exacto se corrigió
a un alumno y de dónde salía ese criterio.

La regla madre está en el §14.1 del Documento Maestro: **una fuente inferior no
puede contradecir a una superior.** Todo lo demás es maquinaria para que se
cumpla sin depender de la memoria de nadie.

## Jerarquía de fuentes

1. Programación didáctica y rúbrica oficial vigente
2. Instrucciones formales de CESUR, centro o coordinación
3. Acuerdos internos documentados y fechados
4. Documento Maestro, guía de desarrollo e índice comentado
5. Manual docente, banco de feedback y casos calibrados
6. Precedentes del curso anterior

Si dos criterios vigentes chocan, el sistema **detiene ese juicio** y crea una
alerta. No elige.

## Las siete reglas

**R1 · Ningún criterio sin origen.** Toda entrada de `criteria/` declara
`fuente: documento#ancla` apuntando a una sección real de `docs/maestro/`.
*Verificada.*

**R2 · La prosa manda.** El YAML se deriva del Markdown, nunca al revés. Si una
sección cambia, hay que revisar su derivado y sellar con `--sellar`. Ojo al
alcance: R2 solo vigila las secciones que algún criterio cita como `fuente:`,
no el Maestro entero, así que editar una sección que ningún criterio deriva no
hace saltar nada y eso no significa que se haya comprobado. Hoy ningún criterio
cita `guia#...`, con lo que la guía de desarrollo entera queda fuera de esa
vigilancia. *Verificada.*

**R3 · Lo pendiente se marca, no se inventa.** `estado: PENDIENTE_OFICIAL`, con
`bloquea` y entrada en `docs/PENDIENTE_OFICIAL.md`. Un criterio pendiente no
lleva valor. Ojo al alcance: la lista de claves que delatan un valor inventado
es corta —`valor`, `valores`, `fechas`, `porcentajes`—, de modo que `niveles`,
`peso`, `porcentaje` o `minimo` colados en un criterio pendiente pasarían sin
protesta. *Verificada.*

**R4 · Los criterios se versionan y se congelan.** Una versión usada en una
corrección aprobada no se modifica: se crea la siguiente. Se cierra con
`--congelar <version>`; hasta que alguien la congele, R4 no vigila nada.
*Verificada.*

**R5 · Un fichero por cambio.** Tocar `criteria/` o `docs/maestro/` exige un
documento en `docs/changes/`. *Verificada.*

**R6 · Nada personal entra en el repositorio.** Ni entregas, ni nombres, ni
datos identificativos. *Verificada.*

**R7 · Las reservas del profesor son bloqueos reales.** Las nueve decisiones
del §13 del Maestro se implementan como estados que el backend no atraviesa
solo. *Pendiente: se implementa con el backend.*

## Cómo se cambia un criterio

```
1. Editar   docs/maestro/<documento>.md          la prosa
2. Ajustar  criteria/vAAAA-AAAA/<fichero>.yaml   el derivado
3. Escribir docs/changes/AAAA-MM-DD-<asunto>.md
4. Anotar   docs/decisions.md                    si es decisión, no ajuste
5. Ejecutar python tools/verificar_gobernanza.py --sellar
6. Commit, incluyendo criteria/.sincronia.json
```

El orden importa, pero **ninguna regla lo comprueba**. R2 solo guarda el hash
del texto de las secciones de prosa: nunca lee el contenido del YAML, así que
cambiar `minimo_paginas_contenido: 20` por `25` sin tocar el Maestro no le hace
saltar. La única guarda real de ese paso es R5, y lo que exige es papeleo —un
documento en `docs/changes/`—, no coherencia: la prosa y su derivado pueden
quedar diciendo cosas distintas sobre cuántas páginas debe escribir un alumno y
el verificador seguirá dando conforme. Cerrar el hueco pediría sellar también
el contenido de los YAML, o comprobar cada cifra contra la sección que cita;
está sin decidir y hoy no se hace.

El sellado del paso 5 reescribe `criteria/.sincronia.json`. Si se queda fuera
del commit, R2 volverá a protestar sobre un repositorio que se cree recién
sellado.

El registro es uno solo para todo `criteria/`, no uno por versión: R2 mira las
anclas que cita **cualquier** versión viva, y guardarlo dentro de una carpeta
de versión haría que sellar escribiese en una versión ya congelada.

## Cuándo se congela una versión y cómo se abre la siguiente

Una versión de criterios se congela **el día en que se aprueba la primera
corrección hecha con ella**. A partir de ahí, esa carpeta es la prueba de con
qué criterio exacto se corrigió a un alumno, y no se toca nunca más.

```
python tools/verificar_gobernanza.py --congelar v2026-2027
```

El sello es `criteria/vAAAA-AAAA/.congelada`, y va al commit como cualquier
otro fichero. R4 compara desde entonces cada `*.yaml` de esa carpeta con el
sello: si alguno cambia, desaparece o se añade, protesta.

Para cambiar un criterio de una versión ya congelada se abre la siguiente:

```
1. Crear   criteria/vAAAA-AAAA/                    la carpeta de la version nueva
2. Copiar  solo los *.yaml de la version anterior  NUNCA la carpeta entera
3. Editar  la prosa primero y el YAML nuevo despues
4. Escribir docs/changes/AAAA-MM-DD-<asunto>.md
5. Ejecutar python tools/verificar_gobernanza.py --sellar
```

El paso 2 es literal. Una copia recursiva arrastra `.congelada`, con lo que la
versión nueva nace congelada y la primera edición vuelve a hacer saltar a R4,
que ya no puede ayudar: `--congelar` se niega a resellar una versión sellada,
justamente para que nadie borre la prueba de que una versión usada fue
alterada.

## Puesta en marcha

```
python -m pip install -r requirements-dev.txt
python tools/instalar_hooks.py
python -m pytest
python tools/verificar_gobernanza.py
```

El hook se salta con `git commit --no-verify`. Existe para emergencias reales.
Saltárselo por prisa deja el repositorio en un estado que nadie sabrá
interpretar después.
