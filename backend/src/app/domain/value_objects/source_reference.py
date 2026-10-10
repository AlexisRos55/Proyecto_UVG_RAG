from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.value_objects.section_anchor import SectionAnchor


@dataclass(frozen=True, slots=True)
class SourceReference:
    """A document location cited as grounding for an answer (explainability, FR-08/FR-10).

    `document_name` keeps its original meaning (the stored filename) so every
    existing consumer keeps working. Since ADR-0014 a reference can also say
    *where* in the document the support is: `document_title` is the title the
    document declares, `section` the structural path («Capítulo IV · Artículo
    18. Condiciones») and `page_number`/`page_end` the PDF pages. All of them
    are optional: a reference to a fragment indexed before structure-aware
    ingestion simply cites the document, as before.
    """

    document_name: str
    page_number: int | None = None
    document_id: UUID | None = None
    document_title: str | None = None
    section: str | None = None
    page_end: int | None = None

    @classmethod
    def at(
        cls,
        document_name: str,
        document_id: UUID | None,
        document_title: str | None,
        anchor: SectionAnchor | None,
    ) -> SourceReference:
        return cls(
            document_name=document_name,
            page_number=anchor.page_start if anchor else None,
            document_id=document_id,
            document_title=document_title,
            section=anchor.citation_label if anchor else None,
            page_end=anchor.page_end if anchor and anchor.page_end != anchor.page_start else None,
        )

    @property
    def dedup_key(self) -> tuple[str, str, int | None]:
        return ((self.document_title or self.document_name).casefold(), self.section or "", self.page_number)

    def to_record(self) -> dict[str, object]:
        return {
            "document_name": self.document_name,
            "page_number": self.page_number,
            "document_id": str(self.document_id) if self.document_id else None,
            "document_title": self.document_title,
            "section": self.section,
            "page_end": self.page_end,
        }

    @classmethod
    def from_record(cls, record: dict[str, object]) -> SourceReference:
        raw_id = record.get("document_id")
        page = record.get("page_number")
        page_end = record.get("page_end")
        return cls(
            document_name=str(record.get("document_name") or ""),
            page_number=int(str(page)) if page is not None else None,
            document_id=UUID(str(raw_id)) if raw_id else None,
            document_title=str(record["document_title"]) if record.get("document_title") else None,
            section=str(record["section"]) if record.get("section") else None,
            page_end=int(str(page_end)) if page_end is not None else None,
        )
