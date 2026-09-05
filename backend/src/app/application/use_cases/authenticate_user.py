from __future__ import annotations

from app.application.dto.auth_dto import AuthenticatedSession, LoginRequest
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.user_repository_port import UserRepositoryPort
from app.domain.value_objects.email_address import EmailAddress
from app.infrastructure.config.settings import AuthSettings
from app.shared.exceptions.domain_errors import InvalidCredentialsError


class AuthenticateUserUseCase:
    """Validates institutional credentials and issues a session (FR-13, ADR-0004)."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        auth_port: AuthPort,
        auth_settings: AuthSettings,
    ) -> None:
        self._user_repository = user_repository
        self._auth_port = auth_port
        self._allowed_domain = auth_settings.allowed_email_domain

    async def execute(self, request: LoginRequest) -> AuthenticatedSession:
        email = EmailAddress(request.email, allowed_domain=self._allowed_domain)
        user = await self._user_repository.get_by_email(email)

        if user is None or not self._auth_port.verify_password(
            request.plain_password, user.password_hash
        ):
            raise InvalidCredentialsError("Correo o contraseña incorrectos")

        token = self._auth_port.create_session_token(user)
        return AuthenticatedSession(
            user_id=user.id, email=str(user.email), role=user.role, session_token=token
        )
