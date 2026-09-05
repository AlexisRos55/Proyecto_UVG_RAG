from __future__ import annotations

from collections.abc import Sequence

from sentence_transformers import SentenceTransformer

from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.value_objects.embedding_vector import EmbeddingVector


class SentenceTransformersEmbeddingAdapter(EmbeddingPort):
    """Embeds text locally using a Sentence Transformers model (FR-04, ADR-0009).

    The model is loaded once per process; encoding runs on CPU by default,
    which is sufficient for the corpus size and query volume of this prototype.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> EmbeddingVector:
        vector = self._model.encode(text, normalize_embeddings=True)
        return EmbeddingVector.from_list(vector.tolist())

    def embed_batch(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        if not texts:
            return []
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [EmbeddingVector.from_list(vector.tolist()) for vector in vectors]
