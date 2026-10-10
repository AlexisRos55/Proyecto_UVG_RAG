"""Modo invitado (ADR-0019): un rol más del modelo de usuarios, sin credenciales ni acceso interno."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.application.use_cases.start_guest_session import StartGuestSessionUseCase
from app.domain.entities.user import User, UserRole
from app.domain.services.local_skill_catalog import LocalSkillCatalog
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent
from app.domain.value_objects.email_address import EmailAddress
from app.domain.value_objects.response_plan import ResponsePlan, SkillName
from app.domain.value_objects.verified_answer import VerificationConfidence, VerifiedAnswer
from app.infrastructure.adapters.auth.institutional_auth_adapter import InstitutionalAuthAdapter
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.infrastructure.config.settings import AuthSettings
from app.infrastructure.entrypoints.api.dependencies import require_admin
from app.shared.exceptions.domain_errors import UnauthorizedError
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id
from tests.fakes.fake_rag_ports import (
    FakeEmbeddingPort,
    FakeVectorStorePort,
    FakeVerificationStrategyPort,
    make_retrieved_chunk,
)
from tests.fakes.in_memory_conversation_repository import InMemoryConversationRepository
from tests.fakes.in_memory_document_repository import InMemoryDocumentRepository
from tests.fakes.in_memory_user_repository import InMemoryUserRepository

GUEST_PERSONAL_DATA = "Esa información únicamente está disponible para usuarios autenticados mediante una cuenta institucional"


def _settings() -> AuthSettings:
    return AuthSettings(session_secret="unit-test-secret", allowed_email_domain="uvg.edu.gt")


def _student(email: str = "estudiante@uvg.edu.gt") -> User:
    return User(new_id(), EmailAddress(email), "hash", UserRole.STUDENT, utc_now())


# --- Modelo de usuarios -------------------------------------------------------------

def test_a_guest_is_a_user_without_credentials_or_privileges() -> None:
    guest = User.guest(new_id(), utc_now())
    assert guest.is_guest and not guest.is_admin
    assert guest.email is None and guest.password_hash is None


def test_only_a_guest_may_lack_credentials() -> None:
    with pytest.raises(ValueError):
        User(new_id(), None, None, UserRole.STUDENT, utc_now())
    with pytest.raises(ValueError):
        User(new_id(), None, None, UserRole.ADMIN, utc_now())
    with pytest.raises(ValueError):
        User(new_id(), EmailAddress("alguien@uvg.edu.gt"), "hash", UserRole.GUEST, utc_now())


# --- Sesión de invitado ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_guest_session_needs_no_email_or_password() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    auth = InstitutionalAuthAdapter(settings)

    session = await StartGuestSessionUseCase(repository, auth, settings).execute()

    assert session.role is UserRole.GUEST and session.email is None
    assert auth.decode_session_token(session.session_token) == session.user_id
    stored = await repository.get_by_id(session.user_id)
    assert stored is not None and stored.is_guest


@pytest.mark.asyncio
async def test_two_guests_never_collide() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    use_case = StartGuestSessionUseCase(repository, InstitutionalAuthAdapter(settings), settings)
    first, second = await use_case.execute(), await use_case.execute()
    assert first.user_id != second.user_id


@pytest.mark.asyncio
async def test_expired_guests_are_purged_but_institutional_accounts_never() -> None:
    repository = InMemoryUserRepository()
    settings = _settings()
    old = utc_now() - timedelta(days=settings.guest_retention_days + 1)
    expired_guest = User.guest(new_id(), old)
    old_student = User(new_id(), EmailAddress("antiguo@uvg.edu.gt"), "hash", UserRole.STUDENT, old)
    recent_guest = User.guest(new_id(), utc_now())
    for user in (expired_guest, old_student, recent_guest):
        await repository.add(user)

    await StartGuestSessionUseCase(repository, InstitutionalAuthAdapter(settings), settings).execute()

    assert await repository.get_by_id(expired_guest.id) is None
    assert await repository.get_by_id(old_student.id) is not None
    assert await repository.get_by_id(recent_guest.id) is not None


# --- Autorización -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_guest_is_never_an_administrator() -> None:
    with pytest.raises(UnauthorizedError):
        await require_admin(User.guest(new_id(), utc_now()))
    with pytest.raises(UnauthorizedError):
        await require_admin(_student())


# --- Conversación -------------------------------------------------------------------

def test_personal_data_for_a_guest_points_to_the_institutional_account() -> None:
    plan = ResponsePlan(skill=SkillName.DECLINE_PERSONAL_DATA, intent=ConversationIntent.PERSONAL_DATA)
    guest_text = LocalSkillCatalog.respond(plan, ConversationContext(), guest=True)
    student_text = LocalSkillCatalog.respond(plan, ConversationContext())
    assert guest_text.startswith(GUEST_PERSONAL_DATA)
    assert not student_text.startswith(GUEST_PERSONAL_DATA)


def _chat_use_case(verification: FakeVerificationStrategyPort) -> AnswerStudentQueryUseCase:
    return AnswerStudentQueryUseCase(
        embedding_port=FakeEmbeddingPort(),
        vector_store_port=FakeVectorStorePort(seeded_results=[make_retrieved_chunk("Proceso de admisión: solicitud y prueba.", score=0.9)]),
        verification_port=verification,
        conversation_repository=InMemoryConversationRepository(),
        document_repository=InMemoryDocumentRepository(),
        intent_classifier=RuleBasedIntentClassifier(),
    )


@pytest.mark.asyncio
async def test_a_guest_asking_for_their_grades_is_told_where_that_information_lives() -> None:
    verification = FakeVerificationStrategyPort()
    response = await _chat_use_case(verification).execute(
        AnswerQueryRequest(user_id=new_id(), question="¿Cuál es mi promedio?", is_guest=True)
    )
    assert response.answer_text.startswith(GUEST_PERSONAL_DATA)
    assert verification.received_questions == []  # sin llamada al modelo


@pytest.mark.asyncio
async def test_a_guest_who_wants_to_study_is_answered_normally() -> None:
    verification = FakeVerificationStrategyPort(
        answer=VerifiedAnswer(answer_text="El proceso de admisión incluye…", is_grounded=True, confidence=VerificationConfidence.HIGH)
    )
    response = await _chat_use_case(verification).execute(
        AnswerQueryRequest(user_id=new_id(), question="Quiero estudiar en UVG, ¿cómo es la admisión?", is_guest=True)
    )
    assert response.is_grounded is True and response.answer_text.startswith("El proceso de admisión")
    assert verification.received_questions  # llegó al modelo como cualquier consulta
