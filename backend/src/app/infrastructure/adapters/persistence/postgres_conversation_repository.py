from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message, MessageRole
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.value_objects.verified_answer import VerificationConfidence
from app.infrastructure.adapters.persistence.orm_models import ConversationModel, MessageModel
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id


class PostgresConversationRepository(ConversationRepositoryPort):
    """SQLAlchemy-backed implementation of ConversationRepositoryPort (ADR-0003, FR-14)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_active_conversation(self, user_id: UUID) -> Conversation:
        statement = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
            .limit(1)
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()

        if model is None:
            model = ConversationModel(id=new_id(), user_id=user_id, created_at=utc_now())
            self._session.add(model)
            await self._session.flush()

        return Conversation(id=model.id, user_id=model.user_id, created_at=model.created_at, messages=[])

    async def add_message(self, conversation_id: UUID, message: Message) -> None:
        model = MessageModel(
            id=message.id,
            conversation_id=conversation_id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
            is_grounded=message.is_grounded,
            confidence=message.confidence.value if message.confidence else None,
            source_chunk_ids=list(message.source_chunk_ids),
            source_document_names=list(message.source_document_names),
        )
        self._session.add(model)
        await self._session.flush()

    async def get_history(self, user_id: UUID) -> list[Conversation]:
        statement = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .options(selectinload(ConversationModel.messages))
            .order_by(ConversationModel.created_at.desc())
        )
        models = (await self._session.execute(statement)).scalars().all()
        return [self._to_entity(model) for model in models]

    @staticmethod
    def _to_entity(model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            user_id=model.user_id,
            created_at=model.created_at,
            messages=[
                Message(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=MessageRole(m.role),
                    content=m.content,
                    created_at=m.created_at,
                    is_grounded=m.is_grounded,
                    confidence=VerificationConfidence(m.confidence) if m.confidence else None,
                    source_chunk_ids=tuple(m.source_chunk_ids),
                    source_document_names=tuple(m.source_document_names),
                )
                for m in model.messages
            ],
        )
