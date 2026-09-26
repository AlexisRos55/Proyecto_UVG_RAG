from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.ports.document_indexer_port import DocumentIndexerPort
from app.domain.ports.document_text_extractor_port import DocumentTextExtractorPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.services.document_naming import resolve_title
from app.domain.services.document_outline_builder import CARD_SECTION
from app.domain.value_objects.document_facts import DocumentFacts
from app.domain.value_objects.section_anchor import SectionAnchor
from app.infrastructure.adapters.document_processing.chunking_service import (
    FixedSizeChunkingService,
)
from app.infrastructure.adapters.document_processing.page_boilerplate import (
    PageBoilerplateRemover,
    document_card,
)
from app.infrastructure.adapters.document_processing.structural_chunking_service import (
    StructuralChunkingService,
)
from app.infrastructure.adapters.document_processing.structure_parser import DocumentStructureParser
from app.infrastructure.adapters.document_processing.table_annotations import annotate_matrix_units
from app.infrastructure.adapters.document_processing.text_cleaner import RegexTextCleaner
from app.shared.kernel.ids import new_id


class DocumentIndexingPipeline(DocumentIndexerPort):
    """Shared extract -> clean -> chunk -> embed -> upsert steps (FR-01 to FR-05).

    Used by both IngestDocumentUseCase (new documents) and TriggerReindexUseCase
    (EPIC-7, re-processing an existing document), so the pipeline itself is defined
    once instead of duplicated across both use cases.

    Two chunking strategies coexist (ADR-0012). Passing `structural_chunking`
    selects structure-aware ingestion; omitting it keeps the original fixed-size
    pipeline exactly as frozen in docs/11-reproducibility.md, so the baseline of
    the experiment can always be reproduced and compared against.
    """

    def __init__(
        self,
        text_extractor: DocumentTextExtractorPort,
        embedding_port: EmbeddingPort,
        vector_store_port: VectorStorePort,
        text_cleaner: RegexTextCleaner | None = None,
        chunking_service: FixedSizeChunkingService | None = None,
        structural_chunking: StructuralChunkingService | None = None,
    ) -> None:
        self._text_extractor = text_extractor
        self._embedding_port = embedding_port
        self._vector_store_port = vector_store_port
        self._text_cleaner = text_cleaner or RegexTextCleaner()
        self._chunking_service = chunking_service or FixedSizeChunkingService()
        self._structural_chunking = structural_chunking
        self._boilerplate = PageBoilerplateRemover()
        self._parser = DocumentStructureParser()

    @property
    def is_structural(self) -> bool:
        return self._structural_chunking is not None

    async def process(
        self, document_id: UUID, file_path: Path, display_name: str | None = None
    ) -> list[Chunk]:
        if self._structural_chunking is None:
            chunks = await self._fixed_size_chunks(document_id, file_path)
        else:
            chunks = await self._structural_chunks(
                document_id, file_path, display_name or file_path.name
            )

        embeddings = await asyncio.to_thread(
            self._embedding_port.embed_batch, [chunk.text_for_embedding for chunk in chunks]
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding

        await asyncio.to_thread(self._vector_store_port.upsert_chunks, chunks)
        return chunks

    async def _fixed_size_chunks(self, document_id: UUID, file_path: Path) -> list[Chunk]:
        raw_text = await asyncio.to_thread(self._text_extractor.extract_text, file_path)
        clean_text = self._text_cleaner.clean(raw_text)
        fragments = self._chunking_service.split(clean_text)
        return [
            Chunk(id=new_id(), document_id=document_id, text=fragment, position=position)
            for position, fragment in enumerate(fragments)
        ]

    async def _structural_chunks(
        self, document_id: UUID, file_path: Path, display_name: str
    ) -> list[Chunk]:
        assert self._structural_chunking is not None
        extracted = await asyncio.to_thread(self._text_extractor.extract_document, file_path)
        without_boilerplate = self._boilerplate.remove(extracted.pages)
        units = self._parser.parse(without_boilerplate.pages)
        pieces = self._structural_chunking.split(units)

        fields = without_boilerplate.fields
        facts = DocumentFacts(
            title=resolve_title(display_name, extracted.title, without_boilerplate.header_lines),
            code=fields.get("code"),
            version=fields.get("version"),
            effective_date=fields.get("effective_date"),
            page_count=len(extracted.pages),
        )
        pieces = [piece for piece in pieces if piece.text.strip()]
        texts = annotate_matrix_units(
            [self._text_cleaner.clean(piece.text) for piece in pieces],
            [piece.anchor.section_key for piece in pieces],
        )
        chunks = [
            Chunk(
                id=new_id(),
                document_id=document_id,
                text=text,
                position=position,
                anchor=piece.anchor,
                document=facts,
            )
            for position, (piece, text) in enumerate(zip(pieces, texts, strict=True))
        ]
        card = document_card(without_boilerplate.header_lines, facts.title)
        if card:
            chunks.append(
                Chunk(
                    id=new_id(),
                    document_id=document_id,
                    text=card,
                    position=len(pieces),
                    anchor=SectionAnchor(section=CARD_SECTION, page_start=1, page_end=1),
                    document=facts,
                )
            )
        return chunks
