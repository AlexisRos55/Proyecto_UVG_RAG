from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.ports.document_text_extractor_port import DocumentTextExtractorPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.infrastructure.adapters.document_processing.chunking_service import (
    FixedSizeChunkingService,
)
from app.infrastructure.adapters.document_processing.text_cleaner import RegexTextCleaner
from app.shared.kernel.ids import new_id


class DocumentIndexingPipeline:
    """Shared extract -> clean -> chunk -> embed -> upsert steps (FR-01 to FR-05).

    Used by both IngestDocumentUseCase (new documents) and TriggerReindexUseCase
    (EPIC-7, re-processing an existing document), so the pipeline itself is defined
    once instead of duplicated across both use cases.
    """

    def __init__(
        self,
        text_extractor: DocumentTextExtractorPort,
        embedding_port: EmbeddingPort,
        vector_store_port: VectorStorePort,
        text_cleaner: RegexTextCleaner | None = None,
        chunking_service: FixedSizeChunkingService | None = None,
    ) -> None:
        self._text_extractor = text_extractor
        self._embedding_port = embedding_port
        self._vector_store_port = vector_store_port
        self._text_cleaner = text_cleaner or RegexTextCleaner()
        self._chunking_service = chunking_service or FixedSizeChunkingService()

    async def process(self, document_id: UUID, file_path: Path) -> list[Chunk]:
        raw_text = await asyncio.to_thread(self._text_extractor.extract_text, file_path)
        clean_text = self._text_cleaner.clean(raw_text)
        fragments = self._chunking_service.split(clean_text)

        chunks = [
            Chunk(id=new_id(), document_id=document_id, text=fragment, position=position)
            for position, fragment in enumerate(fragments)
        ]

        embeddings = await asyncio.to_thread(
            self._embedding_port.embed_batch, [chunk.text for chunk in chunks]
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding

        await asyncio.to_thread(self._vector_store_port.upsert_chunks, chunks)
        return chunks
