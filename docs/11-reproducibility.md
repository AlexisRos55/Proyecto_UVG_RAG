# Reproducibilidad experimental

Matriz oficial de parámetros del pipeline RAG y del entorno de ejecución, congelados a partir de la Fase 3.1 (Preparación de la Investigación) para garantizar que la Fase V del Protocolo de Investigación (`docs/source/Protocolo Alexis Rosales.docx`) pueda repetirse exactamente por cualquier investigador.

Este documento es la fuente de verdad operativa de los valores; el razonamiento y la justificación de cada decisión están en [`docs/10-addendum-tecnico-implementacion.md`](10-addendum-tecnico-implementacion.md) (sección VII).

**Regla de congelamiento:** ningún valor de este documento debe modificarse durante la ejecución de la Fase V sin actualizar este archivo y dejar registro de la fecha y el motivo del cambio en la tabla de historial al final.

## Parámetros del pipeline RAG

Centralizados en `RagSettings` (`backend/src/app/infrastructure/config/settings.py`), expuestos vía variables de entorno con prefijo `RAG_`.

| Parámetro | Valor congelado | Variable de entorno | Antes de la Fase 3.1 |
|---|---|---|---|
| Top-K (fragmentos recuperados) | `10` | `RAG_TOP_K` | Valor de constructor no expuesto en configuración |
| Umbral mínimo de similitud (coseno) | `0.35` | `RAG_MIN_SIMILARITY_THRESHOLD` | Valor de constructor no expuesto en configuración |
| Tamaño de chunk | `1000` caracteres | `RAG_CHUNK_SIZE` | Valor de constructor no expuesto en configuración |
| Solapamiento (overlap) | `100` caracteres | `RAG_CHUNK_OVERLAP` | Valor de constructor no expuesto en configuración |
| Modelo de embeddings | `sentence-transformers/all-MiniLM-L6-v2` | `RAG_EMBEDDING_MODEL_NAME` | Instanciado sin argumentos en `main.py` |
| Nombre de colección ChromaDB | `institutional_documents` | `RAG_CHROMA_COLLECTION_NAME` | Valor de constructor no expuesto en configuración |
| Métrica de distancia vectorial | Coseno (`hnsw:space: cosine`) | *(no expuesto — ver nota)* | Hardcodeado, sin cambios en esta fase |
| Top-P | *Sin definir* | *(no expuesto)* | Brecha pendiente — ver `docs/10-addendum-tecnico-implementacion.md`, sección V. No incluido en el congelamiento de esta fase por decisión explícita: fijar un valor sin justificación experimental introduciría una variación no controlada |

### Parámetros añadidos en la Fase 9 (ADR-0012 a ADR-0014)

La configuración por defecto pasa a ser la mejorada. **La línea base congelada anterior se reproduce exactamente** con `RAG_CHUNKING_STRATEGY=fixed`, `RAG_RETRIEVAL_MODE=dense` y `RAG_CONTEXT_CHAR_BUDGET=0`: con esos valores el pipeline ejecuta el mismo código de ingesta, recuperación y contexto que antes de la Fase 9. Ambas configuraciones pueden compararse sobre el mismo corpus con `scripts/evaluate_retrieval.py`.

| Parámetro | Valor | Variable de entorno | Justificación |
|---|---|---|---|
| Estrategia de fragmentación | `structural` | `RAG_CHUNKING_STRATEGY` | ADR-0012 |
| Tamaño máximo de fragmento estructural | `600` caracteres | `RAG_STRUCTURAL_CHUNK_SIZE` | Cabe en las 256 subpalabras de all-MiniLM-L6-v2 con su encabezado |
| Modo de recuperación | `hybrid` (BM25 + coseno, RRF) | `RAG_RETRIEVAL_MODE` | ADR-0012 |
| Candidatos por canal | `30` | `RAG_CANDIDATE_POOL` | — |
| Cobertura léxica para evidencia fuerte | `0.5` | `RAG_MIN_LEXICAL_COVERAGE` | Por encima del máximo observado en preguntas fuera de dominio (0.43) |
| Coseno para evidencia fuerte | `0.55` | `RAG_EVIDENCE_SIMILARITY_THRESHOLD` | Por encima del máximo observado en preguntas fuera de dominio (0.48) |
| Cobertura léxica mínima para entrar al contexto | `0.25` | `RAG_CONTEXT_MIN_LEXICAL_COVERAGE` | — |
| k de Reciprocal Rank Fusion | `60` | `RAG_RRF_K` | Valor del artículo original (Cormack et al., 2009) |
| Presupuesto de contexto | `6000` caracteres por pregunta | `RAG_CONTEXT_CHAR_BUDGET` | `0` desactiva el presupuesto (línea base) |
| Expansión al artículo completo | hasta `1400` caracteres | `RAG_SECTION_EXPANSION_LIMIT` | Estrategia *small-to-big* |

El umbral congelado `RAG_MIN_SIMILARITY_THRESHOLD=0.35` conserva su significado (similitud mínima para que un fragmento entre al contexto). El índice guarda una firma de la configuración que determina sus vectores (`rag_index_manifest.json` junto a ChromaDB); si al arrancar no coincide con la configuración actual, el backend reindexa todos los documentos.

**Nota sobre la métrica de distancia:** permanece hardcodeada dentro de `ChromaVectorStoreAdapter` porque el Protocolo fija explícitamente la similitud de coseno como método de recuperación (no es un parámetro sujeto a experimentación en este trabajo) — exponerlo como variable de entorno sugeriría, incorrectamente, que es una decisión abierta.

## Parámetros del modelo generativo

| Parámetro | Valor congelado | Variable de entorno |
|---|---|---|
| Modelo | `claude-haiku-4-5-20251001` | `ANTHROPIC_MODEL` |
| Temperatura | `0.0` | Hardcodeado en `AnthropicLLMAdapter.complete` (vía `extra_body`, ver ADR-0006 addendum) |
| Tope de tokens de salida | `2048` (antes `1024`) | `ANTHROPIC_MAX_TOKENS` — es un tope, no un consumo: 1024 truncaba respuestas de panorama o por programa (ADR-0015) |

## Prompt del sistema y estrategia de verificación

| Elemento | Ubicación congelada |
|---|---|
| System Prompt (Chain-of-Verification) | `backend/src/app/infrastructure/adapters/llm/single_call_verification_adapter.py`, constante `_SYSTEM_PROMPT` — texto literal, no debe editarse durante la Fase V sin registrar el cambio aquí. Modificado en la Fase 9 (ADR-0014): fragmentos rotulados con documento y ubicación, reglas de integración multidocumento y de discrepancias, campos `coverage` y `cited_fragments` |
| Estrategia de verificación | Una sola llamada (`SingleCallVerificationAdapter`), ver ADR-0005 |

## Entorno de ejecución

| Componente | Versión congelada | Cómo se fija |
|---|---|---|
| Python | `3.12.14` | `backend/pyproject.toml` (`>=3.12`, rango de desarrollo) + `backend/requirements-lock.txt` (snapshot exacto) |
| SDK de Anthropic | `1.3.0` | `backend/requirements-lock.txt` |
| ChromaDB | `1.5.9` | `backend/requirements-lock.txt` |
| Sentence Transformers | `6.0.1` | `backend/requirements-lock.txt` |
| PyMuPDF | `1.28.2` | `backend/requirements-lock.txt` |
| React | `19.2.8` | `frontend/package-lock.json` |
| Tailwind CSS | `4.3.3` | `frontend/package-lock.json` |
| Vite | `5.4.x` | `frontend/package-lock.json` |

## Cómo instalar el entorno exacto (reproducción exacta, no desarrollo normal)

**Backend:**
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e . --no-deps
```

**Frontend:**
```bash
cd frontend
npm ci   # respeta package-lock.json al pie de la letra; no usar `npm install` para reproducir resultados
```

> Para desarrollo normal (no reproducción de resultados experimentales), seguir las instrucciones estándar del README (`pip install -e ".[dev]"`, `npm install`), que permiten rangos de versión más flexibles.

## Brechas de reproducibilidad conocidas, no resueltas en esta fase

Documentadas explícitamente para que no se confundan con congelamiento ya realizado:

- **Top-P**: sin definir (ver arriba).
- **Imágenes base de Docker** (`python:3.12-slim`, `node:22-slim`, `nginx:1.27-alpine`, `postgres:16-alpine`): fijadas a nivel de minor/major, no a un dígito de parche ni a un digest SHA exacto. Se decidió explícitamente no fijarlas en esta fase (ver decisión registrada en el historial de esta fase de trabajo).
- **Entorno Windows**: el Protocolo especifica Windows como entorno de validación; a la fecha de este documento, la ejecución completa del sistema no ha sido verificada en ese sistema operativo.

## Historial de cambios a este congelamiento

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-11 | Congelamiento inicial de todos los parámetros de esta tabla | Fase 3.1 — Preparación de la Investigación, Bloque 2 |
| 2026-09-24 | Capa de inteligencia de recuperación (ADR-0015): reglas 7 y 2 del prompt de sistema (tablas sin marcas, sin ejemplos ni generalizaciones propias), `ANTHROPIC_MAX_TOKENS=2048`, versión de ingesta `structural-v6` (ficha del documento y anotación de tablas; fuerza reindexación automática) | Prueba en vivo: respuesta truncada y matriz de requisitos inventada; ambas corregidas |
| 2026-09-24 | Nuevos parámetros de la Fase 9 y nuevo prompt de sistema; la configuración anterior queda como línea base seleccionable | Evidencia medida sobre el corpus oficial (ADR-0012 a ADR-0014, `docs/12-fase9-evolucion-motor-rag.md`). La Fase V del Protocolo aún no había comenzado |
