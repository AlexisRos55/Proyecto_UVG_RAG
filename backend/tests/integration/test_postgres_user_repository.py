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


# --- Modo invitado (ADR-0019) ---------------------------------------------------------

@pytest.mark.asyncio
async def test_a_guest_round_trips_without_credentials(db_session) -> None:
    repository = PostgresUserRepository(db_session)
    first, second = User.guest(new_id(), utc_now()), User.guest(new_id(), utc_now())

    await repository.add(first)
    await repository.add(second)  # varios invitados conviven: el correo nulo no es único

    found = await repository.get_by_id(first.id)
    assert found is not None and found.is_guest and found.email is None and found.password_hash is None


@pytest.mark.asyncio
async def test_the_database_rejects_an_institutional_account_without_credentials(db_session) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.infrastructure.adapters.persistence.orm_models import UserModel

    db_session.add(UserModel(id=new_id(), email=None, password_hash=None, role=UserRole.STUDENT.value, created_at=utc_now()))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_purging_expired_guests_removes_their_conversations_and_keeps_students(db_session) -> None:
    from datetime import timedelta

    from app.infrastructure.adapters.persistence.postgres_conversation_repository import (
        PostgresConversationRepository,
    )

    users = PostgresUserRepository(db_session)
    conversations = PostgresConversationRepository(db_session)
    old = utc_now() - timedelta(days=8)
    expired_guest = User.guest(new_id(), old)
    old_student = User(new_id(), EmailAddress(f"antiguo.{new_id().hex[:8]}@uvg.edu.gt"), "hash", UserRole.STUDENT, old)
    await users.add(expired_guest)
    await users.add(old_student)
    await conversations.get_or_create_active_conversation(expired_guest.id)

    removed = await users.delete_guests_created_before(utc_now() - timedelta(days=7))

    assert removed >= 1
    assert await users.get_by_id(expired_guest.id) is None
    assert await conversations.get_history(expired_guest.id) == []
    assert await users.get_by_id(old_student.id) is not None
