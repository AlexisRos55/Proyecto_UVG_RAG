# Tests

- `unit/`: casos de uso y entidades de dominio probados con dobles de prueba (fakes/stubs) que implementan los puertos de `domain/ports`. No requieren red, base de datos ni credenciales reales.
- `integration/`: adaptadores concretos (`infrastructure/adapters/*`) probados contra infraestructura real (PostgreSQL de prueba, ChromaDB), o contra la API de Anthropic solo cuando sea indispensable y con costo controlado.
- `e2e/`: flujos completos vía el cliente HTTP del API (`httpx.AsyncClient` contra la app de FastAPI), verificando el sistema de punta a punta.

Prioridad de cobertura dado el presupuesto de tiempo del proyecto (ver `docs/07-backlog.md`): los casos de uso críticos (`AnswerStudentQueryUseCase`, `IngestDocumentUseCase`) deben tener pruebas unitarias antes que cobertura exhaustiva de casos borde en capas secundarias como el panel administrativo.
