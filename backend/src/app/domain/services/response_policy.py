from __future__ import annotations

import re

from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent, IntentClassification
from app.domain.value_objects.response_plan import ResponsePlan, ResponseStyle, SkillName

# Por debajo de este umbral, el clasificador no sabe lo suficiente como para
# desviar el mensaje del camino normal.
MIN_CONFIDENCE_FOR_LOCAL_SKILL = 0.70

_SKILL_BY_INTENT = {
    ConversationIntent.GREETING: SkillName.INTRODUCE,
    ConversationIntent.FAREWELL: SkillName.CLOSE,
    ConversationIntent.THANKS: SkillName.ACKNOWLEDGE,
    ConversationIntent.ACKNOWLEDGEMENT: SkillName.ACKNOWLEDGE,
    ConversationIntent.SMALL_TALK: SkillName.ACKNOWLEDGE,
    ConversationIntent.FRUSTRATION: SkillName.CONTAIN_FRUSTRATION,
    ConversationIntent.IDENTITY: SkillName.DECLARE_IDENTITY,
    ConversationIntent.CAPABILITIES: SkillName.DECLARE_CAPABILITIES,
    ConversationIntent.DOCUMENT_SCOPE: SkillName.DECLARE_DOCUMENT_SCOPE,
    ConversationIntent.HOW_IT_WORKS: SkillName.EXPLAIN_HOW_IT_WORKS,
    ConversationIntent.USAGE_HELP: SkillName.EXPLAIN_USAGE,
    ConversationIntent.PRIVACY: SkillName.EXPLAIN_PRIVACY,
    ConversationIntent.AMBIGUOUS: SkillName.DISAMBIGUATE,
    ConversationIntent.NOISE: SkillName.HANDLE_NOISE,
    ConversationIntent.OUT_OF_DOMAIN: SkillName.DECLINE_OUT_OF_DOMAIN,
    ConversationIntent.PERSONAL_DATA: SkillName.DECLINE_PERSONAL_DATA,
    ConversationIntent.PROMPT_INJECTION: SkillName.RESIST_INJECTION,
}

# --- Señales léxicas de formato -------------------------------------------------
_STEPS = re.compile(r"\bcomo\s+(?:me\s+)?(?:puedo\s+)?(inscrib|solicit|tramit|aplic|registr|renov|matricul)")
_COMPARISON = re.compile(r"\bdiferencia\b|\bversus\b|\bvs\b|\bcual\s+(?:me\s+)?(?:conviene|es\s+mejor)\b|\bcomparar\b")
_DEFINITION = re.compile(r"\bque\s+(?:significa|es|son)\b|\bdefinicion\b|\ben\s+que\s+consiste\b")
_DIRECT = re.compile(r"\bcuanto\b|\bcuando\b|\bdonde\b|\bcual\s+es\s+el\s+(?:monto|plazo|porcentaje|limite)\b")
_ENUMERABLE = re.compile(r"\bque\s+(becas|requisitos|beneficios|documentos|pasos|opciones|tipos|seguros)\b")
_QUESTION_MARK = re.compile(r"\?")

# Referencias que solo tienen sentido con el turno anterior delante.
_ANAPHORA = re.compile(
    r"^(?:y\s+)?(?:eso|esa|ese|esos|esas|la\s+otra|el\s+otro|ahi|alli)\b"
    r"|^(?:y|pero|entonces)\s+"
    r"|\b(?:esa|ese|eso|dicha|dicho|la\s+misma|el\s+mismo)\b"
)


def detect_style(normalized_query: str) -> ResponseStyle:
    """Elige la forma de la respuesta a partir de la forma de la pregunta.

    Cuando ninguna señal aplica devuelve `UNSPECIFIED` y el modelo decide, que es
    el comportamiento actual y un buen valor por defecto.
    """
    if len(_QUESTION_MARK.findall(normalized_query)) >= 2:
        return ResponseStyle.SECTIONED
    if _STEPS.search(normalized_query):
        return ResponseStyle.STEPS
    if _COMPARISON.search(normalized_query):
        return ResponseStyle.COMPARISON
    if _DEFINITION.search(normalized_query):
        return ResponseStyle.DEFINITION
    if _ENUMERABLE.search(normalized_query):
        return ResponseStyle.LIST
    if _DIRECT.search(normalized_query):
        return ResponseStyle.DIRECT
    return ResponseStyle.UNSPECIFIED


def looks_like_follow_up(normalized_query: str, context: ConversationContext) -> bool:
    """Un seguimiento necesita un turno previo y una referencia que resolver."""
    if context.last_resolved_query is None:
        return False
    if len(normalized_query.split()) > 12:
        return False
    return bool(_ANAPHORA.search(normalized_query))


def resolve_reference(query: str, context: ConversationContext) -> str:
    """Reescribe la consulta anafórica con las palabras del propio usuario.

    Nunca se usa texto recuperado de documentos: eso enviaría contenido
    institucional de vuelta dentro de la consulta y ampliaría la exposición que
    R-03 ya señala. Solo se antepone la pregunta anterior del estudiante.

    La composición resultante sirve tanto para recuperar como para generar: el
    modelo ve las dos preguntas tal como el estudiante las hizo, que es la
    información que necesitaba para resolver el «esa».
    """
    previous = context.last_resolved_query
    if not previous:
        return query
    return f"{previous.strip()} {query.strip()}".strip()


def decide(
    classification: IntentClassification,
    context: ConversationContext,
    normalized_query: str,
    prompt_query: str | None = None,
) -> ResponsePlan:
    """Función pura: decide qué habilidad ejecutar y con qué forma.

    Regla de seguridad: si el clasificador no supera el umbral de confianza, la
    decisión es siempre la respuesta fundamentada. Un mensaje de consulta
    clasificado como social produciría una respuesta enlatada a una pregunta
    legítima —el peor fallo posible—; al revés solo se desperdicia una llamada,
    que es exactamente lo que ocurre hoy con todos los mensajes.
    """
    intent = classification.intent

    if intent.needs_retrieval or classification.confidence < MIN_CONFIDENCE_FOR_LOCAL_SKILL:
        # El texto que ve el modelo conserva la ortografía original; la detección
        # de formato y de anáfora trabaja sobre la forma normalizada.
        query = prompt_query or normalized_query
        if intent is ConversationIntent.FOLLOW_UP or looks_like_follow_up(normalized_query, context):
            query = resolve_reference(query, context)
        return ResponsePlan(
            skill=SkillName.GROUNDED_ANSWER,
            intent=intent,
            style=detect_style(normalized_query),
            resolved_query=query,
        )

    return ResponsePlan(skill=_SKILL_BY_INTENT[intent], intent=intent)
