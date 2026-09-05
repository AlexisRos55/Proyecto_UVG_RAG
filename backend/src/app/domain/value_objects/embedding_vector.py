from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    """Immutable numeric vector produced by an EmbeddingPort implementation."""

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise ValueError("Un EmbeddingVector no puede estar vacío")

    @property
    def dimension(self) -> int:
        return len(self.values)

    def as_list(self) -> list[float]:
        return list(self.values)

    @classmethod
    def from_list(cls, values: list[float]) -> EmbeddingVector:
        return cls(values=tuple(values))
