from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.entities.chunk import RetrievedChunk
from app.domain.value_objects.verified_answer import VerifiedAnswer


class VerificationStrategyPort(ABC):
    """Produces an answer grounded in retrieved context, applying Chain-of-Verification (FR-10).

    This is the port `AnswerStudentQueryUseCase` depends on directly. The only implementation
    in this version is `SingleCallVerificationAdapter` (ADR-0005), which composes `LLMPort`
    internally with exactly one call. A future `MultiCallVerificationAdapter` could call
    `LLMPort` more than once without requiring any change to the use case (Open/Closed).
    """

    @abstractmethod
    async def answer(self, question: str, context_chunks: Sequence[RetrievedChunk]) -> VerifiedAnswer:
        """Generate a verified answer to `question` using only `context_chunks` as grounding."""
