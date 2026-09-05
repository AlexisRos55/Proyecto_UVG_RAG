import pytest

from app.domain.entities.message import Message, MessageRole
from app.domain.entities.user import User, UserRole
from app.domain.value_objects.email_address import EmailAddress
from app.domain.value_objects.verified_answer import VerificationConfidence
from app.infrastructure.adapters.persistence.postgres_conversation_repository import (
    PostgresConversationRepository,
)
from app.infrastructure.adapters.persistence.postgres_user_repository import PostgresUserRepository
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

pytestmark = pytest.mark.integration


async def _persisted_user(db_session, email: str):
    user_repository = PostgresUserRepository(db_session)
    user = User(
        id=new_id(),
        email=EmailAddress(email),
        password_hash="hashed",
        role=UserRole.STUDENT,
        created_at=utc_now(),
    )
    await user_repository.add(user)
    return user


@pytest.mark.asyncio
async def test_get_or_create_returns_the_same_conversation_on_second_call(db_session) -> None:
    user = await _persisted_user(db_session, "conversacion.uno@uvg.edu.gt")
    repository = PostgresConversationRepository(db_session)

    first = await repository.get_or_create_active_conversation(user.id)
    second = await repository.get_or_create_active_conversation(user.id)

    assert first.id == second.id


@pytest.mark.asyncio
async def test_add_message_and_get_history_round_trips_all_fields(db_session) -> None:
    user = await _persisted_user(db_session, "conversacion.dos@uvg.edu.gt")
    repository = PostgresConversationRepository(db_session)
    conversation = await repository.get_or_create_active_conversation(user.id)

    student_message = Message(
        id=new_id(),
        conversation_id=conversation.id,
        role=MessageRole.STUDENT,
        content="¿Cómo solicito una beca?",
        created_at=utc_now(),
    )
    chunk_id = new_id()
    assistant_message = Message(
        id=new_id(),
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content="Debes presentar la solicitud en la oficina de becas.",
        created_at=utc_now(),
        is_grounded=True,
        confidence=VerificationConfidence.HIGH,
        source_chunk_ids=(chunk_id,),
    )
    await repository.add_message(conversation.id, student_message)
    await repository.add_message(conversation.id, assistant_message)

    history = await repository.get_history(user.id)

    assert len(history) == 1
    messages = history[0].messages
    assert len(messages) == 2
    assert messages[0].role is MessageRole.STUDENT
    assert messages[1].role is MessageRole.ASSISTANT
    assert messages[1].is_grounded is True
    assert messages[1].confidence is VerificationConfidence.HIGH
    assert messages[1].source_chunk_ids == (chunk_id,)


@pytest.mark.asyncio
async def test_get_history_is_empty_for_user_with_no_conversations(db_session) -> None:
    user = await _persisted_user(db_session, "sin.conversaciones@uvg.edu.gt")
    repository = PostgresConversationRepository(db_session)

    assert await repository.get_history(user.id) == []
