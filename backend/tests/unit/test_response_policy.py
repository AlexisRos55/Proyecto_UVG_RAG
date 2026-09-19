"""La política es una función pura: se comprueba exhaustivamente por tabla."""

from __future__ import annotations

import pytest

from app.domain.services import response_policy
from app.domain.services.message_sanitizer import MessageSanitizer
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent, IntentClassification
from app.domain.value_objects.response_plan import ResponseStyle, SkillName

HIGH = 0.95
LOW = 0.40


def classify(intent: ConversationIntent, confidence: float = HIGH) -> IntentClassification:
    return IntentClassification(intent, confidence, "test")


@pytest.mark.parametrize(
    ("intent", "expected_skill"),
    [
        (ConversationIntent.GREETING, SkillName.INTRODUCE),
        (ConversationIntent.FAREWELL, SkillName.CLOSE),
        (ConversationIntent.THANKS, SkillName.ACKNOWLEDGE),
        (ConversationIntent.IDENTITY, SkillName.DECLARE_IDENTITY),
        (ConversationIntent.CAPABILITIES, SkillName.DECLARE_CAPABILITIES),
        (ConversationIntent.DOCUMENT_SCOPE, SkillName.DECLARE_DOCUMENT_SCOPE),
        (ConversationIntent.AMBIGUOUS, SkillName.DISAMBIGUATE),
        (ConversationIntent.OUT_OF_DOMAIN, SkillName.DECLINE_OUT_OF_DOMAIN),
        (ConversationIntent.PERSONAL_DATA, SkillName.DECLINE_PERSONAL_DATA),
        (ConversationIntent.PROMPT_INJECTION, SkillName.RESIST_INJECTION),
        (ConversationIntent.NOISE, SkillName.HANDLE_NOISE),
        (ConversationIntent.FRUSTRATION, SkillName.CONTAIN_FRUSTRATION),
    ],
)
def test_routes_each_intent_to_its_skill(
    intent: ConversationIntent, expected_skill: SkillName
) -> None:
    plan = response_policy.decide(classify(intent), ConversationContext(), "mensaje")
    assert plan.skill is expected_skill
    assert plan.is_local


def test_institutional_query_goes_to_grounded_answer() -> None:
    plan = response_policy.decide(
        classify(ConversationIntent.INSTITUTIONAL_QUERY), ConversationContext(), "que becas hay"
    )
    assert plan.skill is SkillName.GROUNDED_ANSWER
    assert not plan.is_local


@pytest.mark.parametrize(
    "intent",
    [ConversationIntent.GREETING, ConversationIntent.THANKS, ConversationIntent.OUT_OF_DOMAIN],
)
def test_low_confidence_always_falls_back_to_grounded_answer(intent: ConversationIntent) -> None:
    """Regla de seguridad: el peor caso debe ser el comportamiento actual, no una
    respuesta enlatada a una pregunta legítima."""
    plan = response_policy.decide(classify(intent, LOW), ConversationContext(), "mensaje dudoso")
    assert plan.skill is SkillName.GROUNDED_ANSWER


@pytest.mark.parametrize(
    ("query", "expected_style"),
    [
        ("como me inscribo a un curso", ResponseStyle.STEPS),
        ("cual es la diferencia entre las dos becas", ResponseStyle.COMPARISON),
        ("que significa indice academico", ResponseStyle.DEFINITION),
        ("que becas existen", ResponseStyle.LIST),
        ("cuanto cubre el seguro", ResponseStyle.DIRECT),
        ("que becas hay? y como las solicito?", ResponseStyle.SECTIONED),
        ("informacion general de la universidad", ResponseStyle.UNSPECIFIED),
    ],
)
def test_detects_response_style_from_question_shape(
    query: str, expected_style: ResponseStyle
) -> None:
    assert response_policy.detect_style(query) is expected_style


def test_unspecified_style_emits_no_directive() -> None:
    """Sin señal clara, el modelo decide: es el comportamiento actual."""
    assert ResponseStyle.UNSPECIFIED.directive is None


class TestFollowUp:
    def test_resolves_anaphora_using_previous_question(self) -> None:
        context = ConversationContext(
            last_resolved_query="que becas ofrece la universidad", turn_count=1
        )
        normalized = MessageSanitizer.normalize("¿y cuánto cubre esa?")
        plan = response_policy.decide(
            classify(ConversationIntent.INSTITUTIONAL_QUERY), context, normalized
        )
        assert plan.resolved_query is not None
        assert "becas" in plan.resolved_query
        assert "cuanto cubre" in plan.resolved_query

    def test_does_not_resolve_without_previous_turn(self) -> None:
        normalized = MessageSanitizer.normalize("¿y cuánto cubre esa?")
        plan = response_policy.decide(
            classify(ConversationIntent.INSTITUTIONAL_QUERY), ConversationContext(), normalized
        )
        assert plan.resolved_query == normalized

    def test_long_message_is_not_treated_as_follow_up(self) -> None:
        """Un mensaje largo se explica solo; concatenarlo distorsionaría la búsqueda."""
        context = ConversationContext(last_resolved_query="que becas hay", turn_count=1)
        query = MessageSanitizer.normalize(
            "y me gustaria saber cuales son todos los requisitos completos para poder "
            "aplicar a esa beca durante el proximo semestre academico"
        )
        plan = response_policy.decide(
            classify(ConversationIntent.INSTITUTIONAL_QUERY), context, query
        )
        assert plan.resolved_query == query

    def test_reference_resolution_never_uses_document_text(self) -> None:
        """R-03: solo se concatenan palabras del propio usuario."""
        context = ConversationContext(
            last_resolved_query="que becas hay",
            topic_documents=("reglamento_secreto.pdf",),
            turn_count=1,
        )
        resolved = response_policy.resolve_reference("y cuanto cubre esa", context)
        assert "reglamento_secreto" not in resolved
