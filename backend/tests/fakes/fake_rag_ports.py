from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.value_objects.embedding_vector import EmbeddingVector
from app.domain.value_objects.similarity_score import SimilarityScore
from app.domain.value_objects.verified_answer import VerificationConfidence, VerifiedAnswer
from app.shared.kernel.ids import new_id


class FakeEmbeddingPort(EmbeddingPort):
    """Deterministic embedding double: encodes text length so tests stay predictable."""

    def embed_text(self, text: str) -> EmbeddingVector:
        return EmbeddingVector.from_list([float(len(text)), 0.0, 0.0])

    def embed_batch(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        return [self.embed_text(text) for text in texts]


class FakeVectorStorePort(VectorStorePort):
    """In-memory vector store double that returns pre-seeded results regardless of the query."""

    def __init__(self, seeded_results: list[RetrievedChunk] | None = None) -> None:
        self._seeded_results = seeded_results or []
        self.upserted_chunks: list[Chunk] = []

    def upsert_chunks(self, chunks: Sequence[Chunk]) -> None:
        self.upserted_chunks.extend(chunks)

    def search(self, query_embedding: EmbeddingVector, top_k: int) -> list[RetrievedChunk]:
        return self._seeded_results[:top_k]

    def delete_by_document_id(self, document_id) -> None:  # noqa: ANN001
        self.upserted_chunks = [c for c in self.upserted_chunks if c.document_id != document_id]


def make_retrieved_chunk(text: str, score: float, document_id=None) -> RetrievedChunk:  # noqa: ANN001
    chunk = Chunk(id=new_id(), document_id=document_id or new_id(), text=text, position=0)
    return RetrievedChunk(chunk=chunk, score=SimilarityScore(score))


class FakeVerificationStrategyPort(VerificationStrategyPort):
    """Returns a pre-configured VerifiedAnswer, bypassing any real LLM call."""

    def __init__(self, answer: VerifiedAnswer | None = None) -> None:
        # Public and mutable so a test can reconfigure it after construction (e.g. once the
        # `client`/`verification_double` fixtures already wired it into the app).
        self.configured_answer = answer or VerifiedAnswer(
            answer_text="Respuesta de prueba fundamentada en el contexto.",
            is_grounded=True,
            confidence=VerificationConfidence.HIGH,
        )
        self.received_questions: list[str] = []

    async def answer(self, question: str, context_chunks) -> VerifiedAnswer:  # noqa: ANN001
        self.received_questions.append(question)
        return self.configured_answer
