from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message


class ConversationRepositoryPort(ABC):
    """Persists conversation history per student (FR-14). Implemented by PostgresConversationRepository."""

    @abstractmethod
    async def get_or_create_active_conversation(self, user_id: UUID) -> Conversation:
        """Return the student's current conversation, creating one if none exists yet."""

    @abstractmethod
    async def add_message(self, conversation_id: UUID, message: Message) -> None: ...

    @abstractmethod
    async def get_history(self, user_id: UUID) -> list[Conversation]:
        """Return all conversations for a student, most recent first."""
