"""Construcción del pipeline RAG a partir de `RagSettings`, en un único lugar.

El backend, `scripts/ingest.py`, `scripts/evaluate.py` y
`scripts/evaluate_retrieval.py` usan estas funciones. Antes cada uno armaba su
propio pipeline y llegaron a divergir (el addendum técnico documenta un Top-K
distinto entre evaluación y producción); centralizarlo elimina esa clase de
error: lo que se evalúa es, por construcción, lo que se despliega.
"""

from __future__ import annotations

import hashlib
import json

from app.application.services.context_assembler import AssemblySettings, ContextAssembler
from app.application.services.knowledge_retriever import KnowledgeRetriever, RetrievalSettings
from app.domain.ports.corpus_catalog_port import CorpusCatalogPort
from app.domain.ports.document_text_extractor_port import DocumentTextExtractorPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.lexical_search_port import LexicalSearchPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.infrastructure.adapters.document_processing.chunking_service import (
    FixedSizeChunkingService,
)
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.infrastructure.adapters.document_processing.structural_chunking_service import (
    StructuralChunkingService,
)
from app.infrastructure.config.settings import RagSettings

# Se incrementa cuando cambia la forma en que se extrae o fragmenta un documento,
# aunque la configuración sea la misma: obliga a reindexar lo ya indexado.
INGESTION_ALGORITHM_VERSION = "2026-09-24.structural-v6"


def build_indexing_pipeline(
    text_extractor: DocumentTextExtractorPort,
    embedding_port: EmbeddingPort,
    vector_store_port: VectorStorePort,
    settings: RagSettings,
) -> DocumentIndexingPipeline:
    structural = (
        StructuralChunkingService(max_chars=settings.structural_chunk_size, overlap=settings.chunk_overlap)
        if settings.chunking_strategy == "structural"
        else None
    )
    return DocumentIndexingPipeline(
        text_extractor=text_extractor,
        embedding_port=embedding_port,
        vector_store_port=vector_store_port,
        chunking_service=FixedSizeChunkingService(
            chunk_size=settings.chunk_size, overlap=settings.chunk_overlap
        ),
        structural_chunking=structural,
    )


def build_retriever(
    embedding_port: EmbeddingPort,
    vector_store_port: VectorStorePort,
    lexical_search: LexicalSearchPort | None,
    settings: RagSettings,
) -> KnowledgeRetriever:
    return KnowledgeRetriever(
        embedding_port=embedding_port,
        vector_store_port=vector_store_port,
        lexical_search=lexical_search,
        settings=RetrievalSettings(
            top_k=settings.top_k,
            min_similarity=settings.min_similarity_threshold,
            hybrid=settings.retrieval_mode == "hybrid",
            candidate_pool=settings.candidate_pool,
            min_lexical_coverage=settings.min_lexical_coverage,
            rrf_k=settings.rrf_k,
            evidence_similarity=settings.evidence_similarity_threshold,
            context_min_lexical_coverage=settings.context_min_lexical_coverage,
        ),
    )


def build_context_assembler(catalog: CorpusCatalogPort | None, settings: RagSettings) -> ContextAssembler:
    return ContextAssembler(
        catalog=catalog,
        settings=AssemblySettings(
            char_budget=settings.context_char_budget,
            expand_sections_up_to=settings.section_expansion_limit,
        ),
    )


def index_signature(settings: RagSettings) -> str:
    """Huella de todo lo que determina el contenido del índice vectorial.

    Si cambia el modelo de embeddings, la estrategia o el tamaño de fragmento,
    los vectores guardados dejan de ser comparables con los de las consultas.
    El arranque compara esta huella con la del índice y reindexa si difieren,
    en lugar de mezclar en silencio dos esquemas de indexación.
    """
    relevant = {
        "algorithm": INGESTION_ALGORITHM_VERSION if settings.chunking_strategy == "structural" else "fixed-v1",
        "embedding_model": settings.embedding_model_name,
        "chunking_strategy": settings.chunking_strategy,
        "chunk_size": settings.chunk_size if settings.chunking_strategy == "fixed" else settings.structural_chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }
    digest = hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()[:16]
    return f"{relevant['chunking_strategy']}:{digest}"
