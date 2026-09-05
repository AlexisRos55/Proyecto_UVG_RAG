from __future__ import annotations

import asyncio
from uuid import UUID

from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.shared.exceptions.domain_errors import NotFoundError


class ManageDocumentUseCase:
    """Deletes an administered document and its indexed chunks (FR-17, EPIC-7)."""

    def __init__(
        self,
        document_repository: DocumentRepositoryPort,
        vector_store_port: VectorStorePort,
    ) -> None:
        self._document_repository = document_repository
        self._vector_store_port = vector_store_port

    async def delete(self, document_id: UUID) -> None:
        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"No existe un documento con id {document_id}")

        await asyncio.to_thread(self._vector_store_port.delete_by_document_id, document_id)
        await self._document_repository.delete(document_id)
