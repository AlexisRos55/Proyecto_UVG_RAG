from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.value_objects.embedding_vector import EmbeddingVector
from app.domain.value_objects.similarity_score import SimilarityScore


@dataclass(slots=True)
class Chunk:
    """A fixed-size fragment of a document's cleaned text (FR-03), with its embedding (FR-04)."""

    id: UUID
    document_id: UUID
    text: str
    position: int
    embedding: EmbeddingVector | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned by VectorStorePort.search, paired with its similarity to the query (FR-06)."""

    chunk: Chunk
    score: SimilarityScore
