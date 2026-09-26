from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.domain.entities.chunk import RetrievedChunk
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.lexical_search_port import LexicalHit, LexicalSearchPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.services.evidence_reranker import is_anchored, structural_bonus
from app.domain.services.query_analyzer import QueryAnalysis
from app.domain.services.rank_fusion import reciprocal_rank_fusion
from app.domain.value_objects.similarity_score import SimilarityScore


@dataclass(frozen=True, slots=True)
class RetrievalSettings:
    """Parámetros de recuperación (docs/11-reproducibility.md).

    `hybrid=False` reproduce exactamente la recuperación congelada original:
    Top-K por coseno y umbral fijo, sin fusión ni señales adicionales.
    """

    top_k: int = 10
    min_similarity: float = 0.35
    hybrid: bool = True
    candidate_pool: int = 30
    min_lexical_coverage: float = 0.5
    rrf_k: int = 60
    evidence_similarity: float = 0.55
    context_min_lexical_coverage: float = 0.25


class KnowledgeRetriever:
    """Recuperación híbrida: semántica + léxica, fusionadas por rango (ADR-0012).

    La admisión tiene dos etapas, porque responden a preguntas distintas:

    1. **¿Hay evidencia para esta consulta?** (FR-08, nivel consulta). Se exige
       evidencia *fuerte* en al menos un candidato: coseno ≥ `evidence_similarity`,
       o la mitad de la información léxica de la consulta, o el artículo citado
       por número. Si no, se devuelve una lista vacía y el asistente se abstiene
       sin gastar una llamada al modelo.
    2. **¿Qué entra al contexto?** (nivel fragmento). Una vez establecido que la
       consulta pertenece al corpus, basta evidencia *débil*: el umbral congelado
       de 0.35 o un cuarto de la información léxica.

    Medido sobre el corpus real, el umbral único anterior (0.35) no separaba
    nada: «¿Cuál es la capital de Francia?» superaba 0.35 con diez fragmentos,
    porque all-MiniLM-L6-v2 —entrenado en inglés— sitúa todo texto en español en
    la misma región del espacio. La abstención previa a la llamada nunca ocurría.
    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_store_port: VectorStorePort,
        lexical_search: LexicalSearchPort | None = None,
        settings: RetrievalSettings | None = None,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_store_port = vector_store_port
        self._lexical_search = lexical_search
        self._settings = settings or RetrievalSettings()

    @property
    def is_hybrid(self) -> bool:
        return self._settings.hybrid and self._lexical_search is not None

    async def retrieve(self, analysis: QueryAnalysis) -> list[RetrievedChunk]:
        if not self.is_hybrid:
            return await self._dense_only(analysis.text)

        queries = analysis.sub_queries if analysis.is_multi_part else (analysis.text,)
        per_query = await asyncio.gather(*(self._hybrid(query, analysis) for query in queries))
        # Cada subpregunta supera la etapa 1 por su cuenta: una parte fuera de
        # dominio no debe arrastrar a la otra ni colarse con evidencia débil.
        answered = [items for items in per_query if any(self._is_strong(item, analysis) for item in items)]
        # Top-K por subpregunta: dos preguntas en un turno siguen costando una
        # sola llamada, frente a las dos que costaría hacerlas por separado.
        return self._interleave(answered)[: self._settings.top_k * max(1, len(answered))]

    async def _dense_only(self, query: str) -> list[RetrievedChunk]:
        embedding = await asyncio.to_thread(self._embedding_port.embed_text, query)
        candidates = await asyncio.to_thread(self._vector_store_port.search, embedding, self._settings.top_k)
        return [c for c in candidates if c.score.meets_threshold(self._settings.min_similarity)]

    async def _hybrid(self, query: str, analysis: QueryAnalysis) -> list[RetrievedChunk]:
        assert self._lexical_search is not None
        settings = self._settings
        scope = analysis.target_documents or None

        embedding = await asyncio.to_thread(self._embedding_port.embed_text, query)
        dense, lexical = await asyncio.gather(
            asyncio.to_thread(self._vector_store_port.search, embedding, settings.candidate_pool, scope),
            asyncio.to_thread(
                self._lexical_search.search,
                query,
                settings.candidate_pool,
                expansions=analysis.expansions,
                document_ids=scope,
            ),
        )

        by_id: dict[UUID, RetrievedChunk] = {item.chunk.id: item for item in dense}
        coverage: dict[UUID, float] = {}
        for hit in lexical:
            coverage[hit.chunk.id] = hit.coverage
            by_id.setdefault(hit.chunk.id, self._from_lexical(hit))

        # Fusión adaptativa: un canal que no encontró evidencia fuerte para esta
        # consulta vota con la mitad de peso. Medido en el corpus real: cuando el
        # coseno máximo no supera el umbral de evidencia, el orden semántico es
        # casi aleatorio y, con peso completo, desplazaba al acierto léxico.
        dense_is_informative = bool(dense) and dense[0].score.meets_threshold(settings.evidence_similarity)
        lexical_is_informative = any(hit.coverage >= settings.min_lexical_coverage for hit in lexical)
        fused = reciprocal_rank_fusion(
            [[item.chunk.id for item in dense], [hit.chunk.id for hit in lexical]],
            k=settings.rrf_k,
            weights=[1.0 if dense_is_informative else 0.5, 1.0 if lexical_is_informative else 0.5],
        )
        for chunk_id, item in by_id.items():
            fused[chunk_id] = fused.get(chunk_id, 0.0) + structural_bonus(item, analysis, settings.rrf_k)

        admissible = [
            replace(item, lexical_coverage=coverage.get(chunk_id, 0.0), fused_score=fused[chunk_id])
            for chunk_id, item in by_id.items()
        ]
        # Con un tema nombrado o heredado, todo el contexto debe ser de ese tema: si no,
        # un solo fragmento anclado abriría la puerta a los demás («seguros» en un folleto
        # de Informática dejaba pasar artículos de grupos estudiantiles).
        admissible = [item for item in admissible if self._is_context(item, analysis) and is_anchored(item, analysis)]
        admissible.sort(key=lambda item: item.fused_score, reverse=True)
        return admissible

    def _is_strong(self, item: RetrievedChunk, analysis: QueryAnalysis) -> bool:
        # En un seguimiento, la evidencia fuerte debe además hablar del foco
        # heredado: si no, la conversación cambiaría de tema sin que nadie lo pidiera.
        return is_anchored(item, analysis) and (
            item.score.meets_threshold(self._settings.evidence_similarity)
            or item.lexical_coverage >= self._settings.min_lexical_coverage
            or self._cites_article(item, analysis)
        )

    def _is_context(self, item: RetrievedChunk, analysis: QueryAnalysis) -> bool:
        return (
            item.score.meets_threshold(self._settings.min_similarity)
            or item.lexical_coverage >= self._settings.context_min_lexical_coverage
            or self._cites_article(item, analysis)
        )

    @staticmethod
    def _cites_article(item: RetrievedChunk, analysis: QueryAnalysis) -> bool:
        anchor = item.chunk.anchor
        return bool(anchor and any(anchor.covers_article(number) for number in analysis.article_numbers))

    @staticmethod
    def _from_lexical(hit: LexicalHit) -> RetrievedChunk:
        # Sin posición en la lista semántica no hay coseno medido: 0.0 significa
        # «no evaluado por el canal semántico», y así lo trata el umbral.
        return RetrievedChunk(chunk=hit.chunk, score=SimilarityScore(0.0))

    @staticmethod
    def _interleave(per_query: Sequence[list[RetrievedChunk]]) -> list[RetrievedChunk]:
        """Turnos entre subpreguntas: cada parte aporta su mejor evidencia antes que la segunda de otra."""
        merged: list[RetrievedChunk] = []
        seen: set[UUID] = set()
        for rank in range(max((len(items) for items in per_query), default=0)):
            for items in per_query:
                if rank < len(items) and items[rank].chunk.id not in seen:
                    seen.add(items[rank].chunk.id)
                    merged.append(items[rank])
        return merged
