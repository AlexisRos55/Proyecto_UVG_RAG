from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from app.domain.entities.chunk import RetrievedChunk
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.value_objects.llm_completion import LLMCompletion
from app.domain.value_objects.verified_answer import VerificationConfidence, VerifiedAnswer
from app.shared.exceptions.domain_errors import VerificationFailedError

_SCHEMA_NAME: Final = "submit_verified_answer"

_SYSTEM_PROMPT: Final = """Eres el asistente virtual institucional de UVG Altiplano. Respondes \
preguntas de estudiantes sobre normativa, beneficios y seguros, basándote EXCLUSIVAMENTE en los \
fragmentos de documentos oficiales que se te proporcionan como contexto.

Reglas estrictas (aplica Chain-of-Verification antes de responder):
1. Lee cada fragmento del contexto y determina qué afirmaciones puedes sustentar literalmente en él.
2. Redacta una respuesta clara y breve en español, usando únicamente esas afirmaciones sustentadas.
3. Nunca inventes artículos, cifras, fechas, montos ni nombres que no aparezcan en el contexto.
4. Después de redactar la respuesta, revísala afirmación por afirmación contra el contexto:
   - Si TODAS las afirmaciones están respaldadas, marca is_grounded=true.
   - Si el contexto no contiene información suficiente para responder con certeza, o si alguna
     afirmación no está respaldada, marca is_grounded=false y lista esas afirmaciones en
     unsupported_claims, incluso si eso significa dejar la pregunta sin responder del todo.
5. Nunca marques is_grounded=true "para quedar bien": es preferible abstenerse que alucinar.
6. Reporta tu nivel de confianza (confidence) de forma honesta: "low" si el contexto es ambiguo o \
parcial, "medium" si cubre la pregunta pero con matices, "high" solo si el contexto responde la \
pregunta de forma directa y completa."""

_OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "answer_text": {
            "type": "string",
            "description": "Respuesta al estudiante en español, basada solo en el contexto.",
        },
        "is_grounded": {
            "type": "boolean",
            "description": "true solo si CADA afirmación de answer_text está respaldada por el contexto.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Confianza autoevaluada de la respuesta.",
        },
        "unsupported_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Afirmaciones que no pudieron sustentarse en el contexto, si las hay.",
        },
    },
    "required": ["answer_text", "is_grounded", "confidence", "unsupported_claims"],
}


class SingleCallVerificationAdapter(VerificationStrategyPort):
    """Chain-of-Verification in a single LLM call (ADR-0005): generation and self-verification
    happen in the same structured-output request, to keep cost and latency close to a plain
    generation call (NFR-01, NFR-02). Composes LLMPort with exactly one call.
    """

    def __init__(self, llm_port: LLMPort) -> None:
        self._llm_port = llm_port

    async def answer(self, question: str, context_chunks: Sequence[RetrievedChunk]) -> VerifiedAnswer:
        user_prompt = self._build_user_prompt(question, context_chunks)

        completion = await self._llm_port.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=_OUTPUT_SCHEMA,
            output_schema_name=_SCHEMA_NAME,
        )
        return self._parse(completion)

    @staticmethod
    def _build_user_prompt(question: str, context_chunks: Sequence[RetrievedChunk]) -> str:
        context_block = "\n\n".join(
            f"[Fragmento {index + 1}]\n{retrieved.chunk.text}"
            for index, retrieved in enumerate(context_chunks)
        )
        return (
            f"CONTEXTO RECUPERADO:\n{context_block}\n\n"
            f"PREGUNTA DEL ESTUDIANTE:\n{question}"
        )

    @staticmethod
    def _parse(completion: LLMCompletion) -> VerifiedAnswer:
        data = completion.content
        try:
            return VerifiedAnswer(
                answer_text=str(data["answer_text"]),
                is_grounded=bool(data["is_grounded"]),
                confidence=VerificationConfidence(data["confidence"]),
                unsupported_claims=tuple(data.get("unsupported_claims", [])),
            )
        except (KeyError, ValueError) as exc:
            raise VerificationFailedError(
                f"La salida estructurada del modelo no tiene el formato esperado: {exc}"
            ) from exc
