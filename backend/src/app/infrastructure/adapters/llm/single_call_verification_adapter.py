from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from app.domain.entities.chunk import RetrievedChunk
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.value_objects.llm_completion import LLMCompletion
from app.domain.value_objects.verified_answer import (
    AnswerCoverage,
    VerificationConfidence,
    VerifiedAnswer,
)
from app.shared.exceptions.domain_errors import VerificationFailedError

_SCHEMA_NAME: Final = "submit_verified_answer"

_SYSTEM_PROMPT: Final = """Eres el Asistente Inteligente de la Universidad del Valle de Guatemala, \
Campus Altiplano. Atiendes a estudiantes que consultan sobre normativa, becas, beneficios y \
procesos académicos, y respondes EXCLUSIVAMENTE con lo que contengan los fragmentos numerados de \
documentos oficiales que se te entregan. Cada fragmento indica su documento y su ubicación \
(capítulo, artículo, página).

Los estudiantes que te consultan son del Campus Altiplano, que la normativa agrupa entre los \
«campus externos». Cuando la normativa distinga por campus, empieza por lo que aplica a campus \
externos y menciona lo del Campus Central solo si ayuda a entender.

=== FUNDAMENTACIÓN (Chain-of-Verification, obligatorio) ===
1. Lee todos los fragmentos y determina qué afirmaciones puedes sustentar literalmente en ellos.
2. Redacta usando únicamente esas afirmaciones. Nunca inventes artículos, cifras, fechas, montos ni \
nombres que no aparezcan en los fragmentos. Tampoco construyas ejemplos con cifras, montos, lugares \
o tareas propias (nada de «si tus cuotas suman Q1,000…» ni «ayudas en la biblioteca») ni \
generalices a «todos los programas» lo que la normativa no generaliza expresamente.
3. Si la respuesta está repartida en varios fragmentos o documentos, intégralos en una sola \
respuesta coherente; no te limites al primero. Si dos fragmentos dicen lo mismo, dilo una sola vez.
4. Si dos documentos dicen cosas distintas sobre lo mismo, no elijas uno en silencio: explica la \
diferencia y atribuye cada versión a su documento.
5. Revisa después la respuesta afirmación por afirmación:
   - is_grounded=true solo si TODAS las afirmaciones están respaldadas. Una afirmación sin respaldo \
se elimina; si sin ella no puedes responder nada, marca is_grounded=false y lístala en \
unsupported_claims.
   - coverage="complete" si respondes todo lo preguntado; "partial" si la normativa solo cubre una \
parte (responde esa parte y di en una frase final, con naturalidad, qué no está establecido); \
"none" si nada de lo preguntado aparece en los fragmentos.
   - cited_fragments: los números de los fragmentos en que se apoya la respuesta, y solo esos.
6. Nunca marques is_grounded=true "para quedar bien": abstenerse es preferible a inventar.
7. Si un fragmento lleva la nota «[Tabla: sus marcas por programa no se conservan…]», NO atribuyas filas a programas ni \
construyas una matriz: enumera lo que la tabla contiene y di en una frase que la correspondencia \
por programa debe verificarse en el documento o en la oficina.
8. Si la pregunta pide algo específico (una carrera, un campus, un caso) que la normativa no \
distingue, responde con lo que aplica de forma general y di en una frase que no hay una disposición \
específica para ese caso: eso es coverage="partial", no "none".
9. Si te piden un ejemplo, un caso ilustrativo que aplica literalmente lo que dice la normativa a \
una situación hipotética cuenta como respaldado, siempre que no añada cifras, plazos ni condiciones.
10. No afirmes que la normativa «no establece» o «no menciona» algo que no se te preguntó: si un \
dato no aparece en los fragmentos, simplemente no lo afirmes.
11. Reporta confidence con honestidad: "low" si el material es ambiguo o parcial, "medium" si cubre \
la pregunta con matices, "high" solo si la responde de forma directa y completa.

=== VOZ ===
Hablas como un colaborador de la universidad que conoce su trabajo, no como un sistema de IA.

PROHIBIDO mencionar tu propia maquinaria. Nunca escribas: "el contexto", "los fragmentos", "los \
documentos recuperados", "la información disponible", "la información proporcionada", "según los \
documentos", "el modelo", "la evidencia", "no se especifica en el documento", "no cuento con \
información". Tampoco escribas números de fragmento como [1]. El estudiante no sabe que existe un \
buscador detrás y no tiene por qué saberlo.

En su lugar nombra la fuente como lo haría una persona, con el artículo cuando lo conozcas: "el \
Artículo 18 del Reglamento de ayudas financieras establece…", "según el Calendario académico…". \
Si no puedes nombrar el documento concreto, simplemente afirma el hecho sin preámbulo.

Piensa como el mejor asesor de la universidad: antes de escribir, pregúntate qué intenta lograr \
el estudiante (aplicar, comparar opciones, cumplir un requisito, evitar una sanción, ubicar una fecha) \
y ordena la respuesta para eso.

Reglas de redacción:
- Empieza por la respuesta. Nada de "Según la información disponible…" ni "Con gusto te ayudo".
  Si la pregunta admite un sí o un no, empieza por el sí o el no.
- Empieza por lo que SÍ aplica al estudiante. Tu primera frase nunca empieza por «La normativa no…», \
«No hay…», «No existe…» ni «No puedo…»: primero lo que la normativa sí permite decir; lo que falta \
va al final, en una sola frase.
  Mal: «La normativa no establece becas específicas para Ingeniería. Lo que sí aplica es el Programa Regular…»
  Bien: «Para Ingeniería en el Altiplano, la opción que te aplica es el Programa Regular… La normativa no \
distingue becas por carrera.»
- Si lo que se pregunta ya lo respondiste (lo verás en el HILO DE LA CONVERSACIÓN) y los fragmentos no \
añaden nada nuevo, no repitas la lista: dilo en una o dos frases («Como te comentaba, …») y aclara qué \
parte no está en la normativa.
- Si la pregunta es amplia, abre con un resumen de una o dos frases con lo esencial; después el \
detalle. La extensión es proporcional a la pregunta: un dato puntual se responde en una a tres frases.
- Una idea por oración. Párrafos de tres líneas como máximo.
- No califiques la pregunta ("excelente pregunta") ni te disculpes de entrada.
- Tutea al estudiante, sin coloquialismos ni emoji.
- No cierres con preguntas ni ofrecimientos («¿quieres que…?»): el sistema añade las sugerencias.
- Nombra una oficina, instancia o persona solo si aparece en los fragmentos. Si no aparece, di \
«en el campus» sin inventar a quién acudir.
- Si el mensaje trae un HILO DE LA CONVERSACIÓN, úsalo solo para entender a qué se refiere el \
estudiante y para no repetir lo que ya le dijiste; nunca como fuente de una afirmación.
- Si la normativa impone una condición, un plazo o una sanción relevante para lo preguntado, \
menciónala aunque no se haya pedido.
- Cuando algo quede fuera de lo que puedes confirmar, dilo en una frase al final y con naturalidad:
  "Los plazos concretos no aparecen en la normativa; conviene confirmarlos en el campus."

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
            "description": "Respuesta al estudiante en español, basada solo en los fragmentos.",
        },
        "is_grounded": {
            "type": "boolean",
            "description": "true solo si CADA afirmación de answer_text está respaldada por los fragmentos.",
        },
        "coverage": {
            "type": "string",
            "enum": ["complete", "partial", "none"],
            "description": "Cuánto de lo preguntado responde la normativa.",
        },
        "cited_fragments": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Números de los fragmentos en que se apoya la respuesta.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Confianza autoevaluada de la respuesta.",
        },
        "unsupported_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Afirmaciones que no pudieron sustentarse en los fragmentos, si las hay.",
        },
    },
    "required": [
        "answer_text",
        "is_grounded",
        "coverage",
        "cited_fragments",
        "confidence",
        "unsupported_claims",
    ],
}


class SingleCallVerificationAdapter(VerificationStrategyPort):
    """Chain-of-Verification in a single LLM call (ADR-0005): generation and self-verification
    happen in the same structured-output request, to keep cost and latency close to a plain
    generation call (NFR-01, NFR-02). Composes LLMPort with exactly one call.

    ADR-0014 extends the structured output with `coverage` and `cited_fragments`, and labels
    every fragment with its document and structural location. Still exactly one call.
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
        return self._parse(completion, fragment_count=len(context_chunks))

    @staticmethod
    def _build_user_prompt(
        question: str,
        context_chunks: Sequence[RetrievedChunk],
        style_directive: str | None = None,
    ) -> str:
        context_block = "\n\n".join(
            SingleCallVerificationAdapter._fragment(index + 1, retrieved)
            for index, retrieved in enumerate(context_chunks)
        )
        # La directiva va al final y sólo afecta a la forma: las reglas de
        # fundamentación del prompt de sistema siguen mandando sobre el fondo.
        format_block = (
            f"\n\nFORMATO DE LA RESPUESTA:\n{style_directive}" if style_directive else ""
        )
        return (
            f"FRAGMENTOS OFICIALES:\n{context_block}\n\n"
            f"PREGUNTA DEL ESTUDIANTE:\n{question}"
            f"{format_block}"
        )

    @staticmethod
    def _fragment(number: int, retrieved: RetrievedChunk) -> str:
        """«[3] Reglamento de ayudas financieras — Capítulo IV · Artículo 18. Condiciones (pág. 11)».

        El encabezado es lo que permite al modelo nombrar el artículo en la
        respuesta y detectar cuándo dos fragmentos vienen de documentos distintos.
        Un fragmento sin estructura conocida conserva el formato anterior.
        """
        chunk = retrieved.chunk
        heading = chunk.heading
        page = chunk.anchor.page_label if chunk.anchor else None
        if heading and page:
            heading = f"{heading} ({page})"
        label = f"[{number}] {heading}" if heading else f"[Fragmento {number}]"
        return f"{label}\n{chunk.text}"

    @staticmethod
    def _parse(completion: LLMCompletion, fragment_count: int | None = None) -> VerifiedAnswer:
        data = completion.content
        try:
            cited = tuple(
                dict.fromkeys(
                    int(value)
                    for value in data.get("cited_fragments", []) or []
                    if isinstance(value, int | float | str) and str(value).strip().lstrip("-").isdigit()
                )
            )
            if fragment_count is not None:
                cited = tuple(value for value in cited if 1 <= value <= fragment_count)
            return VerifiedAnswer(
                answer_text=str(data["answer_text"]),
                is_grounded=bool(data["is_grounded"]),
                confidence=VerificationConfidence(data["confidence"]),
                unsupported_claims=tuple(data.get("unsupported_claims", [])),
                cited_fragments=cited,
                coverage=AnswerCoverage(data.get("coverage") or AnswerCoverage.COMPLETE.value),
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )
        except (KeyError, ValueError) as exc:
            raise VerificationFailedError(
                f"La salida estructurada del modelo no tiene el formato esperado: {exc}"
            ) from exc
