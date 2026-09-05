from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import chromadb

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.value_objects.embedding_vector import EmbeddingVector
from app.domain.value_objects.similarity_score import SimilarityScore


class ChromaVectorStoreAdapter(VectorStorePort):
    """Indexes and retrieves chunks in a local, persistent ChromaDB collection (FR-05, FR-06, ADR-0009)."""

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "institutional_documents",
    ) -> None:
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return

        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"El chunk {chunk.id} no tiene embedding asignado")

        self._collection.upsert(
            ids=[str(chunk.id) for chunk in chunks],
            embeddings=[chunk.embedding.as_list() for chunk in chunks],  # type: ignore[union-attr]
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {"document_id": str(chunk.document_id), "position": chunk.position} for chunk in chunks
            ],
        )

    def search(self, query_embedding: EmbeddingVector, top_k: int) -> list[RetrievedChunk]:
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding.as_list()],
            n_results=min(top_k, self._collection.count()),
        )

        retrieved: list[RetrievedChunk] = []
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
            similarity_value = max(-1.0, min(1.0, 1.0 - distance))
            chunk = Chunk(
                id=UUID(chunk_id),
                document_id=UUID(str(metadata["document_id"])),
                text=text,
                position=int(metadata["position"]),  # type: ignore[arg-type]
            )
            retrieved.append(RetrievedChunk(chunk=chunk, score=SimilarityScore(similarity_value)))

        return retrieved

    def delete_by_document_id(self, document_id: UUID) -> None:
        self._collection.delete(where={"document_id": str(document_id)})
