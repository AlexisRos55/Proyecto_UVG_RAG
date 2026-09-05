# scripts

Utilidades operativas independientes del servidor HTTP. Requieren el entorno del backend activo (`cd backend && source .venv/bin/activate`, o `pip install -e ".[dev]"`) y las mismas variables de entorno que el backend (`DATABASE_URL`, `CHROMA_PERSIST_DIR`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`).

## Sprint 1 demo: la ingesta ya no es un paso manual

Desde el sprint 1, el backend indexa automáticamente al arrancar cualquier PDF en `backend/documents/` que aún no esté indexado (ver `app/infrastructure/bootstrap.py` y `docs/adr/0011-sprint1-demo-scope.md`). `docker compose up` (o `uvicorn ... --reload` en local) es suficiente — no hace falta correr `ingest.py` a mano salvo para reindexar manualmente o preparar `evaluate.py` contra un ChromaDB distinto.

```bash
python scripts/generate_sample_corpus.py   # (re)genera 3 PDF de ejemplo en backend/documents/
python scripts/ingest.py                    # opcional: ingesta manual/reindexado
python scripts/evaluate.py                  # corre RAGAS contra golden_dataset.json (requiere ANTHROPIC_API_KEY real)
```

## Archivos

- `generate_sample_corpus.py`: genera un corpus de ejemplo (reglamento, becas, seguro) **ficticio** en `backend/documents/`, para poder demostrar el pipeline sin depender de los documentos oficiales reales de UVG Altiplano (ver Project Charter, sección 7). Reemplázalo por los documentos reales antes de una demo o defensa real.
- `golden_dataset.json`: conjunto de referencia para RAGAS (12 preguntas, 10 con respuesta esperada en el corpus y 2 fuera de dominio para verificar la abstención de FR-08). Debe reemplazarse por preguntas reales una vez se ingesten documentos reales.
- `ingest.py`: ejecuta `IngestDocumentUseCase` (vía `DocumentIndexingPipeline`) contra un directorio de PDFs — el mismo pipeline que corre automáticamente al arrancar el backend y que usa el panel administrativo (EPIC-7).
- `evaluate.py`: ejecuta RAGAS (fidelidad, relevancia de respuesta, precisión y exhaustividad de contexto) más latencia y exactitud de abstención, usando los adaptadores reales de producción. Guarda el reporte en `scripts/evaluation_report.json`. Ver el addendum de implementación en [ADR-0010](../docs/adr/0010-ragas-evaluation-framework.md) sobre el pin de versión de `ragas` y el uso de `langchain-anthropic`/`langchain-huggingface` como dependencias exclusivas de esta herramienta de evaluación (no del pipeline de producción, ver [ADR-0002](../docs/adr/0002-no-langchain-direct-anthropic-sdk.md)).

Ninguno reimplementa lógica del pipeline: todos reutilizan directamente `backend/src/app/application/use_cases` e `infrastructure/adapters`.

## Limitaciones conocidas

- `evaluate.py` no se pudo ejecutar de punta a punta durante la implementación por no contar con una `ANTHROPIC_API_KEY` real: se validó estructuralmente hasta el límite de esa credencial (ver el addendum de implementación en [ADR-0006](../docs/adr/0006-configurable-llm-model-selection.md)). El equipo debe ejecutarlo con una key real antes de la defensa para obtener las métricas reales de RAGAS.
- RAGAS, la evaluación de métricas avanzadas, RBAC completo y el panel administrativo **no forman parte del guion de la demo del sprint 1** (ver `docs/adr/0011-sprint1-demo-scope.md`), aunque su código sigue implementado y probado desde la fase de implementación anterior.
