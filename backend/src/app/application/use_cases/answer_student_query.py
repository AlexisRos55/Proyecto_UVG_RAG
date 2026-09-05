from __future__ import annotations

import asyncio
import time
from uuid import UUID

from loguru import logger

from app.application.dto.chat_dto import AnswerQueryRequest, AnswerQueryResponse
from app.domain.entities.chunk import RetrievedChunk
from app.domain.entities.message import Message, MessageRole
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.value_objects.source_reference import SourceReference
from app.domain.value_objects.verified_answer import VerificationConfidence
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

NO_INFORMATION_MESSAGE = (
    "No cuento con información suficiente en los documentos oficiales para responder "
    "esta pregunta con certeza. Te recomiendo consultar directamente con la oficina "
    "correspondiente de UVG Altiplano."
)


class AnswerStudentQueryUseCase:
    """Orchestrates FR-06 to FR-10 and FR-14: retrieve, verify, answer, persist.

    Depends only on ports (Dependency Inversion, ADR-0001). Does not depend on
    LLMPort directly: verification (including the underlying LLM call) is fully
    delegated to VerificationStrategyPort (ADR-0005).
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
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_store_port = vector_store_port
        self._verification_port = verification_port
        self._conversation_repository = conversation_repository
        self._document_repository = document_repository
        self._top_k = top_k
        self._min_similarity_threshold = min_similarity_threshold

    async def execute(self, request: AnswerQueryRequest) -> AnswerQueryResponse:
        started_at = time.perf_counter()
        logger.info("Pregunta recibida: '{}'", request.question)

        conversation = await self._conversation_repository.get_or_create_active_conversation(
            request.user_id
        )

        student_message = Message(
            id=new_id(),
            conversation_id=conversation.id,
            role=MessageRole.STUDENT,
            content=request.question,
            created_at=utc_now(),
        )
        await self._conversation_repository.add_message(conversation.id, student_message)

        retrieval_started_at = time.perf_counter()
        relevant_chunks = await self._retrieve_relevant_chunks(request.question)
        retrieval_seconds = time.perf_counter() - retrieval_started_at

        if not relevant_chunks:
            logger.info(
                "Sin contexto relevante (conversation_id={}, retrieval={:.2f}s); el asistente se abstiene.",
                conversation.id,
                retrieval_seconds,
            )
            return await self._persist_and_build_response(
                conversation_id=conversation.id,
                answer_text=NO_INFORMATION_MESSAGE,
                is_grounded=False,
                confidence=VerificationConfidence.LOW,
                source_chunk_ids=(),
                sources=(),
                started_at=started_at,
                retrieval_seconds=retrieval_seconds,
            )

        generation_started_at = time.perf_counter()
        verified_answer = await self._verification_port.answer(request.question, relevant_chunks)
        generation_seconds = time.perf_counter() - generation_started_at

        if not verified_answer.is_grounded:
            logger.info(
                "Verificación marcó la respuesta como no fundamentada (conversation_id={}); el asistente se abstiene.",
                conversation.id,
            )
            return await self._persist_and_build_response(
                conversation_id=conversation.id,
                answer_text=NO_INFORMATION_MESSAGE,
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
            answer_text=verified_answer.answer_text,
            is_grounded=True,
            confidence=verified_answer.confidence,
            source_chunk_ids=tuple(rc.chunk.id for rc in relevant_chunks),
            sources=sources,
            started_at=started_at,
            retrieval_seconds=retrieval_seconds,
            generation_seconds=generation_seconds,
        )

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
        is_grounded: bool,
        confidence: VerificationConfidence,
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
