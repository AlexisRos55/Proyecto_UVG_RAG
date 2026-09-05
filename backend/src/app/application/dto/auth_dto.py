from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.user import UserRole


@dataclass(frozen=True, slots=True)
class RegisterStudentRequest:
    email: str
    plain_password: str


@dataclass(frozen=True, slots=True)
class LoginRequest:
    email: str
    plain_password: str


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user_id: UUID
    email: str
    role: UserRole
    session_token: str
