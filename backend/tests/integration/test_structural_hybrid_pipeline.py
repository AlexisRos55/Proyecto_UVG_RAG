"""Fase 9 con tecnología real: PDF multipágina con membrete → ingesta estructural → MiniLM →
ChromaDB → índice BM25 → recuperación híbrida. No requiere PostgreSQL."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.domain.services.query_analyzer import QueryAnalyzer
from app.infrastructure.adapters.document_processing.pymupdf_extractor import (
    PyMuPDFExtractorAdapter,
)
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.infrastructure.adapters.search.synchronized_vector_store import SynchronizedVectorStore
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.config.settings import RagSettings
from app.infrastructure.rag_factory import build_indexing_pipeline, build_retriever, index_signature
from app.shared.kernel.ids import new_id

pytestmark = pytest.mark.integration

_LETTERHEAD = (
    "UNIVERSIDAD DEL VALLE DE GUATEMALA\nCódigo:\nUVG.TST.01.001\nVersión:\n3.0\n"
    "REGLAMENTO DE PRUEBA ESTUDIANTIL\nPágina {n} de 3\n"
)
_PAGES = (
    ("CAPITULO 1\nDISPOSICIONES GENERALES\nArtículo 1. Objeto. Este reglamento regula la vida\n"
    "estudiantil del campus.\nArtículo 2. Horas beca. Todo becado presta horas de servicio."),
    ("CAPITULO II\nELECCIONES\nArtículo 3. Horario. Las elecciones se realizan el jueves a las\n"
    "10:00 horas y concluyen a las 19:00 horas."),
    ("Artículo 4. Empate. En caso de empate decide el Consejo Electoral.\nControl de Cambios\n"
    "3.0 Acta 06-2025 se actualiza el horario electoral."),
)


@pytest.fixture(scope="module")
def embedding() -> SentenceTransformersEmbeddingAdapter:
    return SentenceTransformersEmbeddingAdapter()


@pytest.fixture
def regulation_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "reglamento_prueba.pdf"
    document = pymupdf.open()
    for number, body in enumerate(_PAGES, start=1):
        page = document.new_page()
        page.insert_text((72, 72), _LETTERHEAD.format(n=number) + body, fontsize=10)
    document.set_metadata({"title": ""})
    document.save(path)
    document.close()
    return path


@pytest.mark.asyncio
async def test_structural_ingestion_persists_anchors_and_hybrid_retrieval_cites_them(
    tmp_path: Path, regulation_pdf: Path, embedding: SentenceTransformersEmbeddingAdapter
) -> None:
    settings = RagSettings()
    chroma = ChromaVectorStoreAdapter(str(tmp_path / "chroma"), "phase9_it")
    index = InMemoryCorpusIndex(loader=chroma.iter_chunks, size_probe=chroma.count)
    store = SynchronizedVectorStore(chroma, index)
    document_id = new_id()

    chunks = await build_indexing_pipeline(PyMuPDFExtractorAdapter(), embedding, store, settings).process(
        document_id, regulation_pdf, display_name="reglamento_prueba.pdf"
    )

    assert all("UNIVERSIDAD DEL VALLE" not in c.text for c in chunks)
    assert chunks[0].document is not None
    assert (chunks[0].document.title, chunks[0].document.code, chunks[0].document.version) == (
        "Reglamento de prueba estudiantil",
        "UVG.TST.01.001",
        "3.0",
    )

    # Lo persistido en ChromaDB se reconstruye con su estructura: el índice léxico
    # arranca desde ahí en producción.
    restored = {c.anchor.article_from: c for c in chroma.iter_chunks() if c.anchor}
    assert restored[3].anchor.page_start == 2
    assert restored[3].anchor.chapter == "Capítulo II. Elecciones"

    retriever = build_retriever(embedding, store, index, settings)
    hits = await retriever.retrieve(QueryAnalyzer.analyze("¿A qué hora son las elecciones?", index.list_outlines()))
    assert hits and hits[0].chunk.anchor.article_from == 3

    outline = index.get_outline(document_id)
    assert outline is not None and [d.label for d in outline.divisions][-1] == "Control de Cambios"

    changes = await retriever.retrieve(QueryAnalyzer.analyze("¿Qué cambios tuvo el reglamento?", index.list_outlines()))
    assert any(hit.chunk.anchor and hit.chunk.anchor.section == "Control de Cambios" for hit in changes[:3])

    irrelevant = await retriever.retrieve(QueryAnalyzer.analyze("¿Cuál es la capital de Francia?"))
    assert irrelevant == []


def test_document_scoped_search_and_index_signature(tmp_path: Path, embedding) -> None:
    chroma = ChromaVectorStoreAdapter(str(tmp_path / "chroma"), "phase9_scope")
    assert chroma.read_index_signature() is None
    signature = index_signature(RagSettings())
    chroma.write_index_signature(signature)
    assert ChromaVectorStoreAdapter(str(tmp_path / "chroma"), "phase9_scope").read_index_signature() == signature
    # Cambiar algo que altera los vectores cambia la firma y obliga a reindexar.
    assert index_signature(RagSettings(embedding_model_name="otro-modelo")) != signature
    assert index_signature(RagSettings(chunking_strategy="fixed")) != signature


@pytest.mark.asyncio
async def test_a_real_conversation_keeps_its_topic_through_the_full_stack(
    tmp_path: Path, regulation_pdf: Path, embedding: SentenceTransformersEmbeddingAdapter
) -> None:
    """Conversación de tres turnos sobre el stack real: el seguimiento «¿y si hay
    empate?» debe llegar al modelo con el artículo de empate y con la pregunta
    literal intacta, y el tercer turno debe reconocer al Consejo Electoral."""
    from app.application.dto.chat_dto import AnswerQueryRequest
    from app.application.dto.document_dto import IngestDocumentRequest
    from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
    from app.application.use_cases.ingest_document import IngestDocumentUseCase
    from app.infrastructure.adapters.nlp.rule_based_intent_classifier import (
        RuleBasedIntentClassifier,
    )
    from app.infrastructure.rag_factory import build_context_assembler
    from tests.fakes.fake_rag_ports import FakeVerificationStrategyPort
    from tests.fakes.in_memory_conversation_repository import InMemoryConversationRepository
    from tests.fakes.in_memory_document_repository import InMemoryDocumentRepository

    settings = RagSettings()
    chroma = ChromaVectorStoreAdapter(str(tmp_path / "chroma"), "phase9_conversation")
    index = InMemoryCorpusIndex(loader=chroma.iter_chunks, size_probe=chroma.count)
    store = SynchronizedVectorStore(chroma, index)
    documents = InMemoryDocumentRepository()
    await IngestDocumentUseCase(
        documents, build_indexing_pipeline(PyMuPDFExtractorAdapter(), embedding, store, settings)
    ).execute(IngestDocumentRequest(filename="reglamento_prueba.pdf", file_path=regulation_pdf))

    verification = FakeVerificationStrategyPort()
    captured: list[list[str]] = []
    original_answer = verification.answer

    async def recording_answer(question, context_chunks, style_directive=None):
        captured.append([c.chunk.text for c in context_chunks])
        return await original_answer(question, context_chunks, style_directive)

    verification.answer = recording_answer  # type: ignore[method-assign]
    use_case = AnswerStudentQueryUseCase(
        embedding_port=embedding,
        vector_store_port=store,
        verification_port=verification,
        conversation_repository=InMemoryConversationRepository(),
        document_repository=documents,
        intent_classifier=RuleBasedIntentClassifier(),
        retriever=build_retriever(embedding, store, index, settings),
        context_assembler=build_context_assembler(index, settings),
        corpus_catalog=index,
    )
    user_id = new_id()
    await use_case.execute(AnswerQueryRequest(user_id=user_id, question="¿A qué hora son las elecciones?"))
    await use_case.execute(AnswerQueryRequest(user_id=user_id, question="¿Y si hay empate?"))

    assert verification.received_questions[-1].startswith("¿Y si hay empate?")
    assert "se refiere a las elecciones estudiantiles" in verification.received_questions[-1]
    assert any("En caso de empate decide el Consejo Electoral" in text for text in captured[-1])
