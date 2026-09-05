from __future__ import annotations

from typing import Any

from app.domain.ports.llm_port import LLMPort
from app.domain.value_objects.llm_completion import LLMCompletion


class FakeLLMPort(LLMPort):
    """Test double for LLMPort: returns a pre-configured structured payload without any network call."""

    def __init__(self, response_content: dict[str, Any]) -> None:
        self._response_content = response_content
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None
        self.call_count = 0

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        output_schema_name: str,
    ) -> LLMCompletion:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return LLMCompletion(
            content=self._response_content,
            input_tokens=100,
            output_tokens=50,
            model="fake-model",
        )
