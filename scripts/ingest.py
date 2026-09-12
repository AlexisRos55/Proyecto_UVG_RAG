"""Ingesta por línea de comandos de un directorio de documentos PDF (EPIC-1).

Ejecuta el mismo DocumentIndexingPipeline que usa el panel administrativo (EPIC-7) y el
arranque automático del backend (sprint 1 demo, ver app/infrastructure/bootstrap.py), sin
pasar por el API HTTP. Útil para reindexar manualmente o preparar scripts/evaluate.py.

Requisitos previos: PostgreSQL y ChromaDB accesibles (mismas variables de entorno que el
backend: DATABASE_URL, CHROMA_PERSIST_DIR).

Uso:
    python scripts/ingest.py [directorio]   # por defecto: backend/documents
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.dto.document_dto import IngestDocumentRequest
from app.application.use_cases.ingest_document import IngestDocumentUseCase
from app.infrastructure.adapters.document_processing.chunking_service import (
    FixedSizeChunkingService,
)
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.infrastructure.adapters.document_processing.pymupdf_extractor import (
    PyMuPDFExtractorAdapter,
)
from app.infrastructure.adapters.persistence.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.config.settings import (
    get_chroma_settings,
    get_database_settings,
    get_rag_settings,
)

DEFAULT_CORPUS_DIR = Path(__file__).parent.parent / "backend" / "documents"


async def ingest_directory(directory: Path) -> None:
    pdf_paths = sorted(directory.glob("*.pdf"))
    if not pdf_paths:
        logger.warning("No se encontraron archivos PDF en {}", directory)
        return

    engine = create_async_engine(get_database_settings().database_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    rag_settings = get_rag_settings()
    pipeline = DocumentIndexingPipeline(
        text_extractor=PyMuPDFExtractorAdapter(),
        embedding_port=SentenceTransformersEmbeddingAdapter(
            model_name=rag_settings.embedding_model_name
        ),
        vector_store_port=ChromaVectorStoreAdapter(
            persist_directory=get_chroma_settings().chroma_persist_dir,
            collection_name=rag_settings.chroma_collection_name,
        ),
        chunking_service=FixedSizeChunkingService(
            chunk_size=rag_settings.chunk_size, overlap=rag_settings.chunk_overlap
        ),
    )

    async with session_factory() as session:
        use_case = IngestDocumentUseCase(
            document_repository=PostgresDocumentRepository(session),
            indexing_pipeline=pipeline,
        )

        for pdf_path in pdf_paths:
            result = await use_case.execute(
                IngestDocumentRequest(filename=pdf_path.name, file_path=pdf_path)
            )
            await session.commit()

            if result.status.value == "indexed":
                logger.info("✔ {} -> {} fragmentos indexados", pdf_path.name, result.chunk_count)
            else:
                logger.error("✘ {} -> error: {}", pdf_path.name, result.error_message)

    await engine.dispose()


if __name__ == "__main__":
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CORPUS_DIR
    asyncio.run(ingest_directory(target_dir))
