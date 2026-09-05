from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerificationConfidence(str, Enum):
    """Self-reported confidence from the Chain-of-Verification step (ADR-0005)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class VerifiedAnswer:
    """Output of a VerificationStrategyPort implementation.

    `is_grounded=False` signals that the answer must NOT be shown to the student
    as-is; the abstention message (FR-08) is decided by the use case, not here,
    so that the "no tengo información" wording has a single source of truth.
    """

    answer_text: str
    is_grounded: bool
    confidence: VerificationConfidence
    unsupported_claims: tuple[str, ...] = field(default_factory=tuple)
