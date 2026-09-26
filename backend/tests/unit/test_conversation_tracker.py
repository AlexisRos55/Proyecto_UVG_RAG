"""Estado conversacional y resolución de referencias (capa de inteligencia de recuperación)."""

from __future__ import annotations

from collections.abc import Collection

from app.domain.entities.message import Message, MessageRole
from app.domain.services.conversation_tracker import (
    ConversationTracker,
    focus_label,
    pending_aspects,
)
from app.domain.services.entity_extractor import entity_key
from app.domain.value_objects.conversation_state import ConversationState, TurnMode
from app.domain.value_objects.corpus_entity import CorpusEntity, EntityKind
from app.domain.value_objects.source_reference import SourceReference
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

AID = new_id()
GROUPS = new_id()
DESPEGA = CorpusEntity("Beca Despega", EntityKind.PROGRAM, entity_key("Beca Despega"), ("despeg",), (AID,), ((AID, 29),))
REGULAR = CorpusEntity("Programa Regular", EntityKind.PROGRAM, entity_key("Programa Regular"), ("regul",), (AID,), ((AID, 13),))
ELECTORAL = CorpusEntity("Consejo Electoral", EntityKind.OFFICE, entity_key("Consejo Electoral"), ("electoral",), (GROUPS,))

# Coocurrencias mínimas del corpus: «directiva» aparece junto a «club»; «parqueo», con nada del tema.
_COOCCURRENCES = {("directiv", "club"), ("empat", "eleccion"), ("cuot", "educativ")}


def _co_occur(terms: Collection[str], context: Collection[str]) -> bool:
    return any((t, c) in _COOCCURRENCES for t in terms for c in context)


def _tracker() -> ConversationTracker:
    return ConversationTracker([DESPEGA, REGULAR, ELECTORAL], co_occur=_co_occur)


def _conversation(*turns: tuple[str, str, bool | None, tuple[SourceReference, ...]]) -> list[Message]:
    conversation_id = new_id()
    messages: list[Message] = []
    for student, assistant, grounded, sources in turns:
        messages.append(Message(new_id(), conversation_id, MessageRole.STUDENT, student, utc_now()))
        messages.append(
            Message(new_id(), conversation_id, MessageRole.ASSISTANT, assistant, utc_now(), is_grounded=grounded, sources=sources)
        )
    return messages


def _source(document_id, section: str | None = None) -> SourceReference:
    return SourceReference("doc.pdf", document_id=document_id, section=section)


def test_the_phase_nine_thread_keeps_its_topic_across_references() -> None:
    tracker = _tracker()
    history = _conversation(("Háblame de las becas.", "Hay varios programas: Programa Regular y Beca Despega.", True, (_source(AID),)))
    state = tracker.replay(history)
    assert state.topic == "becas"

    turn = tracker.interpret("¿Cuánto cubre esa?", state)
    assert turn.mode is TurnMode.FOLLOW_UP
    assert "becas" in turn.retrieval_query and "cobertura porcentaje" in turn.expansions
    assert turn.reading and "becas" in turn.reading and "cuánto cubre" in turn.reading

    history += _conversation(("¿Cuánto cubre esa?", "Depende del programa.", True, (_source(AID),)))
    for question, aspect_term in (
        ("¿Y cuáles son los requisitos?", "requisitos"),
        ("¿Hasta cuándo puedo aplicar?", "plazo"),
    ):
        turn = tracker.interpret(question, tracker.replay(history))
        assert turn.mode is TurnMode.FOLLOW_UP and "becas" in turn.retrieval_query
        assert any(aspect_term in expansion for expansion in turn.expansions)

    # «la beca» con tema propio sigue siendo una pregunta completa del mismo tema.
    turn = tracker.interpret("¿Pierdo la beca si bajo mi promedio?", tracker.replay(history))
    assert turn.topic == "becas" and turn.aspect == "consecuencias"


def test_social_turns_do_not_break_the_active_topic() -> None:
    tracker = _tracker()
    history = _conversation(
        ("Hola", "Hola.", None, ()),
        ("Becas", "La normativa trata becas en…", True, (_source(AID),)),
        ("Requisitos", "Los requisitos son…", True, (_source(AID),)),
        ("Gracias", "Con gusto.", None, ()),
        ("Hola", "Hola de nuevo.", None, ()),
    )
    state = tracker.replay(history)
    assert state.topic == "becas" and state.covered_aspects == ("requisitos",)
    assert tracker.interpret("Continuemos", state).mode is TurnMode.RESUME
    assert focus_label(state) == "las becas y ayudas financieras"
    assert "cuánto cubre" in pending_aspects(state)


def test_a_single_named_entity_in_the_answer_resolves_esa() -> None:
    tracker = _tracker()
    history = _conversation(("¿Qué ayudas hay para colaboradores?", "Existe la Beca Despega.", True, (_source(AID),)))
    turn = tracker.interpret("¿Cuánto cubre esa?", tracker.replay(history))
    assert turn.entity == DESPEGA
    assert "Beca Despega" in turn.retrieval_query
    assert turn.required_terms == ("despeg",)


def test_several_entities_in_the_answer_keep_the_question_at_topic_level() -> None:
    tracker = _tracker()
    history = _conversation(
        ("Háblame de las becas", "Están el Programa Regular y la Beca Despega.", True, (_source(AID),))
    )
    turn = tracker.interpret("¿Cuánto cubre esa?", tracker.replay(history))
    assert turn.entity is None and turn.topic == "becas"


def test_an_entity_stays_in_focus_and_the_enclitic_pronoun_is_resolved() -> None:
    tracker = _tracker()
    history = _conversation(("¿Qué es la beca Despega?", "Es una ayuda…", True, (_source(AID),)))
    turn = tracker.interpret("¿Y quién puede solicitarla?", tracker.replay(history))
    assert turn.entity == DESPEGA
    assert "solicitar" in turn.retrieval_query and "solicitarla" not in turn.retrieval_query


def test_a_new_topic_replaces_the_previous_one() -> None:
    tracker = _tracker()
    history = _conversation(("¿Cuál es el interés del crédito educativo?", "10% anual.", True, (_source(AID),)))
    turn = tracker.interpret("¿Y cuándo es la ceremonia de graduación?", tracker.replay(history))
    assert turn.mode is TurnMode.NEW and turn.topic == "graduacion"
    assert "credito" not in turn.retrieval_query.lower()


def test_a_back_pointing_pronoun_outweighs_a_generic_topic_word() -> None:
    tracker = _tracker()
    history = _conversation(("Quiero información sobre el crédito educativo", "El crédito…", True, (_source(AID),)))
    turn = tracker.interpret("¿Y en cuántas cuotas lo pago?", tracker.replay(history))
    assert turn.mode is TurnMode.FOLLOW_UP and turn.topic == "credito"


def test_a_noun_foreign_to_the_topic_starts_a_new_question() -> None:
    tracker = _tracker()
    history = _conversation(("¿Cómo se eligen los representantes estudiantiles?", "Por votación…", True, (_source(GROUPS),)))
    state = tracker.replay(history)
    assert tracker.interpret("¿Cuánto cuesta el parqueo?", state).mode is TurnMode.NEW
    # …pero una palabra del mismo tema sigue la conversación.
    assert tracker.interpret("¿Y si hay empate?", state).mode is TurnMode.FOLLOW_UP


def test_next_article_is_resolved_against_the_active_one() -> None:
    tracker = _tracker()
    history = _conversation(
        ("¿Qué dice el artículo 58 del reglamento de grupos?", "El Artículo 58…", True, (_source(GROUPS, "Artículo 58. Horario"),))
    )
    turn = tracker.interpret("¿Y el siguiente?", tracker.replay(history))
    assert turn.mode is TurnMode.ARTICLE_STEP and turn.article_numbers == (59,)


def test_deepen_reuses_the_last_internal_query() -> None:
    tracker = _tracker()
    history = _conversation(("¿Cuáles son los requisitos de las becas?", "Son…", True, (_source(AID),)))
    state = tracker.replay(history)
    turn = tracker.interpret("Explícalo mejor", state)
    assert turn.mode is TurnMode.DEEPEN and turn.retrieval_query == state.last_query


def test_an_abstained_topic_remains_the_focus_of_its_follow_ups() -> None:
    tracker = _tracker()
    history = _conversation(("Háblame del seguro médico estudiantil", "No encontré normativa…", False, ()))
    turn = tracker.interpret("¿Y cuánto cubre?", tracker.replay(history))
    assert turn.topic == "seguro" and "seguro" in turn.retrieval_query
    assert "poliz" in turn.required_terms  # «segur» también es la raíz de «seguridad»


def test_overview_expands_with_corpus_programs_and_their_defining_articles() -> None:
    turn = _tracker().interpret("Háblame de las becas", ConversationState())
    assert turn.is_overview
    assert set(turn.expansions) == {"Beca Despega", "Programa Regular"}
    assert set(turn.defining_articles) == {(AID, 29), (AID, 13)}


def test_explicit_messages_are_never_rewritten_as_follow_ups() -> None:
    state = ConversationState(topic="becas")
    turn = _tracker().interpret("¿Qué hace el Consejo Electoral?", state)
    assert turn.mode is TurnMode.NEW and turn.entity == ELECTORAL


def test_a_long_conversation_does_not_forget_its_topic() -> None:
    tracker = _tracker()
    history = _conversation(("Háblame de las becas", "…", True, (_source(AID),)))
    for _ in range(20):
        history += _conversation(("Explícalo", "…", True, (_source(AID),)), ("Gracias", "Con gusto.", None, ()))
    assert tracker.replay(history).topic == "becas"


def test_memory_fades_after_a_long_silence_but_survives_until_tomorrow() -> None:
    from datetime import timedelta

    tracker = _tracker()
    history = _conversation(("Háblame de las becas", "…", True, (_source(AID),)))
    tomorrow = _conversation(("Hola", "Hola de nuevo.", None, ()))
    for message in tomorrow:
        message.created_at = message.created_at + timedelta(days=1)
    assert tracker.replay(history + tomorrow).topic == "becas"
    next_month = _conversation(("Hola", "Hola.", None, ()))
    for message in next_month:
        message.created_at = message.created_at + timedelta(days=30)
    assert tracker.replay(history + next_month).topic is None


def test_article_references_navigate_and_deepen_without_the_model() -> None:
    tracker = _tracker()
    history = _conversation(("Háblame del reglamento de grupos", "El reglamento…", True, (_source(GROUPS),)))
    turn = tracker.interpret("Artículo 20", tracker.replay(history))
    assert turn.mode is TurnMode.ARTICLE_STEP and turn.article_numbers == (20,)

    history += _conversation(("Artículo 20", "El Artículo 20…", True, (_source(GROUPS, "Artículo 20. De los Fines"),)))
    state = tracker.replay(history)
    assert tracker.interpret("¿Y el anterior?", state).article_numbers == (19,)
    why = tracker.interpret("¿Por qué?", state)
    assert why.mode is TurnMode.DEEPEN and why.article_numbers == (20,)
    example = tracker.interpret("Dame un ejemplo", state)
    assert example.wants_example and example.article_numbers == (20,)


def test_after_a_ranking_question_esa_is_the_winner_named_first() -> None:
    tracker = _tracker()
    history = _conversation(
        ("Háblame de las becas", "Están el Programa Regular y la Beca Despega.", True, (_source(AID),)),
        ("¿Cuál cubre más?", "La Beca Despega cubre hasta 15%; el Programa Regular depende del estudio.", True, (_source(AID),)),
    )
    turn = tracker.interpret("¿Y esa tiene requisitos?", tracker.replay(history))
    assert turn.entity == DESPEGA


def test_a_new_career_replaces_the_previous_one_in_the_same_question() -> None:
    tracker = _tracker()
    history = _conversation(
        ("¿Qué becas existen?", "Programa Regular y Beca Despega.", True, (_source(AID),)),
        ("¿Cuál conviene más para Ingeniería?", "Depende…", True, (_source(AID),)),
    )
    turn = tracker.interpret("¿Y para Tecnología?", tracker.replay(history))
    query = turn.retrieval_query.lower()
    assert "tecnolog" in query and "ingenier" not in query and "beca" in query


def test_see_you_later_is_not_a_search() -> None:
    tracker = _tracker()
    history = _conversation(("Háblame de las becas", "…", True, (_source(AID),)))
    turn = tracker.interpret("Continuemos mañana", tracker.replay(history))
    assert not turn.retrieval_query


# --- Fase 10: memoria de conversación humana ---------------------------------------

TRASCIENDE = CorpusEntity("Becas Trasciende", EntityKind.PROGRAM, entity_key("Becas Trasciende"), ("trasciend",), (AID,), ((AID, 28),))
CLUBS_SOURCE = new_id()


def _tracker10() -> ConversationTracker:
    return ConversationTracker([DESPEGA, REGULAR, ELECTORAL, TRASCIENDE], co_occur=_co_occur)


def test_a_third_person_object_pronoun_keeps_the_topic() -> None:
    tracker = _tracker10()
    history = _conversation(("¿Cómo funcionan las elecciones estudiantiles?", "Por votación…", True, (_source(GROUPS),)))
    turn = tracker.interpret("¿Quién las organiza?", tracker.replay(history))
    assert turn.mode is TurnMode.FOLLOW_UP and turn.topic == "elecciones"


def test_the_pronoun_carries_the_object_of_the_previous_question() -> None:
    tracker = _tracker10()
    history = _conversation(
        ("Quiero cambiar de carrera", "El cambio de carrera…", True, (_source(AID),)),
        ("¿Necesito autorización?", "Sí, de la entidad patrocinadora.", True, (_source(AID),)),
    )
    turn = tracker.interpret("¿Quién la da?", tracker.replay(history))
    assert "autorización" in turn.retrieval_query and "carrera" in turn.retrieval_query
    assert turn.reading and "¿Necesito autorización?" in turn.reading


def test_a_clitic_does_not_bind_the_single_option_named_in_passing() -> None:
    tracker = _tracker10()
    history = _conversation(("Háblame de las becas", "Está el Programa Regular.", True, (_source(AID),)))
    assert tracker.interpret("¿Quién lo decide?", tracker.replay(history)).entity is None
    assert tracker.interpret("¿Cuánto cubre esa?", tracker.replay(history)).entity == REGULAR


def test_esa_beca_de_antes_returns_to_the_scholarship_after_another_topic() -> None:
    tracker = _tracker10()
    history = _conversation(
        ("¿Qué es la beca Despega?", "La Beca Despega…", True, (_source(AID),)),
        ("Háblame de los clubes", "Los clubes…", True, (_source(CLUBS_SOURCE),)),
    )
    turn = tracker.interpret("¿Y esa beca de antes pide promedio?", tracker.replay(history))
    assert turn.entity == DESPEGA and "Beca Despega" in turn.retrieval_query
    assert "club" not in turn.retrieval_query.lower()


def test_esa_oficina_is_the_office_named_in_the_last_answer() -> None:
    tracker = _tracker10()
    history = _conversation(
        ("¿Quién organiza las elecciones estudiantiles?", "Las organiza el Consejo Electoral.", True, (_source(GROUPS),))
    )
    turn = tracker.interpret("¿Y esa oficina qué más hace?", tracker.replay(history))
    assert turn.entity == ELECTORAL


def test_a_comparison_searches_each_option_and_stays_in_play() -> None:
    tracker = _tracker10()
    first = tracker.interpret("¿Qué diferencia hay entre la Beca Despega y la Beca Trasciende?", ConversationState())
    assert set(first.compared) == {DESPEGA, TRASCIENDE} and len(first.sub_queries) == 2
    assert set(first.defining_articles) == {(AID, 29), (AID, 28)}
    history = _conversation(
        ("¿Qué diferencia hay entre la Beca Despega y la Beca Trasciende?", "La Beca Despega… Becas Trasciende…", True, (_source(AID),))
    )
    turn = tracker.interpret("¿Y cuál me conviene si trabajo en una empresa aliada?", tracker.replay(history))
    assert set(turn.compared) == {DESPEGA, TRASCIENDE}
    assert "Despega" in turn.retrieval_query and "Trasciende" in turn.retrieval_query


def test_a_bare_which_chooses_among_the_options_just_named() -> None:
    tracker = _tracker10()
    history = _conversation(("Háblame de las becas", "Están el Programa Regular y la Beca Despega.", True, (_source(AID),)))
    turn = tracker.interpret("¿Cuál pide más requisitos?", tracker.replay(history))
    assert set(turn.compared) == {REGULAR, DESPEGA}


def test_returning_to_a_previous_topic_reads_the_rest_inside_it() -> None:
    tracker = _tracker10()
    history = _conversation(
        ("¿Cómo funcionan las elecciones estudiantiles?", "Por votación…", True, (_source(GROUPS),)),
        ("Háblame del crédito educativo", "El crédito…", True, (_source(AID),)),
    )
    turn = tracker.interpret("Volviendo a las elecciones, ¿y si hay empate?", tracker.replay(history))
    assert turn.topic == "elecciones" and "empate" in turn.retrieval_query
    assert "credito" not in turn.retrieval_query.lower()


def test_no_entiendo_explains_again_more_simply_and_lost_students_are_oriented() -> None:
    tracker = _tracker10()
    history = _conversation(("Háblame de las becas", "Las becas…", True, (_source(AID),)))
    confused = tracker.interpret("no entiendo", tracker.replay(history))
    assert confused.mode is TurnMode.DEEPEN and confused.simpler
    assert tracker.interpret("no entiendo", ConversationState()).needs_orientation
    assert tracker.interpret("estoy perdido, no sé qué preguntar", tracker.replay(history)).needs_orientation


def test_an_abstention_is_not_remembered_as_a_covered_aspect() -> None:
    tracker = _tracker10()
    history = _conversation(
        ("Háblame de las becas", "Las becas…", True, (_source(AID),)),
        ("¿Y cuándo puedo aplicar?", "No encontré…", False, ()),
    )
    assert "plazo" not in tracker.replay(history).covered_aspects


def test_entities_are_named_with_their_article() -> None:
    assert DESPEGA.spoken == "la Beca Despega"
    assert TRASCIENDE.spoken == "las Becas Trasciende"
    assert ELECTORAL.spoken == "el Consejo Electoral"
    assert REGULAR.spoken == "el Programa Regular"


def test_a_generic_phrase_does_not_name_an_office_as_an_option() -> None:
    comite = CorpusEntity("Comité de Ayudas Financieras", EntityKind.OFFICE, entity_key("Comité de Ayudas Financieras"), ("ayud", "financier"), (AID,))
    tracker = ConversationTracker([DESPEGA, REGULAR, comite], co_occur=_co_occur)
    history = _conversation(
        ("¿Qué becas existen?", "Toda ayuda financiera se otorga así: el Programa Regular y la Beca Despega.", True, (_source(AID),))
    )
    state = tracker.replay(history)
    assert comite not in state.candidates and set(state.candidates) == {REGULAR, DESPEGA}


def test_a_financial_need_in_own_words_opens_the_scholarship_overview() -> None:
    turn = _tracker10().interpret("es que no sé si me alcanza para pagar la carrera", ConversationState())
    assert turn.topic == "becas" and turn.is_overview
