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

**Nota sobre la métrica de distancia:** permanece hardcodeada dentro de `ChromaVectorStoreAdapter` porque el Protocolo fija explícitamente la similitud de coseno como método de recuperación (no es un parámetro sujeto a experimentación en este trabajo) — exponerlo como variable de entorno sugeriría, incorrectamente, que es una decisión abierta.

## Parámetros del modelo generativo

| Parámetro | Valor congelado | Variable de entorno |
|---|---|---|
| Modelo | `claude-haiku-4-5-20251001` | `ANTHROPIC_MODEL` |
| Temperatura | `0.0` | Hardcodeado en `AnthropicLLMAdapter.complete` (vía `extra_body`, ver ADR-0006 addendum) |

## Prompt del sistema y estrategia de verificación

| Elemento | Ubicación congelada |
|---|---|
| System Prompt (Chain-of-Verification) | `backend/src/app/infrastructure/adapters/llm/single_call_verification_adapter.py`, constante `_SYSTEM_PROMPT` — texto literal, no debe editarse durante la Fase V sin registrar el cambio aquí |
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
