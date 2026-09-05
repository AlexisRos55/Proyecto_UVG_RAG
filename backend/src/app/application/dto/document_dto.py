from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.domain.entities.document import DocumentStatus


@dataclass(frozen=True, slots=True)
class IngestDocumentRequest:
    filename: str
    file_path: Path


@dataclass(frozen=True, slots=True)
class IngestDocumentResult:
    document_id: UUID
    filename: str
    status: DocumentStatus
    chunk_count: int
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document_id: UUID
    filename: str
    status: DocumentStatus
    error_message: str | None
