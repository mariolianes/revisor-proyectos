# Taxonomía de incidencias para medir la calibración

**Fecha:** 2026-08-31
**Autor:** Agente (a petición del docente)

## Que cambia

El arnés de calibración (`tools/calibrar.py`) medía el indicador «cobertura»
del §11.1 buscando, en las observaciones del informe, las frases literales
con las que el docente describió cada caso P01-P09 (`debe_encontrar`,
normalizado sin tildes ni mayúsculas). El resultado de esa búsqueda -2 de 26
frases localizadas en la calibración real del 2026-08-30- no distinguía un
sistema que ve los problemas y los llama de otro modo de uno que
efectivamente no los ve.

Ahora existe una taxonomía cerrada de diez categorías de incidencia
(`docs/maestro/04-calibracion.md#13`, derivada en
`criteria/v2026-2027/taxonomia-incidencias.yaml`), y `evaluar()` compara por
categoría, severidad (P1-P4) y evidencia localizada -«evidencias
compatibles»-, no por coincidencia de palabras. `debe_encontrar`/`no_debe`
siguen existiendo -no se han borrado casos ya escritos con ellos, y `no_debe`
sigue siendo una señal razonable sobre economía del feedback-, pero ya no son
de los que depende el indicador de cobertura; se muestran aparte, marcados
como señal léxica heredada.

`docs/calibracion/casos.example.yaml` incorpora `incidencias_esperadas` para
los nueve casos P01-P09, traduciendo el párrafo 6 del calibrador a la
taxonomía. Es una lectura razonada de quien mantiene el fichero de ejemplo,
no una autoridad: varios rasgos del párrafo 6 (metodología débil, proveedor
genérico, lenguaje poco neutral, verificación regulatoria) no encajan en
ninguna de las diez categorías y quedan en notas, no forzados a un código.

## Por que

Instrucción directa del docente, 2026-08-31: «la comparación debería
realizarse mediante una taxonomía estable de incidencias [...] El sistema y
la referencia humana coinciden cuando detectan la misma categoría con una
severidad equivalente y evidencias compatibles, aunque la redacción sea
diferente».

La decisión de dónde sale la categoría de cada observación -del motor, o de
la dimensión ya verificada- se tomó a favor de la dimensión
(`Valoracion.dimension`, `backend/analisis/taxonomia.py`,
`categorias_de_dimension`): pedírsela al motor añadiría una afirmación más
del motor sin manera de comprobarla, y la usaríamos para medir al propio
motor -la fuente que se audita no puede ser también el árbitro de la
auditoría-. El precio, documentado en el propio YAML: una dimensión no
siempre implica una categoría única (D07 puede ser DEV-INSUF, TEO-EXCESO o
APL-FALTA), así que la comparación acepta cualquiera de las categorías
posibles de la dimensión, no una sola calculada.

## Fuente que lo respalda

Instrucción directa del docente sobre cómo medir la calibración
(2026-08-31), transcrita en `docs/maestro/04-calibracion.md#13` -nivel 5 de
la jerarquía del §14.1: calibra el comportamiento del sistema, no crea
criterios académicos nuevos ni contradice al Documento Maestro-.

## Que arrastra

- `docs/maestro/04-calibracion.md` (nueva sección §13, con las anclas
  `calibracion#13-taxonomia-de-incidencias`).
- `criteria/v2026-2027/taxonomia-incidencias.yaml` (nuevo).
- `backend/analisis/taxonomia.py` (nuevo: `CategoriaDeIncidencia`,
  `cargar_taxonomia`, `codigos_validos`, `categorias_de_dimension`).
- `tools/calibrar.py` (`IncidenciaEsperada`, `CasoDeCalibracion.
  incidencias_esperadas`, `ResultadoDeCaso.incidencias_halladas/
  incidencias_ausentes`, `mapa_de_categorias`, `_incidencias_del_informe`,
  `evaluar()`, `_ejecutar_caso()`, `ejecutar()`, `_indicadores()`,
  `_formatear()`).
- `docs/calibracion/casos.example.yaml` (incidencias_esperadas en los nueve
  casos).
- `tools/gobernanza/sincronia.py`: al escribir la nueva sección se
  descubrió que `PATRON_CUALQUIER_ANCLA` no reconocía anclas `calibracion#`
  como límite de sección -un bug preexistente, no introducido aquí, que
  hacía que el «cuerpo» de cualquier sección citada del documento de
  calibración se extendiera siempre hasta el final del fichero en vez de
  hasta la siguiente sección-. Se corrige aquí porque, sin corregirlo, R2
  nunca habría podido sellar limpiamente esta sección nueva sin marcar
  también como «cambiadas» las otras cuatro secciones de calibración ya
  citadas, que no se han tocado. Ver el comentario junto al patrón y
  `tests/gobernanza/test_sincronia.py::test_una_seccion_de_calibracion_no_se_ve_alterada_por_un_cambio_posterior_en_otra`.
- Pruebas nuevas: `tests/analisis/test_taxonomia.py`,
  `tests/tools/test_calibrar_taxonomia.py`, dos casos de regresión añadidos
  a `tests/gobernanza/test_sincronia.py`.

## Correcciones cerradas afectadas

Ninguna: la versión `v2026-2027` de `criteria/` no está congelada todavía
(no hay `.congelada` en `criteria/v2026-2027/`), así que no hay ninguna
corrección aprobada que dependiera del criterio anterior.
