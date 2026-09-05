# Technology Decisions

Cada fila resume una decisión ya tomada. La justificación completa con alternativas y trade-offs vive en el ADR referenciado; esta tabla es el índice ejecutivo.

## Backend

| Tecnología | Rol | Justificación breve | ADR |
|---|---|---|---|
| Python 3.12 | Lenguaje del backend | Versión estable más reciente al momento del proyecto; tipado progresivo maduro, compatible con todo el stack de IA (ChromaDB, Sentence Transformers, PyMuPDF, SDK de Anthropic) | — |
| FastAPI | Framework web / API REST | Asíncrono nativo (relevante para llamadas de red a Anthropic y PostgreSQL), tipado con Pydantic, generación automática de OpenAPI para documentar contratos | — (impuesto por el asesor) |
| Pydantic v2 | Validación de datos y configuración | Usado tanto para DTOs de la API como para `pydantic-settings`; v2 es significativamente más rápido (core en Rust) que v1 | — |
| Anthropic SDK (sin LangChain) | Cliente del LLM | Control total del pipeline, sin abstracciones intermedias que oculten tokens/costo/latencia | [ADR-0002](adr/0002-no-langchain-direct-anthropic-sdk.md) |
| ChromaDB | Vector store | Impuesto por el asesor; local, sin servicio adicional que administrar | [ADR-0009](adr/0009-chromadb-vector-store.md) |
| Sentence Transformers (`all-MiniLM-L6-v2`) | Embeddings | Impuesto por el asesor; modelo local, sin costo de API | [ADR-0009](adr/0009-chromadb-vector-store.md) |
| PyMuPDF | Extracción de texto de PDF | Impuesto por el asesor; rápido y con buen soporte de PDFs con texto nativo | [ADR-0009](adr/0009-chromadb-vector-store.md) |
| PostgreSQL | Persistencia relacional (usuarios, conversaciones, documentos administrados) | El stack original no cubre datos no vectoriales; PostgreSQL es el estándar de facto para este tipo de dato en un sistema "empresarial" | [ADR-0003](adr/0003-postgresql-relational-persistence.md) |
| SQLAlchemy 2.x + Alembic | ORM y migraciones | Integra de forma natural con el patrón Repository detrás de `UserRepositoryPort`/`ConversationRepositoryPort`; Alembic da control de versiones del esquema | [ADR-0003](adr/0003-postgresql-relational-persistence.md) |
| Loguru | Logging estructurado | Impuesto por decisión de arquitectura; configuración mínima frente al módulo `logging` estándar, con soporte nativo de niveles y contexto estructurado | — |
| pytest + httpx | Testing | Estándar de facto en el ecosistema Python/FastAPI; `httpx` permite probar endpoints async sin levantar un servidor real | — |
| RAGAS | Evaluación del pipeline RAG | Impuesto por el asesor como framework de validación de la tríada RAG + latencia | [ADR-0010](adr/0010-ragas-evaluation-framework.md) |

## Frontend

| Tecnología | Rol | Justificación breve |
|---|---|---|
| React | Librería de UI | Impuesto por el asesor |
| TypeScript | Tipado estático | Reduce errores de integración con los contratos de la API (generados desde los esquemas Pydantic/OpenAPI) |
| Vite | Build tool / dev server | Arranque e iteración mucho más rápidos que alternativas basadas en Webpack, relevante dado el presupuesto de tiempo del proyecto |
| Tailwind CSS | Estilos | Impuesto por el asesor |
| shadcn/ui | Componentes de UI | Componentes accesibles y no empaquetados como dependencia opaca (el código se copia al repo), lo que evita una caja negra de estilos sobre Tailwind |
| TanStack Query | Manejo de estado de servidor | Cachea y sincroniza las respuestas del backend (historial de conversación, estado de indexación) sin reinventar manejo de loading/error/retry a mano |
| React Hook Form + Zod | Formularios y validación | Formularios de login y de subida de documentos con validación tipada compartida entre el esquema de formulario y el contrato de la API |

## Infraestructura

| Tecnología | Rol | Justificación breve |
|---|---|---|
| Docker | Empaquetado | Impuesto por el asesor; garantiza reproducibilidad del entorno de ejecución |
| Docker Compose | Orquestación local | Suficiente para el alcance de despliegue decidido (demo local para defensa de tesis) — ver [ADR-0007](adr/0007-local-docker-compose-deployment.md) |
| Variables de entorno (`.env`) | Configuración por ambiente | Evita secretos en código fuente; estándar de doce factores (12-factor app) |
| Health checks (Docker Compose) | Verificación de disponibilidad de servicios | Permite que `backend` espere a que `postgres` esté listo antes de aceptar tráfico |

## Inteligencia Artificial

| Decisión | Resultado | ADR |
|---|---|---|
| Modelo LLM por defecto | Claude Haiku 4.5, configurable vía `ANTHROPIC_MODEL` (nunca hardcodeado) | [ADR-0006](adr/0006-configurable-llm-model-selection.md) |
| Estrategia de verificación | Chain-of-Verification en una sola llamada (salida estructurada), con puerto abierto a un pipeline multi-llamada futuro | [ADR-0005](adr/0005-chain-of-verification-strategy.md) |
| Prompt engineering | Prompt propio, sin plantillas de LangChain | [ADR-0002](adr/0002-no-langchain-direct-anthropic-sdk.md) |

## Decisiones explícitamente descartadas para esta versión

| Alternativa descartada | Por qué no ahora | Dónde queda documentada |
|---|---|---|
| LangChain | Mayor acoplamiento, menos control sobre tokens/costo, superficie de API cambiante entre versiones | [ADR-0002](adr/0002-no-langchain-direct-anthropic-sdk.md) |
| SSO institucional real | Depende de infraestructura de identidad de UVG fuera del control del equipo, inviable en 3 semanas | [ADR-0004](adr/0004-institutional-authentication.md) |
| LLM local (self-hosted) para resolver la privacidad de datos por completo | Costo de cómputo e ingeniería incompatible con el presupuesto y el plazo | [ADR-0006](adr/0006-configurable-llm-model-selection.md) |
| Recuperación híbrida (BM25 + vectorial) y reranking | Mejora de calidad válida pero no esencial para el MVP defendible; documentada como trabajo futuro | `06-high-level-architecture.md` (sección "Evolución futura") |
