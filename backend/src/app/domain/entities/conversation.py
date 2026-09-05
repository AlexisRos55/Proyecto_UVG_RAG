from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities.message import Message


@dataclass(slots=True)
class Conversation:
    """A student's conversation thread with the assistant (FR-14)."""

    id: UUID
    user_id: UUID
    created_at: datetime
    messages: list[Message] = field(default_factory=list)

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
