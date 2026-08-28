# Documento Maestro del Sistema de Corrección y Seguimiento

> **Curso 2026-2027 · Proyecto Intermodular**
> Documento interno. No dirigido al alumnado.
> Origen: `Documento_Maestro_Sistema_Correccion_Proyectos_Intermodulares_2026-2027.pdf`
> Convertido a Markdown el 2026-08-26. Desde esta fecha, **este fichero es la
> fuente de verdad** y el PDF pasa a ser una copia histórica.

Marco académico, modelo de corrección y especificación funcional del asistente local

Base consolidada antes de incorporar la programación didáctica, las rúbricas y el calendario oficial. No es un documento dirigido al alumnado.

## Contenido

**PARTE I. Marco académico y pedagógico**

1. Finalidad, alcance y principios del Documento Maestro
2. Qué es intrínsecamente un Proyecto Intermodular
3. Modalidades y adaptación a los ciclos formativos
4. Estructura académica común del proyecto
5. Ciclo de vida: tema, entregas y defensa
6. Estándar académico y condiciones transversales

**PARTE II. Modelo de corrección, evaluación y seguimiento**

7. Principios del modelo de corrección
8. Dimensiones de evaluación
9. Matriz de revisión por entregas
10. Evaluación continua, nota interna y ficha del alumno
11. Feedback y dos salidas internas
12. Errores recurrentes, alertas y semáforo
13. Decisiones reservadas al profesor

**PARTE III. Especificación funcional del sistema local**

14. Fuentes de verdad y criterios configurables
15. Modelo de datos y estructura local
16. Flujo propuesto de corrección
17. Esquema de las dos salidas
18. Reglas funcionales y condiciones de parada
19. Privacidad, seguridad y trazabilidad
20. Calibración y control de calidad
21. Producto mínimo viable y funciones aplazadas
22. Hoja de ruta de implantación

**PARTE IV. Plantillas y anexos operativos**

Anexos A-H. Fichas, informes, semáforo, instrucciones maestras y control de versiones

---

# PARTE I

## Marco académico y pedagógico

<!-- ancla: maestro#1-principios -->
## 1. Finalidad, alcance y principios del Documento Maestro

Este documento reúne en una única fuente el modelo académico del Proyecto
Intermodular, el método de corrección y seguimiento y los requisitos
funcionales del futuro sistema local. Su función es evitar que la guía del
alumnado, el criterio del docente y el comportamiento del asistente
evolucionen por caminos distintos.

> **Decisión central:** El sistema asistirá en la lectura, la comparación, la
> preevaluación y la redacción de borradores. La valoración definitiva, la
> calificación y cualquier comunicación al alumno pertenecerán siempre al
> profesor.

### 1.1 Usuarios y usos

| Usuario | Uso principal | Límite |
|---|---|---|
| Marcos / docente | Corregir, seguir la evolución, registrar notas y preparar feedback | Aprueba o modifica toda salida |
| Colaborador técnico | Construir, probar y mantener la solución | No redefine criterios académicos |
| Asistente local | Aplicar criterios, localizar evidencias y generar borradores | No decide ni publica |
| Alumno | Recibe únicamente el feedback validado por el docente | No accede al informe interno |

### 1.2 Principios no negociables

- **Nivel propio de Formación Profesional:** riguroso, claro, aplicado y proporcionado.
- **Carácter profesional e intermodular:** el proyecto debe integrar aprendizajes de varios módulos y aplicarlos a una situación significativa del sector.
- **Evaluación progresiva:** cada fase se valora por lo que debe existir en ese momento, no por exigencias de fases posteriores.
- **Documento acumulativo:** cada entrega contiene lo anterior corregido más el nuevo desarrollo.
- **Trazabilidad:** toda observación debe vincularse a una evidencia del documento, una ausencia verificable o un criterio vigente.
- **Prudencia:** el sistema distingue entre hecho, inferencia, duda y decisión reservada al profesor.
- **Humanidad del feedback:** claridad y firmeza sin perder cercanía, contexto ni capacidad de motivar.
- **No automatización del alumno:** ninguna salida se envía ni publica sin revisión docente.

### 1.3 Estado de las decisiones

| Estado | Incluye | Tratamiento |
|---|---|---|
| Estable | Definición del proyecto, tres modalidades, cuatro entregas, documento único, doble salida interna y supervisión humana | Se incorpora al sistema como regla base |
| Configuración docente | Tono, extensión del feedback, semáforo, notas internas y observaciones personales | Puede ajustarse por caso sin alterar la base |
| Pendiente oficial | Fechas, rúbrica, ponderaciones definitivas, defensa y posibles particularidades de centro o comunidad | Se marca y versiona; no se inventa |

<!-- ancla: maestro#2-que-es-un-proyecto-intermodular -->
## 2. Qué es intrínsecamente un Proyecto Intermodular

El Proyecto Intermodular es un trabajo académico-profesional de larga duración en el que el
estudiante integra competencias de distintos módulos para estudiar una necesidad, problema u
oportunidad relacionada con su ciclo formativo. No se limita a demostrar que conoce conceptos:
debe utilizarlos para analizar, decidir, diseñar, investigar, justificar y extraer conclusiones
defendibles.

> **Definición operativa:** Un Proyecto Intermodular parte de una situación profesional concreta,
> formula objetivos, selecciona un procedimiento, desarrolla una respuesta fundamentada y
> demuestra qué resultados, conclusiones o mejoras pueden obtenerse.

### 2.1 Rasgos esenciales

| Rasgo | Significado para el proyecto | Consecuencia para la corrección |
|---|---|---|
| Intermodular | Integra conocimientos y capacidades de varios módulos | No basta con desarrollar un único concepto aislado |
| Aplicado | Utiliza lo aprendido sobre un caso, necesidad o pregunta profesional | Se distingue teoría útil de acumulación teórica |
| Progresivo | Se construye durante aproximadamente nueve meses | Se compara la evolución entre versiones |
| Documentado | Las afirmaciones y decisiones se sostienen con fuentes, datos o método | Se comprueba evidencia y trazabilidad |
| Propio | Refleja la investigación, comprensión y decisiones del alumno | Debe poder explicarse y defenderse |
| Defendible | Culmina en un documento final y una exposición | La coherencia y la comprensión importan tanto como el formato |

### 2.2 Qué no debe confundirse con un Proyecto Intermodular

- Una recopilación de definiciones o un resumen de apuntes sin aplicación.
- Un plan de empresa genérico construido a partir de apartados estándar sin decisiones propias.
- Una investigación puramente teórica sin procedimiento, comparación, resultados ni conclusión propia.
- Una idea atractiva sin desarrollo operativo, datos, viabilidad o criterios de evaluación.
- Un conjunto de capítulos independientes entregados por fascículos.
- Un documento que el estudiante no comprende o no puede defender.

### 2.3 La lógica común

| Movimiento | Pregunta | Resultado esperado |
|---|---|---|
| Delimitar | ¿Qué situación concreta se quiere abordar? | Tema viable y contexto definido |
| Justificar | ¿Por qué importa y qué relación tiene con el ciclo? | Necesidad o interés fundamentado |
| Objetivar | ¿Qué se pretende conseguir? | Objetivo general y objetivos específicos |
| Proceder | ¿Cómo se investigará o desarrollará? | Metodología comprensible |
| Desarrollar | ¿Qué análisis, propuesta o resultados se construyen? | Núcleo aplicado del proyecto |
| Concluir | ¿Qué respuesta se obtiene y qué límites existen? | Conclusiones vinculadas a objetivos |
| Defender | ¿Puede el alumno justificar decisiones y evidencias? | Proyecto propio y defendible |

<!-- ancla: maestro#3-modalidades -->
## 3. Modalidades y adaptación a los ciclos formativos

Existe un único Proyecto Intermodular, pero se admiten tres modalidades internas. No son
módulos distintos ni procesos de evaluación separados: son caminos diferentes para desarrollar
el núcleo del proyecto dentro de una estructura y unas entregas comunes.

| Modalidad | Pregunta central | Núcleo del desarrollo | Resultado característico |
|---|---|---|---|
| Profesional: creación, estrategia o mejora | ¿Qué propuesta puede resolver o mejorar una situación profesional? | Diagnóstico, diseño, recursos, acciones, viabilidad y riesgos | Plan o propuesta aplicable |
| Investigación o innovación aplicada | ¿Qué ocurre, por qué y qué mejora puede comprobarse o plantearse? | Pregunta, método, datos, análisis e interpretación | Resultados y recomendación fundamentada |
| Revisión bibliográfica o documental | ¿Qué respuesta ofrece la evidencia publicada sobre un problema profesional? | Búsqueda, selección, comparación y síntesis crítica | Conclusión propia basada en fuentes |

### 3.1 Adaptación por ciclo

| Ciclo | Profesional | Investigación / innovación | Revisión documental |
|---|---|---|---|
| Marketing y Publicidad | Plan de captación, marca, CRM o fidelización | Análisis de hábitos, campañas, audiencias o experiencia | Evidencia sobre tendencias, canales o comportamiento |
| Comercio Internacional | Plan de exportación, entrada en mercado o logística | Estudio de barreras, demanda, proveedores o procesos | Comparación normativa, mercados o modelos de internacionalización |
| Administración y Finanzas | Mejora de tesorería, control, procesos o viabilidad | Análisis de costes, liquidez, productividad o digitalización | Revisión sobre financiación, control, fiscalidad o gestión |

> **Regla de adaptación:** El ciclo y la modalidad cambian los ejemplos, la metodología y las
> evidencias razonables; no cambian la obligación de justificar, desarrollar, concluir y defender.

### 3.2 Selección de modalidad

- La modalidad se fija al validar el tema y puede ajustarse si el desarrollo demuestra que otro enfoque es más coherente.
- No debe utilizarse una modalidad para rebajar la exigencia, sino para adaptar el método a la pregunta y a las fuentes disponibles.
- Los proyectos híbridos son posibles, pero el sistema debe identificar una modalidad principal para cargar los criterios adecuados.
- Un cambio sustancial de modalidad o tema requiere decisión expresa del profesor y debe quedar registrado.

<!-- ancla: maestro#4-estructura-comun -->
## 4. Estructura académica común del proyecto

La estructura común actúa como mapa. Los títulos pueden adaptarse cuando la programación o
la lógica del proyecto lo requieran, pero cada función académica debe quedar cubierta sin
repeticiones ni apartados vacíos.

| Bloque | Función | Pregunta de corrección |
|---|---|---|
| Portada, resumen e índice | Identificar, sintetizar y organizar | ¿Permiten reconocer y recorrer el trabajo? |
| Introducción y justificación | Presentar la situación y su relevancia | ¿Se entiende qué se aborda y por qué importa? |
| Objetivos | Definir la finalidad y los logros concretos | ¿Son claros, desarrollables y evaluables? |
| Contexto y marco teórico | Aportar solo la base necesaria | ¿La teoría se utiliza después o solo ocupa espacio? |
| Metodología o procedimiento | Explicar cómo se obtuvo y trató la información | ¿Pueden seguirse las decisiones y las evidencias? |
| Desarrollo / resultados | Construir el núcleo aplicado | ¿Existe análisis, propuesta, comparación o resultado real? |
| Conclusiones | Responder a objetivos y reconocer límites | ¿Concluye a partir de lo desarrollado? |
| Bibliografía | Identificar fuentes reales y utilizadas | ¿Las citas y referencias se corresponden? |
| Anexos | Aportar evidencia complementaria | ¿Son útiles y están mencionados? |

### 4.1 Adaptación por modalidad

| Bloque | Profesional | Investigación | Revisión documental |
|---|---|---|---|
| Metodología | Fuentes y pasos para diseñar la propuesta | Muestra, instrumentos y análisis | Búsqueda, criterios de selección y comparación |
| Desarrollo | Acciones, recursos, costes, tiempos y viabilidad | Datos, resultados e interpretación | Síntesis crítica, coincidencias y discrepancias |
| Conclusiones | Valor y viabilidad de la propuesta | Respuesta a la pregunta y límites | Respuesta basada en el conjunto de fuentes |

> **Documento de referencia:** El Índice comentado del Proyecto Intermodular desarrolla qué
> debe aparecer en cada apartado y forma parte de las fuentes maestras del sistema.

<!-- ancla: maestro#5-ciclo-de-vida -->
## 5. Ciclo de vida: tema, entregas y defensa

El trabajo se desarrolla durante aproximadamente nueve meses. La elección del tema es una
validación previa y no una entrega evaluable. Después existen cuatro entregas acumulativas y
una presentación o defensa final.

| Hito | Estado esperado | Finalidad | Continuidad |
|---|---|---|---|
| Validación del tema | Idea concreta, viable y relacionada con el ciclo | Autorizar el inicio y fijar modalidad | No puntúa como entrega |
| 1.ª entrega | Base inicial definida | Comprobar dirección, objetivos e índice | Abre el documento acumulativo |
| 2.ª entrega | Desarrollo sustancial | Construir el núcleo y aplicar el primer feedback | Incluye la 1.ª corregida |
| 3.ª entrega | Proyecto prácticamente completo | Detectar los últimos problemas | Incluye todo lo anterior corregido |
| Entrega final | Documento definitivo | Depositar un trabajo completo y defendible | No borra el proceso previo |
| Presentación | Exposición y defensa | Demostrar comprensión y justificar decisiones | Se registra como componente docente |

### 5.1 Regla del documento único

> **Regla obligatoria:** Cada entrega se realiza sobre el mismo documento acumulativo. La
> nueva versión contiene todo lo anterior corregido más el contenido nuevo de la fase.

- El sistema debe comparar versiones y feedback cuando existan archivos anteriores.
- No debe aceptar como normal una entrega formada únicamente por capítulos nuevos.
- Debe conservar las versiones anteriores sin sobrescribirlas.
- La tercera entrega no se confundirá con la final: es casi completa, pero todavía orientable.
- La entrega final no recupera automáticamente el trabajo no realizado durante el curso.

### 5.2 Función del feedback entre fases

El feedback establece prioridades para la siguiente versión. La corrección no debe limitarse a
volver a analizar el archivo actual desde cero: debe comprobar qué observaciones anteriores
fueron aplicadas, cuáles permanecen y si las modificaciones han generado nuevas
incoherencias.

<!-- ancla: maestro#6-estandar-academico -->
## 6. Estándar académico y condiciones transversales

### 6.1 Nivel y extensión

El estándar busca un trabajo serio y profesional propio de FP, sin convertirlo en una tesis
universitaria. Como regla de trabajo definida, el contenido principal tendrá un mínimo de 20
páginas, excluidas portada, índice y anexos. La extensión debe proceder del análisis y del
desarrollo, no de recursos gráficos o espacios artificiales.

### 6.2 Formato general

| Elemento | Regla base |
|---|---|
| Tipografía | Arial 11, salvo indicación oficial distinta |
| Interlineado | 1,5 |
| Alineación | Texto justificado |
| Márgenes | Regulares, aproximadamente 2,5 cm |
| Navegación | Páginas numeradas, títulos jerarquizados e índice actualizado |
| Archivo | Un único PDF generado desde el original; Word editable cuando se solicite |
| Imágenes y tablas | Proporcionadas, tituladas, citadas y explicadas |

### 6.3 Fuentes y rigor

- Utilizar fuentes reales, localizables y adecuadas al objeto del proyecto.
- Distinguir datos reales, opiniones de fuentes y estimaciones propias.
- Citar mediante APA o Vancouver según las instrucciones aplicables.
- Mantener correspondencia entre citas del texto y bibliografía final.
- No inventar autores, referencias, datos, encuestas, entrevistas ni resultados.

### 6.4 Autoría e inteligencia artificial

El proyecto debe reflejar las decisiones, la investigación y la comprensión del estudiante. Las
normas dirigidas al alumnado no autorizan el uso de IA generativa para redactar apartados,
inventar datos, crear referencias inexistentes, reformular textos ajenos como propios ni sustituir
el proceso de análisis.

> **Regla del sistema:** El asistente puede identificar patrones que justifican una comprobación,
> pero nunca afirmará automáticamente que existe copia o uso indebido de IA. Registrará
> indicios, evidencia y nivel de incertidumbre para decisión del profesor.

### 6.5 Defensa

La presentación es un componente propio de la evaluación. El sistema puede preparar una lista
de comprobación y registrar la valoración introducida por el profesor, pero no evaluará
automáticamente una defensa en directo en la primera versión.

---

# PARTE II

## Modelo de corrección, evaluación y seguimiento

<!-- ancla: maestro#7-principios-correccion -->
## 7. Principios del modelo de corrección

La corrección debe ayudar a decidir qué está funcionando, qué impide avanzar y qué debe
priorizarse en la siguiente fase. No consiste en reescribir el proyecto ni en producir una lista
exhaustiva de observaciones menores.

| Principio | Aplicación |
|---|---|
| Adecuación a la fase | No exigir conclusiones definitivas en la primera entrega ni tratar la tercera como final |
| Prioridad | Separar carencias críticas, correcciones importantes y mejoras secundarias |
| Evidencia | Indicar apartado, página o fragmento cuando sea posible |
| Continuidad | Comparar feedback anterior, cambios y pendientes |
| Proporción | Feedback breve por defecto; ampliar solo cuando reconducir lo exija |
| Utilidad | Explicar cómo mejorar sin redactar el contenido por el alumno |
| Coherencia | La nota, el semáforo, el informe y el feedback deben contar la misma historia |

### 7.1 Orden de lectura

1. Validación administrativa. Confirmar alumno, ciclo, modalidad, fase, plazo y legibilidad del archivo.
2. Lectura estructural. Comprobar presencia, orden y equilibrio de los apartados que corresponden.
3. Lectura académica. Valorar contenido aplicado, coherencia, fuentes, método, resultados y conclusiones.
4. Lectura evolutiva. Contrastar la versión actual con feedback y archivos anteriores.
5. Síntesis. Determinar fortalezas, prioridades, semáforo y nota propuesta.
6. Redacción. Generar el informe interno y el borrador de devolución.

<!-- ancla: maestro#8-dimensiones -->
## 8. Dimensiones de evaluación

Las dimensiones son comunes, pero su peso y profundidad se configuran por fase, modalidad y
programación. Una dimensión puede estar activa, ser orientativa o no corresponder todavía.

| Código | Dimensión | Qué observa |
|---|---|---|
| D01 | Adecuación al ciclo e intermodularidad | Relación profesional e integración de aprendizajes |
| D02 | Tema, necesidad y justificación | Concreción, relevancia y evidencia de partida |
| D03 | Objetivos | Claridad, coherencia y posibilidad de respuesta |
| D04 | Estructura y coherencia global | Orden, equilibrio y ausencia de contradicciones |
| D05 | Fundamentación y fuentes | Selección, calidad, citas y uso real |
| D06 | Metodología o procedimiento | Trazabilidad del trabajo y adecuación al enfoque |
| D07 | Desarrollo aplicado | Profundidad, decisiones, viabilidad y uso de competencias |
| D08 | Resultados e interpretación | Evidencias, significado y relación con objetivos |
| D09 | Conclusiones | Respuesta, límites, aportación y mejora |
| D10 | Evolución y feedback | Correcciones incorporadas y progreso entre versiones |
| D11 | Redacción y presentación | Claridad, rigor, formato, tablas e imágenes |
| D12 | Autoría y defendibilidad | Comprensión, decisiones propias y ausencia de indicios críticos |

### 8.1 Escala de valoración provisional

| Nivel | Significado | Uso |
|---|---|---|
| Sólido | Cumple con claridad y aporta evidencia suficiente | Conservar y, si procede, pulir |
| Adecuado | Cumple lo esencial con mejoras localizadas | Avanzar aplicando ajustes |
| En desarrollo | Existe base, pero falta profundidad, conexión o evidencia | Priorizar correcciones antes de cerrar |
| Insuficiente | La carencia impide valorar o sostener una parte esencial | Reconducir y revisar docente |
| No aplicable | No corresponde a la fase o modalidad | No penaliza |
| No verificable | Falta archivo, evidencia o criterio confirmado | Detener juicio y escalar |

<!-- ancla: maestro#9-matriz-entregas -->
## 9. Matriz de revisión por entregas

### 9.1 Validación del tema

| Debe existir | Se comprueba | Salida |
|---|---|---|
| Título o frase provisional | Concreción y comprensión | Validar / concretar |
| Problema, necesidad u oportunidad | Interés profesional | Orientación del enfoque |
| Relación con el ciclo | Adecuación | Modalidad y ciclo registrados |
| Intención del alumno | Qué analizará, diseñará o comprobará | Primeros límites |
| Acceso probable a información | Viabilidad | Riesgos de fuentes |

### 9.2 Primera entrega

Finalidad: comprobar que el proyecto tiene una dirección viable. No se espera un documento
terminado.

1. Portada y título provisional.
2. Presentación del tema y situación de partida.
3. Justificación vinculada al ciclo y al ámbito profesional.
4. Objetivo general y objetivos específicos.
5. Modalidad principal e índice provisional.
6. Primeras fuentes o datos que permitan investigar.

> **No corresponde todavía:** Exigir resultados definitivos, conclusiones cerradas, bibliografía
> completa o un desarrollo exhaustivo.

### 9.3 Segunda entrega

Finalidad: convertir la idea en un proyecto con contenido sustancial e incorporar las
correcciones de la primera fase.

7. Primera entrega corregida e integrada.
8. Introducción, justificación y objetivos revisados.
9. Contexto y marco teórico útil, sin inflación conceptual.
10. Metodología o procedimiento comprensible.
11. Desarrollo aplicado inicial o sustancial.
12. Datos, ejemplos, fuentes o evidencias que sostienen decisiones.
13. Bibliografía actualizada con fuentes utilizadas.

> **Alerta característica:** Subir únicamente los capítulos nuevos o repetir el contenido de la
> primera entrega sin progreso real.

### 9.4 Tercera entrega

Finalidad: presentar un proyecto prácticamente completo y detectar los últimos problemas antes
de la versión definitiva.

14. Todo lo anterior corregido y actualizado.
15. Desarrollo completo de la propuesta, investigación o revisión.
16. Resultados, interpretación, viabilidad o impacto.
17. Conclusiones provisionales relacionadas con objetivos.
18. Bibliografía prácticamente completa y anexos necesarios.
19. Presentación formal cercana a la definitiva.

> **Regla clave:** La tercera entrega no es la final. Debe estar casi terminada para que el último
> feedback se dedique a cerrar, no a construir desde cero.

### 9.5 Entrega final

Finalidad: depositar el documento definitivo, completo, revisado y defendible.

20. Todos los apartados completos y ordenados.
21. Conclusiones definitivas que responden a los objetivos.
22. Citas y bibliografía revisadas.
23. Tablas, gráficos, imágenes y anexos identificados y justificados.
24. Índice y páginas actualizados.
25. Formato uniforme y PDF correctamente generado.
26. Presentación depositada según el procedimiento establecido.

### 9.6 Presentación y defensa

El sistema preparará una ficha de defensa, pero la valoración será introducida por el profesor.
Se observarán comprensión, selección de ideas, claridad, capacidad para justificar decisiones y
respuestas a preguntas.

<!-- ancla: maestro#10-evaluacion-continua -->
## 10. Evaluación continua, nota interna y ficha del alumno

Cada entrega tendrá una valoración interna. El alumno recibirá feedback, pero no verá
necesariamente la calificación numérica de cada fase. El objetivo es evitar que una nota
temprana sustituya a la responsabilidad de seguir trabajando.

> **Modelo provisional previsto:** Primera entrega, segunda entrega, tercera entrega, entrega
> final y presentación: 20 % cada componente. Esta distribución debe permanecer
> configurable hasta validarla con la programación oficial.

### 10.1 Reglas operativas

- Una entrega no realizada o presentada fuera de plazo recibe 0 y no se evalúa académicamente, salvo instrucción oficial o decisión documentada aplicable al caso.
- La entrega final no sustituye automáticamente las fases no realizadas.
- La nota propuesta por el sistema es interna y provisional hasta aprobación docente.
- La presentación se registra manualmente porque incluye observación humana en directo.
- Los casos personales pueden influir en el tono, la orientación o una decisión excepcional, pero no serán inferidos por el sistema: los añadirá el profesor.

### 10.2 Campos de seguimiento

| Campo | Descripción | Visibilidad |
|---|---|---|
| Nota propuesta | Cálculo o valoración preliminar | Solo docente |
| Nota aprobada | Calificación validada por Marcos | Solo docente / acta cuando proceda |
| Semáforo | Estado pedagógico de la fase | Solo docente salvo traducción a feedback |
| Fortalezas | Aspectos que conviene conservar | Base del feedback |
| Prioridades | Cambios que condicionan el avance | Base del feedback |
| Observaciones personales | Contexto aportado por el profesor | Solo docente |
| Estado de feedback | Borrador, revisado, aprobado o comunicado | Solo docente |

<!-- ancla: maestro#11-feedback-y-salidas -->
## 11. Feedback y dos salidas internas

> **Aclaración esencial:** Las dos salidas se generan para el profesor. El borrador dirigido al
> alumno nunca se envía ni se publica automáticamente.

### 11.1 Salida A: informe técnico interno

- Identificación anónima, ciclo, modalidad, fase y versión de criterios.
- Resumen ejecutivo del estado del proyecto.
- Resultado de validaciones administrativas y formales.
- Valoración por dimensiones con evidencias localizadas.
- Comparación con feedback y versiones anteriores.
- Fortalezas, carencias, errores críticos y prioridades.
- Semáforo y nota provisional.
- Dudas o decisiones que requieren criterio docente.
- Propuesta de acción: avanza, avanza con correcciones o necesita reconducción.

### 11.2 Salida B: borrador de devolución al alumno

- Apertura breve que reconozca el trabajo o la evolución real.
- Qué está funcionando y debe conservarse.
- Qué debe corregirse, ordenado por prioridad.
- Orientación concreta sobre cómo mejorar sin redactar el contenido.
- Qué se espera en la siguiente fase.
- Cierre cercano y coherente con el estado del proyecto.

### 11.3 Longitud y tono

| Tipo | Cuándo | Extensión orientativa |
|---|---|---|
| Breve | Proyecto sólido o ajustes localizados | Uno o dos párrafos |
| Estándar | Varias prioridades conectadas | Dos párrafos estructurados |
| Ampliado | Reconducción, carencia crítica o comprobación de autoría | Hasta tres párrafos, con revisión docente reforzada |

El tono será claro, directo, cercano, firme y constructivo. Se evitarán fórmulas vacías como “está
incompleto” sin indicar qué falta, dónde se observa y por qué importa. También se evitará
convertir cada feedback en una tutoría teórica interminable.

<!-- ancla: maestro#12-errores-y-semaforo -->
## 12. Errores recurrentes, alertas y semáforo

| Error | Evidencia habitual | Prioridad |
|---|---|---|
| Tema demasiado amplio | No delimita sector, destinatario o problema | Alta si impide desarrollar |
| Exceso teórico | Muchas definiciones sin uso posterior | Media / alta |
| Proyecto genérico | Apartados estándar sin decisiones ligadas al caso | Alta |
| Objetivos desconectados | No reaparecen en desarrollo o conclusiones | Alta |
| Metodología opaca | No explica de dónde salen datos o decisiones | Alta |
| Fuentes débiles o inventadas | Enlaces sin autor, referencias inexistentes | Crítica |
| Sin evolución | Repite versión o ignora feedback | Alta |
| Formato artificial | Espacios, imágenes o saltos para alcanzar extensión | Media / alta |
| Texto no defendible | Redacción genérica o técnica que el alumno no explica | Crítica / revisión humana |

### 12.1 Semáforo pedagógico

| Estado | Significado | Acción |
|---|---|---|
| VERDE | Cumple la fase y puede avanzar | Mantener fortalezas y aplicar ajustes menores |
| ÁMBAR | Avanza, pero existen correcciones prioritarias | Aplicar cambios antes de cerrar la siguiente fase |
| ROJO | Carencia estructural o académica que exige reconducción | Revisión docente y plan de corrección |
| GRIS | No evaluable: falta, fuera de plazo, archivo ilegible o criterio bloqueado | Resolver incidencia; no emitir juicio académico automático |

> **Importante:** El semáforo resume el estado; no sustituye la rúbrica, la nota ni la explicación.
> Un mismo color puede responder a causas diferentes.

<!-- ancla: maestro#13-reservas-del-profesor -->
## 13. Decisiones reservadas al profesor

- Interpretar situaciones ambiguas, excepcionales o personales.
- Decidir si una carencia impide avanzar de fase.
- Aprobar o modificar cualquier calificación.
- Valorar autenticidad, autoría y posible uso indebido de IA.
- Autorizar cambios tardíos de tema o modalidad.
- Determinar si un documento final es apto para depósito o defensa.
- Valorar la presentación y las respuestas al tribunal.
- Modificar el tono o la profundidad del feedback por contexto conocido.
- Enviar, publicar o no utilizar el borrador preparado.

> **Regla de aprobación:** El sistema podrá marcar cada observación como aceptar, editar o
> descartar. Solo la versión aprobada por el profesor podrá pasar al histórico de correcciones
> cerradas.

---

# PARTE III

## Especificación funcional del sistema local

<!-- ancla: maestro#14-fuentes-y-criterios -->
## 14. Fuentes de verdad y criterios configurables

El sistema no debe depender de un único prompt rígido. Debe cargar una versión identificada
del Documento Maestro y de las matrices aplicables al ciclo, modalidad y fase.

### 14.1 Jerarquía de fuentes

- Programación didáctica y rúbrica oficial vigente.
- Instrucciones formales posteriores de CESUR, centro o coordinación.
- Acuerdos internos documentados y fechados.
- Documento Maestro, guía de desarrollo e índice comentado.
- Manual docente, banco de feedback y casos calibrados.
- Precedentes históricos del curso anterior.

> **Regla de conflicto:** Una fuente inferior no puede contradecir una superior. Si dos criterios
> vigentes chocan, el sistema detiene ese juicio y crea una alerta de resolución.

### 14.2 Matriz configurable

| Parámetro | Ejemplo | Estado |
|---|---|---|
| Curso / centro / comunidad | 2026-2027 / sede o modalidad | Pendiente de fuente oficial |
| Ciclo | Marketing, Comercio, Administración | Obligatorio |
| Modalidad | Profesional, investigación, revisión | Obligatorio |
| Fase | Tema, E1, E2, E3, final, defensa | Obligatorio |
| Rúbrica | Criterios, niveles y ponderaciones | Versionada |
| Extensión y formato | 20 páginas, Arial 11, PDF | Configurable |
| Calendario | Apertura, cierre y retrasos | Versionado |
| Feedback | Breve, estándar o ampliado | Preferencia docente |

<!-- ancla: maestro#15-modelo-de-datos -->
## 15. Modelo de datos y estructura local

### 15.1 Entidades mínimas

| Entidad | Campos esenciales |
|---|---|
| Alumno | Código anónimo, ciclo, grupo, observaciones docentes |
| Proyecto | Título, tema validado, modalidad, estado, versión de criterios |
| Entrega | Fase, fecha, plazo, archivo, versión, estado administrativo |
| Corrección | Dimensiones, evidencias, semáforo, nota propuesta, decisiones |
| Feedback | Borrador, versión aprobada, fecha y estado de comunicación |
| Defensa | Fecha, soporte, valoración manual, preguntas y nota |
| Registro | Usuario, acción, versión, fecha y cambio |

### 15.2 Estructura de carpetas propuesta

| Ruta lógica | Contenido |
|---|---|
| `00_MAESTRO` | Fuentes oficiales, matrices, rúbricas, plantillas y versiones |
| `01_ALUMNOS/[CODIGO]/00_FICHA` | Ficha del alumno y del proyecto |
| `01_ALUMNOS/[CODIGO]/01_TEMA` | Propuesta y validación |
| `01_ALUMNOS/[CODIGO]/02_ENTREGA_1` | Entrada, borradores y versión aprobada |
| `01_ALUMNOS/[CODIGO]/03_ENTREGA_2` | Entrada, borradores y versión aprobada |
| `01_ALUMNOS/[CODIGO]/04_ENTREGA_3` | Entrada, borradores y versión aprobada |
| `01_ALUMNOS/[CODIGO]/05_FINAL` | Documento final y corrección |
| `01_ALUMNOS/[CODIGO]/06_DEFENSA` | Presentación, ficha y valoración |
| `01_ALUMNOS/[CODIGO]/07_HISTORICO` | Versiones cerradas y registro |
| `02_CALIBRACION` | Casos anonimizados y correcciones de referencia |
| `03_LOGS` | Incidencias técnicas y control de ejecución |

### 15.3 Convención de nombres

Posible formato : `CODIGO_CICLO_FASE_FECHA_VERSION.ext`. Ejemplo: `AF023_E2_2026-12-18_v01.pdf`. Las salidas añadirán `INFORME_INTERNO`, `FEEDBACK_BORRADOR` o
`APROBADO`. Ningún archivo fuente será sobrescrito.

<!-- ancla: maestro#16-flujo-y-estados -->
## 16. Flujo propuesto de corrección

> **Carácter de esta sección:** El flujo es una primera especificación funcional para revisar
> durante la construcción. Puede simplificarse o reorganizarse sin alterar los principios
> académicos y de control humano.

1. Recepción asistida. El sistema vigila la carpeta de entregas y, al aparecer un archivo nuevo, propone alumno y fase deducidos de su nombre. El docente confirma la propuesta o la corrige; si el nombre no permite deducirlos, no se adivinan (D-009).
2. Validación técnica. Se comprueba apertura, legibilidad, integridad y formato preferente PDF.
3. Validación administrativa. Se verifica código, ciclo, modalidad, fase, plazo y correspondencia del archivo.
4. Carga de contexto. Se seleccionan la versión del Documento Maestro, la matriz de fase y los criterios específicos.
5. Lectura estructural. Se identifica el índice real, apartados, extensión, elementos obligatorios y problemas formales.
6. Lectura académica. Se analizan las dimensiones activas y se localizan evidencias, ausencias y dudas.
7. Comparación evolutiva. Se carga feedback anterior y se contrastan cambios, pendientes y coherencia entre versiones.
8. Síntesis provisional. Se organizan fortalezas, prioridades, alertas, semáforo y nota propuesta.
9. Generación de dos salidas. Se redactan el informe técnico y el borrador dirigido al alumno, ambos internos.
10. Revisión docente. Marcos acepta, modifica o descarta observaciones, ajusta la nota y personaliza el tono.
11. Cierre. Se guardan las versiones aprobadas, se actualiza la ficha y queda trazabilidad completa.

### 16.1 Estados de ejecución

| Estado | Significado |
|---|---|
| `RECIBIDO` | Archivo registrado, todavía no procesado |
| `BLOQUEADO` | Falta un dato, criterio o archivo legible |
| `ANALIZADO` | Existe resultado estructurado provisional |
| `BORRADORES_GENERADOS` | Existen las dos salidas internas |
| `EN_REVISION_DOCENTE` | Pendiente de aceptar, editar o descartar |
| `APROBADO` | Corrección cerrada por el profesor |
| `COMUNICADO` | El docente ha registrado que devolvió el feedback |

<!-- ancla: maestro#17-esquema-salidas -->
## 17. Esquema de las dos salidas

### 17.1 Informe interno

| Bloque | Contenido obligatorio |
|---|---|
| Cabecera | Alumno codificado, ciclo, modalidad, fase, fecha y criterios |
| Control previo | Plazo, archivo, extensión, estructura y legibilidad |
| Resumen | Estado general en cinco o seis líneas |
| Dimensiones | Nivel, evidencia, prioridad y observación por criterio |
| Continuidad | Feedback anterior aplicado, pendiente o no verificable |
| Decisiones | Dudas y campos que requieren profesor |
| Resultado | Semáforo, nota propuesta y acción recomendada |

### 17.2 Borrador de devolución

| Bloque | Regla |
|---|---|
| Apertura | Reconocer el trabajo real, sin elogio automático |
| Fortalezas | Mencionar uno o dos elementos concretos |
| Prioridades | Máximo de cambios que el alumno pueda aplicar |
| Orientación | Explicar la mejora sin escribir el apartado |
| Siguiente fase | Recordar qué debe presentar |
| Cierre | Cercano, firme y proporcional |

> **Control de coherencia:** Si el informe interno marca una carencia crítica, el feedback no
> puede describir el proyecto como correcto. Si el proyecto está sólido, el feedback no debe
> inflarse con mejoras menores.

<!-- ancla: maestro#18-reglas-y-paradas -->
## 18. Reglas funcionales y condiciones de parada

### 18.1 Reglas obligatorias

- No modificar ni sobrescribir el archivo entregado.
- No cargar criterios de otra fase o ciclo.
- No inventar apartados ausentes ni completar el trabajo del alumno.
- No convertir una inferencia en hecho.
- No generar una acusación automática de copia o IA.
- No aprobar ni publicar una salida sin acción explícita del profesor.
- No mostrar la nota interna en el borrador al alumno.
- No continuar si falta una fuente normativa necesaria para decidir.

### 18.2 Condiciones de parada

| Condición | Respuesta |
|---|---|
| PDF ilegible, vacío o protegido | Bloquear y solicitar archivo válido |
| Alumno o fase no coinciden | Bloquear y pedir selección correcta |
| Entrega fuera de plazo | Marcar GRIS y 0; no corregir salvo instrucción docente |
| Criterios contradictorios | Crear alerta y detener solo el juicio afectado |
| Falta feedback anterior cuando es necesario | Continuar sin comparación solo con autorización |
| Indicio crítico de autoría | Generar nota interna prudente y escalar |
| Error técnico durante generación | Conservar entrada, registrar error y no crear salida aprobada |

<!-- ancla: maestro#19-privacidad -->
## 19. Privacidad, seguridad y trazabilidad

> **Modificado por D-001 el 2026-08-26.** La versión original de este apartado
> presuponía un sistema estrictamente local. La arquitectura acordada es otra y
> se describe aquí.
>
> **Corregido por D-010 el 2026-08-29.** Este apartado daba por supuesta una
> anonimización previa al envío al proveedor de análisis que no se aplica: el
> texto se transmite íntegro.

Circuito de datos del sistema:

- La ficha del alumno, los criterios versionados, la corrección por
  dimensiones, las evidencias citadas, el semáforo, la nota interna, el
  feedback aprobado y el registro de auditoría se almacenan en Supabase.
- El PDF de la entrega y el texto completo del trabajo **no se almacenan**: ni
  en Supabase, ni en el repositorio.
- Una evidencia citada es la referencia al apartado y la página más un
  fragmento literal de 1.500 caracteres como máximo. El límite lo verifica el
  backend e impide que la suma de evidencias reconstruya el trabajo.
- Durante el análisis, el texto íntegro de la entrega se transmite al
  proveedor de análisis. El sistema no guarda copia de ese texto. Lo que el
  proveedor retenga se rige por sus propias condiciones, ajenas a este sistema
  y sin confirmar: confirmarlas es la condición que la última cautela de este
  apartado exige antes de usar entregas reales.
- Las credenciales técnicas residen en el backend local, nunca en el frontend.

Las cautelas de tratamiento se mantienen íntegras:

- Utilizar códigos de alumno en la configuración y en los archivos del sistema siempre que sea posible.
- Eliminar o evitar DNI, teléfonos, domicilios, firmas, correos y datos de terceros que no sean necesarios.
- Mantener separadas las observaciones personales del texto que pueda convertirse en feedback.
- Registrar versión de criterios, fecha de ejecución, archivo de entrada y persona que aprueba.
- Conservar copias de seguridad de criterios, plantillas, fichas e histórico.
- No usar entregas reales hasta confirmar las condiciones de tratamiento aplicables y superar la calibración con material anonimizado.

### 19.1 Registro mínimo

| Dato | Motivo |
|---|---|
| ID de ejecución | Reconstruir qué ocurrió |
| Código de alumno y fase | Relacionar la corrección |
| Hash o nombre/versionado del archivo | Identificar la entrada sin alterarla |
| Versión de criterios | Explicar el juicio |
| Fecha y estado | Controlar el proceso |
| Decisiones docentes | Diferenciar propuesta y resultado final |

<!-- ancla: maestro#20-calibracion -->
## 20. Calibración y control de calidad

Antes de utilizar el sistema con nuevas entregas se construirá un banco de calibración con
proyectos anteriores anonimizados y ya corregidos por mí. Debe representar ciclos,
modalidades, fases y niveles de calidad diferentes.

### 20.1 Banco inicial

- Entre 9 y 12 proyectos como mínimo aconsejable.
- Tres niveles: sólido, intermedio y deficiente.
- Representación de Marketing, Comercio Internacional y Administración y Finanzas.
- Casos profesionales, de investigación y de revisión documental cuando existan.
- Errores variados: teoría, incoherencia, fuentes, aplicación, formato, feedback ignorado y autoría.
- Corrección humana de referencia y nota interna asociada.

### 20.2 Métricas de control

| Dimensión | Pregunta |
|---|---|
| Cobertura | ¿Revisa todos los criterios aplicables y solo esos? |
| Exactitud | ¿Localiza correctamente evidencias y ausencias? |
| Prioridad | ¿Distingue errores críticos de mejoras secundarias? |
| Continuidad | ¿Comprueba el feedback sin repetirlo mecánicamente? |
| Tono | ¿El borrador es claro, cercano y propio de FP? |
| Prudencia | ¿Expresa dudas sin certezas infundadas? |
| Coherencia | ¿Informe, nota, semáforo y feedback coinciden? |
| Ahorro | ¿Reduce tiempo después de la revisión humana? |

### 20.3 Criterio de aceptación

El sistema estará preparado para uso controlado cuando no omita criterios relevantes, no
invente carencias, priorice de forma comparable a la corrección humana y produzca un ahorro
real sin aumentar el riesgo. Las discrepancias se documentarán y se convertirán en ajustes de
criterios o ejemplos, no en instrucciones improvisadas dentro de cada ejecución.

<!-- ancla: maestro#21-mvp-y-aplazadas -->
## 21. Producto mínimo viable y funciones aplazadas

### 21.1 Primera versión

- Un proyecto por ejecución.
- Activación manual mediante interfaz sencilla o acceso directo.
- Entrada principal en PDF y ficha mínima.
- Selección de ciclo, modalidad, fase y versión de criterios.
- Carga opcional de archivo y feedback anteriores.
- Análisis estructurado con evidencias y alertas.
- Dos salidas internas editables.
- Aprobación humana obligatoria.
- Aplicación con interfaz web local, backend en el equipo del docente y
  persistencia en Supabase (D-001).
- Vigilancia de la carpeta de entregas, con identificación confirmada por el
  docente en cada archivo (D-009).
- Historial consultable y recuperación de errores.

### 21.2 Fuera de la primera versión

- Recogida automática de entregas sin confirmación del docente. La carpeta se
  vigila (D-009), pero de quién es cada archivo y a qué fase corresponde lo
  decide siempre una persona.
- Corrección masiva por lotes.
- Envío de correos o publicación en CESUR.
- Integración directa con el Aula Virtual.
- Panel estadístico avanzado.
- Comparación automática entre alumnos.
- Detección concluyente de IA o plagio.
- Evaluación automática de la defensa oral.

> **Criterio de crecimiento:** Una función se añadirá solo si reduce trabajo o mejora trazabilidad
> después de que el flujo básico sea estable.

<!-- ancla: maestro#22-hoja-de-ruta -->
## 22. Hoja de ruta de implantación

| Etapa | Producto | Criterio de salida |
|---|---|---|
| 0. Consolidación | Documento Maestro, guía e índice | Existe una base coherente |
| 1. Ingesta oficial | Fuentes, cambios y dudas | No quedan contradicciones sin registrar |
| 2. Matrices | Criterios por ciclo, modalidad y fase | Cada criterio tiene fuente y estado |
| 3. Plantillas | Fichas, informe y feedback | Las salidas son utilizables |
| 4. Prototipo | Aplicación mínima local | Procesa un caso sin perder datos |
| 5. Calibración | Pruebas con proyectos anonimizados | Resultados comparables a referencia |
| 6. Piloto | Uso controlado en primeras entregas | Ahorro y calidad confirmados |
| 7. Operación | Historial y revisión continua | Cada corrección queda aprobada |
| 8. Evolución | Lotes, paneles o integraciones | Valor demostrado antes de ampliar |

### 22.1 Próximas decisiones

- Incorporar programación, rúbrica, calendario y normas oficiales cuando estén disponibles.
- Cerrar la matriz de evaluación por fase y modalidad.
- Definir el formato exacto de ficha de alumno y registro de notas.
- Seleccionar el banco anonimizado de calibración.
- Revisar con el colaborador técnico el flujo propuesto y el modelo de carpetas.
- Construir primero una prueba de extremo a extremo con un solo proyecto.

---

# PARTE IV

## Plantillas y anexos operativos

<!-- ancla: maestro#anexo-a-ficha-maestra -->
## Anexo A. Ficha maestra del alumno y del proyecto

Código anónimo del alumno: ____________________________________________________________

Ciclo formativo: ____________________________________________________________

Grupo / sede / modalidad: ____________________________________________________________

Título provisional o definitivo: ____________________________________________________________

Modalidad principal: ____________________________________________________________

Tema validado: Sí / No · Fecha: ____ / ____ / ______

Versión de criterios: ____________________________________________________________

Observaciones docentes reservadas: ____________________________________________________________

### Seguimiento de componentes

| Componente | Fecha | Estado | Nota interna | Feedback |
|---|---|---|---|---|
| 1.ª entrega | | | | |
| 2.ª entrega | | | | |
| 3.ª entrega | | | | |
| Entrega final | | | | |
| Presentación | | | | |

<!-- ancla: maestro#anexo-b-ficha-entrega -->
## Anexo B. Ficha mínima de una entrega

Código del alumno: ____________________________________________________________

Fase / entrega: ____________________________________________________________

Fecha de recepción: ____________________________________________________________

Fecha límite: ____________________________________________________________

Dentro de plazo: Sí / No

Archivo actual: ____________________________________________________________

Versión anterior: ____________________________________________________________

Feedback anterior: ____________________________________________________________

Versión de criterios: ____________________________________________________________

Observación especial del profesor: ____________________________________________________________

<!-- ancla: maestro#anexo-c-informe-interno -->
## Anexo C. Plantilla del informe técnico interno

| Bloque | Contenido |
|---|---|
| Identificación | Código, ciclo, modalidad, fase, fecha, archivos y criterios |
| Control administrativo | Plazo, coincidencia, legibilidad, formato y extensión |
| Resumen ejecutivo | Estado general y evolución |
| Valoración | Dimensión · nivel · evidencia · prioridad · observación |
| Continuidad | Feedback aplicado, pendiente y nuevos efectos |
| Fortalezas | Aspectos concretos a conservar |
| Prioridades | Cambios críticos e importantes |
| Dudas docentes | Decisiones no automatizables |
| Resultado provisional | Semáforo, nota y recomendación |
| Revisión del profesor | Aceptar / editar / descartar · nota final interna |

<!-- ancla: maestro#anexo-d-borrador-devolucion -->
## Anexo D. Plantilla del borrador de devolución

[Apertura breve y reconocimiento del trabajo o de la evolución real].

[Fortalezas concretas que conviene conservar].

[Correcciones prioritarias, ordenadas y explicadas sin redactar el contenido].

[Qué debe aparecer o mejorar en la siguiente fase].

[Cierre cercano y proporcional al estado del proyecto].

> **Control antes de utilizar:** Eliminar cualquier nota interna, calificación, hipótesis de autoría o
> comentario personal que no deba recibir el alumno.

<!-- ancla: maestro#anexo-e-registro-semaforo -->
## Anexo E. Registro del semáforo y decisiones

| Fecha | Fase | Propuesto | Aprobado | Motivo | Decisión |
|---|---|---|---|---|---|
| | | | | | |

<!-- ancla: maestro#anexo-f-instrucciones-maestras -->
## Anexo F. Instrucciones maestras para el asistente

### F.1 Rol

Actúas como asistente interno de corrección y seguimiento de Proyectos Intermodulares de
Formación Profesional. Analizas documentos para ayudar al profesor Marcos Castaño Pérez-Olleros. No eres el evaluador definitivo y no te comunicas directamente con el alumno.

### F.2 Entradas obligatorias

27. Archivo de la entrega actual.
28. Código de alumno, ciclo, modalidad y fase.
29. Versión vigente del Documento Maestro y matriz aplicable.
30. Fecha y estado de plazo.
31. Feedback y versión anteriores cuando existan.
32. Observaciones docentes especiales, si se facilitan.

### F.3 Método obligatorio

33. Valida archivo, identidad, fase, plazo y criterios.
34. Identifica la estructura real y los elementos correspondientes a la fase.
35. Analiza únicamente las dimensiones activas.
36. Localiza evidencias y distingue ausencias, inferencias y dudas.
37. Compara con feedback y versión anteriores.
38. Prioriza hallazgos y propone semáforo y nota interna.
39. Genera un informe técnico y un borrador de devolución, ambos internos.
40. Detén o escala cualquier decisión reservada al profesor.

### F.4 Prohibiciones

41. No inventar contenido ausente.
42. No reescribir el proyecto por el alumno.
43. No acusar de plagio o IA como conclusión automática.
44. No ocultar dudas ni contradicciones de criterio.
45. No mostrar notas internas en el feedback.
46. No enviar, guardar como aprobado ni publicar sin autorización docente.

### F.5 Formato de salida estructurada

| Campo | Tipo de contenido |
|---|---|
| `metadata` | Alumno, ciclo, modalidad, fase, criterios y archivos |
| `precheck` | Plazo, legibilidad, estructura y formato |
| `summary` | Estado ejecutivo |
| `dimensions` | Código, nivel, evidencia, prioridad y comentario |
| `continuity` | Feedback aplicado, pendiente y cambios |
| `alerts` | Bloqueos, dudas y decisiones docentes |
| `provisional_result` | Semáforo, nota propuesta y acción |
| `internal_report` | Informe legible para el profesor |
| `student_draft` | Borrador de feedback sin información reservada |

<!-- ancla: maestro#anexo-g-registro-decisiones -->
## Anexo G. Registro de decisiones del sistema

| Fecha | Fuente | Decisión | Estado | Versión | Responsable |
|---|---|---|---|---|---|
| | | | Provisional / Validada | | |
| | | | Provisional / Validada | | |
| | | | Provisional / Validada | | |
| | | | Provisional / Validada | | |

<!-- ancla: maestro#anexo-h-parametros-pendientes -->
## Anexo H. Parámetros pendientes de cierre oficial

47. Programación didáctica aplicable por centro, sede, modalidad y comunidad autónoma.
48. Resultados de aprendizaje y criterios oficiales vinculados al Proyecto Intermodular.
49. Fechas de tema, entregas, recuperación, final y defensa.
50. Rúbrica, ponderaciones, mínimos y causas oficiales de no superación.
51. Formato, extensión y sistema de citas definitivos si difieren de la guía.
52. Procedimiento de tutorías, correcciones y plazos de respuesta.
53. Duración, soporte y evaluación de la presentación.
54. Política institucional sobre IA, autoría y evidencias admitidas.
55. Condiciones de protección de datos y tratamiento mediante herramientas externas.
56. Reglas para casos especiales, retrasos, cambios de tema y recuperación.

> **Cierre:** Este Documento Maestro ya permite diseñar el sistema sin fijar prematuramente las
> variables oficiales. La siguiente versión deberá incorporar las fuentes de 2026-2027, resolver
> contradicciones y cerrar las matrices antes de la primera corrección real.
