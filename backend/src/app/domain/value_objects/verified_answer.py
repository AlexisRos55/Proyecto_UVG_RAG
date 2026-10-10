from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerificationConfidence(str, Enum):
    """Self-reported confidence from the Chain-of-Verification step (ADR-0005)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnswerCoverage(str, Enum):
    """Cuánto de la pregunta responde la normativa (ADR-0014).

    Es una dimensión distinta de `is_grounded`. Fundamentación responde «¿todo
    lo que dice la respuesta está respaldado?»; cobertura, «¿la respuesta
    contesta todo lo que se preguntó?». Antes ambas se fundían en un único
    booleano, y una respuesta fiel pero incompleta —la normativa dice el
    porcentaje de la beca pero no la fecha de solicitud— se descartaba entera.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class VerifiedAnswer:
    """Output of a VerificationStrategyPort implementation.

    `is_grounded=False` signals that the answer must NOT be shown to the student
    as-is; the abstention message (FR-08) is decided by the use case, not here,
    so that the "no tengo información" wording has a single source of truth.

    `cited_fragments` are the 1-based positions, in the context given to the
    model, of the passages the answer actually relies on. They let the system
    cite the articles used instead of every document retrieved.
    """

    answer_text: str
    is_grounded: bool
    confidence: VerificationConfidence
    unsupported_claims: tuple[str, ...] = field(default_factory=tuple)
    cited_fragments: tuple[int, ...] = field(default_factory=tuple)
    coverage: AnswerCoverage = AnswerCoverage.COMPLETE
    input_tokens: int | None = None
    output_tokens: int | None = None
