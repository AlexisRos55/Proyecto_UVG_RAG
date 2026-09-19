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
    async def answer(
        self,
        question: str,
        context_chunks: Sequence[RetrievedChunk],
        style_directive: str | None = None,
    ) -> VerifiedAnswer:
        """Generate a verified answer to `question` using only `context_chunks` as grounding.

        `style_directive` shapes the *form* of the answer (list, steps, table…), decided
        deterministically before generation. It is an additive, optional parameter: existing
        callers are unaffected, and it never adds a call — it frames the one already made,
        so US-2.2 ("one Anthropic invocation per query") still holds.
        """
