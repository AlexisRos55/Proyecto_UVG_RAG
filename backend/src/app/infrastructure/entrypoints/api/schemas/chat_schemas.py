from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.dto.chat_dto import AnswerQueryResponse
from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message, MessageRole
from app.domain.value_objects.source_reference import SourceReference
from app.domain.value_objects.verified_answer import VerificationConfidence


class AskQuestionRequestSchema(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SourceReferenceSchema(BaseModel):
    document_name: str
    page_number: int | None = None

    @classmethod
    def from_value_object(cls, source: SourceReference) -> SourceReferenceSchema:
        return cls(document_name=source.document_name, page_number=source.page_number)


class AnswerResponseSchema(BaseModel):
    message_id: UUID
    conversation_id: UUID
    answer_text: str
    is_grounded: bool
    confidence: VerificationConfidence
    created_at: datetime
    sources: list[SourceReferenceSchema]

    @classmethod
    def from_dto(cls, dto: AnswerQueryResponse) -> AnswerResponseSchema:
        return cls(
            message_id=dto.message_id,
            conversation_id=dto.conversation_id,
            answer_text=dto.answer_text,
            is_grounded=dto.is_grounded,
            confidence=dto.confidence,
            created_at=dto.created_at,
            sources=[SourceReferenceSchema.from_value_object(s) for s in dto.sources],
        )


class MessageSchema(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    is_grounded: bool | None
    confidence: VerificationConfidence | None
    sources: list[SourceReferenceSchema]

    @classmethod
    def from_entity(cls, message: Message) -> MessageSchema:
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            is_grounded=message.is_grounded,
            confidence=message.confidence,
            sources=[SourceReferenceSchema(document_name=name) for name in message.source_document_names],
        )


class ConversationSchema(BaseModel):
    id: UUID
    created_at: datetime
    messages: list[MessageSchema]

    @classmethod
    def from_entity(cls, conversation: Conversation) -> ConversationSchema:
        return cls(
            id=conversation.id,
            created_at=conversation.created_at,
            messages=[MessageSchema.from_entity(m) for m in conversation.messages],
        )
