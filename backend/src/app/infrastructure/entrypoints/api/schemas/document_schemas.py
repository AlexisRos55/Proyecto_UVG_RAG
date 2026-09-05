from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.application.dto.document_dto import DocumentSummary, IngestDocumentResult
from app.domain.entities.document import Document, DocumentStatus


class DocumentSchema(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    uploaded_at: datetime
    indexed_at: datetime | None
    error_message: str | None

    @classmethod
    def from_entity(cls, document: Document) -> DocumentSchema:
        return cls(
            id=document.id,
            filename=document.filename,
            status=document.status,
            uploaded_at=document.uploaded_at,
            indexed_at=document.indexed_at,
            error_message=document.error_message,
        )


class DocumentSummarySchema(BaseModel):
    document_id: UUID
    filename: str
    status: DocumentStatus
    error_message: str | None

    @classmethod
    def from_dto(cls, summary: DocumentSummary) -> DocumentSummarySchema:
        return cls(
            document_id=summary.document_id,
            filename=summary.filename,
            status=summary.status,
            error_message=summary.error_message,
        )


class IngestResultSchema(BaseModel):
    document_id: UUID
    filename: str
    status: DocumentStatus
    chunk_count: int
    error_message: str | None

    @classmethod
    def from_dto(cls, result: IngestDocumentResult) -> IngestResultSchema:
        return cls(
            document_id=result.document_id,
            filename=result.filename,
            status=result.status,
            chunk_count=result.chunk_count,
            error_message=result.error_message,
        )
