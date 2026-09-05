# ADR-0009: Retener ChromaDB, Sentence Transformers, PyMuPDF y chunking de tamaño fijo

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El documento del asesor especifica explícitamente estas piezas del pipeline de ingesta y recuperación: extracción con PyMuPDF, limpieza por regex, `RecursiveCharacterTextSplitter` (chunking de tamaño fijo con overlap de 100 caracteres), embeddings con `sentence-transformers/all-MiniLM-L6-v2`, y ChromaDB como vector store con similitud de coseno. El análisis técnico inicial del proyecto identificó alternativas potencialmente superiores para cada una de estas piezas (recuperación híbrida, reranking, chunking consciente de estructura legal, embeddings multilingües especializados). Este ADR documenta por qué, aun así, se retiene la especificación original del asesor.

## Decisión

Se mantiene el pipeline de ingesta y recuperación tal como lo especifica el asesor: PyMuPDF + limpieza por regex + chunking de tamaño fijo con overlap de 100 caracteres + `all-MiniLM-L6-v2` + ChromaDB con similitud de coseno. Las alternativas identificadas quedan documentadas como evolución futura (ver `06-high-level-architecture.md`, sección 7), no implementadas en el MVP.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó (por ahora) |
|---|---|---|---|
| Embeddings multilingües especializados (p. ej. modelos de la familia `multilingual-e5`) | Probable mejor recall semántico para terminología legal/reglamentaria en español | Requiere validar empíricamente la mejora (tiempo de experimentación no disponible) y modificar una decisión explícita del asesor sin evidencia todavía recolectada | El asesor especificó el modelo explícitamente; cambiarlo sin evidencia empírica que lo justifique sería una modificación de la especificación funcional/técnica entregada, no una mejora de arquitectura |
| Chunking consciente de estructura (por artículo/inciso) en vez de tamaño fijo | Mejor coherencia semántica por fragmento para documentos normativos | Requiere reglas de parsing específicas por tipo de documento; tiempo de implementación no disponible en el plazo de 3 semanas | Se documenta como mejora futura; el chunking de tamaño fijo con overlap sigue siendo una base razonable y es la que pidió el asesor |
| Recuperación híbrida (BM25 + vectorial) | Mejor recall en consultas con términos exactos (p. ej. "Artículo 14") | Requiere mantener un índice adicional en paralelo a ChromaDB | Fuera del alcance de tiempo disponible; documentado como evolución futura |
| Mantener la especificación del asesor tal cual (elegida) | Cumple literalmente el requisito funcional/técnico entregado; el pipeline queda encapsulado detrás de puertos (`EmbeddingPort`, `VectorStorePort`, `DocumentTextExtractorPort`), por lo que cualquier alternativa puede incorporarse después sin rediseño | Puede tener menor recall en casos específicos frente a las alternativas descartadas | — |

## Consecuencias

**Positivas:**
- Cumplimiento literal e inequívoco de la especificación técnica del asesor, sin ambigüedad interpretativa.
- Todas las alternativas descartadas quedan disponibles como adaptadores futuros sin rediseño de arquitectura, porque cada pieza ya está detrás de un puerto (ver `04-software-architecture.md`, sección 2.1).

**Negativas / trade-offs aceptados:**
- El sistema puede tener menor recall en consultas que citan artículos o cláusulas específicas, frente a lo que lograría una recuperación híbrida — riesgo documentado en `09-risk-register.md`.

## Cómo se ajusta a las restricciones del proyecto

Respeta el mandato explícito del Project Charter: "no debes modificar los objetivos funcionales establecidos" por el asesor. Las mejoras identificadas se documentan con rigor (para que el tribunal vea que fueron consideradas, no ignoradas) pero no se implementan, priorizando el tiempo disponible para completar el flujo funcional completo antes que optimizar una pieza específica del pipeline.
