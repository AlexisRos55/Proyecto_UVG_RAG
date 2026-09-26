"""Comportamiento del caso de uso con los colaboradores de la Fase 9 (ADR-0012 a ADR-0014)."""

import pytest

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.services.context_assembler import ContextAssembler
from app.application.services.knowledge_retriever import KnowledgeRetriever
from app.application.use_cases.answer_student_query import (
    NOT_GROUNDED_MESSAGE,
    AnswerStudentQueryUseCase,
)
from app.domain.entities.document import Document, DocumentStatus
from app.domain.value_objects.response_plan import ResponseStyle
from app.domain.value_objects.verified_answer import (
    AnswerCoverage,
    VerificationConfidence,
    VerifiedAnswer,
)
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk
from tests.fakes.fake_rag_ports import (
    FakeEmbeddingPort,
    FakeVectorStorePort,
    FakeVerificationStrategyPort,
)
from tests.fakes.in_memory_conversation_repository import InMemoryConversationRepository
from tests.fakes.in_memory_document_repository import InMemoryDocumentRepository

AID = new_id()
GROUPS = new_id()


async def _build(answer: VerifiedAnswer | None = None):
    index = InMemoryCorpusIndex()
    index.add(
        [
            chunk("Artículo 1. Objetivo General. El programa apoya a estudiantes con limitaciones económicas.",
                  document_id=AID, position=0, chapter="Capítulo 1. Disposiciones generales", article=1,
                  article_title="Objetivo General", page=3),
            chunk("Artículo 17. Cobertura. La beca cubre hasta el 50% de la colegiatura.",
                  document_id=AID, position=1, chapter="Capítulo IV. Programas", article=17,
                  article_title="Cobertura", page=9),
            chunk("Artículo 19. Penalizaciones. La beca se reduce por cursos reprobados.",
                  document_id=AID, position=2, chapter="Capítulo IV. Programas", article=19,
                  article_title="Penalizaciones", page=11),
            chunk("Artículo 58. Horario. Las elecciones son el jueves a las 10:00 horas.",
                  document_id=GROUPS, title="Reglamento de grupos estudiantiles", position=0,
                  chapter="Capítulo 2. Asociaciones", article=58, article_title="Horario", page=20),
        ]
    )
    documents = InMemoryDocumentRepository()
    for document_id, name in ((AID, "ayudas.pdf"), (GROUPS, "grupos.pdf")):
        await documents.add(
            Document(id=document_id, filename=name, status=DocumentStatus.INDEXED, uploaded_at=utc_now(), storage_path=name)
        )
    verification = FakeVerificationStrategyPort(answer)
    vector_store = FakeVectorStorePort()
    use_case = AnswerStudentQueryUseCase(
        embedding_port=FakeEmbeddingPort(),
        vector_store_port=vector_store,
        verification_port=verification,
        conversation_repository=InMemoryConversationRepository(),
        document_repository=documents,
        intent_classifier=RuleBasedIntentClassifier(),
        retriever=KnowledgeRetriever(FakeEmbeddingPort(), vector_store, index),
        context_assembler=ContextAssembler(catalog=index),
        corpus_catalog=index,
    )
    return use_case, verification


async def _ask(use_case: AnswerStudentQueryUseCase, question: str, user_id=None):
    return await use_case.execute(AnswerQueryRequest(user_id=user_id or new_id(), question=question))


@pytest.mark.asyncio
async def test_document_overview_is_answered_from_the_catalog_without_calling_the_llm() -> None:
    use_case, verification = await _build()
    response = await _ask(use_case, "¿De qué trata el reglamento de ayudas financieras?")
    assert verification.received_questions == []  # cero tokens
    assert "Según su Artículo 1" in response.answer_text
    assert response.is_grounded is True
    assert response.sources[0].document_title == "Reglamento de ayudas financieras"


@pytest.mark.asyncio
async def test_this_document_resolves_to_the_one_cited_in_the_previous_turn() -> None:
    use_case, _ = await _build()
    user_id = new_id()
    await _ask(use_case, "¿Dónde habla sobre elecciones?", user_id)
    response = await _ask(use_case, "¿Cuáles son los capítulos de este reglamento?", user_id)
    assert "Reglamento de grupos estudiantiles" in response.answer_text


@pytest.mark.asyncio
async def test_locating_a_topic_cites_articles_and_pages() -> None:
    use_case, verification = await _build()
    response = await _ask(use_case, "¿Qué artículos hablan de la beca?")
    assert verification.received_questions == []
    assert "Capítulo IV · Artículo 17. Cobertura (pág. 9)" in response.answer_text
    assert {source.page_number for source in response.sources} >= {9, 11}


@pytest.mark.asyncio
async def test_single_word_topic_gets_the_topic_overview_instead_of_an_index() -> None:
    # Fase 10: «beca» a secas se responde como lo haría un asesor, con el panorama
    # del tema; antes devolvía un índice de apartados.
    use_case, verification = await _build()
    await _ask(use_case, "beca")
    assert len(verification.received_questions) == 1
    assert verification.received_style_directives[-1] == ResponseStyle.OVERVIEW.directive


@pytest.mark.asyncio
async def test_only_the_passages_the_model_relied_on_are_cited() -> None:
    use_case, _ = await _build(
        VerifiedAnswer(
            answer_text="El Artículo 17 establece que la beca cubre hasta el 50%.",
            is_grounded=True,
            confidence=VerificationConfidence.HIGH,
            cited_fragments=(1,),
        )
    )
    response = await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?")
    assert len(response.sources) == 1
    assert response.sources[0].section == "Capítulo IV · Artículo 17. Cobertura"
    assert response.sources[0].page_number == 9


@pytest.mark.asyncio
async def test_partial_coverage_is_shown_with_capped_confidence_and_no_generic_caveat() -> None:
    use_case, _ = await _build(
        VerifiedAnswer(
            answer_text="La beca cubre hasta el 50%. La fecha de solicitud no está establecida en la normativa.",
            is_grounded=True,
            confidence=VerificationConfidence.HIGH,
            coverage=AnswerCoverage.PARTIAL,
        )
    )
    response = await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?")
    assert response.is_grounded is True
    assert response.confidence is VerificationConfidence.MEDIUM
    assert "matices" not in response.answer_text


@pytest.mark.asyncio
async def test_abstention_points_to_the_nearest_regulation() -> None:
    use_case, _ = await _build(
        VerifiedAnswer(answer_text="-", is_grounded=False, confidence=VerificationConfidence.LOW)
    )
    response = await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?")
    # La abstención nombra el tema y el aspecto entendidos y dice qué sí trata la
    # normativa, en lugar de un texto genérico.
    assert response.answer_text.startswith("No encontré en el ")
    assert "una disposición que establezca la cobertura de las becas y ayudas financieras." in response.answer_text
    assert NOT_GROUNDED_MESSAGE not in response.answer_text
    assert "Sí describe las penalizaciones" in response.answer_text
    # Deja escrita la siguiente pregunta útil.
    assert "seguimos con las penalizaciones: por ejemplo, «" in response.answer_text
    assert response.sources == ()


@pytest.mark.asyncio
async def test_out_of_domain_question_never_reaches_the_llm() -> None:
    use_case, verification = await _build()
    response = await _ask(use_case, "¿Cómo preparo un pastel de chocolate con vainilla?")
    assert response.is_grounded is False
    assert verification.received_questions == []


@pytest.mark.asyncio
async def test_multi_part_questions_request_a_sectioned_answer() -> None:
    use_case, verification = await _build()
    await _ask(use_case, "¿Cuánto cubre la beca y a qué hora son las elecciones?")
    directive = verification.received_style_directives[-1]
    assert directive is not None and "varias preguntas" in directive


# --- Capa de inteligencia de recuperación (conversación) ---------------------------------


@pytest.mark.asyncio
async def test_follow_up_keeps_the_literal_question_and_adds_the_interpretation() -> None:
    use_case, verification = await _build()
    user_id = new_id()
    await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?", user_id)
    await _ask(use_case, "¿Y qué penalizaciones tiene?", user_id)
    question = verification.received_questions[-1]
    # Lo que escribió el estudiante llega intacto; la interpretación lo acompaña.
    assert question.startswith("¿Y qué penalizaciones tiene?")
    assert "se refiere a las becas y ayudas financieras" in question


@pytest.mark.asyncio
async def test_single_word_aspect_after_a_topic_is_answered_not_disambiguated() -> None:
    use_case, verification = await _build()
    user_id = new_id()
    await _ask(use_case, "beca", user_id)
    await _ask(use_case, "Penalizaciones", user_id)
    # Ambos llegan al modelo como consultas fundamentadas; la segunda, dentro del tema.
    assert len(verification.received_questions) == 2
    assert verification.received_questions[-1].startswith("Penalizaciones")


@pytest.mark.asyncio
async def test_greeting_again_offers_to_resume_the_active_topic_and_continuemos_recaps() -> None:
    use_case, _ = await _build()
    user_id = new_id()
    await _ask(use_case, "Hola", user_id)
    await _ask(use_case, "beca", user_id)
    await _ask(use_case, "Gracias", user_id)
    greeting = await _ask(use_case, "Hola", user_id)
    assert "¿Seguimos con las becas y ayudas financieras" in greeting.answer_text
    resume = await _ask(use_case, "Continuemos", user_id)
    assert resume.answer_text.startswith("Claro, sigamos con las becas y ayudas financieras.")


@pytest.mark.asyncio
async def test_the_current_message_is_never_read_as_the_previous_one() -> None:
    # Regresión: el repositorio en memoria devuelve la lista viva de mensajes; sin
    # copiarla, la pregunta actual pasaba por «la anterior» y se duplicaba.
    use_case, verification = await _build()
    user_id = new_id()
    await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?", user_id)
    await _ask(use_case, "¿Cuánto cubre esa?", user_id)
    assert verification.received_questions[-1].count("¿Cuánto cubre esa?") == 1


@pytest.mark.asyncio
async def test_without_the_conversation_layer_the_previous_behaviour_is_kept() -> None:
    use_case, verification = await _build()
    use_case._conversation_intelligence = False
    user_id = new_id()
    await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?", user_id)
    await _ask(use_case, "¿y cuánto cubre esa?", user_id)
    assert "se refiere a" not in verification.received_questions[-1]


@pytest.mark.asyncio
async def test_a_generation_failure_reaches_the_student_as_a_natural_message() -> None:
    from app.application.use_cases.answer_student_query import GENERATION_FAILED_MESSAGE
    from app.shared.exceptions.domain_errors import LLMGenerationError

    use_case, verification = await _build()

    async def failing(*_args, **_kwargs):
        raise LLMGenerationError("La respuesta del modelo se truncó al alcanzar max_tokens=2048")

    verification.answer = failing  # type: ignore[method-assign]
    response = await _ask(use_case, "¿Cuánto cubre la beca de la colegiatura?")
    assert response.answer_text == GENERATION_FAILED_MESSAGE
    assert response.is_grounded is False and response.sources == ()
