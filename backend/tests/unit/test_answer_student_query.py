import pytest

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.use_cases.answer_student_query import (
    NO_INFORMATION_MESSAGE,
    AnswerStudentQueryUseCase,
)
from app.domain.entities.document import Document, DocumentStatus
from app.domain.value_objects.verified_answer import VerificationConfidence, VerifiedAnswer
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


def _make_use_case(
    *,
    seeded_results,
    verification,
    conversation_repository=None,
    document_repository=None,
    min_similarity_threshold=0.35,
) -> AnswerStudentQueryUseCase:
    return AnswerStudentQueryUseCase(
        embedding_port=FakeEmbeddingPort(),
        vector_store_port=FakeVectorStorePort(seeded_results=seeded_results),
        verification_port=verification,
        conversation_repository=conversation_repository or InMemoryConversationRepository(),
        document_repository=document_repository or InMemoryDocumentRepository(),
        min_similarity_threshold=min_similarity_threshold,
    )


@pytest.mark.asyncio
async def test_answers_with_grounded_response_when_relevant_context_exists() -> None:
    seeded = [make_retrieved_chunk("El reglamento indica que...", score=0.9)]
    verification = FakeVerificationStrategyPort(
        answer=VerifiedAnswer(
            answer_text="Según el reglamento, la respuesta es X.",
            is_grounded=True,
            confidence=VerificationConfidence.HIGH,
        )
    )
    use_case = _make_use_case(seeded_results=seeded, verification=verification)

    response = await use_case.execute(AnswerQueryRequest(user_id=new_id(), question="¿Qué dice el reglamento?"))

    assert response.is_grounded is True
    assert response.answer_text == "Según el reglamento, la respuesta es X."
    assert verification.received_questions == ["¿Qué dice el reglamento?"]


@pytest.mark.asyncio
async def test_grounded_response_includes_source_document_name() -> None:
    document_repository = InMemoryDocumentRepository()
    document = Document(
        id=new_id(),
        filename="reglamento_estudiantil.pdf",
        status=DocumentStatus.INDEXED,
        uploaded_at=utc_now(),
        storage_path="/app/documents/reglamento_estudiantil.pdf",
    )
    await document_repository.add(document)
    seeded = [make_retrieved_chunk("El reglamento indica que...", score=0.9, document_id=document.id)]
    verification = FakeVerificationStrategyPort(
        answer=VerifiedAnswer(
            answer_text="Según el reglamento, la respuesta es X.",
            is_grounded=True,
            confidence=VerificationConfidence.HIGH,
        )
    )
    use_case = _make_use_case(seeded_results=seeded, verification=verification, document_repository=document_repository)

    response = await use_case.execute(AnswerQueryRequest(user_id=new_id(), question="¿Qué dice el reglamento?"))

    assert len(response.sources) == 1
    assert response.sources[0].document_name == "reglamento_estudiantil.pdf"
    assert response.sources[0].page_number is None


@pytest.mark.asyncio
async def test_abstains_without_calling_llm_when_no_relevant_context() -> None:
    verification = FakeVerificationStrategyPort()
    use_case = _make_use_case(seeded_results=[], verification=verification)

    response = await use_case.execute(AnswerQueryRequest(user_id=new_id(), question="¿Cuál es la capital de Francia?"))

    assert response.is_grounded is False
    assert response.answer_text == NO_INFORMATION_MESSAGE
    assert response.sources == ()
    assert verification.received_questions == []  # NFR-02: no token spent when there is no context


@pytest.mark.asyncio
async def test_filters_out_chunks_below_similarity_threshold() -> None:
    seeded = [make_retrieved_chunk("fragmento poco relacionado", score=0.1)]
    verification = FakeVerificationStrategyPort()
    use_case = _make_use_case(seeded_results=seeded, verification=verification, min_similarity_threshold=0.35)

    response = await use_case.execute(AnswerQueryRequest(user_id=new_id(), question="algo no relacionado"))

    assert response.is_grounded is False
    assert verification.received_questions == []


@pytest.mark.asyncio
async def test_abstains_when_verification_marks_answer_as_not_grounded() -> None:
    seeded = [make_retrieved_chunk("contenido recuperado", score=0.8)]
    verification = FakeVerificationStrategyPort(
        answer=VerifiedAnswer(
            answer_text="Una respuesta que el propio modelo no pudo fundamentar.",
            is_grounded=False,
            confidence=VerificationConfidence.LOW,
            unsupported_claims=("afirmación sin respaldo",),
        )
    )
    use_case = _make_use_case(seeded_results=seeded, verification=verification)

    response = await use_case.execute(AnswerQueryRequest(user_id=new_id(), question="pregunta ambigua"))

    assert response.is_grounded is False
    assert response.answer_text == NO_INFORMATION_MESSAGE
    assert response.sources == ()


@pytest.mark.asyncio
async def test_persists_both_student_and_assistant_messages() -> None:
    seeded = [make_retrieved_chunk("contenido recuperado", score=0.8)]
    conversation_repository = InMemoryConversationRepository()
    use_case = _make_use_case(
        seeded_results=seeded,
        verification=FakeVerificationStrategyPort(),
        conversation_repository=conversation_repository,
    )
    user_id = new_id()

    await use_case.execute(AnswerQueryRequest(user_id=user_id, question="pregunta de prueba"))

    history = await conversation_repository.get_history(user_id)
    assert len(history) == 1
    assert len(history[0].messages) == 2  # student question + assistant answer
