# domain/entities

Entidades del negocio: objetos con identidad y ciclo de vida propio, independientes de cualquier framework o SDK.

Previstas (ver `docs/04-software-architecture.md`, sección 2.1): `Document`, `Chunk`, `Conversation`, `Message`, `User`, `VerifiedAnswer`.

Reglas:
- No importan `pydantic` de FastAPI, `sqlalchemy`, `anthropic` ni `chromadb`.
- No contienen lógica de acceso a datos ni de infraestructura, solo invariantes y comportamiento propio del negocio.
