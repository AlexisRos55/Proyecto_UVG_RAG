# Figura 4. Arquitectura hexagonal del prototipo

| Campo | Valor |
|---|---|
| Número | Figura 4 |
| Nombre | Arquitectura hexagonal del prototipo |
| Tipo | Diagrama (Mermaid, bloques); texto impreso ≈ 5.5 pt a 5.65 × 7.1 in |
| Fuente | [`../diagrams/architecture.mmd`](../diagrams/architecture.mmd) |
| Archivo para el documento | `../diagrams/architecture.png` |
| Ubicación | Anexo C (tras intercambiar C y D, ver el índice); se cita en VI.H.1 y VIII.D |
| Orientación | Horizontal (página apaisada o ancho completo) |

## Objetivo

Demostrar que el prototipo cumple la Arquitectura Hexagonal y la regla de dependencias de Clean Architecture: el dominio declara puertos, cada tecnología entra por un adaptador que implementa uno de ellos, y nada del dominio conoce FastAPI, Anthropic, ChromaDB ni SQLAlchemy. Da al lector un mapa de los componentes que nombra el texto de VI.H.1–2 y de la Fase IV.

## Qué debe mostrar

De arriba hacia abajo, una franja por capa:

1. **Actores**: estudiante, administrador e invitado en el navegador; investigador en la línea de comandos.
2. **Frontend**: inicio de sesión y modo invitado · chat, fuentes e historial · panel administrativo.
3. **Adaptadores de entrada**: API REST FastAPI (`/auth`, `/chat`, `/admin/documents`, `/health`, con validación de JWT y rol) y los scripts `ingest.py` y `evaluate.py`.
4. **Capa de aplicación**: casos de uso de acceso, de consulta y de gestión documental, y los servicios `KnowledgeRetriever` y `ContextAssembler`.
5. **Dominio**: entidades, servicios de dominio y objetos de valor.
6. **Puertos**: trece interfaces en nueve rectángulos verde oscuro (los tres repositorios, LexicalSearch + CorpusCatalog y DocumentIndexer + TextExtractor comparten rectángulo).
7. **Adaptadores de salida**: cada uno **en la misma columna** que el puerto que implementa.
8. **Servicios externos**: PostgreSQL 16, API de Anthropic (Claude Haiku 4.5), all-MiniLM-L6-v2, ChromaDB embebido y los PDF.
9. **Evaluación**: `evaluate.py → evaluation_report.json → analyze.py → resultados.md`.

Correspondencias verificadas en el código (`backend/src/app`):

| Puerto | Adaptador |
|---|---|
| AuthPort | InstitutionalAuthAdapter (bcrypt + PyJWT) |
| User / Conversation / DocumentRepositoryPort | Repositorios PostgreSQL (SQLAlchemy asíncrono) |
| IntentClassifierPort | RuleBasedIntentClassifier |
| VerificationStrategyPort | SingleCallVerificationAdapter (usa LLMPort) |
| LLMPort | AnthropicLLMAdapter |
| EmbeddingPort | SentenceTransformersEmbeddingAdapter |
| VectorStorePort | ChromaVectorStoreAdapter, envuelto por SynchronizedVectorStore |
| LexicalSearchPort y CorpusCatalogPort | InMemoryCorpusIndex (BM25 y catálogo) |
| DocumentIndexerPort y DocumentTextExtractorPort | DocumentIndexingPipeline y PyMuPDFExtractorAdapter |

## Cómo generarla

1. Usa el PNG ya exportado (5652 × 3381 px), o vuelve a generarlo con las instrucciones de [`../diagrams/README.md`](../diagrams/README.md) si cambias el `.mmd`.
2. En Word: Insertar → Imágenes → el PNG; ajústalo al ancho del área de texto (16,5 cm en carta con márgenes de 2,5 cm). Si el texto queda por debajo de 7 pt impreso, pon esa página en orientación horizontal.
3. No uses el SVG en Word (ver README de diagramas).

## Pie de figura

> Figura 4. Arquitectura hexagonal del prototipo. Elaboración propia con base en el repositorio del proyecto.

## Referencia dentro del texto

Insertada en el protocolo (VI.H.1, al final del párrafo que enumera los puertos):

> La Figura 4 (Anexo C) muestra cómo se organizan estos componentes en el prototipo: cada capa se apoya en la siguiente, el dominio declara los puertos y, debajo de cada puerto, se ubica el adaptador que lo implementa con una tecnología concreta. Ninguna parte del dominio depende de FastAPI, de Anthropic, de ChromaDB ni de SQLAlchemy, que solo aparecen en la capa de adaptadores.
