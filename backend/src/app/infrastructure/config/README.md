# infrastructure/config

Configuración centralizada mediante `pydantic-settings`, leyendo variables de entorno (ver `.env.example` en la raíz del repositorio).

Previsto: una clase `Settings` (o una por dominio de configuración: `AnthropicSettings`, `DatabaseSettings`, `AuthSettings`) que expone, entre otros:

- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (ver [ADR-0006](../../../../../docs/adr/0006-configurable-llm-model-selection.md))
- `DATABASE_URL` (PostgreSQL)
- `CHROMA_PERSIST_DIR`
- `SESSION_SECRET`
- `LOG_LEVEL`

Regla: ningún adaptador lee `os.environ` directamente. Todo pasa por esta capa, que es la única con conocimiento de nombres de variables de entorno.
