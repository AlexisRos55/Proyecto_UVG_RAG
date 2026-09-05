import pytest

from app.domain.entities.user import User, UserRole
from app.domain.value_objects.email_address import EmailAddress
from app.infrastructure.adapters.persistence.postgres_user_repository import PostgresUserRepository
from app.shared.exceptions.domain_errors import DuplicateUserError
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

pytestmark = pytest.mark.integration


def _user(email: str) -> User:
    return User(
        id=new_id(),
        email=EmailAddress(email),
        password_hash="hashed-value",
        role=UserRole.STUDENT,
        created_at=utc_now(),
    )


@pytest.mark.asyncio
async def test_add_and_get_by_email(db_session) -> None:
    repository = PostgresUserRepository(db_session)
    user = _user("integracion.usuario@uvg.edu.gt")

    await repository.add(user)
    found = await repository.get_by_email(EmailAddress("integracion.usuario@uvg.edu.gt"))

    assert found is not None
    assert found.id == user.id
    assert found.role is UserRole.STUDENT


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(db_session) -> None:
    repository = PostgresUserRepository(db_session)
    assert await repository.get_by_id(new_id()) is None


@pytest.mark.asyncio
async def test_adding_duplicate_email_raises_domain_error(db_session) -> None:
    repository = PostgresUserRepository(db_session)
    await repository.add(_user("duplicado.integracion@uvg.edu.gt"))

    with pytest.raises(DuplicateUserError):
        await repository.add(_user("duplicado.integracion@uvg.edu.gt"))
