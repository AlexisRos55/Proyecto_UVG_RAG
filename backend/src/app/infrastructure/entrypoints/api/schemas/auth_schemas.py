from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.application.dto.auth_dto import AuthenticatedSession
from app.domain.entities.user import UserRole


class RegisterRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AuthResponseSchema(BaseModel):
    user_id: UUID
    email: str
    role: UserRole
    session_token: str

    @classmethod
    def from_session(cls, session: AuthenticatedSession) -> AuthResponseSchema:
        return cls(
            user_id=session.user_id,
            email=session.email,
            role=session.role,
            session_token=session.session_token,
        )
