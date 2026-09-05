from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceReference:
    """A document cited as grounding for an answer (explainability, FR-08/FR-10).

    `page_number` is modeled now but always None in this sprint: the ingestion pipeline
    (FR-01 to FR-03) concatenates all pages before chunking, so per-page attribution is not
    yet tracked. Kept here so adding it later is a data change, not an API/schema change.
    """

    document_name: str
    page_number: int | None = None
