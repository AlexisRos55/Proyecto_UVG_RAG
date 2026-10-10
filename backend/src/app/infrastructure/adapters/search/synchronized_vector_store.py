from __future__ import annotations

from collections.abc import Collection, Sequence
from uuid import UUID

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.value_objects.embedding_vector import EmbeddingVector
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex


class SynchronizedVectorStore(VectorStorePort):
    """Decorador que mantiene el índice léxico al día con cada escritura vectorial.

    Es la razón por la que la recuperación híbrida no obligó a tocar ningún caso
    de uso de ingesta, reindexación o borrado (Open/Closed): todos siguen
    escribiendo en un `VectorStorePort`, y este decorador replica cada escritura
    en el índice en memoria. La búsqueda vectorial se delega sin cambios.
    """

    def __init__(self, inner: VectorStorePort, corpus_index: InMemoryCorpusIndex) -> None:
        self._inner = inner
        self._corpus_index = corpus_index

    def upsert_chunks(self, chunks: Sequence[Chunk]) -> None:
        self._inner.upsert_chunks(chunks)
        self._corpus_index.add(chunks)

    def search(
        self,
        query_embedding: EmbeddingVector,
        top_k: int,
        document_ids: Collection[UUID] | None = None,
    ) -> list[RetrievedChunk]:
        return self._inner.search(query_embedding, top_k, document_ids)

    def delete_by_document_id(self, document_id: UUID) -> None:
        self._inner.delete_by_document_id(document_id)
        self._corpus_index.remove_document(document_id)
