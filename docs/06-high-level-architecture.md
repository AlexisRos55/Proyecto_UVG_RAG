# High Level Architecture

## 1. Diagrama de contexto (C4 — Nivel 1)

```mermaid
graph TD
    Student[Estudiante UVG Altiplano]
    Admin[Administrador de contenido]
    System[Asistente Virtual RAG]
    Anthropic[API de Anthropic - Claude]

    Student -->|Hace preguntas sobre normativa| System
    Admin -->|Gestiona documentos oficiales| System
    System -->|Envia pregunta + contexto recuperado| Anthropic
    Anthropic -->|Respuesta generada y verificada| System
```

El sistema no se integra con ningún otro sistema institucional de UVG (no hay SSO, no hay integración con el sistema académico) — es una decisión de alcance explícita, no una omisión (ver [ADR-0004](adr/0004-institutional-authentication.md)).

## 2. Diagrama de contenedores (C4 — Nivel 2)

```mermaid
graph TD
    subgraph Cliente
        FE[Frontend React + Vite<br/>Chat + Panel Admin]
    end

    subgraph "Backend - FastAPI (Docker)"
        API[API REST asincrona]
    end

    subgraph Persistencia
        PG[(PostgreSQL<br/>usuarios, conversaciones, documentos)]
        CH[(ChromaDB<br/>vectores institucionales)]
    end

    Anthropic[API externa: Anthropic Claude]

    FE -->|HTTPS / JSON| API
    API -->|SQL| PG
    API -->|Consultas vectoriales| CH
    API -->|Generacion de respuesta| Anthropic
```

Todos los contenedores (frontend, backend, PostgreSQL) se orquestan mediante `docker-compose.yml`. ChromaDB se ejecuta embebido dentro del proceso backend con persistencia en volumen, no como servicio de red aparte — evita un contenedor adicional que el alcance del proyecto no justifica.

## 3. Componentes del backend (C4 — Nivel 3, capa de aplicación)

```mermaid
graph LR
    subgraph "Entrypoints (infrastructure)"
        R1[Router: /auth]
        R2[Router: /chat]
        R3[Router: /admin/documents]
    end

    subgraph "Application (casos de uso)"
        U1[AuthenticateUserUseCase]
        U2[AnswerStudentQueryUseCase]
        U3[IngestDocumentUseCase]
        U4[ManageDocumentUseCase]
    end

    subgraph "Domain (puertos)"
        P1[AuthPort]
        P2[LLMPort]
        P3[VectorStorePort]
        P4[EmbeddingPort]
        P5[VerificationStrategyPort]
        P6[DocumentTextExtractorPort]
        P7[ConversationRepositoryPort]
        P8[DocumentRepositoryPort]
    end

    subgraph "Adapters (infrastructure)"
        A1[InstitutionalAuthAdapter -> Postgres]
        A2[AnthropicLLMAdapter]
        A3[ChromaVectorStoreAdapter]
        A4[SentenceTransformersEmbeddingAdapter]
        A5[SingleCallVerificationAdapter]
        A6[PyMuPDFExtractorAdapter]
        A7[PostgresConversationRepository]
        A8[PostgresDocumentRepository]
    end

    R1 --> U1 --> P1 --> A1
    R2 --> U2
    U2 --> P3 --> A3
    U2 --> P2 --> A2
    U2 --> P5 --> A5
    U2 --> P7 --> A7
    R3 --> U3
    U3 --> P6 --> A6
    U3 --> P4 --> A4
    U3 --> P3
    R3 --> U4 --> P8 --> A8
```

## 4. Flujo de secuencia — "El estudiante pregunta algo"

```mermaid
sequenceDiagram
    participant S as Estudiante
    participant FE as Frontend
    participant API as API (FastAPI)
    participant UC as AnswerStudentQueryUseCase
    participant EMB as EmbeddingPort
    participant VS as VectorStorePort (Chroma)
    participant LLM as LLMPort (Anthropic)
    participant DB as ConversationRepositoryPort (Postgres)

    S->>FE: Escribe pregunta
    FE->>API: POST /chat (pregunta, sesion)
    API->>UC: execute(pregunta, usuario)
    UC->>EMB: embed(pregunta)
    EMB-->>UC: vector
    UC->>VS: search(vector, top_k)
    VS-->>UC: fragmentos relevantes (o vacio)
    alt Sin fragmentos relevantes
        UC-->>API: "No tengo informacion suficiente"
    else Con fragmentos relevantes
        UC->>LLM: generate(pregunta, fragmentos) [single-call CoV]
        LLM-->>UC: respuesta + autoverificacion
        UC->>DB: guardar intercambio
        UC-->>API: respuesta verificada
    end
    API-->>FE: respuesta (JSON)
    FE-->>S: muestra respuesta en el chat
```

## 5. Flujo de secuencia — "Ingesta de un documento nuevo"

```mermaid
sequenceDiagram
    participant Admin as Administrador
    participant FE as Panel Admin (Frontend)
    participant API as API (FastAPI)
    participant UC as IngestDocumentUseCase
    participant EXT as DocumentTextExtractorPort (PyMuPDF)
    participant CH as ChunkingService
    participant EMB as EmbeddingPort
    participant VS as VectorStorePort (Chroma)
    participant DB as DocumentRepositoryPort (Postgres)

    Admin->>FE: Sube PDF
    FE->>API: POST /admin/documents
    API->>UC: execute(archivo)
    UC->>EXT: extract_text(archivo)
    EXT-->>UC: texto crudo
    UC->>CH: split(texto, tamano, overlap=100)
    CH-->>UC: fragmentos
    UC->>EMB: embed_batch(fragmentos)
    EMB-->>UC: vectores
    UC->>VS: upsert(vectores, metadatos)
    UC->>DB: registrar documento + estado "indexado"
    UC-->>API: confirmacion
    API-->>FE: estado de indexacion
```

## 6. Vista de despliegue

```mermaid
graph TD
    subgraph "Host local (equipo de desarrollo)"
        subgraph "docker compose"
            FEC[Contenedor: frontend<br/>Vite build servido estatico]
            BEC[Contenedor: backend<br/>FastAPI + Uvicorn<br/>ChromaDB embebido]
            PGC[Contenedor: postgres]
        end
        VOL1[(Volumen: chroma_data)]
        VOL2[(Volumen: postgres_data)]
    end
    Internet((Internet))

    FEC -->|proxy /api| BEC
    BEC --> VOL1
    PGC --> VOL2
    BEC --> PGC
    BEC -->|HTTPS| Internet
    Internet -->|API Anthropic| BEC
```

## 7. Evolución futura (documentada, no implementada en esta versión)

Estas mejoras fueron identificadas en el análisis inicial del proyecto como oportunidades válidas, pero deliberadamente no forman parte del MVP dado el presupuesto de tiempo (~21 horas, un desarrollador). Se documentan aquí para que el tribunal vea que fueron consideradas y descartadas por una razón explícita, no por desconocimiento:

- **Recuperación híbrida (BM25 + vectorial):** mejoraría el recall en consultas que citan artículos o números de reglamento exactos. Requiere mantener un índice adicional (p. ej. Whoosh o similar) en paralelo a ChromaDB.
- **Reranking con cross-encoder:** reduciría ruido en el Top-K antes de enviarlo al LLM, mejorando la métrica de fidelidad de RAGAS a costa de latencia adicional.
- **Chunking consciente de estructura legal/normativa:** dividir por artículo/inciso en vez de tamaño fijo, mejorando la coherencia semántica de cada fragmento.
- **Caché semántico de respuestas:** para preguntas frecuentes, evitar una llamada nueva al LLM — impacto directo en NFR-02 (costo).
- **`MultiCallVerificationAdapter`:** implementación real del pipeline de verificación en múltiples llamadas, ya contemplado por el puerto `VerificationStrategyPort` pero no implementado (ver [ADR-0005](adr/0005-chain-of-verification-strategy.md)).
