from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.domain.value_objects.document_facts import DocumentFacts
from app.domain.value_objects.embedding_vector import EmbeddingVector
from app.domain.value_objects.section_anchor import SectionAnchor
from app.domain.value_objects.similarity_score import SimilarityScore


@dataclass(slots=True)
class Chunk:
    """A fragment of a document's cleaned text (FR-03), with its embedding (FR-04).

    `anchor` and `document` are optional so that fragments indexed before
    structure-aware ingestion (ADR-0012) remain valid: they simply cite less.
    """

    id: UUID
    document_id: UUID
    text: str
    position: int
    embedding: EmbeddingVector | None = None
    anchor: SectionAnchor | None = None
    document: DocumentFacts | None = None

    @property
    def heading(self) -> str:
        """Contexto que el fragmento no dice por sí mismo: documento y ubicación.

        Un artículo que empieza «Mantener la carga completa…» no menciona que
        habla de becas; su encabezado sí. Anteponerlo al embeber es la versión
        determinista, y sin coste, de la «recuperación contextual».
        """
        parts = [self.document.title] if self.document else []
        if self.anchor and self.anchor.location_label:
            parts.append(self.anchor.location_label)
        return " — ".join(parts)

    @property
    def text_for_embedding(self) -> str:
        heading = self.heading
        return f"{heading}\n{self.text}" if heading else self.text


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned by retrieval, paired with its similarity to the query (FR-06).

    `score` keeps its original meaning (dense cosine similarity) so the FR-08
    threshold is still applied to the same quantity. Hybrid retrieval adds the
    lexical evidence and the fused rank score alongside, never in place of it.
    `source_chunk_ids` lists the indexed fragments a merged passage came from.
    """

    chunk: Chunk
    score: SimilarityScore
    lexical_coverage: float = 0.0
    fused_score: float = 0.0
    source_chunk_ids: tuple[UUID, ...] = field(default_factory=tuple)

    @property
    def origin_ids(self) -> tuple[UUID, ...]:
        return self.source_chunk_ids or (self.chunk.id,)
