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
hace saltar nada y eso no significa que se haya comprobado. *Verificada.*

**R3 · Lo pendiente se marca, no se inventa.** `estado: PENDIENTE_OFICIAL`, con
`bloquea` y entrada en `docs/PENDIENTE_OFICIAL.md`. Un criterio pendiente no
lleva valor. *Verificada.*

**R4 · Los criterios se versionan y se congelan.** Una versión usada en una
corrección aprobada no se modifica: se crea la siguiente. *Verificada.*

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
6. Commit, incluyendo criteria/vAAAA-AAAA/.sincronia.json
```

El orden importa. Editar el YAML primero es exactamente lo que R2 impide.

El sellado del paso 5 reescribe `criteria/vAAAA-AAAA/.sincronia.json`. Si se
queda fuera del commit, R2 volverá a protestar sobre un repositorio que se
cree recién sellado.

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
