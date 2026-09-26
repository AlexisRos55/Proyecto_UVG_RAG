"""Planificación de la forma de la respuesta con la evidencia ya recuperada.

`response_policy.detect_style` decide la forma a partir de la pregunta. Aquí se
afina con dos datos que solo existen después de buscar: cómo se entendió el
turno (panorama, seguimiento, «profundiza») y qué trajo la evidencia. Si se
pregunta por la cobertura de «las becas» y la evidencia viene de los artículos
de cobertura de tres programas distintos, la mejor respuesta es una por programa,
no un párrafo que los mezcle.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.chunk import RetrievedChunk
from app.domain.value_objects.conversation_state import TurnInterpretation, TurnMode
from app.domain.value_objects.response_plan import ResponseStyle

_OPEN_STYLES = frozenset({ResponseStyle.UNSPECIFIED, ResponseStyle.DIRECT, ResponseStyle.LIST})
_COMPARABLE_ASPECTS = frozenset({"cobertura", "requisitos", "condiciones", "plazo", "duracion", "consecuencias"})
_MIN_DISTINCT_UNITS = 3


def plan_style(
    style: ResponseStyle, turn: TurnInterpretation | None, passages: Sequence[RetrievedChunk]
) -> ResponseStyle:
    if turn is None:
        return style
    if turn.mode is TurnMode.DEEPEN:
        if turn.simpler:
            return ResponseStyle.SIMPLER
        return ResponseStyle.EXAMPLE if turn.wants_example else ResponseStyle.EXPLANATION
    if turn.is_overview and style in _OPEN_STYLES:
        return ResponseStyle.OVERVIEW
    if (
        style in _OPEN_STYLES
        and turn.aspect in _COMPARABLE_ASPECTS
        and turn.entity is None
        and _distinct_units(passages) >= _MIN_DISTINCT_UNITS
    ):
        return ResponseStyle.PER_ITEM
    if style in _OPEN_STYLES and turn.aspect == "consecuencias":
        return ResponseStyle.CONSEQUENCES
    return style


def _distinct_units(passages: Sequence[RetrievedChunk]) -> int:
    """Artículos distintos del mismo tipo (p. ej. «Cobertura» en tres capítulos)."""
    return len(
        {
            (p.chunk.document_id, p.chunk.anchor.article_from)
            for p in passages
            if p.chunk.anchor and p.chunk.anchor.article_from is not None
        }
    )
