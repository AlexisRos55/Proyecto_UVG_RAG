from __future__ import annotations

from datetime import timedelta

from app.application.dto.auth_dto import AuthenticatedSession
from app.domain.entities.user import User
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.user_repository_port import UserRepositoryPort
from app.infrastructure.config.settings import AuthSettings
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id


class StartGuestSessionUseCase:
    """Opens a temporary session for a visitor without an institutional account (ADR-0019).

    The guest is a regular `User` with the GUEST role and no credentials, so the
    chat, its memory and every authorization check work exactly as for any other
    role. Each new guest session also purges the guests past their retention
    period: no scheduler is needed and visitor data does not accumulate.
    """

    def __init__(self, user_repository: UserRepositoryPort, auth_port: AuthPort, auth_settings: AuthSettings) -> None:
        self._user_repository = user_repository
        self._auth_port = auth_port
        self._retention = timedelta(days=auth_settings.guest_retention_days)

    async def execute(self) -> AuthenticatedSession:
        now = utc_now()
        await self._user_repository.delete_guests_created_before(now - self._retention)
        guest = User.guest(new_id(), now)
        await self._user_repository.add(guest)
        token = self._auth_port.create_session_token(guest)
        return AuthenticatedSession(user_id=guest.id, email=None, role=guest.role, session_token=token)
