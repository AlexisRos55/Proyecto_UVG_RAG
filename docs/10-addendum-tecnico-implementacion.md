# Addendum Técnico de Implementación (ATI)

**Complemento formal al Protocolo de Investigación — no lo modifica ni lo reemplaza.**

| | |
|---|---|
| **Proyecto** | Diseño y desarrollo de un prototipo de asistente virtual basado en arquitectura RAG con pruebas de recuperación, relevancia y latencia para la consulta de normativas en UVG Altiplano |
| **Autor** | William's Alexis Rosales García |
| **Institución** | Universidad del Valle de Guatemala — Facultad de Ingeniería |
| **Documento base** | `docs/source/Protocolo Alexis Rosales.docx` |
| **Versión** | 1.0 |
| **Fecha** | 2026-09-11 |
| **Estado** | Vigente |

---

## Índice

- [I. Propósito y alcance del documento](#i-propósito-y-alcance-del-documento)
- [II. Metodología de esta auditoría](#ii-metodología-de-esta-auditoría)
- [III. Registro de decisiones técnicas divergentes del Protocolo](#iii-registro-de-decisiones-técnicas-divergentes-del-protocolo)
  - [III.1 Ausencia de LangChain como orquestador](#iii1-ausencia-de-langchain-como-framework-de-orquestación)
  - [III.2 Modelo generativo: Claude 3.5 Sonnet → Claude Haiku 4.5](#iii2-modelo-generativo-claude-35-sonnet--claude-haiku-45-configurable)
  - [III.3 Algoritmo de chunking: `RecursiveCharacterTextSplitter` → clase propia](#iii3-algoritmo-de-chunking-recursivecharactertextsplitter--fixedsizechunkingservice)
  - [III.4 Parámetro Top-K: rango sugerido → valor de producción](#iii4-parámetro-top-k-rango-sugerido-3-5--valor-de-producción-10)
  - [III.5 Métricas RAGAS: Tríada → 4 métricas](#iii5-métricas-ragas-tríada-3-métricas--4-métricas-implementadas)
- [IV. Adiciones no contempladas por el Protocolo](#iv-adiciones-no-contempladas-por-el-protocolo)
- [V. Brechas pendientes](#v-brechas-pendientes)
- [VI. Matriz consolidada de trazabilidad Protocolo → Implementación](#vi-matriz-consolidada-de-trazabilidad-protocolo--implementación)
- [VII. Parámetros de control congelados para el experimento](#vii-parámetros-de-control-congelados-para-el-experimento)
- [Anexo A — Extractos literales del Protocolo citados en este documento](#anexo-a--extractos-literales-del-protocolo-citados-en-este-documento)
- [Anexo B — Extractos de los ADR referenciados](#anexo-b--extractos-de-los-adr-referenciados)
- [Anexo C — Evidencia reproducible de verificación](#anexo-c--evidencia-reproducible-de-verificación)

---

## I. Propósito y alcance del documento

### I.1 Por qué existe este documento

El Protocolo de Investigación (`docs/source/Protocolo Alexis Rosales.docx`) fue aprobado antes de iniciar la implementación técnica del prototipo. Durante la construcción del sistema, el equipo de desarrollo tomó una serie de decisiones de ingeniería que se apartan, en aspectos puntuales, de lo especificado literalmente en el Protocolo — no por falta de rigor, sino como resultado de aplicar criterio profesional ante restricciones reales (presupuesto de API personal, plazo de desarrollo de tres semanas, disponibilidad de modelos vigentes de Anthropic al momento de implementar).

Este Addendum Técnico de Implementación (ATI) tiene un único propósito: **dejar registro trazable, justificado y defendible de cada una de esas decisiones**, de modo que en la etapa de redacción de resultados y en la defensa oral no exista ninguna divergencia entre el Protocolo, la documentación del proyecto (ADR) y el código fuente que no haya sido explicada de antemano.

### I.2 Qué NO es este documento

- No modifica ni sustituye ninguna sección del Protocolo aprobado.
- No introduce nuevos objetivos, hipótesis ni alcance de investigación.
- No reporta resultados experimentales — la Fase V del Protocolo (validación experimental) no ha comenzado a la fecha de este documento, y este ATI no adelanta ni presupone ningún resultado.
- No es un ADR nuevo — complementa a los ADR existentes (`docs/adr/`), que documentan *decisiones de arquitectura de software*; este documento reconcilia esas decisiones específicamente contra el Protocolo de Investigación, algo que ningún ADR hace hoy (ver hallazgo en la sección II.2).

### I.3 Cómo debe citarse en la tesis

En el documento final de tesis, cualquier discrepancia observable entre el texto del Protocolo (capítulos VI-VIII) y el sistema implementado debe remitirse a este documento con la fórmula: *"Ver Addendum Técnico de Implementación, sección III.N"*. La sección VI de este documento (matriz consolidada) está diseñada para insertarse, con mínima adaptación de formato, directamente en el capítulo de Metodología o en un anexo del documento final de tesis.

---

## II. Metodología de esta auditoría

### II.1 Fuentes revisadas

1. `docs/source/Protocolo Alexis Rosales.docx` — protocolo de investigación completo (Resumen, Introducción, Antecedentes, Justificación, Objetivos, Hipótesis, Marco Teórico, Marco Referencial, Metodología de 5 fases, Anexos), convertido a texto plano y leído en su totalidad para esta auditoría.
2. `docs/source/Descripción Técnica_ Asistente Virtual RAG - UVG Altiplano.docx` — documento técnico del asesor.
3. Los 11 Architecture Decision Records en `docs/adr/`.
4. El código fuente completo de `backend/src/app/` y `frontend/src/`.
5. `README.md`, `backend/README.md`, `frontend/README.md`, `docs/07-backlog.md`, `docs/08-roadmap.md`.

### II.2 Hallazgo metodológico previo, que motiva la existencia de este documento

Los ADR existentes (en particular ADR-0002 y ADR-0006) justifican explícitamente sus decisiones citando **"el documento del asesor"**. Se verificó, leyendo cada ADR en su totalidad, que **ninguno de los 11 ADR menciona al Protocolo de Investigación**. Son documentos distintos: el documento del asesor es una descripción técnica informal; el Protocolo es el instrumento metodológico formal, aprobado, que define la hipótesis, el diseño experimental y el corpus autorizado de la investigación (Anexo — Diccionario de Fuentes de Datos). Las decisiones documentadas en los ADR son técnicamente sólidas, pero nunca fueron confrontadas contra el documento que un tribunal de tesis usará como referencia principal. Este ATI cierra esa brecha.

### II.3 Criterio de clasificación de diferencias

Cada diferencia identificada se clasifica en una de cuatro categorías, aplicadas de forma consistente en la sección VI:

| Categoría | Definición |
|---|---|
| **Intencional** | Existe una decisión documentada (ADR u otro registro), con alternativas consideradas y justificación explícita |
| **Aceptable** | No contradice al Protocolo; es una consecuencia de una decisión intencional, o una ampliación estricta de lo pedido |
| **Debe corregirse** | Es una omisión de configuración o documentación, no una decisión tomada — corrección de bajo costo |
| **Crítica** | Es una brecha que bloquea la ejecución de la Fase V del Protocolo si no se resuelve |

---

## III. Registro de decisiones técnicas divergentes del Protocolo

### III.1 Ausencia de LangChain como framework de orquestación

| Campo | Contenido |
|---|---|
| **Qué decía el Protocolo** | *"La interacción fluida entre el LLM, la base de conocimientos y el usuario requiere de un framework de orquestación, como LangChain"* (Marco Teórico, sección B); *"Mediante el uso de LangChain, se enlazará el motor de recuperación con la API de Anthropic (Sonnet)"* (Metodología, Fase III) — ver Anexo A.1 |
| **Qué se implementó** | El SDK oficial de Anthropic (`anthropic`, línea 1.x) invocado directamente. La orquestación del flujo recuperar → construir prompt → invocar LLM → verificar se expresa como código propio en `backend/src/app/infrastructure/adapters/llm/single_call_verification_adapter.py` y `backend/src/app/application/use_cases/answer_student_query.py`, detrás del puerto `LLMPort` (`backend/src/app/domain/ports/llm_port.py`) |
| **Por qué se tomó esa decisión** | Documentado en [ADR-0002](adr/0002-no-langchain-direct-anthropic-sdk.md) (ver Anexo B.1): (a) control total y auditable sobre el conteo de tokens por llamada, relevante bajo un presupuesto de API personal y limitado; (b) LangChain presenta una superficie de API históricamente cambiante, con riesgo real de romper el proyecto a mitad de un desarrollo de tres semanas; (c) la Arquitectura Hexagonal adoptada ya provee, mediante `LLMPort`, la abstracción de desacoplamiento que un framework de orquestación ofrecería |
| **Ventajas obtenidas** | Visibilidad exacta de `input_tokens`/`output_tokens` por llamada, registrada en logs estructurados (`AnthropicLLMAdapter.complete`, línea con `logger.info`); una dependencia externa menos susceptible a *breaking changes*; la lógica de Chain-of-Verification queda expresada en código propio, íntegramente legible y explicable durante la defensa |
| **Desventajas** | Debieron implementarse a mano la construcción de prompts y el parseo de la salida estructurada (tool-use de Anthropic), utilidades que LangChain habría provisto |
| **Riesgos mitigados** | Riesgo de que una actualización de LangChain interrumpiera el desarrollo sin aviso durante la ventana de tres semanas disponible; riesgo de opacidad en el consumo de tokens, variable de costo directo del proyecto |
| **Por qué mejora la calidad del sistema** | Reduce la superficie de fallo dependiente de terceros; mantiene el pipeline RAG completo auditable dentro del propio repositorio del trabajo de graduación, sin requerir que el lector conozca la API interna de una librería externa para entender la lógica central de la investigación |
| **Cómo defenderla ante el tribunal** | El Protocolo proponía LangChain como *medio* para lograr un objetivo explícito: orquestar el flujo entre recuperación y generación. Ese mismo objetivo se logró mediante el patrón Ports & Adapters de la Arquitectura Hexagonal, un mecanismo de desacoplamiento más explícito y verificable en el código fuente. El comportamiento funcional exigido por el Protocolo (Chain-of-Verification, restricción del agente al contexto recuperado) se cumple de forma equivalente, verificado mediante prueba automatizada (`backend/tests/unit/test_single_call_verification_adapter.py`) |

### III.2 Modelo generativo: Claude 3.5 Sonnet → Claude Haiku 4.5 (configurable)

| Campo | Contenido |
|---|---|
| **Qué decía el Protocolo** | *"Modelo Generativo: Claude 3.5 Sonnet (v. [insertar versión específica de la API])"*, listado como parámetro de control del diseño experimental (Metodología, sección "Control de Parámetros del Sistema RAG") — ver Anexo A.2 |
| **Qué se implementó** | El nombre del modelo se lee desde la variable de entorno `ANTHROPIC_MODEL` (`backend/src/app/infrastructure/config/settings.py`), con `claude-haiku-4-5-20251001` como valor por defecto en `.env.example`. Nunca está hardcodeado en el código del adaptador |
| **Por qué se tomó esa decisión** | Documentado en [ADR-0006](adr/0006-configurable-llm-model-selection.md) (ver Anexo B.2): Claude 3.5 Sonnet corresponde a una generación de modelos anterior a la disponible al momento de la implementación (2026-09), con riesgo de deprecación antes de la fecha de defensa; el presupuesto de API es personal y limitado, por lo que el costo por token es un criterio de selección tan relevante como la capacidad de razonamiento del modelo |
| **Ventajas obtenidas** | Menor costo y latencia por consulta — variable dependiente directamente relevante para la Fase V del Protocolo, donde la latencia del prototipo se contrasta contra la atención manual; la configurabilidad permite comparar empíricamente distintos modelos (p. ej. Haiku 4.5 vs. Sonnet 5) durante la evaluación RAGAS sin modificar código, solo la variable de entorno |
| **Desventajas** | Haiku 4.5, al ser el modelo de menor costo de su familia vigente, podría rendir por debajo de un modelo de mayor capacidad en la métrica de Fidelidad de RAGAS — riesgo explícitamente aceptado y documentado en la propia ADR-0006 al momento de tomar la decisión, no descubierto retroactivamente |
| **Riesgos mitigados** | Deprecación del modelo literal nombrado por el Protocolo antes de la fecha de defensa; costo de API no controlado bajo un presupuesto personal |
| **Por qué mejora la calidad del sistema** | La configurabilidad por variable de entorno es, en sí misma, una mejora de mantenibilidad (principio de aplicación de doce factores) sobre un modelo fijado en código; el cambio es reversible sin tocar arquitectura: si la evaluación RAGAS (pendiente, ver sección V) muestra fidelidad insuficiente, cambiar a un modelo de mayor capacidad es una modificación de configuración, no de diseño |
| **Cómo defenderla ante el tribunal** | El Protocolo fijaba un modelo como parámetro de control experimental con la intención de garantizar determinismo y reproducibilidad. Esa misma intención se preserva: el modelo efectivamente usado es fijo y configurable explícitamente, solo que su valor por defecto es uno vigente y de menor costo. El parámetro real a reportar en la sección de resultados de la tesis es "Claude Haiku 4.5" en lugar de "Claude 3.5 Sonnet" — un ajuste de valor del parámetro, no una alteración del diseño experimental |

**Nota de actualización sobre este mismo punto:** el addendum de implementación de ADR-0006 (fechado 2026-09-04) declara que el envío de `temperature: 0.0` vía `extra_body` *"no se pudo confirmar con una respuesta exitosa completa por no contar con una API key real durante la implementación"*. Esta afirmación **quedó desactualizada**: en sesiones de trabajo posteriores a esa fecha, el sistema fue validado exitosamente con una API key real, generando respuestas completas y correctamente fundamentadas (evidencia: capturas de pantalla en `docs/screenshots/chat-conversation.png`, que muestra una respuesta real con fuentes citadas). Se recomienda actualizar el addendum de ADR-0006 para reflejar esta confirmación (tarea de bajo costo, no incluida en el alcance de este documento).

### III.3 Algoritmo de chunking: `RecursiveCharacterTextSplitter` → `FixedSizeChunkingService`

| Campo | Contenido |
|---|---|
| **Qué decía el Protocolo** | *"El texto limpio se dividirá en bloques de tamaño fijo utilizando el algoritmo RecursiveCharacterTextSplitter"*, con *"una técnica de superposición (overlap) de 100 caracteres entre los fragmentos"* (Metodología, Fase I) — ver Anexo A.3 |
| **Qué se implementó** | Clase propia `FixedSizeChunkingService` (`backend/src/app/infrastructure/adapters/document_processing/chunking_service.py`), con `chunk_size=1000` y `overlap=100` como valores por defecto del constructor |
| **Por qué se tomó esa decisión** | Consecuencia directa de III.1: al no adoptarse LangChain, el comportamiento funcional pedido —bloques de tamaño fijo con solapamiento de 100 caracteres— se reimplementó sin esa dependencia |
| **Ventajas obtenidas** | Los valores por defecto de la implementación (`chunk_size=1000`, `overlap=100`) **coinciden exactamente** con los valores de ejemplo que el propio Protocolo sugiere (*"tamaño de bloque de [Ej. 1000] caracteres y solapamiento (overlap) de 100 caracteres"*, sección "Control de Parámetros del Sistema RAG") — no existe pérdida de fidelidad metodológica respecto al Protocolo, únicamente de herramienta utilizada. La implementación es una clase de treinta líneas, verificada con cinco pruebas unitarias dedicadas (`backend/tests/unit/test_chunking_service.py`) |
| **Desventajas** | Es un algoritmo de división más simple que `RecursiveCharacterTextSplitter`, el cual intenta preferentemente cortar en separadores naturales del texto (párrafos, oraciones) antes de cortar por conteo fijo de caracteres; en documentos con estructura compleja, la implementación actual podría dividir una oración a la mitad con mayor frecuencia |
| **Riesgos mitigados** | Los mismos de III.1 (dependencia externa con riesgo de cambio de API) |
| **Por qué mejora la calidad del sistema** | Elimina una dependencia externa para una operación puramente determinística de manipulación de cadenas de texto, con comportamiento cien por ciento predecible y cubierto por prueba automatizada |
| **Cómo defenderla ante el tribunal** | Se implementó el mismo algoritmo conceptual descrito en el Protocolo —bloques de tamaño fijo con solapamiento de 100 caracteres— con idénticos valores de configuración a los sugeridos, sin depender de una librería de terceros. La diferencia es de herramienta de implementación, no de método aplicado |

### III.4 Parámetro Top-K: rango sugerido "3 a 5" → valor de producción "10"

| Campo | Contenido |
|---|---|
| **Qué decía el Protocolo** | *"Parámetro de Recuperación (Top-K): Búsqueda restringida a los [Ej. 3 o 5] fragmentos de texto con mayor similitud del coseno"* (Metodología, sección "Control de Parámetros del Sistema RAG") — ver Anexo A.4 |
| **Qué se implementó** | `top_k=10` como valor por defecto del constructor de `AnswerStudentQueryUseCase` (`backend/src/app/application/use_cases/answer_student_query.py`) |
| **Por qué se tomó esa decisión** | Hallazgo empírico durante pruebas manuales del sistema con un corpus de documentos en crecimiento: se identificó un caso real en el que el fragmento correcto para responder una consulta ocupaba la posición número 10 en orden de similitud, quedando fuera de una ventana de recuperación de `top_k=5` — generando una abstención incorrecta del sistema pese a existir evidencia documental relevante por encima del umbral de similitud configurado |
| **Ventajas obtenidas** | Reduce falsos negativos de recuperación — consultas con respuesta real existente en el corpus que, con un `top_k` menor, el sistema abstenía incorrectamente |
| **Desventajas** | Un `top_k` mayor incrementa el volumen de texto enviado como contexto al modelo generativo (mayor consumo de tokens y costo por consulta) y puede introducir fragmentos marginalmente relevantes que el mecanismo de verificación debe descartar activamente |
| **Riesgos mitigados** | Abstención incorrecta ante preguntas respondibles, que afecta directamente la métrica de exactitud de abstención y, potencialmente, la Relevancia de Contexto medida por RAGAS |
| **Por qué mejora la calidad del sistema** | Es un ajuste basado en evidencia empírica documentada, no en una suposición arbitraria — exactamente el tipo de refinamiento que un proceso de ingeniería de datos riguroso debe producir al observar el comportamiento real del sistema frente a un corpus creciente |
| **Cómo defenderla ante el tribunal** | El Protocolo propuso un rango de referencia antes de contar con evidencia empírica del comportamiento del motor de recuperación. Durante la validación del prototipo se identificó un caso concreto en que ese rango producía falsos negativos, y el parámetro se ajustó con base en esa evidencia. El valor a reportar como parámetro de control en la sección de resultados de la tesis es 10, congelado a partir de este documento (ver sección VII) |

**Advertencia metodológica:** este parámetro debe permanecer fijo en `10` durante toda la ejecución de la Fase V. Modificarlo después de iniciada la recolección de datos experimentales invalidaría la reproducibilidad exigida por el propio Protocolo.

### III.5 Métricas RAGAS: Tríada (3 métricas) → 4 métricas implementadas

| Campo | Contenido |
|---|---|
| **Qué decía el Protocolo** | La "Tríada RAG": Fidelidad, Relevancia del Contexto, Relevancia de la Respuesta (Marco Teórico, sección D; Operacionalización de Variables, sección F) — ver Anexo A.5 |
| **Qué se implementó** | Cuatro métricas del framework RAGAS en `scripts/evaluate.py`: `Faithfulness`, `ResponseRelevancy`, `LLMContextPrecisionWithReference`, `LLMContextRecall` |
| **Por qué se tomó esa decisión** | Es la forma nativa en que la librería RAGAS descompone la dimensión de "Relevancia del Contexto" en dos métricas complementarias: precisión (los fragmentos recuperados son relevantes) y exhaustividad (no faltan fragmentos relevantes que sí existen en el corpus). No es una decisión de apartarse del Protocolo, sino de usar el framework —expresamente solicitado por el propio Protocolo— tal como está diseñado |
| **Ventajas obtenidas** | Diagnóstico más fino del motor de recuperación: permite distinguir si una deficiencia observada es de precisión o de exhaustividad, información que una métrica única de "relevancia de contexto" no distinguiría |
| **Desventajas** | Implica reportar cuatro valores numéricos en lugar de tres en la sección de resultados, lo cual debe explicitarse para no generar una impresión de inconsistencia frente al Protocolo aprobado |
| **Riesgos mitigados** | Ninguno adicional — es una ampliación de cobertura de medición, no una mitigación de riesgo |
| **Por qué mejora la calidad del sistema** | Provee mayor poder diagnóstico exactamente sobre el componente que el propio Protocolo identifica como crítico para la validez de la investigación: el motor de búsqueda vectorial |
| **Cómo defenderla ante el tribunal** | El framework RAGAS, solicitado explícitamente por el Protocolo, descompone la "Relevancia del Contexto" en Precisión y Exhaustividad. Se reportan ambas dimensiones porque ofrecen mayor poder de diagnóstico sin contradecir la intención metodológica original — la satisfacen con mayor nivel de detalle |

---

## IV. Adiciones no contempladas por el Protocolo

Las siguientes decisiones **no constituyen desviaciones del Protocolo**, ya que este no las prohíbe ni las contempla explícitamente. Se listan por completitud y trazabilidad, no porque requieran ser "defendidas" en el mismo sentido que la sección III.

| Adición | Fundamento en el Protocolo | Naturaleza de la adición |
|---|---|---|
| Arquitectura Hexagonal + Clean Architecture + SOLID | El Protocolo pide genéricamente una *"arquitectura fuertemente desacoplada"* (Marco Referencial, sección C) | Es una implementación específica, más rigurosa y formalmente documentada (ver [ADR-0001](adr/0001-hexagonal-architecture.md)), de ese requisito genérico — no lo contradice, lo satisface con mayor especificidad |
| PostgreSQL para persistencia relacional | El Protocolo no menciona persistencia relacional en ningún punto; su alcance técnico se centra en el núcleo RAG (ChromaDB para vectores) | Soporta funcionalidad fuera del alcance explícito del núcleo de investigación (autenticación de usuarios, historial de conversación) — ver [ADR-0003](adr/0003-postgresql-relational-persistence.md) |
| Sistema de autenticación institucional y roles | No mencionado en el Protocolo | Necesario para que el prototipo sea operable como aplicación web real, per la Fase IV de la Metodología ("Desarrollo del Prototipo (MVP)") — ver [ADR-0004](adr/0004-institutional-authentication.md) |
| Panel administrativo de documentos | No mencionado en el Protocolo | Facilita la carga y gestión del corpus documental sin intervención manual en el sistema de archivos — ver [ADR-0008](adr/0008-admin-panel-scope.md) |

---

## V. Brechas pendientes

A diferencia de la sección III, lo siguiente **no son decisiones tomadas**, sino trabajo aún no realizado. Se documentan aquí para que ninguna quede confundida con una decisión de diseño deliberada.

| Brecha | Estado | Clasificación |
|---|---|---|
| Parámetro Top-P sin definir | Ningún adaptador del sistema configura `top_p`; no existe ADR que justifique omitirlo | Debe corregirse |
| Corpus oficial de 4 documentos (Reglamento de Vida Estudiantil 2024, Guía de Inscripción, Catálogo de Becas, Calendario Académico 2026) | No presente en el repositorio; `backend/documents/` contiene únicamente 3 documentos sintéticos de ejemplo, explícitamente etiquetados como tales | Crítica — bloquea el inicio de la Fase V |
| Formato `.docx` del documento "Guía de Pasos para Inscripción" (DOC-02 según el Anexo del Protocolo) | La interfaz de administración restringe la carga a `application/pdf`; el extractor de texto (`PyMuPDFExtractorAdapter`) asume estructura de PDF | Crítica condicional — debe verificarse contra el documento real antes de asumir que requiere trabajo adicional |
| Banco de 30 preguntas con Gold Standard validado por panel de expertos (SME) de UVG Altiplano | `scripts/golden_dataset.json` contiene 12 preguntas sintéticas, no validadas por personal institucional | Crítica |
| Línea base de atención manual (tiempo de respuesta del personal administrativo) | No existe ningún registro de esta medición en el proyecto | Crítica |
| Análisis estadístico (prueba de normalidad Shapiro-Wilk; prueba t de Student o U de Mann-Whitney; α=0.05) | No existe ningún script ni proceso de análisis estadístico en el repositorio | Crítica |
| Sincronización de `scripts/evaluate.py` con los parámetros reales de producción | El script fija `TOP_K = 5`, mientras que el sistema en producción usa `top_k = 10` (ver III.4) | Debe corregirse |
| Verificación del sistema en un entorno Windows | El Protocolo especifica Windows como entorno de validación (Marco Referencial, sección C); todo el desarrollo y las pruebas documentadas hasta la fecha se realizaron sobre macOS | Debe corregirse |
| Archivo de bloqueo de dependencias del backend | `backend/pyproject.toml` usa restricciones de mínimo (`>=`), sin un lockfile que fije versiones exactas; el frontend sí cuenta con `package-lock.json` | Debe corregirse, previo a Fase V |

El detalle completo de cómo resolver cada una de estas brechas está desarrollado en el documento *Plan de Consolidación Académica y Validación Experimental* (fase de planificación anterior a este ATI), que no se repite aquí para evitar duplicación de contenido.

---

## VI. Matriz consolidada de trazabilidad Protocolo → Implementación

| Requisito del Protocolo | Estado | Evidencia (archivo) | Cumplimiento | Clasificación |
|---|---|---|---|---|
| Extracción de texto con PyMuPDF | Implementado | `pymupdf_extractor.py` | 100% | — |
| Limpieza con expresiones regulares | Implementado | `text_cleaner.py` | 100% | — |
| Chunking de tamaño fijo con overlap de 100 | Implementado (herramienta distinta) | `chunking_service.py` | 100% funcional | Aceptable (III.3) |
| Framework de orquestación LangChain | No implementado | — | 0% (por diseño) | Intencional (III.1) |
| Embeddings `sentence-transformers/all-MiniLM-L6-v2` | Implementado | `sentence_transformers_embedding.py` | 100% | — |
| ChromaDB con similitud de coseno | Implementado | `chroma_vector_store.py` | 100% | — |
| Top-K = 3 a 5 | Divergente (valor 10) | `answer_student_query.py` | — | Intencional (III.4) |
| Chain-of-Verification en el prompt | Implementado | `single_call_verification_adapter.py` | 100% | — |
| Modelo Claude 3.5 Sonnet | Divergente (Haiku 4.5, configurable) | `.env`, ADR-0006 | 0% literal / 100% en espíritu | Intencional (III.2) |
| Temperatura 0.0 | Implementado | `anthropic_llm_adapter.py` | 100% | — |
| Top-P como parámetro de control | No implementado | — | 0% | Debe corregirse (V) |
| Backend FastAPI, API RESTful asíncrona | Implementado | `entrypoints/api/` | 100% | — |
| Frontend React + Tailwind CSS | Implementado | `frontend/src/` | 100% | — |
| Docker + Docker Compose | Implementado y verificado en ejecución real | `docker-compose.yml` | 100% | — |
| Entorno de validación Windows | No verificado | Guía en README | — | Debe corregirse (V) |
| Corpus autorizado de 4 documentos nombrados | No existe en el repositorio | — | 0% | Crítica (V) |
| Banco de 30 preguntas con Gold Standard validado por SME | No existe (12 preguntas sintéticas) | `golden_dataset.json` | 13% en cantidad, 0% en validación | Crítica (V) |
| Línea base de atención manual | No existe | — | 0% | Crítica (V) |
| Transcripción y evaluación RAGAS del Sujeto A | No existe | — | 0% | Crítica (V) |
| Medición de latencia con 3 repeticiones | Parcial (1 repetición) | `evaluate.py` | 40% | Debe corregirse (V) |
| Prueba de normalidad y prueba de hipótesis estadística | No existe | — | 0% | Crítica (V) |
| Tríada RAGAS (Fidelidad, Rel. Contexto, Rel. Respuesta) | Implementado, ampliado a 4 métricas | `evaluate.py` | 100%+ | Aceptable (III.5) |

---

## VII. Parámetros de control congelados para el experimento

Desde la Fase 3.1 (Preparación de la Investigación, Bloque 2), estos parámetros dejaron de ser únicamente valores de constructor y quedaron centralizados en `RagSettings` (`backend/src/app/infrastructure/config/settings.py`), expuestos por variable de entorno (prefijo `RAG_`) y documentados de forma autoritativa en **[`docs/11-reproducibility.md`](11-reproducibility.md)**, que es ahora la fuente de verdad operativa de estos valores — este documento no la duplica para evitar que ambos diverjan con el tiempo.

Como referencia rápida, los valores congelados a la fecha son: Top-K `10`, umbral de similitud `0.35`, tamaño de chunk `1000`, overlap `100`, modelo de embeddings `all-MiniLM-L6-v2`, modelo generativo `claude-haiku-4-5-20251001`, temperatura `0.0`. Top-P permanece sin definir (ver sección V), decisión explícita de no fijarlo sin justificación experimental.

---

## Anexo A — Extractos literales del Protocolo citados en este documento

**A.1** (Marco Teórico, sección B): *"La interacción fluida entre el LLM, la base de conocimientos y el usuario requiere de un framework de orquestación, como LangChain (LangChain, 2024)."*
(Metodología, Fase III): *"Acoplamiento y orquestación del flujo RAG: Mediante el uso de LangChain, se enlazará el motor de recuperación con la API de Anthropic (Sonnet)."*

**A.2** (Metodología, "Control de Parámetros del Sistema RAG"): *"Modelo Generativo: Claude 3.5 Sonnet (v. [insertar versión específica de la API])."*

**A.3** (Metodología, Fase I): *"Utilizando el framework de orquestación LangChain, el texto limpio se dividirá en bloques de tamaño fijo utilizando el algoritmo RecursiveCharacterTextSplitter. Se implementará una técnica de superposición (overlap) de 100 caracteres entre los fragmentos."*

**A.4** (Metodología, "Control de Parámetros del Sistema RAG"): *"Parámetro de Recuperación (Top-K): Búsqueda restringida a los [Ej. 3 o 5] fragmentos de texto con mayor similitud del coseno."*

**A.5** (Marco Teórico, sección D): *"Este marco metodológico se fundamenta en la 'Tríada RAG', la cual mide tres dimensiones críticas: Fidelidad, Relevancia del Contexto, Relevancia de la Respuesta."*

---

## Anexo B — Extractos de los ADR referenciados

**B.1 — ADR-0002** (Contexto): *"El documento del asesor menciona LangChain como parte del stack tecnológico original (junto con FastAPI). Sin embargo, el equipo decidió conscientemente no utilizarlo, sustituyéndolo por el SDK oficial de Anthropic invocado directamente desde los adaptadores de la capa de infraestructura."*

**B.2 — ADR-0006** (Contexto): *"El documento original del asesor especifica 'Claude 3.5 Sonnet'. Esa versión corresponde a una generación de modelos de Anthropic anterior a la disponible actualmente; para el desarrollo directo mediante el SDK de Anthropic se necesita fijar un modelo vigente."*

Nota: ambos extractos citan **"el documento del asesor"**, no el Protocolo de Investigación — es precisamente la brecha documental que motiva este ATI (ver sección II.2).

---

## Anexo C — Evidencia reproducible de verificación

Los siguientes comandos, ejecutados sobre el estado del repositorio a la fecha de este documento (commit `0073f09`), sustentan las afirmaciones de esta auditoría y pueden repetirse para verificarlas:

```bash
# Confirmar ausencia de LangChain en el pipeline de producción
grep -rn "langchain" backend/src/app/                     # sin resultados

# Confirmar el modelo configurado
grep ANTHROPIC_MODEL .env                                  # claude-haiku-4-5-20251001

# Confirmar el valor real de top_k en producción
grep -n "top_k" backend/src/app/application/use_cases/answer_student_query.py

# Confirmar el valor de TOP_K usado en el script de evaluación (desincronizado)
grep -n "TOP_K" backend/scripts/evaluate.py

# Confirmar ausencia de top_p en todo el backend
grep -rn "top_p" backend/src/                               # sin resultados

# Confirmar ausencia de lockfile de dependencias del backend
find backend -maxdepth 1 -iname "*.lock" -o -iname "requirements*.txt"   # sin resultados
```

---

*Fin del Addendum Técnico de Implementación. Documento listo para su cita cruzada desde el documento final de tesis y desde el material de defensa.*
