from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.value_objects.embedding_vector import EmbeddingVector


class VectorStorePort(ABC):
    """Indexes and retrieves chunks by semantic similarity (FR-05, FR-06). Implemented by ChromaVectorStoreAdapter."""

    @abstractmethod
    def upsert_chunks(self, chunks: Sequence[Chunk]) -> None:
        """Persist chunks (with their embeddings already set) into the vector store."""

    @abstractmethod
    def search(self, query_embedding: EmbeddingVector, top_k: int) -> list[RetrievedChunk]:
        """Return the `top_k` chunks most similar to `query_embedding`, ordered by descending similarity."""

    @abstractmethod
    def delete_by_document_id(self, document_id: UUID) -> None:
        """Remove all chunks belonging to a document (used when a document is deleted/replaced, FR-17)."""
