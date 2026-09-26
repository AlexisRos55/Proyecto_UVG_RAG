# ADR-0012: Ingesta consciente de estructura y recuperación híbrida

**Estado:** Aceptado — reemplaza parcialmente a [ADR-0009](0009-chromadb-vector-store.md) (fragmentación y recuperación); conserva PyMuPDF, limpieza por regex, `all-MiniLM-L6-v2` y ChromaDB con coseno.

**Fecha:** 2026-09-24

## Contexto

ADR-0009 retuvo la fragmentación de tamaño fijo y la recuperación puramente vectorial por falta de evidencia empírica y de tiempo, y dejó documentadas como evolución la recuperación híbrida y el chunking por artículo. La Fase 9 auditó el pipeline sobre el **corpus oficial real** (16 PDF) y obtuvo esa evidencia:

1. **Membretes repetidos.** Los reglamentos repiten en cada página un membrete de ~600 caracteres (código, versión, nombres de autoridades). Con fragmentos fijos de 1000 caracteres, cerca de la mitad de cada fragmento era ese bloque: todos los vectores de un reglamento se parecían entre sí, y FR-02 («remoción de encabezados y pies de página») no se cumplía en la práctica.
2. **Truncamiento del embedding.** `all-MiniLM-L6-v2` trunca a 256 subpalabras; en español rinde ≈3 caracteres por subpalabra. El **94 %** de los fragmentos de 1000 caracteres se truncaba: la cola de cada fragmento nunca llegaba al vector.
3. **Umbral sin poder discriminante.** El modelo, entrenado en inglés, sitúa todo texto en español en la misma región del espacio. Las preguntas fuera de dominio superaban el umbral de 0.35 con diez fragmentos: **0 de 4** se abstenían antes de llamar al LLM.
4. **Pérdida de páginas y de estructura.** Concatenar todas las páginas antes de fragmentar impedía citar página o artículo (ADR-0011 lo dejó explícito).
5. **Tablas de calendario desordenadas.** PyMuPDF entrega la columna de fechas separada de la de actividades: «17» y «Último día para pagar la cuota de agosto» terminaban en fragmentos distintos.

## Decisión

**Ingesta.** Extracción por página; retiro de membretes por repetición entre páginas (con captura de código, versión y vigencia); reconstrucción de líneas lógicas; reconocimiento de la jerarquía capítulo → sección → artículo; fragmentación por unidad estructural con tope de 600 caracteres y solapamiento de 100 dentro de cada artículo largo (la regla de FR-03, aplicada por artículo); embedding del fragmento precedido de su encabezado («documento — capítulo · artículo»), variante determinista y sin coste de la *recuperación contextual*; reconstrucción por filas de las páginas con forma de tabla fechada.

**Recuperación.** Canal léxico BM25 (k1=1.2, b=0.75) con lematización ligera del español, corrección ortográfica contra el vocabulario del corpus y factor de coordinación; fusión con el canal vectorial por **Reciprocal Rank Fusion** (k=60) con pesos adaptativos por consulta; admisión en dos etapas (evidencia fuerte para no abstenerse, evidencia débil para entrar al contexto); descomposición de preguntas múltiples; ensamblado de contexto con presupuesto de caracteres, deduplicación, fusión de piezas contiguas y expansión al artículo completo (*small-to-big*).

**Reproducibilidad.** La línea base congelada sigue disponible y es seleccionable por configuración (`RAG_CHUNKING_STRATEGY=fixed`, `RAG_RETRIEVAL_MODE=dense`, `RAG_CONTEXT_CHAR_BUDGET=0`). El índice guarda una firma de su configuración y el backend reindexa al arrancar si no coincide.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| Cambiar el modelo de embeddings por uno multilingüe | Ataca la causa de 2 y 3 | Modifica una especificación explícita del asesor | Se evaluó experimentalmente (ver informe de la Fase 9) y queda como propuesta con evidencia; no se cambia sin aprobación del asesor |
| Reranking con cross-encoder | Mejor precisión en el Top-K | +100–500 ms en CPU por consulta, modelo adicional de ~120 MB | La fusión con señales estructurales cerró la mayor parte de la brecha medida; se reserva para cuando exista un banco validado que lo justifique |
| Combinación ponderada de puntajes (α·coseno + β·BM25) | Simple | Escalas incomparables; pesos a calibrar con datos que no existen | RRF no requiere calibración |
| Segundo almacén persistente (Whoosh, Elasticsearch) para BM25 | Persistencia propia | Dos fuentes de verdad; otro servicio en Docker | El índice BM25 se reconstruye desde ChromaDB en milisegundos |
| Expansión o reescritura de consultas con el LLM | Mayor cobertura semántica | Una llamada adicional por consulta (NFR-02, ADR-0005) | Léxico institucional determinista: cero tokens, auditable |

## Consecuencias

**Positivas** (banco de 46 casos sobre el corpus real, `scripts/evaluate_retrieval.py`): recall de contexto 0.391 → 0.891; hit@1 0.109 → 0.457; contexto enviado al modelo −52 %; abstención previa al LLM en preguntas fuera de dominio 0/4 → 4/4; cero abstenciones falsas. Cada fragmento conoce su artículo y sus páginas.

**Negativas / trade-offs aceptados:** más código de ingesta basado en heurísticas del formato institucional (cubierto por pruebas unitarias con los casos reales encontrados); el índice léxico vive en memoria (adecuado para el volumen actual; ver informe, sección de escalabilidad); el banco de evaluación fue etiquetado por el equipo y no sustituye al banco validado por expertos que exige el Protocolo.

## Cómo se ajusta a las restricciones del proyecto

No añade llamadas al LLM, dependencias nuevas ni servicios a Docker Compose. Todo cambio está detrás de puertos existentes o nuevos (`LexicalSearchPort`, `CorpusCatalogPort`, `DocumentIndexerPort`), y la línea base del experimento sigue siendo reproducible bit a bit.
