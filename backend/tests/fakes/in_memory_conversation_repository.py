from __future__ import annotations

from uuid import UUID

from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id


class InMemoryConversationRepository(ConversationRepositoryPort):
    """Test double for ConversationRepositoryPort (NFR-03): no database required."""

    def __init__(self) -> None:
        self._conversations: dict[UUID, Conversation] = {}
        self._active_by_user: dict[UUID, UUID] = {}

    async def get_or_create_active_conversation(self, user_id: UUID) -> Conversation:
        conversation_id = self._active_by_user.get(user_id)
        if conversation_id is not None:
            return self._conversations[conversation_id]

        conversation = Conversation(id=new_id(), user_id=user_id, created_at=utc_now())
        self._conversations[conversation.id] = conversation
        self._active_by_user[user_id] = conversation.id
        return conversation

    async def add_message(self, conversation_id: UUID, message: Message) -> None:
        self._conversations[conversation_id].add_message(message)

    async def get_history(self, user_id: UUID) -> list[Conversation]:
        return [c for c in self._conversations.values() if c.user_id == user_id]
