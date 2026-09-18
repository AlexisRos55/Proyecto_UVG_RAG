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
    # Nullable: una respuesta local (saludo, identidad, guia) no es una afirmacion
    # sobre la normativa, asi que no tiene sentido evaluarla contra documentos.
    # `MessageDto` ya usaba `bool | None` para el historial; esto solo alinea ambos.
    is_grounded: bool | None
    confidence: VerificationConfidence | None
    created_at: datetime
    sources: tuple[SourceReference, ...] = field(default_factory=tuple)
