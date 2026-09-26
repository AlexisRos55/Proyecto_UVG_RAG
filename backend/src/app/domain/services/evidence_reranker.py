"""Reordenamiento de la evidencia con señales estructurales y conversacionales.

La fusión por rango (RRF) combina lo que dicen los dos recuperadores sobre el
texto. Este servicio añade lo que ellos no ven:

- el artículo citado por número;
- la sección «Control de cambios» cuando se pregunta por cambios;
- la entidad en foco («Beca Despega») en el título del apartado;
- el aspecto preguntado («Requisitos», «Cobertura») en el título del artículo;
- los documentos preferidos por la conversación.

Cada señal se expresa en la unidad de RRF (lo que aportaría una lista adicional
que pusiera el fragmento en cierta posición). Así no hay pesos inventados que
calibrar: una señal «vale» lo mismo que un tercer recuperador que la respaldara.
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.entities.chunk import RetrievedChunk
from app.domain.services.query_analyzer import QueryAnalysis
from app.domain.services.rank_fusion import rank_bonus
from app.domain.services.spanish_text import analyze, fold

_CHANGE_LOG_SECTION = "control de cambios"


def structural_bonus(item: RetrievedChunk, analysis: QueryAnalysis, k: int) -> float:
    anchor = item.chunk.anchor
    bonus = 0.0
    if anchor and any(anchor.covers_article(number) for number in analysis.article_numbers):
        bonus += rank_bonus(k, 1)
    if analysis.asks_for_changes and anchor and (anchor.section or "").lower() == _CHANGE_LOG_SECTION:
        bonus += rank_bonus(k, 1)
    if item.chunk.document_id in analysis.preferred_documents:
        # Una preferencia, no un filtro: media posición de una lista adicional.
        bonus += rank_bonus(k, 1) / 2
    heading_stems = _stems(item.chunk.heading)
    if analysis.focus_terms and set(analysis.focus_terms) <= heading_stems | _stems(item.chunk.text[:200]):
        bonus += rank_bonus(k, 1)
    if (
        analysis.defining_articles
        and anchor
        and anchor.article_from is not None
        and (item.chunk.document_id, anchor.article_from) in analysis.defining_articles
    ):
        bonus += rank_bonus(k, 1)
    if analysis.aspect_title_words and anchor and anchor.article_title:
        title = fold(anchor.article_title)
        # «Penalizaciones» solo cuenta si el apartado es del tema preguntado: una
        # pregunta por sanciones electorales no debe premiar las de las becas.
        on_topic = not analysis.topic_terms or bool(
            set(analysis.topic_terms) & _stems(f"{item.chunk.heading}\n{item.chunk.text}")
        )
        if on_topic and any(word in title for word in analysis.aspect_title_words):
            bonus += rank_bonus(k, 2)
    return bonus


def is_anchored(item: RetrievedChunk, analysis: QueryAnalysis) -> bool:
    """¿La evidencia habla del foco de la conversación? Siempre cierto si no hay foco."""
    if not analysis.required_terms:
        return True
    stems = _stems(f"{item.chunk.heading}\n{item.chunk.text}")
    return bool(set(analysis.required_terms) & stems)


@lru_cache(maxsize=4096)
def _stems(text: str) -> frozenset[str]:
    return frozenset(analyze(text))
