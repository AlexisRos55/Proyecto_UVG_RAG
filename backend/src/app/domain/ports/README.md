# domain/ports

Interfaces (puertos) que el dominio necesita para operar, sin conocer su implementación concreta. Cada puerto se define en términos del negocio, no de un SDK específico.

Puertos previstos (ver `docs/04-software-architecture.md`, sección 2.1, para el mapeo completo puerto → adaptador):

| Puerto | Responsabilidad |
|---|---|
| `LLMPort` | Generar una respuesta verificada a partir de una pregunta y un contexto |
| `VectorStorePort` | Indexar y recuperar fragmentos por similitud semántica |
| `EmbeddingPort` | Convertir texto en vectores |
| `DocumentTextExtractorPort` | Extraer texto crudo de un documento |
| `VerificationStrategyPort` | Verificar que una respuesta esté fundamentada en el contexto |
| `UserRepositoryPort` | Persistir y consultar usuarios |
| `ConversationRepositoryPort` | Persistir historial de conversación |
| `DocumentRepositoryPort` | Persistir metadatos de documentos administrados |
| `AuthPort` | Autenticar credenciales y emitir/validar sesión |

Regla: los adaptadores concretos de estos puertos viven en `infrastructure/adapters`, nunca aquí.
