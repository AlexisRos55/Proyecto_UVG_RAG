from __future__ import annotations

from app.application.dto.auth_dto import AuthenticatedSession, RegisterStudentRequest
from app.domain.entities.user import User, UserRole
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.user_repository_port import UserRepositoryPort
from app.domain.value_objects.email_address import EmailAddress
from app.infrastructure.config.settings import AuthSettings
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id


class RegisterStudentUseCase:
    """Registers a new student with an institutional email (FR-13, ADR-0004)."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        auth_port: AuthPort,
        auth_settings: AuthSettings,
    ) -> None:
        self._user_repository = user_repository
        self._auth_port = auth_port
        self._allowed_domain = auth_settings.allowed_email_domain
        self._admin_emails = set(auth_settings.admin_emails_list)

    async def execute(self, request: RegisterStudentRequest) -> AuthenticatedSession:
        email = EmailAddress(request.email, allowed_domain=self._allowed_domain)
        role = UserRole.ADMIN if str(email) in self._admin_emails else UserRole.STUDENT

        user = User(
            id=new_id(),
            email=email,
            password_hash=self._auth_port.hash_password(request.plain_password),
            role=role,
            created_at=utc_now(),
        )
        await self._user_repository.add(user)

        token = self._auth_port.create_session_token(user)
        return AuthenticatedSession(
            user_id=user.id, email=str(user.email), role=user.role, session_token=token
        )
