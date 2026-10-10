from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.domain.value_objects.email_address import EmailAddress


class UserRole(str, Enum):
    """Authorization role (ADR-0004, ADR-0008, ADR-0019)."""

    STUDENT = "student"
    ADMIN = "admin"
    # Visitante sin cuenta institucional (aspirante, padre de familia…): conversa con
    # el asistente sobre la normativa pública, sin acceso a funciones internas.
    GUEST = "guest"


@dataclass(slots=True)
class User:
    """An authenticated actor: a student, an administrator or a guest.

    A guest has no credentials (no email, no password): it exists so its
    conversation can be persisted and remembered like any other, which keeps a
    single conversation flow for every role (ADR-0019).
    """

    id: UUID
    email: EmailAddress | None
    password_hash: str | None
    role: UserRole
    created_at: datetime

    def __post_init__(self) -> None:
        # Only a guest may lack credentials: an institutional account always has both.
        if self.role is not UserRole.GUEST and (self.email is None or self.password_hash is None):
            raise ValueError("Una cuenta institucional requiere correo y contraseña")
        if self.role is UserRole.GUEST and (self.email is not None or self.password_hash is not None):
            raise ValueError("Una sesión de invitado no tiene credenciales")

    @classmethod
    def guest(cls, user_id: UUID, created_at: datetime) -> User:
        return cls(id=user_id, email=None, password_hash=None, role=UserRole.GUEST, created_at=created_at)

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @property
    def is_guest(self) -> bool:
        return self.role is UserRole.GUEST
