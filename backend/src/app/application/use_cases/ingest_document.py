from __future__ import annotations

from loguru import logger

from app.application.dto.document_dto import IngestDocumentRequest, IngestDocumentResult
from app.domain.entities.document import Document, DocumentStatus
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.shared.exceptions.domain_errors import DomainError
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id


class IngestDocumentUseCase:
    """Orchestrates FR-01 to FR-05 for a brand-new document: register it, then index it
    through the shared DocumentIndexingPipeline (also used by TriggerReindexUseCase, EPIC-7).
    """

    def __init__(
        self,
        document_repository: DocumentRepositoryPort,
        indexing_pipeline: DocumentIndexingPipeline,
    ) -> None:
        self._document_repository = document_repository
        self._indexing_pipeline = indexing_pipeline

    async def execute(self, request: IngestDocumentRequest) -> IngestDocumentResult:
        document = Document(
            id=new_id(),
            filename=request.filename,
            status=DocumentStatus.PENDING,
            uploaded_at=utc_now(),
            storage_path=str(request.file_path),
        )
        await self._document_repository.add(document)

        try:
            chunks = await self._indexing_pipeline.process(document.id, request.file_path)

            document.mark_indexed(utc_now())
            await self._document_repository.update_status(document.id, DocumentStatus.INDEXED)

            logger.info(
                "Documento '{}' indexado correctamente ({} fragmentos)",
                document.filename,
                len(chunks),
            )
            return IngestDocumentResult(
                document_id=document.id,
                filename=document.filename,
                status=DocumentStatus.INDEXED,
                chunk_count=len(chunks),
            )

        except DomainError as error:
            document.mark_error(str(error))
            await self._document_repository.update_status(
                document.id, DocumentStatus.ERROR, error_message=str(error)
            )
            logger.error("Fallo al indexar '{}': {}", document.filename, error)
            return IngestDocumentResult(
                document_id=document.id,
                filename=document.filename,
                status=DocumentStatus.ERROR,
                chunk_count=0,
                error_message=str(error),
            )
