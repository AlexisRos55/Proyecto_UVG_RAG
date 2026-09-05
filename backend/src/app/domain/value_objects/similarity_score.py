from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class SimilarityScore:
    """Cosine similarity between a query embedding and a chunk embedding, in [-1.0, 1.0]."""

    value: float

    def __post_init__(self) -> None:
        if not (-1.0 <= self.value <= 1.0):
            raise ValueError(f"SimilarityScore debe estar en [-1.0, 1.0], se recibió {self.value}")

    def meets_threshold(self, threshold: float) -> bool:
        return self.value >= threshold
