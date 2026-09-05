from __future__ import annotations

from uuid import UUID

from app.domain.entities.document import Document, DocumentStatus
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.shared.kernel.clock import utc_now


class InMemoryDocumentRepository(DocumentRepositoryPort):
    """Test double for DocumentRepositoryPort (NFR-03): no database required."""

    def __init__(self) -> None:
        self._documents: dict[UUID, Document] = {}

    async def add(self, document: Document) -> None:
        self._documents[document.id] = document

    async def update_status(
        self, document_id: UUID, status: DocumentStatus, error_message: str | None = None
    ) -> None:
        document = self._documents.get(document_id)
        if document is None:
            return
        document.status = status
        document.error_message = error_message
        if status is DocumentStatus.INDEXED:
            document.indexed_at = utc_now()

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self._documents.get(document_id)

    async def list_all(self) -> list[Document]:
        return list(self._documents.values())

    async def delete(self, document_id: UUID) -> None:
        self._documents.pop(document_id, None)
