from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class DocumentStatus(str, Enum):
    """Indexing lifecycle of an administered document (FR-19)."""

    PENDING = "pending"
    INDEXED = "indexed"
    ERROR = "error"


@dataclass(slots=True)
class Document:
    """An official PDF document managed through the admin panel (EPIC-7)."""

    id: UUID
    filename: str
    status: DocumentStatus
    uploaded_at: datetime
    storage_path: str
    indexed_at: datetime | None = None
    error_message: str | None = None

    def mark_indexed(self, indexed_at: datetime) -> None:
        self.status = DocumentStatus.INDEXED
        self.indexed_at = indexed_at
        self.error_message = None

    def mark_error(self, error_message: str) -> None:
        self.status = DocumentStatus.ERROR
        self.error_message = error_message
