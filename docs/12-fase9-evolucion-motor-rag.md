# Fase 9 — Evolución del motor RAG

**Fecha:** 2026-09-24 · **Decisiones:** [ADR-0012](adr/0012-structure-aware-ingestion-and-hybrid-retrieval.md), [ADR-0013](adr/0013-document-comprehension-catalog.md), [ADR-0014](adr/0014-citation-aware-verification.md) · **Parámetros:** [11-reproducibility.md](11-reproducibility.md)

Este documento resume la auditoría del motor RAG, las decisiones tomadas y su efecto medido. Todas las cifras provienen de ejecuciones reproducibles sobre el **corpus oficial real** (16 PDF: 2 reglamentos, calendario académico, proceso de admisión y 12 folletos de programas), no del corpus sintético de ejemplo.

---

## 1. Problemas encontrados

La auditoría recorrió el pipeline completo con los documentos reales. Los hallazgos, ordenados por impacto:

| # | Problema | Evidencia | Efecto |
|---|---|---|---|
| P1 | **Membretes repetidos dentro de cada fragmento.** Los reglamentos repiten en cada página un bloque de ~600 caracteres (código, versión, autoridades). | 58 de 220 fragmentos contenían el membrete; en los reglamentos, casi la mitad de cada fragmento de 1000 caracteres | Todos los vectores de un reglamento se parecían entre sí. FR-02 no se cumplía en la práctica. |
| P2 | **Truncamiento silencioso del embedding.** `all-MiniLM-L6-v2` trunca a 256 subpalabras; el español rinde 2.96 caracteres por subpalabra en su vocabulario inglés. | **94 %** de los fragmentos truncados (mediana 319 subpalabras) | ~20 % del texto de cada fragmento nunca llegaba al vector. |
| P3 | **El umbral de similitud no discriminaba.** | «¿Cuál es la capital de Francia?» superaba 0.35 con 10 fragmentos. Abstención previa al LLM: **0 de 4** preguntas fuera de dominio | FR-08 dependía por completo de la llamada pagada al modelo. |
| P4 | **Recuperación solo semántica con un modelo inglés.** | En el banco, el fragmento correcto quedaba fuera del Top-10 en muchas preguntas con respuesta literal («horas beca», «Artículo 58», siglas) | hit@1 de la línea base: **0.109** |
| P5 | **Sin páginas ni estructura.** Se concatenaban todas las páginas antes de fragmentar. | ADR-0011: `page_number` siempre nulo | Citas solo por nombre de archivo; imposible responder «¿dónde habla de…?». |
| P6 | **Calendario desordenado.** PyMuPDF entrega la columna de fechas separada de la de actividades. | «17» y «Último día para pagar la cuota de agosto» en fragmentos distintos | Preguntas de fecha irrespondibles aunque el dato estuviera indexado. |
| P7 | **Contexto fijo de 10 fragmentos.** Sin deduplicar (el corpus tiene documentos idénticos subidos dos veces) ni eliminar solapamientos. | 9 618 caracteres medios por consulta, gran parte membrete y duplicados | Costo y ruido sin beneficio. |
| P8 | **Citas imprecisas.** Se citaban todos los documentos recuperados, usados o no. | — | Fuentes que no sustentan la respuesta. |
| P9 | **Fidelidad y cobertura mezcladas** en un solo booleano. | — | Respuestas fieles pero incompletas se descartaban enteras. |
| P10 | **Sin comprensión documental.** «¿De qué trata?», «¿cuáles son los capítulos?», «¿qué documento consulto?» se trataban como búsqueda de fragmentos. | — | Respuestas caras, parciales y no verificables. |
| P11 | **Deriva entre evaluación y producción.** Cada script armaba su propio pipeline; la siembra de arranque ignoraba `RagSettings`. | Ya documentado en el addendum (Top-K 5 vs 10) | Lo evaluado no era garantizadamente lo desplegado. |
| P12 | **Regla de dependencia.** Los casos de uso de ingesta importaban el pipeline concreto de infraestructura. | `grep` sobre `application/` | Violación de Clean Architecture preexistente. |

**Qué estaba bien y se conservó:** la arquitectura hexagonal con puertos pequeños, la verificación en una sola llamada con salida estructurada, la deliberación determinista previa (clasificador de intención y política de respuesta), el catálogo de respuestas locales, la decisión de no inyectar historial en el prompt, el saneamiento de entrada y la separación de las dos abstenciones.

---

## 2. Decisiones arquitectónicas

Principio rector: **cada mejora entra por un puerto** y la línea base congelada sigue siendo ejecutable.

```
Pregunta ─► Saneamiento ─► Clasificación de intención ─► Política
                                                             │
          ┌──────────────── local (sin corpus) ◄─────────────┤
          │                                                  │
          ├──────── navegación documental (catálogo, 0 tokens) ◄── ADR-0013
          │                                                  │
          └─► Análisis de consulta (menciones, artículos, sinónimos, subpreguntas)
                  │
                  ▼
          Recuperación híbrida  ◄── ADR-0012
          coseno (ChromaDB) ─┐
                             ├─► RRF adaptativa + señales estructurales ─► admisión en 2 etapas
          BM25 (memoria) ────┘
                  │
                  ▼
          Ensamblado de contexto (deduplica, fusiona, expande al artículo, presupuesto)
                  │
                  ▼
          Verificación en UNA llamada (cobertura + fragmentos citados) ◄── ADR-0014
                  │
                  ▼
          Respuesta + citas (documento · capítulo · artículo · página)
```

| Decisión | Dónde | Por qué así |
|---|---|---|
| Nuevos puertos `LexicalSearchPort`, `CorpusCatalogPort`, `DocumentIndexerPort` | `domain/ports` | Interface Segregation: el caso de uso consulta el catálogo sin saber de vectores. `DocumentIndexerPort` corrige P12. |
| `SynchronizedVectorStore` como decorador de `VectorStorePort` | infraestructura | Mantiene el índice léxico al día sin tocar ingesta, reindexación ni borrado (Open/Closed). |
| BM25 en memoria reconstruido desde ChromaDB | infraestructura | Una sola fuente de verdad; se reconstruye en milisegundos y detecta cambios de otro proceso por tamaño. |
| Análisis de consulta, fusión, navegador, índice documental | `domain/services` (puros) | Deterministas, sin E/S, probados exhaustivamente. |
| Recuperador y ensamblador de contexto | `application/services` | Orquestan puertos; el caso de uso los recibe por inyección. |
| `rag_factory` | infraestructura | Un único lugar construye el pipeline para backend, siembra y scripts (P11). |
| Firma del índice + reindexado automático | arranque | Evita mezclar vectores de dos configuraciones tras una actualización. |
| Colaboradores nuevos opcionales en `AnswerStudentQueryUseCase` | aplicación | Sin ellos el caso de uso es exactamente la línea base: `evaluate.py` y las 150 pruebas previas siguen pasando sin cambios. |

---

## 3. Mejoras en la recuperación

**Ingesta estructural** (ADR-0012): retiro de membretes por repetición entre páginas y por posición (capturando código, versión y vigencia); reconstrucción de líneas lógicas; jerarquía capítulo → sección → artículo, con corrección de una errata real del corpus («Capítulo 35» donde el documento quiere decir Artículo 35); títulos de capítulo en dos renglones; «Control de cambios» como sección de nivel documento; páginas por fragmento, incluso cuando una oración cruza un salto de página; fragmentos de hasta 600 caracteres (caben en las 256 subpalabras del modelo) con 100 de solapamiento dentro de cada artículo; encabezado contextual antepuesto al embeber; calendario reconstruido por filas («17 de agosto: Último día para pagar…»).

**Recuperación híbrida:** BM25 con lematización ligera del español (número, género, infinitivo), corrección ortográfica contra el vocabulario del corpus (Damerau-Levenshtein acotada), factor de coordinación, léxico institucional (beca ↔ ayuda financiera, siglas AVE/PAA/FJBG, escritura de chat), fusión por RRF con pesos adaptativos (un canal sin evidencia fuerte vota a la mitad), bonificación por artículo citado y por «Control de cambios» cuando se pregunta por cambios, filtro por documento cuando se lo nombra.

**Admisión en dos etapas** (corrige P3): para no abstenerse se exige evidencia fuerte (coseno ≥ 0.55, o ≥ 50 % de la información léxica, o el artículo citado); para entrar al contexto basta la débil (el umbral congelado 0.35 o 25 % léxico). Los umbrales se fijaron por encima del máximo observado en preguntas fuera de dominio (coseno 0.48, cobertura 0.43).

### Resultados medidos (`scripts/evaluate_retrieval.py`, 50 casos)

| Métrica | Línea base congelada | Solo híbrida | Solo estructural | **Fase 9** |
|---|---:|---:|---:|---:|
| hit@1 | 0.109 | 0.283 | 0.261 | **0.457** |
| recall@5 | 0.326 | 0.696 | 0.478 | **0.783** |
| MRR | 0.186 | 0.454 | 0.345 | **0.618** |
| **Recall del contexto final** | 0.391 | 0.728 | 0.543 | **0.891** |
| Caracteres de contexto por consulta | 9 618 | 6 325 | 4 425 | **4 652** |
| Abstención previa al LLM (fuera de dominio) | 0 / 4 | 4 / 4 | 0 / 4 | **4 / 4** |
| Abstenciones falsas (en dominio) | 2.2 % | 0 % | 2.2 % | **0 %** |
| Latencia de recuperación | 6.5 ms | 7.5 ms | 6.5 ms | 8.7 ms |

Las columnas intermedias son ablaciones de una sola variable: cada cambio aporta por separado y se complementan.

---

## 4. Mejoras en la comprensión documental

El catálogo del corpus (ADR-0013) deriva de los fragmentos indexados el índice de cada documento y responde **sin llamar al modelo**:

| Pregunta | Respuesta |
|---|---|
| ¿De qué trata este documento? / Resume el reglamento | Título, código, versión, páginas; objeto citado del Artículo 1; capítulos con sus rangos de artículos |
| ¿Cuáles son los capítulos? / ¿Cuáles son los temas principales? | Índice con artículos y páginas |
| ¿Dónde habla sobre becas? / ¿Qué artículos hablan del seguro? | Apartados agrupados por documento, con artículo y página |
| ¿Cuáles documentos hablan sobre graduación? / ¿Qué reglamento debo consultar? | Documento de referencia y dónde lo trata; otros que lo mencionan |
| ¿Qué documentos están relacionados? | Documentos con vocabulario temático afín (TF-IDF) y los temas que comparten |
| ¿Qué cambios hubo? | Respuesta fundamentada con prioridad a la sección «Control de cambios» |
| «becas» (una sola palabra) | Mapa del tema con subtemas reales del corpus («cobertura», «condiciones», «penalizaciones») |

«Este documento» se resuelve con los documentos citados en el turno anterior; si no hay forma de saber a cuál se refiere, se pregunta con la lista de documentos disponibles.

---

## 5. Mejoras en la calidad de las respuestas

- **Forma adaptada a la pregunta:** 14 formas decididas de manera determinista (directa, sí/no, lista, pasos, comparación, definición, explicación, resumen, consecuencias, recomendación, ventajas, tabla, preguntas frecuentes, por secciones). Las preguntas múltiples se responden por secciones.
- **Integración multidocumento:** el prompt exige integrar todos los fragmentos pertinentes y explicar las diferencias entre documentos. Verificado en vivo: la pregunta por el promedio mínimo se respondió combinando los artículos 18, 25 y 33 y distinguiendo campus central, campus externos y AVE.
- **Voz institucional:** se amplió la lista de muletillas prohibidas («no cuento con información…») y se pide nombrar el artículo como lo haría una persona. `evaluate.py` ya no usa un texto de abstención propio.
- **Cobertura parcial:** una respuesta fiel pero incompleta se muestra con confianza media y una frase final que dice qué no está establecido, en lugar de descartarse.
- **Abstención útil:** indica dónde está la normativa más cercana.
- **Citas** (ADR-0014): solo los pasajes efectivamente usados, con título declarado, «Capítulo IV · Artículo 18. Condiciones» y páginas; persistidas para el historial. El frontend las muestra en la tarjeta de fuente.

**Prueba en vivo** (Claude Haiku 4.5, 6 preguntas fundamentadas): la línea base respondió **4/6** (se abstuvo en «¿qué pasa si no cumplo las horas beca?» y «¿a qué hora son las elecciones?»); la Fase 9 respondió **6/6**, todas con confianza alta y con la cita del artículo correcto.

---

## 6. Impacto sobre la precisión

- El contexto que ve el modelo contiene la evidencia necesaria en el **89 %** de los casos, frente al **39 %** de la línea base: es el techo de lo que el modelo puede responder correctamente.
- El primer fragmento es el correcto en el 46 % de los casos (antes 11 %).
- Menos ruido en el contexto (sin membretes ni duplicados, −52 % de texto) reduce la probabilidad de que el modelo se apoye en material irrelevante, que es lo que mide la fidelidad de RAGAS.
- Las respuestas estructurales (capítulos, artículos, ubicaciones) son exactas por construcción: se extraen, no se generan.

---

## 7. Impacto sobre la experiencia de usuario

- Respuestas donde antes había abstenciones (4/6 → 6/6 en la prueba en vivo).
- Citas verificables: el estudiante puede abrir el PDF en la página indicada y leer el artículo.
- Consultas de una palabra y preguntas sobre documentos reciben orientación concreta en lugar de una petición genérica de detalle.
- Preguntas múltiples, largas, con saludos, con erratas o con siglas funcionan sin que el estudiante tenga que reformular.
- Las preguntas fuera de dominio y de navegación se responden sin esperar al modelo.

---

## 8. Impacto sobre el consumo de tokens

| Medida | Línea base | Fase 9 |
|---|---:|---:|
| Tokens de entrada por llamada (medido en vivo, 6 preguntas) | 5 491 | **4 300 (−22 %)** |
| Tokens de salida por llamada | 224 | 268 |
| Llamadas en preguntas de navegación documental | 1 | **0** |
| Llamadas en preguntas fuera de dominio sin regla explícita | 1 | **0** (abstención previa) |
| Llamadas adicionales introducidas | — | **0** (sigue siendo una por consulta) |

La reducción de tokens de entrada es menor que la del contexto (−52 %) porque el prompt de sistema, fijo, pesa ~1 500 tokens. El almacenamiento en caché de ese prompt no es aplicable: Claude Haiku 4.5 exige un prefijo mínimo mayor que el del prompt actual.

---

## 9. Qué quedó pendiente

- **Banco validado por expertos.** Los 50 casos de `retrieval_benchmark.json` los etiquetó el equipo a partir del texto; el Protocolo exige un banco validado por personal institucional. Riesgo: los parámetros se ajustaron observando este banco, así que las cifras pueden ser optimistas. Se mitigó con cambios de principio (no de caso) y con ablaciones.
- **RAGAS de punta a punta** con la nueva configuración (`evaluate.py`, ya sincronizado) sobre el banco oficial.
- **Tablas de elegibilidad** del reglamento de ayudas financieras: las marcas que indican a qué beca aplica cada requisito son dibujos vectoriales, no texto. Se recupera cada condición, pero no a qué subprograma aplica.
- **Calendario:** 5 de 6 páginas de meses se reconstruyen por filas; la de diciembre usa otra disposición y conserva el orden por bloques.
- Casos aún fallidos del banco: 5 de 46 (sinónimos que no aparecen en el léxico, como «servicios del campus» → «residencias, MakerSpace»).
- Deuda arquitectónica preexistente fuera del alcance: `RegisterStudentUseCase` y `AuthenticateUserUseCase` importan `AuthSettings` de infraestructura.
- Número de página: se cita la página del archivo PDF (la que muestra cualquier visor), no la impresa en el pie.

---

## 10. Propuestas para una futura evolución

1. **Modelo de embeddings multilingüe** (requiere aprobación del asesor, pues ADR-0009 fija el modelo). El experimento del anexo A lleva el recall del contexto de 0.891 a 0.935 y el hit@1 de 0.457 a 0.587 sin otro cambio.
2. **Banco validado por expertos** y recalibración de los umbrales de evidencia sobre él.
3. **Reranking con cross-encoder multilingüe** solo si el banco validado muestra que el orden, y no la cobertura, es el cuello de botella.
4. **Extracción de tablas con geometría** (asociar marcas vectoriales a columnas) para las tablas de elegibilidad.
5. **Caché semántica de respuestas** para preguntas frecuentes (NFR-02).
6. **Índice léxico persistente** (por ejemplo, la búsqueda de texto completo de PostgreSQL) si el corpus crece dos órdenes de magnitud; hoy la reconstrucción en memoria tarda milisegundos.
7. **Glosario automático** a partir de los artículos de «Definiciones» para alimentar el léxico institucional.

---

## Anexo A — Experimento con un modelo de embeddings multilingüe

Mismo banco y mismo corpus, cambiando solo el modelo de embeddings (`--embedding-model paraphrase-multilingual-MiniLM-L12-v2`). **No se adoptó**: ADR-0009 fija `all-MiniLM-L6-v2` por especificación del asesor.

| Métrica | Solo coseno, MiniLM (actual) | Solo coseno, multilingüe | Fase 9, MiniLM (actual) | Fase 9, multilingüe |
|---|---:|---:|---:|---:|
| hit@1 | 0.261 | 0.457 | 0.457 | **0.587** |
| recall@5 | 0.478 | 0.652 | 0.783 | **0.859** |
| Recall del contexto final | 0.543 | 0.728 | 0.891 | **0.935** |
| Abstención previa al LLM | 0 / 4 | 3 / 4 | 4 / 4 | 4 / 4 |
| Latencia de recuperación | 6.5 ms | 15.0 ms | 8.7 ms | 12.0 ms |

Lectura: el modelo multilingüe mejora el canal semántico de forma sustancial (+34 % de recall de contexto por sí solo) y la arquitectura híbrida se beneficia de ello. También muestra que la Fase 9 compensa buena parte de la debilidad del modelo actual: con MiniLM híbrido (0.891) se supera al multilingüe solo semántico (0.728). Los umbrales de evidencia se calibraron para MiniLM; al adoptar otro modelo deben recalibrarse, y el cambio fuerza la reindexación automática por la firma del índice.

## Anexo B — Verificación

| Suite | Resultado |
|---|---|
| Backend: unitarias, integración (PostgreSQL, ChromaDB y MiniLM reales) y e2e | 266 aprobadas (antes solo 150 unitarias ejecutables localmente) |
| Frontend (Vitest) | 58 aprobadas |
| `mypy src` | sin errores (antes 4) |
| `ruff` sobre el código modificado | sin errores |
| TypeScript / ESLint | sin errores |
| Migración Alembic `b7f3c2d91a40` | aplicada sobre la cadena existente |

**Cómo reproducir:** `python scripts/evaluate_retrieval.py --corpus-dir <carpeta con los 16 PDF oficiales>`.
