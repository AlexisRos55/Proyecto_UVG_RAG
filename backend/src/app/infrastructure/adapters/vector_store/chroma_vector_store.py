from __future__ import annotations

import json
from collections.abc import Collection, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import chromadb

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.value_objects.document_facts import DocumentFacts
from app.domain.value_objects.embedding_vector import EmbeddingVector
from app.domain.value_objects.section_anchor import SectionAnchor
from app.domain.value_objects.similarity_score import SimilarityScore

_MANIFEST_FILENAME = "rag_index_manifest.json"
_PAGE_SIZE = 500


class ChromaVectorStoreAdapter(VectorStorePort):
    """Indexes and retrieves chunks in a local, persistent ChromaDB collection (FR-05, FR-06, ADR-0009).

    Since ADR-0012 each fragment also carries its structural anchor and document
    facts as metadata. ChromaDB metadata cannot hold `None`, so absent values are
    simply omitted and restored as `None`, which keeps fragments indexed before
    that change fully readable.
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "institutional_documents",
    ) -> None:
        self._persist_directory = Path(persist_directory)
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection_name = collection_name

    def upsert_chunks(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return

        embeddings: list[list[float]] = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"El chunk {chunk.id} no tiene embedding asignado")
            embeddings.append(chunk.embedding.as_list())

        self._collection.upsert(
            ids=[str(chunk.id) for chunk in chunks],
            embeddings=embeddings,  # type: ignore[arg-type]
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._to_metadata(chunk) for chunk in chunks],  # type: ignore[misc]
        )

    def search(
        self,
        query_embedding: EmbeddingVector,
        top_k: int,
        document_ids: Collection[UUID] | None = None,
    ) -> list[RetrievedChunk]:
        total = self._collection.count()
        if total == 0 or top_k <= 0:
            return []

        where: dict[str, Any] | None = None
        if document_ids is not None:
            if not document_ids:
                return []
            where = {"document_id": {"$in": [str(document_id) for document_id in document_ids]}}

        results = self._collection.query(
            query_embeddings=[cast(Sequence[float], query_embedding.as_list())],
            n_results=min(top_k, total),
            where=where,  # type: ignore[arg-type]
        )

        ids = (results.get("ids") or [[]])[0]
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        retrieved: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
            similarity_value = max(-1.0, min(1.0, 1.0 - distance))
            chunk = self._from_record(chunk_id, text, metadata)
            retrieved.append(RetrievedChunk(chunk=chunk, score=SimilarityScore(similarity_value)))

        return retrieved

    def delete_by_document_id(self, document_id: UUID) -> None:
        self._collection.delete(where={"document_id": str(document_id)})

    # --- Operaciones de infraestructura (fuera del puerto) --------------------------

    def count(self) -> int:
        return self._collection.count()

    def iter_chunks(self) -> Iterator[Chunk]:
        """Todos los fragmentos, sin embeddings: alimenta la reconstrucción del índice léxico."""
        offset = 0
        while True:
            page = self._collection.get(include=["documents", "metadatas"], limit=_PAGE_SIZE, offset=offset)
            ids = page.get("ids") or []
            if not ids:
                return
            documents = page.get("documents") or [""] * len(ids)
            metadatas = page.get("metadatas") or [{}] * len(ids)
            for chunk_id, text, metadata in zip(ids, documents, metadatas, strict=True):
                yield self._from_record(chunk_id, text, metadata)
            offset += len(ids)

    def read_index_signature(self) -> str | None:
        """Firma de la configuración con la que se construyó el índice.

        Se guarda en un archivo junto a la colección y no en sus metadatos: en
        ChromaDB, modificar los metadatos de una colección existente puede
        chocar con los parámetros HNSW fijados al crearla.
        """
        manifest = self._manifest_path()
        if not manifest.exists():
            return None
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        signature = data.get(self._collection_name)
        return str(signature) if signature is not None else None

    def write_index_signature(self, signature: str) -> None:
        manifest = self._manifest_path()
        data: dict[str, Any] = {}
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        data[self._collection_name] = signature
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _manifest_path(self) -> Path:
        return self._persist_directory / _MANIFEST_FILENAME

    # --- Serialización de metadatos --------------------------------------------------

    @staticmethod
    def _to_metadata(chunk: Chunk) -> dict[str, str | int]:
        metadata: dict[str, str | int | None] = {
            "document_id": str(chunk.document_id),
            "position": chunk.position,
        }
        if chunk.document is not None:
            metadata.update(
                doc_title=chunk.document.title,
                doc_code=chunk.document.code,
                doc_version=chunk.document.version,
                doc_effective_date=chunk.document.effective_date,
                doc_page_count=chunk.document.page_count,
            )
        if chunk.anchor is not None:
            metadata.update(
                chapter=chunk.anchor.chapter,
                section=chunk.anchor.section,
                article_from=chunk.anchor.article_from,
                article_to=chunk.anchor.article_to,
                article_title=chunk.anchor.article_title,
                page_start=chunk.anchor.page_start,
                page_end=chunk.anchor.page_end,
            )
        return {key: value for key, value in metadata.items() if value is not None}

    @staticmethod
    def _from_record(chunk_id: str, text: str | None, metadata: Mapping[str, Any] | None) -> Chunk:
        meta = dict(metadata or {})

        def text_field(key: str) -> str | None:
            value = meta.get(key)
            return str(value) if value is not None else None

        def int_field(key: str) -> int | None:
            value = meta.get(key)
            return int(value) if value is not None else None

        title = text_field("doc_title")
        document = (
            DocumentFacts(
                title=title,
                code=text_field("doc_code"),
                version=text_field("doc_version"),
                effective_date=text_field("doc_effective_date"),
                page_count=int_field("doc_page_count"),
            )
            if title
            else None
        )
        anchor_keys = ("chapter", "section", "article_from", "article_title", "page_start")
        anchor = (
            SectionAnchor(
                chapter=text_field("chapter"),
                section=text_field("section"),
                article_from=int_field("article_from"),
                article_to=int_field("article_to"),
                article_title=text_field("article_title"),
                page_start=int_field("page_start"),
                page_end=int_field("page_end"),
            )
            if any(key in meta for key in anchor_keys)
            else None
        )
        return Chunk(
            id=UUID(chunk_id),
            document_id=UUID(str(meta["document_id"])),
            text=text or "",
            position=int(meta.get("position", 0)),
            anchor=anchor,
            document=document,
        )
