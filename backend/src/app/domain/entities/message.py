from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.domain.value_objects.verified_answer import VerificationConfidence


class MessageRole(str, Enum):
    STUDENT = "student"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class Message:
    """One turn of a conversation (FR-11, FR-14)."""

    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    is_grounded: bool | None = None
    confidence: VerificationConfidence | None = None
    source_chunk_ids: tuple[UUID, ...] = field(default_factory=tuple)
    source_document_names: tuple[str, ...] = field(default_factory=tuple)
    """Distinct filenames of the documents behind source_chunk_ids (explainability, sprint 1 demo)."""
