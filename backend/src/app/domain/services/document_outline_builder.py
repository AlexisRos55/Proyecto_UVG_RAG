from __future__ import annotations

import re
from collections.abc import Sequence
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.value_objects.document_facts import DocumentFacts
from app.domain.value_objects.document_outline import (
    DocumentOutline,
    OutlineArticle,
    OutlineDivision,
)

_ARTICLE_PREFIX = re.compile(r"^art[ií]culo\s+\d+\s*[.:\-–]\s*(?:[^.:]{2,80}[.:]\s+)?", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_SUMMARY_MAX_CHARS = 420
_SUMMARY_MIN_CHARS = 120
# La ficha es metadato del documento (membrete), no parte de su estructura.
CARD_SECTION = "Ficha del documento"


class DocumentOutlineBuilder:
    """Deriva el índice de un documento a partir de sus fragmentos indexados.

    Que el índice se derive —y no se almacene aparte— garantiza que siempre
    describe exactamente lo que está indexado: si un documento se reindexa, su
    índice cambia con él, sin migraciones ni tablas que sincronizar.
    """

    @staticmethod
    def build(
        document_id: UUID,
        chunks: Sequence[Chunk],
        keywords: tuple[str, ...] = (),
        fallback_title: str = "Documento",
    ) -> DocumentOutline:
        ordered = sorted(
            (c for c in chunks if not (c.anchor and c.anchor.section == CARD_SECTION)), key=lambda c: c.position
        )
        facts = next((chunk.document for chunk in ordered if chunk.document), None) or DocumentFacts(
            title=fallback_title
        )
        return DocumentOutline(
            document_id=document_id,
            facts=facts,
            divisions=DocumentOutlineBuilder._divisions(ordered),
            summary=DocumentOutlineBuilder._summary(ordered),
            keywords=keywords,
            fragment_count=len(ordered),
            aliases=tuple(alias for alias in (facts.code,) if alias),
        )

    @staticmethod
    def _divisions(chunks: Sequence[Chunk]) -> tuple[OutlineDivision, ...]:
        has_chapters = any(chunk.anchor and chunk.anchor.chapter for chunk in chunks)
        divisions: list[OutlineDivision] = []
        current_label: str | None = None
        current_page: int | None = None
        articles: dict[int, OutlineArticle] = {}

        def close() -> None:
            if current_label is not None:
                divisions.append(
                    OutlineDivision(
                        label=current_label,
                        page_start=current_page,
                        articles=tuple(articles[number] for number in sorted(articles)),
                    )
                )

        for chunk in chunks:
            anchor = chunk.anchor
            if anchor is None:
                continue
            # En documentos con capítulos, una sección sin capítulo es de nivel
            # documento («Control de cambios»); en los que no tienen, las
            # secciones son la única división disponible.
            label = anchor.chapter or anchor.section if has_chapters else anchor.section
            if label is None:
                continue
            if label != current_label:
                close()
                current_label, current_page, articles = label, anchor.page_start, {}
            if anchor.article_from is not None:
                last = anchor.article_to or anchor.article_from
                for number in range(anchor.article_from, last + 1):
                    if number not in articles:
                        title = anchor.article_title if anchor.article_from == last else None
                        articles[number] = OutlineArticle(number=number, title=title, page=anchor.page_start)
        close()
        return tuple(divisions)

    @staticmethod
    def _summary(chunks: Sequence[Chunk]) -> str | None:
        """El objeto del documento en sus propias palabras.

        En un reglamento, el Artículo 1 declara su objeto: es el mejor resumen
        posible y no requiere generarlo. Sin articulado se usa el primer párrafo
        sustantivo.
        """
        first_article = next(
            (chunk for chunk in chunks if chunk.anchor and chunk.anchor.article_from == 1), None
        )
        candidates = [first_article] if first_article else []
        candidates += [chunk for chunk in chunks if len(chunk.text) >= _SUMMARY_MIN_CHARS]
        for chunk in candidates:
            text = _ARTICLE_PREFIX.sub("", " ".join(chunk.text.split()))
            if len(text) >= 40:
                return DocumentOutlineBuilder._trim(text)
        return None

    @staticmethod
    def _trim(text: str) -> str:
        if len(text) <= _SUMMARY_MAX_CHARS:
            return text
        kept = ""
        for sentence in _SENTENCE_END.split(text):
            if len(kept) + len(sentence) > _SUMMARY_MAX_CHARS:
                break
            kept = f"{kept} {sentence}".strip()
        return kept or text[:_SUMMARY_MAX_CHARS].rsplit(" ", 1)[0] + "…"
