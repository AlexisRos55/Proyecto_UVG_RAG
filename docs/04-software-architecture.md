# Software Architecture

## 1. Por qué Hexagonal *y* Clean Architecture juntas (no es redundante)

Es una pregunta legítima que un tribunal puede hacer: ¿por qué combinar dos estilos que suenan similares? Se combinan porque resuelven problemas distintos y complementarios:

- **Arquitectura Hexagonal (Ports & Adapters)** define la **forma de la frontera**: el dominio expone *puertos* (interfaces) y el mundo exterior (frameworks, bases de datos, SDKs) se conecta mediante *adaptadores* que implementan esos puertos. Resuelve "¿cómo se desacopla el negocio de la tecnología?".
- **Clean Architecture** define la **regla de dependencia**: las capas internas (dominio, casos de uso) nunca dependen de las externas (infraestructura, frameworks); es siempre al revés. Resuelve "¿en qué dirección puede apuntar cada import?" y organiza el código alrededor de casos de uso, no de capas técnicas genéricas.

En este proyecto, Hexagonal decide **qué puertos existen** (`LLMPort`, `VectorStorePort`, `DocumentRepositoryPort`, `UserRepositoryPort`, `ConversationRepositoryPort`, `AuthPort`, `VerificationStrategyPort`), y Clean Architecture decide **cómo se organizan las carpetas y qué puede importar qué** (`domain` no importa nada de `infrastructure`; `application` solo importa `domain`; `infrastructure` importa `domain` y `application`, nunca al revés). Usarlas juntas es una decisión estándar en la industria (es, de hecho, cómo Alistair Cockburn y Robert C. Martin describen arquitecturas compatibles, no competidoras) y es defendible como aplicación coherente de ambos principios, no como acumulación de buzzwords.

## 2. Capas

```
backend/src/app/
├── domain/            # Entidades, Value Objects, Puertos (interfaces). Cero dependencias externas.
├── application/       # Casos de uso. Depende solo de domain.
├── infrastructure/    # Adaptadores concretos + entrypoints (API). Depende de domain y application.
└── shared/            # Utilidades transversales (logging, excepciones base). No contiene lógica de negocio.
```

**Regla de dependencia:** `infrastructure → application → domain`. Nunca al revés. Un caso de uso jamás importa `anthropic`, `chromadb`, `sqlalchemy` ni `fastapi` directamente — siempre a través de un puerto definido en `domain/ports`.

### 2.1 Domain

Contiene las entidades del negocio (`Document`, `Chunk`, `Conversation`, `Message`, `User`, `VerifiedAnswer`) y los puertos que el dominio necesita para operar:

| Puerto | Responsabilidad | Adaptador(es) previstos |
|---|---|---|
| `LLMPort` | Generar una respuesta a partir de una pregunta y un contexto | `AnthropicLLMAdapter` |
| `VectorStorePort` | Indexar y recuperar fragmentos por similitud semántica | `ChromaVectorStoreAdapter` |
| `EmbeddingPort` | Convertir texto en vectores | `SentenceTransformersEmbeddingAdapter` |
| `DocumentTextExtractorPort` | Extraer texto crudo de un documento | `PyMuPDFExtractorAdapter` |
| `VerificationStrategyPort` | Verificar que una respuesta esté fundamentada en el contexto | `SingleCallVerificationAdapter` (implementado); `MultiCallVerificationAdapter` (futuro, no implementado) |
| `UserRepositoryPort` | Persistir y consultar usuarios | `PostgresUserRepository` |
| `ConversationRepositoryPort` | Persistir historial de conversación | `PostgresConversationRepository` |
| `DocumentRepositoryPort` | Persistir metadatos de documentos administrados (nombre, estado de indexación) | `PostgresDocumentRepository` |
| `AuthPort` | Autenticar credenciales y emitir/validar sesión | `InstitutionalAuthAdapter` |

Ningún puerto depende de un SDK concreto: son interfaces definidas en términos del dominio (p. ej. `LLMPort.generate(question: str, context: list[Chunk]) -> VerifiedAnswer`), no en términos de la API de Anthropic.

### 2.2 Application

Casos de uso, cada uno con una única responsabilidad (SRP):

- `AnswerStudentQueryUseCase`: orquesta recuperación → generación → verificación → persistencia del intercambio.
- `IngestDocumentUseCase`: extracción → limpieza → chunking → embedding → indexación de un documento.
- `AuthenticateUserUseCase`: valida credenciales institucionales y emite sesión.
- `ManageDocumentUseCase` (subir/eliminar/reemplazar) y `TriggerReindexUseCase`: casos de uso del panel administrativo.
- `GetIndexingStatusUseCase`: consulta de estado para el panel administrativo.

Los casos de uso reciben sus puertos por inyección de dependencias (constructor), nunca los instancian.

### 2.3 Infrastructure

- **Adapters:** implementaciones concretas de cada puerto (una por tecnología). Es la única capa que puede importar `anthropic`, `chromadb`, `sentence_transformers`, `pymupdf`, `sqlalchemy`.
- **Entrypoints/api:** routers de FastAPI, esquemas Pydantic de entrada/salida (DTOs de transporte, distintos de las entidades de dominio), middlewares (autenticación, manejo de errores, CORS).
- **Config:** configuración vía `pydantic-settings`, leyendo variables de entorno (ver [ADR-0006](adr/0006-configurable-llm-model-selection.md)).

### 2.4 Shared

Logging (Loguru configurado una sola vez), jerarquía de excepciones de dominio (`DomainError`, `NotFoundError`, `VerificationFailedError`), y utilidades sin estado que no constituyen lógica de negocio.

## 3. SOLID aplicado (mapeo concreto, no genérico)

| Principio | Aplicación concreta en este proyecto |
|---|---|
| **S**ingle Responsibility | `PyMuPDFExtractorAdapter` solo extrae texto; el chunking vive en un servicio de dominio separado (`ChunkingService`); el embedding es otro adaptador distinto. No existe una clase "RAGService" que haga todo. |
| **O**pen/Closed | `VerificationStrategyPort` permite añadir `MultiCallVerificationAdapter` en el futuro sin modificar `AnswerStudentQueryUseCase`. |
| **L**iskov Substitution | Cualquier implementación de `VectorStorePort` (Chroma hoy, otro motor mañana) debe ser sustituible sin romper el caso de uso que la consume — se verifica con pruebas de contrato compartidas entre implementaciones reales y fakes. |
| **I**nterface Segregation | Puertos pequeños y específicos (`EmbeddingPort` separado de `VectorStorePort`) en vez de una interfaz `RAGPort` monolítica. |
| **D**ependency Inversion | `application` depende de las abstracciones en `domain/ports`, nunca de los adaptadores concretos en `infrastructure`. La inyección de dependencias concretas ocurre solo en el punto de composición (`main.py` / contenedor de dependencias de FastAPI). |

## 4. Manejo de errores

Las excepciones de infraestructura (p. ej. `anthropic.APIError`, errores de conexión a PostgreSQL) se capturan en el adaptador correspondiente y se traducen a excepciones de dominio antes de propagarse a la capa de aplicación. Los casos de uso y el dominio nunca conocen excepciones específicas de una librería externa — de lo contrario, cambiar de proveedor también obligaría a cambiar el manejo de errores en el núcleo del negocio, violando la misma inversión de dependencias que sostiene toda la arquitectura.

## 5. Configuración y secretos

Toda configuración sensible o dependiente del entorno (API keys, cadena de conexión a PostgreSQL, nombre del modelo de Claude, secreto de firma de sesión) se centraliza en `infrastructure/config` mediante `pydantic-settings`, que lee variables de entorno. Ningún adaptador lee `os.environ` directamente ni contiene valores por defecto sensibles hardcodeados (ver [ADR-0006](adr/0006-configurable-llm-model-selection.md)).
