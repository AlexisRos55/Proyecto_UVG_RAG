# application/use_cases

Casos de uso del sistema: orquestan entidades y puertos del dominio para cumplir un objetivo concreto del negocio. Cada caso de uso tiene una única responsabilidad (SRP) y recibe sus puertos por inyección de dependencias (constructor), nunca los instancia.

Previstos (ver `docs/07-backlog.md` para su priorización):

- `AnswerStudentQueryUseCase`
- `IngestDocumentUseCase`
- `AuthenticateUserUseCase`
- `ManageDocumentUseCase`
- `TriggerReindexUseCase`
- `GetIndexingStatusUseCase`

Regla: un caso de uso solo importa `domain` (entidades, value objects, puertos). Nunca importa `fastapi`, `anthropic`, `chromadb` ni `sqlalchemy` directamente.
