from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.domain.value_objects.email_address import EmailAddress


class UserRole(str, Enum):
    """Authorization role (ADR-0004, ADR-0008)."""

    STUDENT = "student"
    ADMIN = "admin"


@dataclass(slots=True)
class User:
    """An authenticated actor: a student or an administrator."""

    id: UUID
    email: EmailAddress
    password_hash: str
    role: UserRole
    created_at: datetime

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN
