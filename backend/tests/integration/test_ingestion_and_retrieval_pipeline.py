"""End-to-end validation of EPIC-1 with real technology (no mocks): PyMuPDF extracts a real
PDF, Sentence Transformers embeds it locally, and ChromaDB indexes and retrieves it. This is
the strongest evidence that the hexagonal ports and their real adapters actually fit together.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.application.dto.document_dto import IngestDocumentRequest
from app.application.use_cases.ingest_document import IngestDocumentUseCase
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.infrastructure.adapters.document_processing.pymupdf_extractor import PyMuPDFExtractorAdapter
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from tests.fakes.in_memory_document_repository import InMemoryDocumentRepository

pytestmark = pytest.mark.integration

_SAMPLE_TEXT = (
    "Reglamento Estudiantil de UVG Altiplano\n\n"
    "Articulo 1. Reincorporacion. El estudiante que haya interrumpido sus estudios podra "
    "solicitar su reincorporacion en la oficina de registro academico, presentando su "
    "solicitud por escrito con al menos 30 dias de anticipacion al inicio del ciclo.\n\n"
    "Articulo 2. Becas. La universidad ofrece becas de excelencia academica que cubren "
    "hasta el 50% de la colegiatura, sujetas a mantener un indice academico minimo de 85 puntos.\n\n"
    "Articulo 3. Seguro estudiantil. Todo estudiante inscrito cuenta con un seguro medico "
    "basico que cubre accidentes dentro del campus durante el horario academico."
)


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "reglamento_prueba.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), _SAMPLE_TEXT, fontsize=11)
    document.save(pdf_path)
    document.close()
    return pdf_path


@pytest.fixture
def chroma_store(tmp_path: Path) -> ChromaVectorStoreAdapter:
    return ChromaVectorStoreAdapter(
        persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
    )


@pytest.fixture(scope="module")
def embedding_adapter() -> SentenceTransformersEmbeddingAdapter:
    return SentenceTransformersEmbeddingAdapter()


@pytest.mark.asyncio
async def test_ingested_document_is_retrievable_by_semantic_similarity(
    sample_pdf: Path, chroma_store: ChromaVectorStoreAdapter, embedding_adapter
) -> None:
    document_repository = InMemoryDocumentRepository()
    pipeline = DocumentIndexingPipeline(
        text_extractor=PyMuPDFExtractorAdapter(),
        embedding_port=embedding_adapter,
        vector_store_port=chroma_store,
    )
    use_case = IngestDocumentUseCase(
        document_repository=document_repository,
        indexing_pipeline=pipeline,
    )

    result = await use_case.execute(
        IngestDocumentRequest(filename="reglamento_prueba.pdf", file_path=sample_pdf)
    )

    assert result.status.value == "indexed"
    assert result.chunk_count > 0

    query_embedding = embedding_adapter.embed_text("¿Cómo solicito mi reincorporación?")
    retrieved = chroma_store.search(query_embedding, top_k=2)

    assert len(retrieved) > 0
    assert any("reincorporaci" in r.chunk.text.lower() for r in retrieved)
    assert retrieved[0].score.value > 0.3


@pytest.mark.asyncio
async def test_ingestion_of_unreadable_file_is_recorded_as_error(
    tmp_path: Path, chroma_store: ChromaVectorStoreAdapter, embedding_adapter
) -> None:
    broken_file = tmp_path / "no_es_un_pdf.pdf"
    broken_file.write_text("esto no es un PDF valido")
    document_repository = InMemoryDocumentRepository()
    pipeline = DocumentIndexingPipeline(
        text_extractor=PyMuPDFExtractorAdapter(),
        embedding_port=embedding_adapter,
        vector_store_port=chroma_store,
    )
    use_case = IngestDocumentUseCase(
        document_repository=document_repository,
        indexing_pipeline=pipeline,
    )

    result = await use_case.execute(
        IngestDocumentRequest(filename="no_es_un_pdf.pdf", file_path=broken_file)
    )

    assert result.status.value == "error"
    assert result.error_message is not None
