from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMCompletion:
    """Raw result of a single LLMPort call, including token usage for cost tracking (NFR-02)."""

    content: dict[str, Any]
    input_tokens: int
    output_tokens: int
    model: str
