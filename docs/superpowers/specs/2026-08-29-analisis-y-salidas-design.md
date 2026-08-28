# Diseño: el análisis y las dos salidas (Parte B)

**Fecha:** 2026-08-29
**Estado:** Aprobado por el docente responsable
**Alcance:** desde que existe la lectura objetiva de una entrega hasta que el docente aprueba el texto que devolverá al alumno. No cubre la evaluación de la defensa, reservada a valoración humana por el §6.5.

**Continúa** el diseño del flujo de corrección de 2026-08-27, cuya Parte A está terminada y fusionada.

---

## 1. Qué resuelve

La Parte A dice si un trabajo cumple el formato. No dice si está bien. Esta parte valora las doce dimensiones, localiza la evidencia de cada juicio, redacta el informe interno y el borrador de devolución, y se detiene para que el docente decida.

El principio no cambia: **propone, evidencia y se detiene.** Lo nuevo es que ahora hay un modelo de lenguaje de por medio, y casi todo este diseño trata de cómo no depender de que se porte bien.

## 2. Cómo se le pide el juicio al motor

**Una sola llamada con el trabajo entero y todas las dimensiones activas.**

Se descartaron dos alternativas. Una llamada por dimensión deja a cada juicio ciego respecto a los demás, y varios de los patrones que el §5 de la calibración considera importantes —la viabilidad declarativa, la incoherencia entre estrategia y contingencia, la bibliografía nominal— solo se ven mirando el documento completo. Trocearlo habría producido un sistema incapaz de encontrar lo que más importa. Dos pasadas —mapa y luego valoración— se parecen más a cómo corrige una persona, pero duplican las llamadas y las piezas que pueden fallar sin resolver nada que la llamada única no resuelva.

### 2.1 El motor rellena un formulario, no redacta

Se le exige una estructura fija y el proveedor la valida antes de devolverla. Por cada **dimensión activa en esa fase**: nivel, prioridad, cita literal del trabajo, apartado aproximado y observación. Además, las fortalezas, los patrones detectados y las dudas que reserva al docente.

Eso convierte «el modelo dijo algo» en «el modelo rellenó estos campos», que sí se puede comprobar.

**Las dimensiones activas salen de `criteria/`, no del motor.** En E1 se le piden cinco y en FINAL doce, según `dimensiones.yaml` y `matriz-fases.yaml`. La instrucción se construye desde los ficheros de criterios —dimensiones, prioridades, feedback, semáforo—, así que **cambiar un criterio cambia lo que se le pide sin tocar código**. Es la misma relación que ya existe entre `formato.yaml` y la comprobación de formato.

### 2.2 El texto se envía íntegro

**Decisión del docente, 2026-08-29: no se anonimiza.** El trabajo va completo al proveedor, portada incluida.

Esto **contradice el §19 del Documento Maestro**, que hoy describe un circuito con anonimización previa, y **obliga a corregirlo** con su documento de cambio. Se toma sabiéndolo.

Lo que **no** cambia: ninguna entrega real pasa por el proveedor hasta que se confirmen las condiciones de tratamiento —la entrada `proteccion_datos` de `docs/PENDIENTE_OFICIAL.md`, que bloquea el piloto—. Eso alcanza también a los nueve casos de calibración, que son trabajos reales del curso anterior.

## 3. Arquitectura

```
backend/analisis/
  contrato.py      el formulario que el motor debe rellenar
  instruccion.py   qué se le pide, construido desde criteria/
  proveedor.py     el puerto ProveedorAnalisis y el adaptador simulado
  openai.py        el adaptador real
  verificacion.py  las defensas deterministas
backend/salidas/
  informe.py       el Anexo C
  borrador.py      el Anexo D
  coherencia.py    el control del §17.2
backend/api/analisis.py
frontend/src/paginas/Revision.tsx
```

`analisis/` no sabe qué es un informe. `salidas/` no sabe qué es OpenAI. Es la misma separación que en la Parte A entre medir y juzgar, y sirve para lo mismo: cambiar de proveedor sin tocar las salidas, y cambiar el formato de un informe sin tocar el motor.

## 4. Las siete defensas

Ninguna depende de que el modelo se porte bien. Todas son código propio y todas son comprobables.

**1. Cada cita se busca en el texto real.** El motor devuelve un fragmento literal; se localiza en el texto que se le envió. Si no aparece, ese juicio pasa a `NO_VERIFICABLE`, no llega al alumno y queda anotado en el informe como no localizado. Un modelo puede inventarse una frase; no puede hacer que exista en el documento.

La comparación normaliza espacios y tildes, y admite que la cita sea un fragmento contiguo del texto. No admite paráfrasis: si el motor resume en vez de citar, no se da por verificado.

**2. Ninguna dimensión de más ni de menos.** Las que no están activas en esa fase se rechazan aunque el motor las devuelva; las que faltan se marcan como ausentes en lugar de darse por buenas.

**3. Los P4 no pasan al borrador. Nunca.** El §7 de la calibración lo fija y aquí es una condición, no una intención.

**4. Máximo cuatro prioridades en el borrador**, por la regla de economía pedagógica del §2.3. Si hay más candidatas, se ordenan por prioridad y se corta; el resto queda en el informe.

**5. Ninguna nota.** Aunque el motor la sugiera, se descarta antes de guardarla. Las ponderaciones siguen en `PENDIENTE_OFICIAL` y R3 prohíbe sustituir un dato oficial ausente por una estimación.

**6. Control de coherencia del §17.2.** Si el informe marca una carencia crítica, el borrador no puede describir el trabajo como correcto; si el trabajo está sólido, el borrador no se infla con mejoras menores. Se comprueba antes de presentar ninguna de las dos salidas.

**7. Ninguna afirmación categórica de autoría.** Se registra el indicio y se reserva la decisión al docente, como piden el §11 y el punto 9 del Anexo B de la calibración.

## 5. Las dos salidas

**El informe técnico interno** sigue el Anexo C: identificación, control administrativo, resumen ejecutivo, valoración por dimensión con evidencia y prioridad, continuidad respecto al feedback anterior, fortalezas, prioridades, dudas docentes y resultado provisional —semáforo y recomendación, **sin nota**—.

**El borrador de devolución** sigue el Anexo D y el formato que fija el §4 de la calibración: dos párrafos por defecto, con valoración general, fortaleza principal, carencia clave y acciones priorizadas. Se amplía solo cuando la situación lo exige.

## 5.1 Qué se guarda, y por qué aquí sí

En la Parte A no se guardan las medidas: recalcularlas es gratis y siempre da
lo mismo. **Aquí es al revés.** Un análisis cuesta dinero y no es
determinista, así que volver a pedirlo no solo se paga dos veces: puede dar
otra cosa, y el docente vería cambiar bajo sus pies un juicio que ya estaba
revisando.

El análisis se persiste en las tablas que ya existen y que se diseñaron para
esto: `correccion`, `valoracion_dimension` y `evidencia`. Sus restricciones ya
protegen lo que hace falta —una evidencia no pasa de 1.500 caracteres, una nota
aprobada exige constancia de quién y cuándo—.

Reanalizar es una acción explícita del docente, nunca un efecto de abrir la
ficha, y deja constancia de que hay un análisis anterior.

**Lo que sigue sin guardarse:** el PDF y el texto del trabajo, por D-001. De la
evidencia se guarda la cita, acotada, no el documento.

## 5.2 Cuando el motor falla

Un proveedor externo se cae, agota su cuota, tarda demasiado o devuelve algo
que no encaja en el formulario. Ninguna de esas cosas puede dejar al docente
mirando un error del servidor, y ninguna puede producir media corrección.

- **El análisis es atómico:** o se guarda entero y validado, o no se guarda
  nada. Una entrega con un análisis a medias no existe.
- **El error llega al docente en castellano**, diciendo qué ha pasado y si
  puede reintentar. Es la misma lección de la Parte A, donde un fallo del
  almacén llegaba como «Internal Server Error».
- **Un formulario mal formado se reintenta una vez**, porque es el fallo más
  común y el más barato de resolver. Si vuelve a fallar, se detiene y se dice.
- **La entrega no cambia de estado** si el análisis no se completó. Sigue en
  `RECIBIDO`, no pasa a `ANALIZADO`.

## 6. La revisión del docente

Observación por observación: aceptar, editar o descartar. Solo lo aprobado pasa al histórico, que es lo que el §13 reserva al profesor.

Al cerrar, el texto aprobado se ofrece listo para copiar. El docente lo pega en el Aula Virtual y marca que lo comunicó, según D-004.

## 7. El arnés de calibración

Un comando **aparte de la suite de tests**, porque depende de la red y cuesta dinero. Pasa los casos P01-P09 por el motor y compara con el diagnóstico que el docente ya escribió: si acierta el semáforo de referencia, si encuentra el problema principal, si respeta los niveles de prioridad y si no se va por las ramas.

Las once pruebas del §11 de la calibración se convierten en su informe de resultados, con los siete indicadores del §11.1 —cobertura, exactitud, prioridad, proporcionalidad, tono, prudencia y ahorro—.

Los PDF de calibración viven **fuera del repositorio**, como las entregas, y por el mismo motivo: son trabajos reales de alumnos y R6 impide que entren en el árbol versionado.

Mientras no lleguen, el arnés se prueba con documentos sintéticos que verifican **el arnés**, no el acierto del motor.

## 8. Cómo se prueba lo que no es determinista

La suite normal **no llama nunca al proveedor real**. Corre contra el adaptador simulado, que devuelve respuestas fijas, y comprueba lo que sí es determinista: que las siete defensas funcionan, que la instrucción se construye con las dimensiones correctas para cada fase, que las salidas tienen la forma del Anexo C y del Anexo D, y que un motor que devuelve basura —una dimensión inexistente, una cita inventada, una nota, quince prioridades— es rechazado.

Ese último grupo es el importante: **se prueba el sistema contra un motor hostil**, no contra uno que colabora.

El acierto del diagnóstico solo se mide en el arnés de calibración, con casos reales, y su resultado es un informe para el docente, no un test en verde.

## 9. Lo que este subsistema no hará

**No habrá nota**, por lo dicho en la defensa 5.

**No se enviará nada al alumno.** El §21.2 deja fuera el envío de correos y la integración con el Aula Virtual.

**No se evaluará la defensa oral**, que el §6.5 reserva a valoración humana.

**No se afirmará que un texto lo ha escrito una IA.** Se registran indicios y decide el docente.

## 10. Lo que arrastra

- Corrección del §19 del Documento Maestro, que describe un circuito con anonimización que ya no se aplica.
- Una decisión nueva en `docs/decisions.md` sobre el envío íntegro del texto.
- La entrada `proteccion_datos` de `PENDIENTE_OFICIAL` sigue bloqueando el piloto con entregas reales, ahora con más razón.
