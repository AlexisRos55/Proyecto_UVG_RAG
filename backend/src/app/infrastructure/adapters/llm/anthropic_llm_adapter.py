from __future__ import annotations

import time
from typing import Any

import anthropic
from loguru import logger

from app.domain.ports.llm_port import LLMPort
from app.domain.value_objects.llm_completion import LLMCompletion
from app.infrastructure.config.settings import AnthropicSettings
from app.shared.exceptions.domain_errors import LLMGenerationError


class AnthropicLLMAdapter(LLMPort):
    """Talks to Claude via the official Anthropic SDK, without LangChain (ADR-0002).

    The model name is read from configuration, never hardcoded (ADR-0006).

    NOTE (FR-09): the anthropic SDK >=1.0 removed `temperature` as a typed parameter of
    `messages.create()` (verified directly against the installed package source, not
    assumed). Determinism is requested via `extra_body`, which forwards raw fields to the
    HTTP request body outside the SDK's typed surface. If the API ever rejects this field,
    it will fail loudly as an `anthropic.APIError` here, not silently ignore it.
    """

    def __init__(self, settings: AnthropicSettings) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.api_key)
        self._model = settings.model
        self._max_tokens = settings.max_tokens

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        output_schema_name: str,
    ) -> LLMCompletion:
        started_at = time.perf_counter()
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[
                    {
                        "name": output_schema_name,
                        "description": "Entrega la salida en el formato estructurado requerido.",
                        "input_schema": output_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": output_schema_name},
                extra_body={"temperature": 0.0},  # FR-09: decodificación determinista
            )
        except anthropic.APIError as exc:
            raise LLMGenerationError(f"Error al invocar el modelo de Anthropic: {exc}") from exc

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"), None
        )
        if tool_use_block is None:
            raise LLMGenerationError(
                "El modelo no devolvió una salida estructurada (tool_use) válida"
            )

        logger.info(
            "Llamada a Anthropic completada en {:.0f}ms (modelo={}, input_tokens={}, output_tokens={})",
            elapsed_ms,
            self._model,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        return LLMCompletion(
            content=dict(tool_use_block.input),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
        )
