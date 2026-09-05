# infrastructure/adapters/llm

Implementación concreta de `LLMPort` y `VerificationStrategyPort` usando el SDK oficial de Anthropic (sin LangChain, ver [ADR-0002](../../../../../../docs/adr/0002-no-langchain-direct-anthropic-sdk.md)).

Previsto: `AnthropicLLMAdapter` (invoca al modelo configurado vía `ANTHROPIC_MODEL`, temperatura 0.0) y `SingleCallVerificationAdapter` (Chain-of-Verification en una sola llamada con salida estructurada, ver [ADR-0005](../../../../../../docs/adr/0005-chain-of-verification-strategy.md)).

Regla: el nombre del modelo, el máximo de tokens y cualquier parámetro de la API se leen de `infrastructure/config`, nunca hardcodeados en este adaptador (ver [ADR-0006](../../../../../../docs/adr/0006-configurable-llm-model-selection.md)).
