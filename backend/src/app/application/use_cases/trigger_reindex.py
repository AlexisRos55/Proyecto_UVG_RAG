from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from loguru import logger

from app.application.dto.document_dto import IngestDocumentResult
from app.domain.entities.document import DocumentStatus
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.shared.exceptions.domain_errors import DocumentProcessingError, DomainError, NotFoundError
from app.shared.kernel.clock import utc_now


class TriggerReindexUseCase:
    """Re-processes an already-administered document from its stored file (FR-18, EPIC-7).

    Clears its previous chunks before re-indexing, using the same
    DocumentIndexingPipeline as IngestDocumentUseCase (no duplicated pipeline logic).
    """

    def __init__(
        self,
        document_repository: DocumentRepositoryPort,
        vector_store_port: VectorStorePort,
        indexing_pipeline: DocumentIndexingPipeline,
    ) -> None:
        self._document_repository = document_repository
        self._vector_store_port = vector_store_port
        self._indexing_pipeline = indexing_pipeline

    async def execute(self, document_id: UUID) -> IngestDocumentResult:
        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"No existe un documento con id {document_id}")

        if not Path(document.storage_path).exists():
            raise DocumentProcessingError(
                f"El archivo original de '{document.filename}' ya no está disponible en "
                f"'{document.storage_path}'; no es posible reindexar"
            )

        try:
            await asyncio.to_thread(self._vector_store_port.delete_by_document_id, document_id)
            chunks = await self._indexing_pipeline.process(document_id, Path(document.storage_path))

            document.mark_indexed(utc_now())
            await self._document_repository.update_status(document_id, DocumentStatus.INDEXED)

            logger.info("Documento '{}' reindexado ({} fragmentos)", document.filename, len(chunks))
            return IngestDocumentResult(
                document_id=document_id,
                filename=document.filename,
                status=DocumentStatus.INDEXED,
                chunk_count=len(chunks),
            )
        except DomainError as error:
            document.mark_error(str(error))
            await self._document_repository.update_status(
                document_id, DocumentStatus.ERROR, error_message=str(error)
            )
            logger.error("Fallo al reindexar '{}': {}", document.filename, error)
            return IngestDocumentResult(
                document_id=document_id,
                filename=document.filename,
                status=DocumentStatus.ERROR,
                chunk_count=0,
                error_message=str(error),
            )
