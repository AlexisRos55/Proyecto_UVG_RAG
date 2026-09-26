from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.value_objects.section_anchor import SectionAnchor
from app.infrastructure.adapters.document_processing.structure_parser import StructuralUnit

# Corte preferente: fin de oración o de inciso. Nunca a mitad de palabra.
_SEGMENT_BOUNDARY = re.compile(r"(?<=[.;:!?])\s+|\n")


@dataclass(frozen=True, slots=True)
class StructuralPiece:
    anchor: SectionAnchor
    text: str


class StructuralChunkingService:
    """Fragmenta respetando la estructura: un artículo es la unidad natural.

    Reglas, en este orden:

    1. Una unidad que cabe en `max_chars` se emite entera: el fragmento coincide
       con un artículo y su cita es exacta.
    2. Unidades muy cortas y contiguas del mismo capítulo se agrupan («Artículo
       7» de una línea junto al 8), para no generar vectores de diez palabras
       que casi nunca ganan una búsqueda y que desperdician posiciones del Top-K.
    3. Una unidad más larga se parte por oraciones con solapamiento de
       `overlap` caracteres, que es exactamente la regla de FR-03 aplicada
       dentro de cada artículo en lugar de sobre el documento entero.

    `max_chars` por defecto (600) no es arbitrario: all-MiniLM-L6-v2 trunca a
    256 subpalabras y el español rinde ≈3 caracteres por subpalabra en su
    vocabulario inglés. Con 1000 caracteres, el 94 % de los fragmentos del corpus
    real se truncaba: la cola de cada fragmento nunca llegaba al vector.
    """

    def __init__(self, max_chars: int = 600, overlap: int = 100) -> None:
        if max_chars <= overlap:
            raise ValueError("max_chars debe ser mayor que overlap")
        self._max_chars = max_chars
        self._overlap = overlap
        self._small = max_chars // 3

    def split(self, units: list[StructuralUnit]) -> list[StructuralPiece]:
        pieces: list[StructuralPiece] = []
        pending: StructuralUnit | None = None

        for unit in units:
            if pending is not None and self._should_merge(pending, unit):
                pending = self._merge(pending, unit)
                continue
            if pending is not None:
                pieces.extend(self._emit(pending))
            pending = unit
        if pending is not None:
            pieces.extend(self._emit(pending))
        return pieces

    def _should_merge(self, left: StructuralUnit, right: StructuralUnit) -> bool:
        if left.anchor.chapter != right.anchor.chapter:
            return False
        if len(left.text) + len(right.text) + 1 > self._max_chars:
            return False
        return len(left.text) < self._small or len(right.text) < self._small

    @staticmethod
    def _merge(left: StructuralUnit, right: StructuralUnit) -> StructuralUnit:
        shift = len(left.text) + 1
        return StructuralUnit(
            anchor=left.anchor.spanning(right.anchor),
            text=f"{left.text}\n{right.text}",
            line_offsets=left.line_offsets + [(offset + shift, page) for offset, page in right.line_offsets],
        )

    def _emit(self, unit: StructuralUnit) -> list[StructuralPiece]:
        if len(unit.text) <= self._max_chars:
            return [StructuralPiece(anchor=unit.anchor, text=unit.text)]

        pieces: list[StructuralPiece] = []
        for start, end in self._windows(unit.text):
            page_start, page_end = unit.pages_for_span(start, end)
            anchor = SectionAnchor(
                chapter=unit.anchor.chapter,
                section=unit.anchor.section,
                article_from=unit.anchor.article_from,
                article_to=unit.anchor.article_to,
                article_title=unit.anchor.article_title,
                page_start=page_start,
                page_end=page_end,
            )
            pieces.append(StructuralPiece(anchor=anchor, text=unit.text[start:end].strip()))
        return pieces

    def _windows(self, text: str) -> list[tuple[int, int]]:
        """Ventanas [inicio, fin) que cortan en límites de oración cuando es posible."""
        boundaries = [match.end() for match in _SEGMENT_BOUNDARY.finditer(text)] + [len(text)]
        windows: list[tuple[int, int]] = []
        start = 0
        while start < len(text):
            limit = start + self._max_chars
            if limit >= len(text):
                windows.append((start, len(text)))
                break
            candidates = [b for b in boundaries if start + self._small < b <= limit]
            end = candidates[-1] if candidates else self._word_boundary(text, limit, start)
            windows.append((start, end))
            start = self._overlap_start(text, end, start)
        return windows

    @staticmethod
    def _word_boundary(text: str, limit: int, start: int) -> int:
        space = text.rfind(" ", start + 1, limit)
        return space if space > start else limit

    def _overlap_start(self, text: str, end: int, previous_start: int) -> int:
        target = max(end - self._overlap, previous_start + 1)
        space = text.find(" ", target, end)
        return space + 1 if space != -1 else target
