from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User, UserRole
from app.domain.ports.user_repository_port import UserRepositoryPort
from app.domain.value_objects.email_address import EmailAddress
from app.infrastructure.adapters.persistence.orm_models import UserModel
from app.shared.exceptions.domain_errors import DuplicateUserError


class PostgresUserRepository(UserRepositoryPort):
    """SQLAlchemy-backed implementation of UserRepositoryPort (ADR-0003)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        model = UserModel(
            id=user.id,
            email=str(user.email),
            password_hash=user.password_hash,
            role=user.role.value,
            created_at=user.created_at,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateUserError(f"Ya existe un usuario registrado con el correo {user.email}") from exc

    async def get_by_email(self, email: EmailAddress) -> User | None:
        statement = select(UserModel).where(UserModel.email == str(email))
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_entity(model) if model is not None else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return self._to_entity(model) if model is not None else None

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=EmailAddress(model.email),
            password_hash=model.password_hash,
            role=UserRole(model.role),
            created_at=model.created_at,
        )
