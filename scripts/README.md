# scripts

Utilidades operativas independientes del servidor HTTP. Requieren el entorno del backend activo (`cd backend && source .venv/bin/activate`, o `pip install -e ".[dev]"`) y las mismas variables de entorno que el backend (`DATABASE_URL`, `CHROMA_PERSIST_DIR`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`).

## Sprint 1 demo: la ingesta ya no es un paso manual

Desde el sprint 1, el backend indexa automáticamente al arrancar cualquier PDF en `backend/documents/` que aún no esté indexado (ver `app/infrastructure/bootstrap.py` y `docs/adr/0011-sprint1-demo-scope.md`). `docker compose up` (o `uvicorn ... --reload` en local) es suficiente — no hace falta correr `ingest.py` a mano salvo para reindexar manualmente o preparar `evaluate.py` contra un ChromaDB distinto.

```bash
python scripts/generate_sample_corpus.py   # (re)genera 3 PDF de ejemplo en backend/documents/
python scripts/ingest.py                    # opcional: ingesta manual/reindexado
python scripts/evaluate.py                  # corre RAGAS contra golden_dataset.json (requiere ANTHROPIC_API_KEY real)
python scripts/evaluate_retrieval.py --corpus-dir <carpeta con los PDF oficiales>   # sin LLM ni costo
```

## Archivos

- `generate_sample_corpus.py`: genera un corpus de ejemplo (reglamento, becas, seguro) **ficticio** en `backend/documents/`, para poder demostrar el pipeline sin depender de los documentos oficiales reales de UVG Altiplano (ver Project Charter, sección 7). Reemplázalo por los documentos reales antes de una demo o defensa real.
- `golden_dataset.json`: conjunto de referencia para RAGAS (12 preguntas, 10 con respuesta esperada en el corpus y 2 fuera de dominio para verificar la abstención de FR-08). Debe reemplazarse por preguntas reales una vez se ingesten documentos reales.
- `ingest.py`: ejecuta `IngestDocumentUseCase` (vía `DocumentIndexingPipeline`) contra un directorio de PDFs — el mismo pipeline que corre automáticamente al arrancar el backend y que usa el panel administrativo (EPIC-7).
- `evaluate.py`: ejecuta RAGAS (fidelidad, relevancia de respuesta, precisión y exhaustividad de contexto) más latencia y exactitud de abstención, usando los adaptadores reales de producción. Guarda el reporte en `scripts/evaluation_report.json`. Ver el addendum de implementación en [ADR-0010](../docs/adr/0010-ragas-evaluation-framework.md) sobre el pin de versión de `ragas` y el uso de `langchain-anthropic`/`langchain-huggingface` como dependencias exclusivas de esta herramienta de evaluación (no del pipeline de producción, ver [ADR-0002](../docs/adr/0002-no-langchain-direct-anthropic-sdk.md)).

- `evaluate_retrieval.py` (Fase 9; configuración `conversational` desde la Fase 10): evaluación **offline y gratuita** de la recuperación. `conversational` mide el camino desplegado para una primera pregunta (analizador + interpretación del rastreador conversacional); `enhanced`, el analizador solo, como en la Fase 9. Indexa el corpus en ChromaDB temporales y compara la línea base congelada con la configuración actual y dos ablaciones (hit@1, recall@5, MRR, recall del contexto final, tamaño del contexto, abstención previa al LLM). `--embedding-model` permite experimentar con otro modelo sin tocar la configuración.
- `retrieval_benchmark.json`: 50 preguntas sobre el corpus oficial (46 con evidencia esperada y 4 fuera de dominio), cada una con los hechos que el contexto debe contener, tomados literalmente de los documentos. Etiquetado por el equipo de desarrollo: complementa, pero no sustituye, al banco validado por expertos que exige el Protocolo.

- `evaluate_conversations.py` (Fase 9, ADR-0015): recorre conversaciones multiturno con el caso de uso real y el pipeline real; solo el modelo se sustituye por un registrador. Mide si cada referencia («esa», «¿y los requisitos?», «continuemos») se resolvió, si el contexto contiene los hechos esperados, si un cambio de tema se respetó y si hubo abstención previa al modelo.
- `conversation_benchmark.json` (22 conversaciones, 86 turnos, usado durante el desarrollo; incluye los cinco casos de la Fase 9.2 y los nueve de la Fase 10) y `conversation_benchmark_holdout.json` (31 turnos; los de la Fase 10, `h10-*`, se redactaron y midieron antes de implementar nada): la diferencia entre ambos estima el sobreajuste. La marca `no_llm` exige que un turno se resuelva sin llamar al modelo.
- `simulate_conversations.py` (Fase 9.2, ADR-0016): genera con semilla fija cientos de conversaciones largas (temas, seguimientos elípticos, «explícalo», cortesías, pausas «continuemos mañana», saludos de regreso, reanudaciones, interrupciones fuera de dominio y cambios de tema) y contrasta cada turno con **invariantes** de conversación en lugar de respuestas escritas a mano. Desde la Fase 10 incluye además orientación del estudiante perdido, «no entiendo», regreso explícito a un tema, comparaciones que siguen en juego y «esa beca de antes» (14 invariantes). Se ejecuta desde `scripts/`: `PYTHONPATH=../backend/src python simulate_conversations.py --corpus-dir <PDF> --seed 7`.

`ingest.py`, `evaluate.py`, `evaluate_retrieval.py`, `evaluate_conversations.py` y `simulate_conversations.py` construyen el pipeline con `app.infrastructure.rag_factory`, igual que el backend: lo evaluado es, por construcción, lo desplegado.

Ninguno reimplementa lógica del pipeline: todos reutilizan directamente `backend/src/app/application/use_cases` e `infrastructure/adapters`.

## Limitaciones conocidas

- `evaluate.py` no se pudo ejecutar de punta a punta durante la implementación por no contar con una `ANTHROPIC_API_KEY` real: se validó estructuralmente hasta el límite de esa credencial (ver el addendum de implementación en [ADR-0006](../docs/adr/0006-configurable-llm-model-selection.md)). El equipo debe ejecutarlo con una key real antes de la defensa para obtener las métricas reales de RAGAS.
- RAGAS, la evaluación de métricas avanzadas, RBAC completo y el panel administrativo **no forman parte del guion de la demo del sprint 1** (ver `docs/adr/0011-sprint1-demo-scope.md`), aunque su código sigue implementado y probado desde la fase de implementación anterior.
