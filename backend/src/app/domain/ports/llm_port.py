from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.value_objects.llm_completion import LLMCompletion


class LLMPort(ABC):
    """Low-level access to the LLM provider: one call in, one structured completion out.

    Intentionally generic (not RAG-specific): the caller supplies the JSON schema it
    wants back, so this port can be reused by any future adapter, including a future
    multi-call verification strategy (ADR-0005), without knowing anything about
    "verified answers". Business-level orchestration of "answer this question"
    belongs to VerificationStrategyPort, not here. Implemented by AnthropicLLMAdapter.
    """

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        output_schema_name: str,
    ) -> LLMCompletion:
        """Invoke the LLM once at temperature 0.0 (FR-09), forcing structured output that
        conforms to `output_schema` (a JSON Schema object), and return it parsed."""
