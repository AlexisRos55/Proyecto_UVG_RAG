from __future__ import annotations

from uuid import UUID

from app.domain.entities.user import User
from app.domain.ports.user_repository_port import UserRepositoryPort
from app.domain.value_objects.email_address import EmailAddress
from app.shared.exceptions.domain_errors import DuplicateUserError


class InMemoryUserRepository(UserRepositoryPort):
    """Test double for UserRepositoryPort (NFR-03): no database required."""

    def __init__(self) -> None:
        self._users_by_id: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        if any(str(u.email) == str(user.email) for u in self._users_by_id.values()):
            raise DuplicateUserError(f"Ya existe un usuario registrado con el correo {user.email}")
        self._users_by_id[user.id] = user

    async def get_by_email(self, email: EmailAddress) -> User | None:
        return next((u for u in self._users_by_id.values() if str(u.email) == str(email)), None)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users_by_id.get(user_id)
