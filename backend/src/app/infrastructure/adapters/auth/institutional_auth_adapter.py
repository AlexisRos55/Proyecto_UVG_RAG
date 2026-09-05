from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import bcrypt
import jwt

from app.domain.entities.user import User
from app.domain.ports.auth_port import AuthPort
from app.infrastructure.config.settings import AuthSettings
from app.shared.exceptions.domain_errors import UnauthorizedError
from app.shared.kernel.clock import utc_now

_ALGORITHM = "HS256"
_MAX_PASSWORD_BYTES = 72  # limitación propia del algoritmo bcrypt


class InstitutionalAuthAdapter(AuthPort):
    """Password hashing (bcrypt) and session tokens (JWT) for institutional auth (ADR-0004).

    Uses the `bcrypt` library directly rather than passlib, whose bcrypt backend is
    incompatible with bcrypt >=4.1 (unmaintained project, see https://foss.heptapod.net/python-libs/passlib/-/issues/145).
    """

    def __init__(self, settings: AuthSettings) -> None:
        self._secret = settings.session_secret
        self._ttl = timedelta(minutes=settings.session_ttl_minutes)

    def hash_password(self, plain_password: str) -> str:
        password_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        password_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))

    def create_session_token(self, user: User) -> str:
        now = utc_now()
        payload = {
            "sub": str(user.id),
            "role": user.role.value,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def decode_session_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Sesión inválida o expirada") from exc
        return UUID(payload["sub"])
