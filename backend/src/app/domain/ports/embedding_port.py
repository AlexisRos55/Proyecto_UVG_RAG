from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.value_objects.embedding_vector import EmbeddingVector


class EmbeddingPort(ABC):
    """Converts text into numeric vectors (FR-04). Implemented by SentenceTransformersEmbeddingAdapter."""

    @abstractmethod
    def embed_text(self, text: str) -> EmbeddingVector:
        """Embed a single piece of text (typically a student's question)."""

    @abstractmethod
    def embed_batch(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        """Embed many pieces of text at once (typically document chunks during ingestion)."""
