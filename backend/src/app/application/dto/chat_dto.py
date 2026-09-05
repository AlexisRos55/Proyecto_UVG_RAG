from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.value_objects.source_reference import SourceReference
from app.domain.value_objects.verified_answer import VerificationConfidence


@dataclass(frozen=True, slots=True)
class AnswerQueryRequest:
    user_id: UUID
    question: str


@dataclass(frozen=True, slots=True)
class AnswerQueryResponse:
    message_id: UUID
    conversation_id: UUID
    answer_text: str
    is_grounded: bool
    confidence: VerificationConfidence
    created_at: datetime
    sources: tuple[SourceReference, ...] = field(default_factory=tuple)
