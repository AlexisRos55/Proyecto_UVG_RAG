"""Fase 9.5 · el software piensa como asesor antes de llamar al modelo."""

from __future__ import annotations

import pytest

from app.domain.entities.message import Message, MessageRole
from app.domain.services import conversation_guide as guide
from app.domain.services.conversation_tracker import (
    ConversationTracker,
    join_query,
    without_fillers,
)
from app.domain.services.entity_extractor import entity_key
from app.domain.services.message_sanitizer import MessageSanitizer
from app.domain.services.query_analyzer import QueryAnalyzer
from app.domain.value_objects.conversation_intent import ConversationIntent
from app.domain.value_objects.conversation_state import ConversationState, TurnMode
from app.domain.value_objects.corpus_entity import CorpusEntity, EntityKind
from app.domain.value_objects.source_reference import SourceReference
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk

AID = new_id()
DESPEGA = CorpusEntity("Beca Despega", EntityKind.PROGRAM, entity_key("Beca Despega"), ("despeg",), (AID,), ((AID, 29),))
REGULAR = CorpusEntity("Programa Regular", EntityKind.PROGRAM, entity_key("Programa Regular"), ("regul",), (AID,), ((AID, 13),))


def _tracker() -> ConversationTracker:
    return ConversationTracker([DESPEGA, REGULAR])


def _history(*turns: tuple[str, str]) -> list[Message]:
    conversation = new_id()
    messages: list[Message] = []
    for student, assistant in turns:
        messages.append(Message(new_id(), conversation, MessageRole.STUDENT, student, utc_now()))
        messages.append(Message(new_id(), conversation, MessageRole.ASSISTANT, assistant, utc_now(), is_grounded=True,
                                sources=(SourceReference("doc.pdf", document_id=AID),)))
    return messages


def _intent(message: str) -> ConversationIntent:
    return RuleBasedIntentClassifier().classify(MessageSanitizer.sanitize(message).normalized).intent


# --- Comprensión: la necesidad dicha con palabras propias ------------------------------

@pytest.mark.parametrize(
    ("message", "topic"),
    [
        ("Mis papás no pueden pagar la universidad", "becas"),
        ("Soy de bajos recursos, ¿qué puedo hacer?", "becas"),
        ("no tengo plata para la u", "becas"),
        ("quiero estudiar", "admision"),
        ("quiero entrar a la universidad", "admision"),
        ("¿Cómo entro a la UVG?", "admision"),
        ("me quiero salir de un curso", "retiro"),
        ("ya voy a terminar la carrera, ¿qué sigue?", "graduacion"),
    ],
)
def test_a_need_is_understood_as_the_topic_that_answers_it(message: str, topic: str) -> None:
    assert _tracker().interpret(message, ConversationState()).topic == topic


def test_a_paraphrase_is_searched_with_the_words_of_the_regulation() -> None:
    turn = _tracker().interpret("me quiero salir de un curso", ConversationState())
    assert "retiro de cursos" in turn.retrieval_query and "salir" not in turn.retrieval_query


def test_a_need_that_already_names_the_aid_is_a_concrete_question_not_an_overview() -> None:
    tracker = _tracker()
    assert tracker.interpret("Soy de bajos recursos, ¿qué puedo hacer?", ConversationState()).is_overview
    concrete = tracker.interpret("¿La universidad da apoyo económico a estudiantes con pocos recursos?", ConversationState())
    assert concrete.topic == "becas" and not concrete.is_overview


def test_entering_the_university_is_not_joining_a_club() -> None:
    analysis = QueryAnalyzer.analyze("quiero entrar a la universidad")
    assert not any("club" in expansion for expansion in analysis.expansions)


# --- Lo ofrecido: «sí», «no», «la primera» -------------------------------------------

def test_the_offer_closing_an_answer_is_read_back_in_order() -> None:
    line = guide.offer_line(["cobertura", "procedimiento", "responsables"], ())
    assert guide.offered_aspects(f"Respuesta.\n\n{line}") == (
        ("cobertura", "la cobertura"), ("procedimiento", "cómo se solicita"), ("responsables", "quién lo decide"))
    overview = guide.overview_offer(["requisitos", "cobertura"], (), has_options=True)
    assert [key for key, _ in guide.offered_aspects(f"x\n\n{overview}")] == ["requisitos", "cobertura"]
    assert guide.offered_aspects("Una respuesta sin ofrecimiento.") == ()


def _after_offer(offer_keys: list[str]) -> ConversationState:
    tracker = _tracker()
    reply = "La Beca Despega cubre…\n\n" + guide.offer_line(offer_keys, ())
    return tracker.replay(_history(("¿Cuáles son los requisitos de la Beca Despega?", reply)))


def test_yes_to_several_options_asks_which_one_with_the_same_words() -> None:
    state = _after_offer(["cobertura", "procedimiento"])
    turn = _tracker().interpret("sí", state)
    assert turn.needs_clarification
    assert guide.clarify(turn.resolution, None, ()) == "Con gusto. ¿Por cuál empezamos: la cobertura o cómo se solicita?"


def test_yes_to_a_single_option_answers_that_option_about_the_same_focus() -> None:
    turn = _tracker().interpret("dale", _after_offer(["cobertura"]))
    assert turn.accepts_offer and turn.aspect == "cobertura" and turn.entity == DESPEGA


def test_no_to_an_offer_is_respected_without_searching() -> None:
    turn = _tracker().interpret("no por ahora", _after_offer(["cobertura", "procedimiento"]))
    assert turn.needs_clarification and guide.clarify(turn.resolution, None, ()).startswith("Está bien.")


def test_the_first_one_after_an_offer_is_the_first_aspect_offered() -> None:
    turn = _tracker().interpret("la primera", _after_offer(["procedimiento", "cobertura"]))
    assert turn.accepts_offer and turn.aspect == "procedimiento"


# --- Seguimiento -------------------------------------------------------------------

def test_an_elliptical_chain_does_not_grow_the_query() -> None:
    tracker = _tracker()
    history = _history(("Háblame del crédito educativo", "El crédito educativo…"))
    state = tracker.replay(history)
    first = tracker.interpret("¿y cuánto?", state)
    assert first.aspect == "cobertura"
    assert join_query(["", "Crédito Educativo", "crédito educativo Crédito Educativo"]) == "Crédito Educativo"


def test_how_much_depends_on_the_topic() -> None:
    tracker = _tracker()
    becas = tracker.replay(_history(("Háblame de las becas", "Hay varias becas…")))
    assert tracker.interpret("¿y cuánto?", becas).aspect == "cobertura"
    fees = tracker.replay(_history(("¿Cuánto es la colegiatura?", "La cuota…")))
    assert tracker.interpret("¿y cuánto?", fees).aspect == "costo"


@pytest.mark.parametrize("message", ["no", "xd", "sip", "ok", "", "simón"])
def test_a_bare_reply_is_never_a_follow_up_search(message: str) -> None:
    state = _tracker().replay(_history(("Háblame de las becas", "Hay varias becas…")))
    turn = _tracker().interpret(message, state)
    assert turn.mode is TurnMode.NEW and turn.retrieval_query == ""


def test_which_ones_exist_lists_the_options_of_the_topic() -> None:
    tracker = _tracker()
    state = tracker.replay(_history(("Quiero información sobre becas", "Hay varias becas…")))
    turn = tracker.interpret("¿Cuáles existen?", state)
    assert turn.is_overview and turn.topic == "becas" and set(turn.defining_articles) == {(AID, 29), (AID, 13)}


def test_there_points_to_the_document_being_read() -> None:
    tracker = _tracker()
    state = tracker.replay(_history(("¿Qué dice el artículo 13?", "El artículo 13…")))
    turn = tracker.interpret("¿y allí qué dice de los requisitos?", state)
    assert turn.within_document and turn.aspect == "requisitos" and "alli" not in turn.retrieval_query.lower()


def test_what_else_should_i_know_searches_the_focus_and_avoids_repeats() -> None:
    tracker = _tracker()
    state = tracker.replay(_history(("¿Qué es la Beca Despega?", "La Beca Despega…"),
                                    ("¿Cuánto cubre?", "Cubre…"), ("¿y si soy extranjero?", "La normativa…")))
    turn = tracker.interpret("¿Qué más debo saber?", state)
    assert "extranjero" not in turn.retrieval_query and "Despega" in turn.retrieval_query
    assert turn.reading and "no lo repitas" in turn.reading


def test_the_aspect_words_are_not_a_new_subject() -> None:
    tracker = _tracker()
    state = tracker.replay(_history(("¿Qué es la Beca Despega?", "La Beca Despega…")))
    turn = tracker.interpret("¿Qué pasa si no cumplo?", state)
    assert turn.mode is TurnMode.FOLLOW_UP and turn.aspect == "consecuencias"


# --- Lenguaje natural y perfiles ------------------------------------------------------

@pytest.mark.parametrize("message", ["simón", "xd", "nel", "no por ahora", "cool", "sí porfa", "👍", "jeje"])
def test_chat_replies_are_acknowledgements(message: str) -> None:
    assert _intent(message) is ConversationIntent.ACKNOWLEDGEMENT


def test_it_does_not_help_me_is_frustration() -> None:
    assert _intent("esto no me ayuda") is ConversationIntent.FRUSTRATION


def test_what_else_does_that_regulation_say_is_a_document_overview() -> None:
    assert _intent("¿qué más dice ese reglamento?") is ConversationIntent.DOCUMENT_OVERVIEW


def test_fillers_leave_the_question() -> None:
    assert without_fillers("mire fíjese que quiero una beca por favor") == "que quiero una beca"
    assert MessageSanitizer.normalize("👍") == "ok"


def test_an_introduction_ending_in_a_period_keeps_the_question() -> None:
    turn = _tracker().interpret("Soy docente. Háblame del crédito educativo", ConversationState())
    assert turn.audience == "docente" and turn.topic == "credito" and not turn.needs_clarification


def test_an_apology_before_a_follow_up_does_not_change_the_subject() -> None:
    tracker = _tracker()
    state = tracker.replay(_history(("Háblame de las becas", "Hay varias becas…")))
    for message in ("Disculpe la molestia, ¿qué requisitos hay?", "Mire, disculpe, ¿Cuánto cubre?", "¿Cuánto cubre? please"):
        assert tracker.interpret(message, state).mode is TurnMode.FOLLOW_UP, message


def test_two_questions_joined_by_y_ademas_with_a_comma_are_split() -> None:
    assert len(QueryAnalyzer._decompose("Háblame del calendario académico Y además, ¿Cuándo termina el ciclo?")) == 2


# --- Recuperación ---------------------------------------------------------------------

def test_a_verb_absent_from_the_corpus_finds_its_participle() -> None:
    index = InMemoryCorpusIndex()
    index.add([chunk("Artículo 19. Penalizaciones. Se reduce la beca por cursos reprobados.", document_id=AID, position=0,
                     article=19, article_title="Penalizaciones")])
    hits = index.search("voy a reprobar un curso", 3)
    assert hits and hits[0].coverage == 1.0


def test_incremental_replay_is_identical_to_a_full_replay() -> None:
    tracker = _tracker()
    turns = [("Háblame de las becas", "Hay varias becas…\n\n" + guide.offer_line(["cobertura", "requisitos"], ())),
             ("¿Qué es la Beca Despega?", "La Beca Despega…"), ("¿Cuánto cubre?", "Cubre…"), ("gracias", "Con gusto.")]
    history = _history(*turns)
    checkpoint = None
    for end in range(2, len(history) + 1, 2):
        state, checkpoint = tracker.replay_from(history[:end], checkpoint)
        assert state == tracker.replay(history[:end])
    assert checkpoint is not None and checkpoint.consumed == len(history)


# --- Perfiles emocionales -------------------------------------------------------------

def test_worry_with_a_stated_problem_is_answered_not_oriented() -> None:
    turn = _tracker().interpret("AYUDA URGENTE!!! me van a quitar la beca no sé qué hacer", ConversationState())
    assert not turn.needs_orientation and turn.topic == "becas" and turn.aspect == "consecuencias"
    assert turn.mood == "angustia"


def test_telling_ones_situation_is_not_a_request_for_personal_data() -> None:
    assert _intent("estoy muy preocupado porque reprobé dos cursos y tengo beca") is not ConversationIntent.PERSONAL_DATA
    assert _intent("¿cuál es mi promedio?") is ConversationIntent.PERSONAL_DATA


def test_good_news_points_to_keeping_the_scholarship_and_is_celebrated() -> None:
    tracker = _tracker()
    turn = tracker.interpret("¡¡Me dieron la beca!! 🎉🎉 ¿y ahora qué tengo que hacer?", ConversationState())
    assert turn.aspect == "condiciones" and turn.mood == "alegria" and "🎉" not in turn.retrieval_query
    joy = tracker.interpret("jaja qué emoción", ConversationState())
    assert joy.needs_clarification and guide.clarify(joy.resolution, None, ()).startswith("¡Qué gusto!")


def test_a_newcomer_is_welcomed_and_then_given_a_first_step() -> None:
    turn = _tracker().interpret("hola soy nuevo y no entiendo nada de cómo funciona la u", ConversationState())
    assert turn.needs_orientation and turn.resolution == "estudiante nuevo desorientado"
    menu = [("las becas y ayudas financieras", "¿Qué becas hay?"), ("la admisión", "¿Cómo es el proceso de admisión?")]
    welcome = guide.orientation(None, [], menu, newcomer=True)
    assert welcome.startswith("Te doy la bienvenida") and welcome.index("admisión") < welcome.index("becas")
    assert guide.is_orientation(welcome)
    assert guide.recommend_first(None, [], menu, newcomer=True).startswith("Te propongo empezar por la admisión")


@pytest.mark.parametrize("message", ["esto es una porquería, nunca responde nada", "esto no me ayuda", "no me sirve"])
def test_complaints_are_frustration(message: str) -> None:
    assert _intent(message) is ConversationIntent.FRUSTRATION


def test_how_does_the_university_work_is_not_about_the_assistant() -> None:
    assert _intent("no entiendo nada de cómo funciona la u") is not ConversationIntent.HOW_IT_WORKS
    assert _intent("¿Cómo funcionas?") is ConversationIntent.HOW_IT_WORKS


def test_final_audit_phrasings() -> None:
    tracker = _tracker()
    becas = tracker.replay(_history(("Háblame de las becas", "Hay varias becas…")))
    assert tracker.interpret("¿y cuánto me darían?", becas).aspect == "cobertura"
    assert tracker.interpret("quiero volver a estudiar", ConversationState()).topic == "reingreso"
    mother = tracker.interpret(
        "Buenos días, soy mamá de un estudiante de ingeniería. Quiero saber si puede cambiarse de carrera sin perder la beca",
        ConversationState(),
    )
    assert mother.audience == "padre de familia" and "Quiero saber" not in mother.retrieval_query
