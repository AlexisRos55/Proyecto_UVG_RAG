from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.value_objects.conversation_intent import ConversationIntent


class ResponseStyle(Enum):
    """Forma que debe tomar la respuesta fundamentada.

    Se decide antes de generar y viaja al prompt como directiva. No añade
    ninguna llamada: enmarca la que ya se hacía (US-2.2 sigue intacta).
    """

    DIRECT = "direct"
    LIST = "list"
    STEPS = "steps"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    SECTIONED = "sectioned"
    UNSPECIFIED = "unspecified"

    @property
    def directive(self) -> str | None:
        """Instrucción en español para el prompt. `None` deja decidir al modelo."""
        directives = {
            ResponseStyle.DIRECT: (
                "Responde de forma directa en una o dos frases. No uses listas ni encabezados: "
                "la pregunta busca un dato puntual."
            ),
            ResponseStyle.LIST: (
                "Presenta la respuesta como una lista con viñetas, un elemento por concepto, "
                "con el nombre del elemento en negrita seguido de su explicación."
            ),
            ResponseStyle.STEPS: (
                "Presenta la respuesta como una lista numerada de pasos en el orden en que el "
                "estudiante debe realizarlos."
            ),
            ResponseStyle.COMPARISON: (
                "Presenta la comparación como una tabla Markdown cuando haya al menos dos "
                "criterios comparables; si no, usa dos bloques claramente separados."
            ),
            ResponseStyle.DEFINITION: (
                "Comienza con una definición breve y añade después un ejemplo concreto tomado "
                "del contexto."
            ),
            ResponseStyle.SECTIONED: (
                "El estudiante hizo varias preguntas: responde cada una en su propia sección "
                "con un encabezado corto, para que ninguna quede sin responder."
            ),
            ResponseStyle.UNSPECIFIED: None,
        }
        return directives[self]


class SkillName(Enum):
    """Habilidades del agente. Todas son locales salvo las dos fundamentadas."""

    GROUNDED_ANSWER = "grounded_answer"
    INTRODUCE = "introduce"
    DECLARE_IDENTITY = "declare_identity"
    DECLARE_CAPABILITIES = "declare_capabilities"
    DECLARE_DOCUMENT_SCOPE = "declare_document_scope"
    EXPLAIN_HOW_IT_WORKS = "explain_how_it_works"
    EXPLAIN_USAGE = "explain_usage"
    EXPLAIN_PRIVACY = "explain_privacy"
    ACKNOWLEDGE = "acknowledge"
    CLOSE = "close"
    DISAMBIGUATE = "disambiguate"
    DECLINE_OUT_OF_DOMAIN = "decline_out_of_domain"
    DECLINE_PERSONAL_DATA = "decline_personal_data"
    HANDLE_NOISE = "handle_noise"
    RESIST_INJECTION = "resist_injection"
    CONTAIN_FRUSTRATION = "contain_frustration"

    @property
    def needs_generation(self) -> bool:
        return self is SkillName.GROUNDED_ANSWER


@dataclass(frozen=True, slots=True)
class ResponsePlan:
    """Decisión del agente antes de actuar.

    Es la salida de `ResponsePolicy`, una función pura: mismas entradas, misma
    decisión. Esa pureza es lo que permite comprobarla exhaustivamente y
    reportarla como resultado medible.

    Conserva la intención que la originó para que el catálogo pueda matizar la
    redacción sin multiplicar habilidades casi idénticas.
    """

    skill: SkillName
    intent: ConversationIntent
    style: ResponseStyle = ResponseStyle.UNSPECIFIED
    resolved_query: str | None = None

    @property
    def is_local(self) -> bool:
        return not self.skill.needs_generation
