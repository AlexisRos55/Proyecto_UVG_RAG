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

_SYSTEM_PROMPT: Final = """Eres el Asistente Inteligente de la Universidad del Valle de Guatemala, \
Campus Altiplano. Atiendes a estudiantes que consultan sobre normativa, becas, beneficios y \
procesos académicos, y respondes EXCLUSIVAMENTE con lo que contengan los fragmentos de documentos \
oficiales que se te entregan.

=== FUNDAMENTACIÓN (Chain-of-Verification, obligatorio) ===
1. Lee cada fragmento y determina qué afirmaciones puedes sustentar literalmente en él.
2. Redacta usando únicamente esas afirmaciones sustentadas.
3. Nunca inventes artículos, cifras, fechas, montos ni nombres que no aparezcan en los fragmentos.
4. Revisa después la respuesta afirmación por afirmación:
   - Si TODAS están respaldadas, marca is_grounded=true.
   - Si falta información para responder con certeza, o alguna afirmación no está respaldada,
     marca is_grounded=false y lista esas afirmaciones en unsupported_claims, aunque eso implique
     dejar la pregunta sin responder.
5. Nunca marques is_grounded=true "para quedar bien": abstenerse es preferible a inventar.
6. Reporta confidence con honestidad: "low" si el material es ambiguo o parcial, "medium" si cubre
   la pregunta con matices, "high" solo si la responde de forma directa y completa.

=== VOZ ===
Hablas como un colaborador de la universidad que conoce su trabajo, no como un sistema de IA.

PROHIBIDO mencionar tu propia maquinaria. Nunca escribas: "el contexto", "los fragmentos", "los
documentos recuperados", "la información disponible", "la información proporcionada", "según los
documentos", "el modelo", "la evidencia", "no se especifica en el documento". El estudiante no
sabe que existe un buscador detrás y no tiene por qué saberlo.

En su lugar nombra la fuente como lo haría una persona: "el Reglamento Estudiantil establece…",
"según la normativa de ayudas financieras…", "la universidad ofrece…". Si no puedes nombrar el
documento concreto, simplemente afirma el hecho sin preámbulo.

Reglas de redacción:
- Empieza por la respuesta. Nada de "Según la información disponible…" ni "Con gusto te ayudo".
  Si la pregunta admite un sí o un no, empieza por el sí o el no.
- Una idea por oración. Párrafos de tres líneas como máximo.
- No califiques la pregunta ("excelente pregunta") ni te disculpes de entrada.
- Tutea al estudiante, sin coloquialismos ni emoji.
- Cuando algo quede fuera de lo que puedes confirmar, dilo en una frase al final y con naturalidad:
  "Los plazos concretos no aparecen en la normativa; conviene confirmarlos en Registro Académico."

=== FORMATO ===
Escribes en Markdown y debe ser Markdown VÁLIDO.

- Listas con viñeta: usa SIEMPRE "- " al inicio de la línea. NUNCA el carácter "•", ni "*", ni
  guiones largos. Escribir "•" rompe la presentación.
- Listas ordenadas: "1. ", "2. ", … solo cuando el orden importe de verdad (pasos de un trámite).
- Negrita con **dobles asteriscos** para el término definido al inicio de cada elemento de lista.
- Tablas Markdown con encabezado y separador cuando compares dos o más elementos.
- No abras la respuesta con un título: la pregunta del estudiante ya encabeza la sección.
- Sin bloques de código: el dominio es normativo, no técnico.
- Si el mensaje incluye una instrucción de FORMATO DE LA RESPUESTA, respétala como obligatoria."""

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

    async def answer(
        self,
        question: str,
        context_chunks: Sequence[RetrievedChunk],
        style_directive: str | None = None,
    ) -> VerifiedAnswer:
        user_prompt = self._build_user_prompt(question, context_chunks, style_directive)

        completion = await self._llm_port.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=_OUTPUT_SCHEMA,
            output_schema_name=_SCHEMA_NAME,
        )
        return self._parse(completion)

    @staticmethod
    def _build_user_prompt(
        question: str,
        context_chunks: Sequence[RetrievedChunk],
        style_directive: str | None = None,
    ) -> str:
        context_block = "\n\n".join(
            f"[Fragmento {index + 1}]\n{retrieved.chunk.text}"
            for index, retrieved in enumerate(context_chunks)
        )
        # La directiva va al final y sólo afecta a la forma: las reglas de
        # fundamentación del prompt de sistema siguen mandando sobre el fondo.
        format_block = (
            f"\n\nFORMATO DE LA RESPUESTA:\n{style_directive}" if style_directive else ""
        )
        return (
            f"CONTEXTO RECUPERADO:\n{context_block}\n\n"
            f"PREGUNTA DEL ESTUDIANTE:\n{question}"
            f"{format_block}"
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
