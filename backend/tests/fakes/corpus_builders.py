"""Constructores de fragmentos estructurados para pruebas de la Fase 9."""

from __future__ import annotations

from uuid import UUID

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.value_objects.document_facts import DocumentFacts
from app.domain.value_objects.section_anchor import SectionAnchor
from app.domain.value_objects.similarity_score import SimilarityScore
from app.shared.kernel.ids import new_id


def chunk(
    text: str,
    *,
    document_id: UUID | None = None,
    title: str = "Reglamento de ayudas financieras",
    position: int = 0,
    chapter: str | None = None,
    section: str | None = None,
    article: int | None = None,
    article_title: str | None = None,
    page: int | None = 1,
) -> Chunk:
    return Chunk(
        id=new_id(),
        document_id=document_id or new_id(),
        text=text,
        position=position,
        anchor=SectionAnchor(
            chapter=chapter,
            section=section,
            article_from=article,
            article_title=article_title,
            page_start=page,
            page_end=page,
        ),
        document=DocumentFacts(title=title),
    )


def retrieved(item: Chunk, score: float = 0.8, coverage: float = 0.0, fused: float = 0.0) -> RetrievedChunk:
    return RetrievedChunk(chunk=item, score=SimilarityScore(score), lexical_coverage=coverage, fused_score=fused)
