# infrastructure/adapters/vector_store

Implementación concreta de `VectorStorePort` y `EmbeddingPort`.

Previsto: `ChromaVectorStoreAdapter` (indexación y recuperación por similitud de coseno sobre ChromaDB local, persistido en volumen Docker) y `SentenceTransformersEmbeddingAdapter` (`all-MiniLM-L6-v2`, ver [ADR-0009](../../../../../../docs/adr/0009-chromadb-vector-store.md)).

Regla: el caso de uso que consume estos puertos no conoce el nombre de la colección de Chroma ni el modelo de embeddings específico — esos detalles viven únicamente en este adaptador y en su configuración.
