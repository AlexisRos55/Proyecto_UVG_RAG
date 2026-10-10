from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.user import User
from app.domain.value_objects.email_address import EmailAddress


class UserRepositoryPort(ABC):
    """Persists and queries users. Implemented by PostgresUserRepository (ADR-0003)."""

    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def get_by_email(self, email: EmailAddress) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def delete_guests_created_before(self, cutoff: datetime) -> int:
        """Removes guest sessions (and, in cascade, their conversations) older than `cutoff`."""
