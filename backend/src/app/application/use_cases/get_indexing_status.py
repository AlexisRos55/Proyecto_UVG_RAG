from __future__ import annotations

from uuid import UUID

from app.application.dto.document_dto import DocumentSummary
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.shared.exceptions.domain_errors import NotFoundError


class GetIndexingStatusUseCase:
    """Reports indexing status for administered documents (FR-19, EPIC-7)."""

    def __init__(self, document_repository: DocumentRepositoryPort) -> None:
        self._document_repository = document_repository

    async def list_all(self) -> list[DocumentSummary]:
        documents = await self._document_repository.list_all()
        return [self._to_summary(d) for d in documents]

    async def get_one(self, document_id: UUID) -> DocumentSummary:
        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"No existe un documento con id {document_id}")
        return self._to_summary(document)

    @staticmethod
    def _to_summary(document) -> DocumentSummary:
        return DocumentSummary(
            document_id=document.id,
            filename=document.filename,
            status=document.status,
            error_message=document.error_message,
        )
