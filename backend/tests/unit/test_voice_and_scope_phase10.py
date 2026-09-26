"""Fase 10: primero lo que aplica, textos locales fieles al corpus y papeles de un trámite."""

from __future__ import annotations

from app.domain.services.local_skill_catalog import LocalSkillCatalog
from app.domain.services.message_sanitizer import MessageSanitizer
from app.domain.services.voice_guard import enforce_institutional_voice, lead_with_what_applies
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent
from app.domain.value_objects.response_plan import ResponsePlan, SkillName
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier


def test_a_choice_answer_starts_with_the_option_and_ends_with_what_is_missing() -> None:
    answer = (
        "La normativa no establece becas específicas por carrera.\n\n"
        "Lo que sí aplica es que en el Campus Altiplano tienes acceso al Programa Regular.\n\n"
        "Si cursas AVE, hay más opciones.\n\n"
        "Para saber cuál conviene, consulta en el campus."
    )
    reordered = lead_with_what_applies(answer).split("\n\n")
    assert reordered[0] == "En el Campus Altiplano tienes acceso al Programa Regular."
    assert reordered[-2] == "La normativa no establece becas específicas por carrera."
    assert reordered[-1].startswith("Para saber cuál conviene")


def test_the_general_voice_guard_does_not_reorder() -> None:
    # Cuando se pregunta justo por lo que falta, decirlo primero es la respuesta directa.
    answer = "La normativa no describe el trámite.\n\nLo que sí define es el efecto en tu beca.\n\nConfírmalo en el campus."
    assert enforce_institutional_voice(answer) == answer


def test_asking_which_documents_a_procedure_requires_is_not_asking_about_the_assistant() -> None:
    classifier = RuleBasedIntentClassifier()
    normalized = MessageSanitizer.sanitize("¿Qué documentos piden?").normalized
    assert classifier.classify(normalized).intent is not ConversationIntent.DOCUMENT_SCOPE
    scope = MessageSanitizer.sanitize("¿Qué documentos manejas?").normalized
    assert classifier.classify(scope).intent is ConversationIntent.DOCUMENT_SCOPE


def test_capabilities_and_greeting_only_offer_topics_the_corpus_covers() -> None:
    domains = ["las becas y ayudas financieras", "el calendario académico"]
    plan = ResponsePlan(skill=SkillName.DECLARE_CAPABILITIES, intent=ConversationIntent.CAPABILITIES)
    text = LocalSkillCatalog.respond(plan, ConversationContext(), domains=domains)
    assert "- Las becas y ayudas financieras" in text and "Seguro" not in text
    greeting = LocalSkillCatalog.respond(
        ResponsePlan(skill=SkillName.INTRODUCE, intent=ConversationIntent.GREETING), ConversationContext(), domains=domains
    )
    assert "Asistente Inteligente" in greeting and "el calendario académico" in greeting
