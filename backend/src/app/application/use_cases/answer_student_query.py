from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from uuid import UUID

from loguru import logger

from app.application.dto.chat_dto import AnswerQueryRequest, AnswerQueryResponse
from app.domain.entities.chunk import RetrievedChunk
from app.domain.entities.message import Message, MessageRole
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.intent_classifier_port import IntentClassifierPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.services import response_policy
from app.domain.services.local_skill_catalog import LocalSkillCatalog
from app.domain.services.message_sanitizer import MessageSanitizer, SanitizedMessage
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent, IntentClassification
from app.domain.value_objects.response_plan import ResponsePlan, SkillName
from app.domain.value_objects.source_reference import SourceReference
from app.domain.value_objects.verified_answer import VerificationConfidence
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

# Las dos abstenciones son situaciones distintas y la acción útil del estudiante
# también: ante la primera conviene reformular; ante la segunda, el dato
# probablemente no está en el corpus. Antes ambas compartían un único texto.
NO_RETRIEVAL_MESSAGE = (
    "No encontré normativa oficial que hable de eso.\n\n"
    "Puede que el tema no esté cubierto por los reglamentos que manejo, o que con otras "
    "palabras sí lo encuentre. Intenta ser más específico: por ejemplo, en lugar de "
    "«becas», «requisitos de la beca de excelencia académica»."
)

NOT_GROUNDED_MESSAGE = (
    "Hay normativa relacionada con tu consulta, pero no dice lo suficiente como para que "
    "te lo confirme.\n\n"
    "Prefiero no darte un dato que pueda estar equivocado. Para algo así conviene "
    "confirmarlo directamente con la oficina que lleva el tema en el campus."
)

# Se conserva el nombre anterior: `scripts/evaluate.py` y las pruebas existentes
# lo importan, y ADR-0011 exige que las adiciones sean aditivas.
NO_INFORMATION_MESSAGE = NO_RETRIEVAL_MESSAGE

_STRUGGLING_HINT = (
    "\n\nSi seguimos sin dar con ello, puede que convenga preguntarlo directamente en el "
    "campus: a veces el detalle que buscas vive en un procedimiento interno y no en el "
    "reglamento."
)

# Matiz por nivel de confianza autoinformada. La señal ya se calculaba en cada consulta
# y se descartaba: no se inventa una métrica nueva, se empieza a usar la que ya se paga.
# Es autoinformada por el modelo, no una probabilidad calibrada — de ahí que el texto
# hable de "la normativa" y no de un porcentaje de certeza.
#
# La confianza alta no lleva matiz: añadir una coletilla a cada respuesta correcta la
# convertiría en ruido y le quitaría fuerza justo cuando sí importa.
_CONFIDENCE_CAVEATS = {
    VerificationConfidence.MEDIUM: (
        "\n\nLa normativa cubre tu consulta, aunque con matices. Si vas a tomar una "
        "decisión con esto, confirma los detalles en el campus."
    ),
    VerificationConfidence.LOW: (
        "\n\nEn este punto la normativa es parcial y prefiero que lo verifiques antes de "
        "actuar: consulta directamente con la oficina que lleva el tema."
    ),
}


class AnswerStudentQueryUseCase:
    """Orchestrates FR-06 to FR-10 and FR-14: retrieve, verify, answer, persist.

    Depends only on ports (Dependency Inversion, ADR-0001). Does not depend on
    LLMPort directly: verification (including the underlying LLM call) is fully
    delegated to VerificationStrategyPort (ADR-0005).

    Desde la capa de agencia, además orquesta la deliberación previa: sanea,
    clasifica la intención y decide qué habilidad ejecutar. Toda esa deliberación
    es determinista y ocurre **antes** de la única llamada generativa, por lo que
    el coste marginal del agente es cero tokens (ADR-0005, NFR-02, US-2.2).

    `intent_classifier` es opcional para que los constructores existentes
    —incluido el de `scripts/evaluate.py`— sigan funcionando sin cambios; sin él,
    el caso de uso se comporta exactamente como antes.
    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_store_port: VectorStorePort,
        verification_port: VerificationStrategyPort,
        conversation_repository: ConversationRepositoryPort,
        document_repository: DocumentRepositoryPort,
        top_k: int = 10,
        min_similarity_threshold: float = 0.35,
        intent_classifier: IntentClassifierPort | None = None,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_store_port = vector_store_port
        self._verification_port = verification_port
        self._conversation_repository = conversation_repository
        self._document_repository = document_repository
        self._top_k = top_k
        self._min_similarity_threshold = min_similarity_threshold
        self._intent_classifier = intent_classifier

    async def execute(self, request: AnswerQueryRequest) -> AnswerQueryResponse:
        started_at = time.perf_counter()
        logger.info("Pregunta recibida: '{}'", request.question)

        conversation = await self._conversation_repository.get_or_create_active_conversation(
            request.user_id
        )

        # E0 · Saneamiento. Cumple NFR-04: hasta ahora la pregunta se interpolaba
        # cruda en el prompt sin ninguna validación más allá de la longitud.
        sanitized = MessageSanitizer.sanitize(request.question)

        # El historial se lee ANTES de registrar el turno actual, y vía `get_history`
        # porque `get_or_create_active_conversation` devuelve la conversación sin
        # mensajes por rendimiento. Se evita así añadir un método al puerto.
        history = await self._load_history(request.user_id, conversation.id)

        student_message = Message(
            id=new_id(),
            conversation_id=conversation.id,
            role=MessageRole.STUDENT,
            content=request.question,
            created_at=utc_now(),
        )
        await self._conversation_repository.add_message(conversation.id, student_message)

        plan, context = self._deliberate(sanitized, history)

        # E3a · Habilidad local: se resuelve sin recuperación ni modelo, y por
        # construcción nunca lleva fuentes adjuntas.
        if plan.is_local:
            return await self._answer_locally(
                plan=plan,
                context=context,
                sanitized=sanitized,
                conversation_id=conversation.id,
                started_at=started_at,
            )

        query = plan.resolved_query or sanitized.safe_for_prompt

        retrieval_started_at = time.perf_counter()
        relevant_chunks = await self._retrieve_relevant_chunks(query)
        retrieval_seconds = time.perf_counter() - retrieval_started_at

        if not relevant_chunks:
            logger.info(
                "Sin contexto relevante (conversation_id={}, retrieval={:.2f}s); el asistente se abstiene.",
                conversation.id,
                retrieval_seconds,
            )
            return await self._persist_and_build_response(
                conversation_id=conversation.id,
                answer_text=self._abstention_text(NO_RETRIEVAL_MESSAGE, context),
                is_grounded=False,
                confidence=VerificationConfidence.LOW,
                source_chunk_ids=(),
                sources=(),
                started_at=started_at,
                retrieval_seconds=retrieval_seconds,
            )

        generation_started_at = time.perf_counter()
        verified_answer = await self._verification_port.answer(
            query, relevant_chunks, plan.style.directive
        )
        generation_seconds = time.perf_counter() - generation_started_at

        if not verified_answer.is_grounded:
            logger.info(
                "Verificación marcó la respuesta como no fundamentada (conversation_id={}); el asistente se abstiene.",
                conversation.id,
            )
            return await self._persist_and_build_response(
                conversation_id=conversation.id,
                answer_text=self._abstention_text(NOT_GROUNDED_MESSAGE, context),
                is_grounded=False,
                confidence=verified_answer.confidence,
                source_chunk_ids=(),
                sources=(),
                started_at=started_at,
                retrieval_seconds=retrieval_seconds,
                generation_seconds=generation_seconds,
            )

        sources = await self._resolve_sources(relevant_chunks)

        return await self._persist_and_build_response(
            conversation_id=conversation.id,
            answer_text=verified_answer.answer_text + _CONFIDENCE_CAVEATS.get(verified_answer.confidence, ""),
            is_grounded=True,
            confidence=verified_answer.confidence,
            source_chunk_ids=tuple(rc.chunk.id for rc in relevant_chunks),
            sources=sources,
            started_at=started_at,
            retrieval_seconds=retrieval_seconds,
            generation_seconds=generation_seconds,
        )

    async def _load_history(self, user_id: UUID, conversation_id: UUID) -> Sequence[Message]:
        """Mensajes de la conversación activa, para derivar el contexto de sesión.

        Sin clasificador no hay deliberación, así que no se paga la consulta: el
        comportamiento y el coste quedan idénticos a los de antes del agente.
        """
        if self._intent_classifier is None:
            return ()
        conversations = await self._conversation_repository.get_history(user_id)
        for candidate in conversations:
            if candidate.id == conversation_id:
                return candidate.messages
        return ()

    def _deliberate(
        self, sanitized: SanitizedMessage, history: Sequence[Message]
    ) -> tuple[ResponsePlan, ConversationContext]:
        """E1 + E2: comprensión y política. Determinista y sin coste."""
        context = ConversationContext.from_messages(history)

        if self._intent_classifier is None:
            # Sin clasificador el caso de uso conserva su comportamiento original.
            return (
                ResponsePlan(
                    skill=SkillName.GROUNDED_ANSWER,
                    intent=ConversationIntent.INSTITUTIONAL_QUERY,
                    resolved_query=sanitized.safe_for_prompt,
                ),
                context,
            )

        if sanitized.has_injection_markers:
            classification = IntentClassification(
                ConversationIntent.PROMPT_INJECTION, 1.0, "sanitizer"
            )
        else:
            classification = self._intent_classifier.classify(sanitized.normalized)

        plan = response_policy.decide(
            classification, context, sanitized.normalized, sanitized.safe_for_prompt
        )
        logger.info(
            "Intención '{}' (confianza {:.2f}) → habilidad '{}' [{}]",
            classification.intent.value,
            classification.confidence,
            plan.skill.value,
            "local" if plan.is_local else "fundamentada",
        )
        return plan, context

    async def _answer_locally(
        self,
        *,
        plan: ResponsePlan,
        context: ConversationContext,
        sanitized: SanitizedMessage,
        conversation_id: UUID,
        started_at: float,
    ) -> AnswerQueryResponse:
        document_names: tuple[str, ...] = ()
        if plan.skill is SkillName.DECLARE_DOCUMENT_SCOPE:
            documents = await self._document_repository.list_all()
            document_names = tuple(document.filename for document in documents)

        answer_text = LocalSkillCatalog.respond(
            plan,
            context,
            original_message=sanitized.original,
            document_names=document_names,
        )

        # `is_grounded=None` distingue "no aplica" de "no fundamentada": estas
        # respuestas no son afirmaciones sobre la normativa, así que no tiene
        # sentido evaluarlas contra documentos ni adjuntarles fuentes.
        return await self._persist_and_build_response(
            conversation_id=conversation_id,
            answer_text=answer_text,
            is_grounded=None,
            confidence=None,
            source_chunk_ids=(),
            sources=(),
            started_at=started_at,
        )

    @staticmethod
    def _abstention_text(base: str, context: ConversationContext) -> str:
        """Tras dos abstenciones seguidas, orientar es más útil que repetir."""
        return base + (_STRUGGLING_HINT if context.is_struggling else "")

    async def _retrieve_relevant_chunks(self, question: str) -> list[RetrievedChunk]:
        query_embedding = await asyncio.to_thread(self._embedding_port.embed_text, question)
        candidates = await asyncio.to_thread(
            self._vector_store_port.search, query_embedding, self._top_k
        )
        return [c for c in candidates if c.score.meets_threshold(self._min_similarity_threshold)]

    async def _resolve_sources(self, relevant_chunks: list[RetrievedChunk]) -> tuple[SourceReference, ...]:
        """Explainability (sprint 1 demo): distinct source documents behind the answer.

        Page number is not tracked yet (see SourceReference docstring) — always None here.
        """
        seen_document_ids: list[UUID] = []
        for retrieved in relevant_chunks:
            if retrieved.chunk.document_id not in seen_document_ids:
                seen_document_ids.append(retrieved.chunk.document_id)

        sources: list[SourceReference] = []
        for document_id in seen_document_ids:
            document = await self._document_repository.get_by_id(document_id)
            if document is not None:
                sources.append(SourceReference(document_name=document.filename))
        return tuple(sources)

    async def _persist_and_build_response(
        self,
        *,
        conversation_id: UUID,
        answer_text: str,
        is_grounded: bool | None,
        confidence: VerificationConfidence | None,
        source_chunk_ids: tuple[UUID, ...],
        sources: tuple[SourceReference, ...],
        started_at: float,
        retrieval_seconds: float | None = None,
        generation_seconds: float | None = None,
    ) -> AnswerQueryResponse:
        assistant_message = Message(
            id=new_id(),
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer_text,
            created_at=utc_now(),
            is_grounded=is_grounded,
            confidence=confidence,
            source_chunk_ids=source_chunk_ids,
            source_document_names=tuple(s.document_name for s in sources),
        )
        await self._conversation_repository.add_message(conversation_id, assistant_message)

        total_seconds = time.perf_counter() - started_at
        logger.info(
            "Consulta completada en {:.2f}s (retrieval={}, generation={})",
            total_seconds,
            f"{retrieval_seconds:.2f}s" if retrieval_seconds is not None else "n/a",
            f"{generation_seconds:.2f}s" if generation_seconds is not None else "n/a",
        )

        return AnswerQueryResponse(
            message_id=assistant_message.id,
            conversation_id=conversation_id,
            answer_text=answer_text,
            is_grounded=is_grounded,
            confidence=confidence,
            created_at=assistant_message.created_at,
            sources=sources,
        )
