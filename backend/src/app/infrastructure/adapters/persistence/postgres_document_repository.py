from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document, DocumentStatus
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.infrastructure.adapters.persistence.orm_models import DocumentModel
from app.shared.kernel.clock import utc_now


class PostgresDocumentRepository(DocumentRepositoryPort):
    """SQLAlchemy-backed implementation of DocumentRepositoryPort (ADR-0003, EPIC-7)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        model = DocumentModel(
            id=document.id,
            filename=document.filename,
            status=document.status.value,
            uploaded_at=document.uploaded_at,
            storage_path=document.storage_path,
            indexed_at=document.indexed_at,
            error_message=document.error_message,
        )
        self._session.add(model)
        await self._session.flush()

    async def update_status(
        self, document_id: UUID, status: DocumentStatus, error_message: str | None = None
    ) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model is None:
            return
        model.status = status.value
        model.error_message = error_message
        if status is DocumentStatus.INDEXED:
            model.indexed_at = utc_now()
        await self._session.flush()

    async def get_by_id(self, document_id: UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return self._to_entity(model) if model is not None else None

    async def list_all(self) -> list[Document]:
        statement = select(DocumentModel).order_by(DocumentModel.uploaded_at.desc())
        models = (await self._session.execute(statement)).scalars().all()
        return [self._to_entity(model) for model in models]

    async def delete(self, document_id: UUID) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    @staticmethod
    def _to_entity(model: DocumentModel) -> Document:
        return Document(
            id=model.id,
            filename=model.filename,
            status=DocumentStatus(model.status),
            uploaded_at=model.uploaded_at,
            storage_path=model.storage_path,
            indexed_at=model.indexed_at,
            error_message=model.error_message,
        )
