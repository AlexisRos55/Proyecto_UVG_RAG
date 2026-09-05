from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.user import User


class AuthPort(ABC):
    """Password hashing and session token lifecycle (ADR-0004). Implemented by InstitutionalAuthAdapter."""

    @abstractmethod
    def hash_password(self, plain_password: str) -> str: ...

    @abstractmethod
    def verify_password(self, plain_password: str, password_hash: str) -> bool: ...

    @abstractmethod
    def create_session_token(self, user: User) -> str: ...

    @abstractmethod
    def decode_session_token(self, token: str) -> UUID:
        """Return the user id encoded in `token`. Raises UnauthorizedError if invalid/expired."""
