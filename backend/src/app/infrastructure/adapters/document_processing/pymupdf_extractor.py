from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from app.domain.ports.document_text_extractor_port import DocumentTextExtractorPort
from app.shared.exceptions.domain_errors import DocumentProcessingError


class PyMuPDFExtractorAdapter(DocumentTextExtractorPort):
    """Extracts raw text from PDF files using PyMuPDF (FR-01)."""

    def extract_text(self, file_path: Path) -> str:
        if not file_path.exists():
            raise DocumentProcessingError(f"El archivo '{file_path}' no existe")

        try:
            with fitz.open(file_path) as pdf:
                pages_text = [page.get_text() for page in pdf]
        except Exception as exc:
            raise DocumentProcessingError(
                f"No fue posible extraer texto de '{file_path.name}': {exc}"
            ) from exc

        full_text = "\n".join(pages_text)
        if not full_text.strip():
            raise DocumentProcessingError(
                f"'{file_path.name}' no contiene texto extraíble (¿es un PDF escaneado sin OCR?)"
            )
        return full_text
