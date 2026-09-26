"""Evaluación offline de CONVERSACIONES multiturno (Fase 9, capa de inteligencia de recuperación).

Recorre cada conversación de `conversation_benchmark.json` con el caso de uso real y el
pipeline de recuperación real sobre el corpus indicado. Solo el modelo generativo se
sustituye por un registrador que anota qué consulta se usó para buscar y qué pasajes
habrían llegado al modelo; no hay costo de API.

Por turno se comprueba:
    facts                 los hechos esperados están en el contexto entregado (o en la
                          respuesta determinista, si el turno no requería modelo)
    query_terms           la consulta interna contiene estos términos: la referencia
                          («esa», «¿cuánto cubre?») se resolvió al tema correcto
    forbidden_query_terms la consulta NO arrastra un tema anterior tras un cambio de tema
    answer_contains       la respuesta (local o de navegación) menciona lo esperado
    abstain               no se admitió evidencia y el modelo no fue invocado
    grounded_path         el turno llegó a la respuesta fundamentada (no fue desviado)
    no_llm                el turno se resolvió sin llamar al modelo (cortesía, continuidad)

El registrador responde con una frase que nombra los apartados recibidos, como lo haría
una respuesta real; así el estado conversacional se alimenta de forma realista.

Uso:
    python scripts/evaluate_conversations.py --corpus-dir <carpeta con los PDF> [--details]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.dto.document_dto import IngestDocumentRequest
from app.application.services.knowledge_retriever import KnowledgeRetriever
from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.application.use_cases.ingest_document import IngestDocumentUseCase
from app.domain.entities.chunk import RetrievedChunk
from app.domain.entities.conversation import Conversation
from app.domain.entities.document import Document, DocumentStatus
from app.domain.entities.message import Message
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.services.query_analyzer import QueryAnalysis
from app.domain.services.spanish_text import fold
from app.domain.value_objects.verified_answer import VerificationConfidence, VerifiedAnswer
from app.infrastructure.adapters.document_processing.pymupdf_extractor import (
    PyMuPDFExtractorAdapter,
)
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.infrastructure.adapters.search.synchronized_vector_store import SynchronizedVectorStore
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.config.settings import RagSettings
from app.infrastructure.rag_factory import (
    build_context_assembler,
    build_indexing_pipeline,
    build_retriever,
)
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

DEFAULT_BENCHMARK = Path(__file__).parent / "conversation_benchmark.json"


def _normalize(text: str) -> str:
    return " ".join(fold(text).split())


class _Documents(DocumentRepositoryPort):
    def __init__(self) -> None:
        self._items: dict = {}

    async def add(self, document: Document) -> None:
        self._items[document.id] = document

    async def update_status(self, document_id, status: DocumentStatus, error_message: str | None = None) -> None:
        self._items[document_id].status = status

    async def get_by_id(self, document_id):
        return self._items.get(document_id)

    async def list_all(self) -> list[Document]:
        return list(self._items.values())

    async def delete(self, document_id) -> None:
        self._items.pop(document_id, None)


class _Conversations(ConversationRepositoryPort):
    def __init__(self) -> None:
        self._by_user: dict = {}

    async def get_or_create_active_conversation(self, user_id) -> Conversation:
        if user_id not in self._by_user:
            self._by_user[user_id] = Conversation(id=new_id(), user_id=user_id, created_at=utc_now())
        return self._by_user[user_id]

    async def add_message(self, conversation_id, message: Message) -> None:
        for conversation in self._by_user.values():
            if conversation.id == conversation_id:
                conversation.add_message(message)

    async def get_history(self, user_id) -> list[Conversation]:
        return [self._by_user[user_id]] if user_id in self._by_user else []


class _RecordingVerification(VerificationStrategyPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[RetrievedChunk], str | None]] = []

    async def answer(self, question: str, context_chunks: Sequence[RetrievedChunk], style_directive=None):
        self.calls.append((question, list(context_chunks), style_directive))
        named = [c.chunk.anchor.article_title for c in context_chunks if c.chunk.anchor and c.chunk.anchor.article_title]
        text = "Según la normativa: " + "; ".join(dict.fromkeys(named)) if named else "Respuesta fundamentada."
        return VerifiedAnswer(
            answer_text=text,
            is_grounded=True,
            confidence=VerificationConfidence.HIGH,
            cited_fragments=tuple(range(1, len(context_chunks) + 1)),
        )


class _SpyRetriever(KnowledgeRetriever):
    """Registra la consulta interna con la que se busca en cada turno."""

    def __init__(self, inner: KnowledgeRetriever) -> None:
        self._inner = inner
        self.queries: list[str] = []

    @property
    def is_hybrid(self) -> bool:
        return self._inner.is_hybrid

    async def retrieve(self, analysis: QueryAnalysis) -> list[RetrievedChunk]:
        self.queries.append(" | ".join([analysis.text, *analysis.expansions]))
        return await self._inner.retrieve(analysis)


@dataclass
class TurnResult:
    conversation: str
    index: int
    message: str
    checks: dict[str, bool] = field(default_factory=dict)
    query: str = ""
    detail: str = ""

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


async def build_corpus(corpus_dir: Path, settings: RagSettings):
    embedding = SentenceTransformersEmbeddingAdapter(model_name=settings.embedding_model_name)
    chroma = ChromaVectorStoreAdapter(tempfile.mkdtemp(prefix="conv_eval_"), "conversation_eval")
    index = InMemoryCorpusIndex()
    store = SynchronizedVectorStore(chroma, index)
    documents = _Documents()
    ingest = IngestDocumentUseCase(documents, build_indexing_pipeline(PyMuPDFExtractorAdapter(), embedding, store, settings))
    for pdf in sorted(corpus_dir.glob("*.pdf")):
        await ingest.execute(IngestDocumentRequest(filename=pdf.name, file_path=pdf))
    return embedding, store, index, documents


def build_use_case(embedding, store, index, documents, settings: RagSettings, **extra):
    verification = _RecordingVerification()
    spy = _SpyRetriever(build_retriever(embedding, store, index, settings))
    use_case = AnswerStudentQueryUseCase(
        embedding_port=embedding,
        vector_store_port=store,
        verification_port=verification,
        conversation_repository=_Conversations(),
        document_repository=documents,
        top_k=settings.top_k,
        min_similarity_threshold=settings.min_similarity_threshold,
        intent_classifier=RuleBasedIntentClassifier(),
        retriever=spy,
        context_assembler=build_context_assembler(index, settings),
        corpus_catalog=index,
        **extra,
    )
    return use_case, verification, spy


async def run(use_case, verification, spy, conversations: list[dict]) -> list[TurnResult]:
    results: list[TurnResult] = []
    for conversation in conversations:
        user_id = new_id()
        for index, turn in enumerate(conversation["turns"]):
            calls_before, queries_before = len(verification.calls), len(spy.queries)
            response = await use_case.execute(AnswerQueryRequest(user_id=user_id, question=turn["message"]))
            called = len(verification.calls) > calls_before
            passages = verification.calls[-1][1] if called else []
            query = " || ".join(spy.queries[queries_before:])
            evidence = _normalize(" ".join([p.chunk.text for p in passages] + [response.answer_text]))
            result = TurnResult(conversation["id"], index, turn["message"], query=query)

            if turn.get("facts"):
                missing = [fact[0] for fact in turn["facts"] if not any(_normalize(alt) in evidence for alt in fact)]
                result.checks["facts"] = not missing
                result.detail += f" faltan={missing}" if missing else ""
            if turn.get("query_terms"):
                folded_query = fold(query)
                result.checks["reference"] = all(fold(term) in folded_query for term in turn["query_terms"])
            if turn.get("forbidden_query_terms"):
                folded_query = fold(query)
                result.checks["topic_switch"] = not any(fold(term) in folded_query for term in turn["forbidden_query_terms"])
            if turn.get("answer_contains"):
                answer = fold(response.answer_text)
                result.checks["answer"] = all(fold(term) in answer for term in turn["answer_contains"])
            if turn.get("abstain"):
                result.checks["abstain"] = not called and response.is_grounded is not True
            if turn.get("grounded_path"):
                result.checks["grounded_path"] = called
            if turn.get("no_llm"):
                result.checks["no_llm"] = not called
            results.append(result)
    return results


def summarize(results: list[TurnResult]) -> dict[str, float]:
    checked = [r for r in results if r.checks]
    by_kind: dict[str, list[bool]] = {}
    for result in checked:
        for kind, ok in result.checks.items():
            by_kind.setdefault(kind, []).append(ok)
    summary = {kind: sum(values) / len(values) for kind, values in sorted(by_kind.items())}
    summary["turns_passed"] = sum(r.passed for r in checked) / len(checked)
    return summary


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    settings = RagSettings()
    conversations = json.loads(args.benchmark.read_text(encoding="utf-8"))["conversations"]
    embedding, store, index, documents = await build_corpus(args.corpus_dir, settings)
    use_case, verification, spy = build_use_case(embedding, store, index, documents, settings)
    results = await run(use_case, verification, spy, conversations)

    for metric, value in summarize(results).items():
        print(f"  {metric:16} {value:6.3f}")
    if args.details:
        for result in results:
            mark = "ok " if result.passed else "FALLA"
            print(f"  [{mark}] {result.conversation}#{result.index} «{result.message}» {result.checks}{result.detail}")
            print(f"         consulta: {result.query[:160]}")
    if args.report:
        args.report.write_text(json.dumps([r.__dict__ for r in results], indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
