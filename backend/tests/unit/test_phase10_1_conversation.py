"""Fase 10.1: comprensión de turnos reales (erratas, ordinales, «resúmelo», quién escribe)."""

from __future__ import annotations

from app.domain.entities.message import Message, MessageRole
from app.domain.services import conversation_guide as guide
from app.domain.services.conversation_tracker import ConversationTracker
from app.domain.services.entity_extractor import entity_key
from app.domain.services.evidence_reranker import is_anchored
from app.domain.services.institutional_lexicon import correct_typos
from app.domain.services.message_sanitizer import MessageSanitizer
from app.domain.services.query_analyzer import QueryAnalysis
from app.domain.value_objects.conversation_state import ConversationState, TurnMode
from app.domain.value_objects.corpus_entity import CorpusEntity, EntityKind
from app.domain.value_objects.source_reference import SourceReference
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk

AID, GROUPS = new_id(), new_id()
TRASCIENDE = CorpusEntity("Becas Trasciende", EntityKind.PROGRAM, entity_key("Becas Trasciende"), ("trasciend",), (AID,), ((AID, 28),))
DESPEGA = CorpusEntity("Beca Despega", EntityKind.PROGRAM, entity_key("Beca Despega"), ("despeg",), (AID,), ((AID, 29),))
TRANSFORMA = CorpusEntity("Beca Transforma", EntityKind.PROGRAM, entity_key("Beca Transforma"), ("transform",), (AID,), ((AID, 30),))
UMBRELLA = CorpusEntity("Programa de Ayudas Financieras", EntityKind.PROGRAM, entity_key("Programa de Ayudas Financieras"), ("ayud", "financier"), (AID,))
COMITE = CorpusEntity("Comité de Ayudas Financieras", EntityKind.OFFICE, entity_key("Comité de Ayudas Financieras"), ("ayud", "financier"), (AID,))
DIRECCION = CorpusEntity("Dirección de Ayudas Financieras", EntityKind.OFFICE, entity_key("Dirección de Ayudas Financieras"), ("ayud", "financier"), (AID,))


def _tracker() -> ConversationTracker:
    return ConversationTracker([TRASCIENDE, DESPEGA, TRANSFORMA, UMBRELLA, COMITE, DIRECCION])


def _history(*turns: tuple[str, str, bool | None, tuple[SourceReference, ...]]) -> list[Message]:
    conversation = new_id()
    messages: list[Message] = []
    for student, assistant, grounded, sources in turns:
        messages.append(Message(new_id(), conversation, MessageRole.STUDENT, student, utc_now()))
        messages.append(Message(new_id(), conversation, MessageRole.ASSISTANT, assistant, utc_now(), is_grounded=grounded, sources=sources))
    return messages


def _source(document_id, section: str | None = None) -> SourceReference:
    return SourceReference("doc.pdf", document_id=document_id, section=section)


AVE_LIST = ("Háblame de las becas AVE", "Están las Becas Trasciende, la Beca Despega y la Beca Transforma.", True, (_source(AID),))


def test_domain_typos_are_corrected_for_every_layer_but_the_original_is_kept() -> None:
    assert correct_typos("quiero saver de las bcas") == "quiero saber de las becas"
    assert correct_typos("becaz") == "becas" and correct_typos("veca") == "beca"
    assert correct_typos("la clave del portal") == "la clave del portal"  # palabras comunes intactas
    sanitized = MessageSanitizer.sanitize("requisito de inscripsion")
    assert sanitized.original == "requisito de inscripsion"
    assert "inscripcion" in sanitized.safe_for_prompt


def test_ordinals_and_la_otra_pick_from_the_last_list() -> None:
    tracker = _tracker()
    state = tracker.replay(_history(AVE_LIST))
    assert tracker.interpret("¿La primera?", state).entity == TRASCIENDE
    assert tracker.interpret("¿Y la segunda?", state).entity == DESPEGA
    history = _history(AVE_LIST, ("¿Y la segunda?", "La Beca Despega cubre…", True, (_source(AID),)))
    turn = tracker.interpret("¿Y la otra?", tracker.replay(history))
    assert turn.entity == TRANSFORMA and "despega" not in turn.retrieval_query.lower()


def test_otra_pregunta_is_a_topic_switch_not_an_ordinal() -> None:
    tracker = _tracker()
    turn = tracker.interpret("Otra pregunta: ¿cómo funcionan los clubes?", tracker.replay(_history(AVE_LIST)))
    assert turn.topic == "clubes" and turn.entity is None


def test_entities_that_share_words_do_not_become_a_phantom_comparison() -> None:
    turn = _tracker().interpret("¿Quién integra el Comité de Ayudas Financieras?", ConversationState())
    assert turn.entity == COMITE and not turn.compared


def test_the_umbrella_program_is_not_one_of_the_options() -> None:
    tracker = _tracker()
    history = _history(("Háblame de las becas", "El Programa de Ayudas Financieras incluye las Becas Trasciende y la Beca Despega.", True, (_source(AID),)))
    assert UMBRELLA not in tracker.replay(history).options


def test_summarize_continue_and_resume_are_told_apart() -> None:
    tracker = _tracker()
    answered = tracker.replay(_history(("Háblame de las becas", "Las becas…", True, (_source(AID),))))
    summary = tracker.interpret("¿Puedes resumir?", answered)
    assert summary.mode is TurnMode.DEEPEN and summary.wants_summary
    keep_going = tracker.interpret("Continúa", answered)
    assert keep_going.mode is TurnMode.DEEPEN and keep_going.continues
    paused = tracker.replay(_history(("Háblame de las becas", "Las becas…", True, (_source(AID),)), ("Gracias", "Con gusto.", None, ())))
    assert tracker.interpret("Continúa", paused).mode is TurnMode.RESUME


def test_a_bare_reference_without_antecedent_asks_instead_of_searching() -> None:
    tracker = _tracker()
    for message in ("¿Y eso?", "¿Cuál?", "¿La primera?", "requisitos", "¿Puedes resumir?"):
        assert tracker.interpret(message, ConversationState()).needs_clarification, message


def test_who_writes_changes_the_treatment_and_not_the_search() -> None:
    tracker = _tracker()
    turn = tracker.interpret("Soy papá de un estudiante, ¿mi hijo puede tener beca?", ConversationState())
    assert turn.audience == "padre de familia"
    assert "papá" not in turn.retrieval_query.lower() and "beca" in turn.retrieval_query.lower()
    intro = tracker.interpret("Soy mamá de una estudiante de primer ingreso", ConversationState())
    assert intro.needs_clarification and intro.audience == "padre de familia"


def test_the_question_carries_its_aspect_to_a_new_subject() -> None:
    tracker = _tracker()
    history = _history(("¿Cuándo inician las clases?", "El 18 de enero.", True, (_source(AID),)))
    turn = tracker.interpret("¿Y la graduación?", tracker.replay(history))
    assert turn.topic == "graduacion" and turn.aspect == "plazo"
    assert turn.reading and "¿Cuándo inician las clases?" in turn.reading


def test_ese_articulo_and_ese_reglamento_point_to_what_is_being_read() -> None:
    tracker = _tracker()
    history = _history(("Artículo 68", "El Artículo 68…", True, (_source(GROUPS, "Capítulo 2 · Artículo 68. En caso de empate"),)))
    state = tracker.replay(history)
    article = tracker.interpret("¿Ese artículo qué dice?", state)
    assert article.mode is TurnMode.ARTICLE_STEP and article.article_numbers == (68,)
    document = tracker.interpret("¿Ese reglamento quién lo aprobó?", state)
    assert document.document_reference and not document.required_terms


def test_lead_ins_are_not_searched() -> None:
    turn = _tracker().interpret("Cambiando de tema, ¿cuándo inician las clases?", ConversationState())
    assert not turn.retrieval_query.lower().startswith("cambiando")


def test_a_long_anchor_also_matches_inside_a_longer_word() -> None:
    analysis = QueryAnalysis(text="x", sub_queries=("x",), required_terms=("eleccion",))
    from app.domain.entities.chunk import RetrievedChunk
    from app.domain.value_objects.similarity_score import SimilarityScore

    item = RetrievedChunk(chunk=chunk("De la duración y la reelección de los cargos: un año."), score=SimilarityScore(0.5))
    assert is_anchored(item, analysis)


def test_guide_clarifies_dedupes_referrals_and_separates_records_from_rules() -> None:
    assert guide.clarify("aspecto sin tema: requisitos", None, ()) .startswith("¿Los requisitos de qué?")
    assert guide.clarify("presentación de padre de familia", None, (("las becas", "¿…?"),)).startswith("Con gusto le ayudo.")
    previous = "Dato.\n\nConviene confirmarlo en el campus."
    assert guide.drop_repeated_referral("Otro dato.\n\nPara más detalle, conviene consultar en el campus.", previous) == "Otro dato."
    assert "no registros de casos" in guide.not_a_record("las elecciones estudiantiles", None)
