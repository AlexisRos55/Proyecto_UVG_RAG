# infrastructure/adapters/persistence

Implementación concreta de `UserRepositoryPort`, `ConversationRepositoryPort` y `DocumentRepositoryPort` usando SQLAlchemy 2.x contra PostgreSQL (ver [ADR-0003](../../../../../../docs/adr/0003-postgresql-relational-persistence.md)).

Previsto:
- `PostgresUserRepository`
- `PostgresConversationRepository`
- `PostgresDocumentRepository`
- Modelos SQLAlchemy (tablas) separados de las entidades de dominio — un repositorio traduce entre la fila de la tabla y la entidad de `domain/entities`, para que el dominio no dependa de un modelo ORM.
- Migraciones de Alembic en un directorio `migrations/` (a crear junto con el primer modelo).
