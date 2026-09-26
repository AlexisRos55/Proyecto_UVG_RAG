from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Texto de un documento conservando sus límites de página.

    Concatenar todas las páginas antes de fragmentar —como hacía la ingesta
    original— destruye dos señales: el número de página de cada fragmento
    (necesario para citar) y la repetición de encabezados entre páginas (que es
    justamente lo que permite reconocerlos como ruido y retirarlos).
    """

    pages: tuple[str, ...]
    title: str | None = None

    @property
    def full_text(self) -> str:
        return "\n".join(self.pages)


class DocumentTextExtractorPort(ABC):
    """Extracts raw text from an official document file (FR-01). Implemented by PyMuPDFExtractorAdapter."""

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """Return the raw text content of the document at `file_path`."""

    def extract_document(self, file_path: Path) -> ExtractedDocument:
        """Texto por página y título embebido, si el formato lo ofrece.

        No es abstracto a propósito: un extractor que solo sabe devolver texto
        plano sigue siendo un sustituto válido (una sola «página», sin título) y
        ninguna implementación existente se rompe por esta ampliación.
        """
        return ExtractedDocument(pages=(self.extract_text(file_path),))
