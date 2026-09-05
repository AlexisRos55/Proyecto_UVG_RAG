import pytest

from app.application.dto.auth_dto import LoginRequest, RegisterStudentRequest
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.register_student import RegisterStudentUseCase
from app.domain.entities.user import UserRole
from app.infrastructure.adapters.auth.institutional_auth_adapter import InstitutionalAuthAdapter
from app.infrastructure.config.settings import AuthSettings
from app.shared.exceptions.domain_errors import (
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidEmailDomainError,
)
from tests.fakes.in_memory_user_repository import InMemoryUserRepository


def _settings() -> AuthSettings:
    return AuthSettings(session_secret="unit-test-secret", allowed_email_domain="uvg.edu.gt")


@pytest.mark.asyncio
async def test_register_student_creates_user_and_returns_session() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    use_case = RegisterStudentUseCase(repository, InstitutionalAuthAdapter(settings), settings)

    session = await use_case.execute(
        RegisterStudentRequest(email="nuevo.estudiante@uvg.edu.gt", plain_password="claveSegura123")
    )

    assert session.role is UserRole.STUDENT
    assert session.email == "nuevo.estudiante@uvg.edu.gt"
    stored_user = await repository.get_by_id(session.user_id)
    assert stored_user is not None
    assert stored_user.password_hash != "claveSegura123"


@pytest.mark.asyncio
async def test_register_rejects_non_institutional_email() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    use_case = RegisterStudentUseCase(repository, InstitutionalAuthAdapter(settings), settings)

    with pytest.raises(InvalidEmailDomainError):
        await use_case.execute(RegisterStudentRequest(email="alguien@gmail.com", plain_password="x"))


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    use_case = RegisterStudentUseCase(repository, InstitutionalAuthAdapter(settings), settings)
    request = RegisterStudentRequest(email="duplicado@uvg.edu.gt", plain_password="claveSegura123")
    await use_case.execute(request)

    with pytest.raises(DuplicateUserError):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_credentials() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    auth_port = InstitutionalAuthAdapter(settings)
    await RegisterStudentUseCase(repository, auth_port, settings).execute(
        RegisterStudentRequest(email="estudiante@uvg.edu.gt", plain_password="claveSegura123")
    )

    session = await AuthenticateUserUseCase(repository, auth_port, settings).execute(
        LoginRequest(email="estudiante@uvg.edu.gt", plain_password="claveSegura123")
    )

    assert session.email == "estudiante@uvg.edu.gt"
    assert session.session_token


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    auth_port = InstitutionalAuthAdapter(settings)
    await RegisterStudentUseCase(repository, auth_port, settings).execute(
        RegisterStudentRequest(email="estudiante@uvg.edu.gt", plain_password="claveSegura123")
    )

    with pytest.raises(InvalidCredentialsError):
        await AuthenticateUserUseCase(repository, auth_port, settings).execute(
            LoginRequest(email="estudiante@uvg.edu.gt", plain_password="incorrecta")
        )


@pytest.mark.asyncio
async def test_login_fails_when_user_does_not_exist() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    auth_port = InstitutionalAuthAdapter(settings)

    with pytest.raises(InvalidCredentialsError):
        await AuthenticateUserUseCase(repository, auth_port, settings).execute(
            LoginRequest(email="inexistente@uvg.edu.gt", plain_password="cualquiera")
        )
