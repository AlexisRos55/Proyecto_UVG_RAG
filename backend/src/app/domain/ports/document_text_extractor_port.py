from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class DocumentTextExtractorPort(ABC):
    """Extracts raw text from an official document file (FR-01). Implemented by PyMuPDFExtractorAdapter."""

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """Return the raw text content of the document at `file_path`."""
