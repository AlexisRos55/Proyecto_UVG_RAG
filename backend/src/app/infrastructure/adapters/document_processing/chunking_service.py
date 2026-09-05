from __future__ import annotations


class FixedSizeChunkingService:
    """Splits cleaned text into fixed-size fragments with overlap (FR-03, ADR-0009).

    Default overlap is 100 characters, as specified by the advisor's original
    technical description. Chunk size is configurable but not part of the
    advisor's functional spec, so it is left tunable via configuration.
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 100) -> None:
        if chunk_size <= overlap:
            raise ValueError("chunk_size debe ser mayor que overlap")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        chunks: list[str] = []
        start = 0
        text_length = len(text)
        step = self._chunk_size - self._overlap

        while start < text_length:
            end = min(start + self._chunk_size, text_length)
            fragment = text[start:end].strip()
            if fragment:
                chunks.append(fragment)
            if end == text_length:
                break
            start += step

        return chunks
