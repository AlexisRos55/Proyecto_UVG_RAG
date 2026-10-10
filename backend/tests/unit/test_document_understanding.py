"""Comprensión documental: entidades, ficha del documento, reordenamiento y forma de respuesta."""

from __future__ import annotations

from app.domain.services import answer_planner
from app.domain.services.entity_extractor import EntityExtractor, find_entities
from app.domain.services.evidence_reranker import is_anchored, structural_bonus
from app.domain.services.message_sanitizer import MessageSanitizer
from app.domain.services.query_analyzer import QueryAnalysis
from app.domain.value_objects.conversation_intent import ConversationIntent
from app.domain.value_objects.conversation_state import TurnInterpretation, TurnMode
from app.domain.value_objects.corpus_entity import EntityKind
from app.domain.value_objects.response_plan import ResponseStyle
from app.infrastructure.adapters.document_processing.page_boilerplate import document_card
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk, retrieved

DOC = new_id()


def _corpus():
    return [
        chunk("Artículo 29. Beca Despega. Ayuda financiera para colaboradores.", document_id=DOC, article=29,
              article_title="Beca Despega"),
        chunk("La Oficina de Vida Estudiantil coordina. La Oficina de Vida Estudiantil aprueba. "
              "La Oficina de Vida\\nEstudiantil informa.", document_id=DOC, position=1),
        chunk("El Consejo Electoral decide. El Consejo Electoral proclama. Becas CONADER UVG.", document_id=DOC, position=2),
        chunk("Crédito Educativo. Crédito Educativo. Crédito Educativo Apoyo Especial Juan", document_id=DOC, position=3),
    ]


def test_extracts_programs_and_offices_and_consolidates_truncated_names() -> None:
    entities = {(e.kind, e.name) for e in EntityExtractor.extract(_corpus())}
    assert (EntityKind.PROGRAM, "Beca Despega") in entities
    assert (EntityKind.PROGRAM, "Becas CONADER") in entities
    assert (EntityKind.PROGRAM, "Crédito Educativo") in entities
    assert (EntityKind.OFFICE, "Consejo Electoral") in entities
    assert (EntityKind.OFFICE, "Oficina de Vida Estudiantil") in entities
    names = {name for _, name in entities}
    assert "Oficina de Vida" not in names  # truncado por salto de línea
    assert "Crédito Educativo Apoyo Especial Juan" not in names  # celda vecina de una tabla


def test_the_defining_article_of_an_entity_is_recorded() -> None:
    despega = next(e for e in EntityExtractor.extract(_corpus()) if e.name == "Beca Despega")
    assert despega.defined_in == ((DOC, 29),)


def test_entity_matching_requires_the_category_word_for_weak_names() -> None:
    entities = EntityExtractor.extract(_corpus())
    assert [e.name for e in find_entities("¿Qué es la beca Despega?", entities)] == ["Beca Despega"]
    assert find_entities("junta directiva del consejo", entities) == [] or all(
        e.name != "Consejo Directivo" for e in find_entities("junta directiva", entities)
    )
    assert [e.name for e in find_entities("¿qué hace el consejo electoral?", entities)] == ["Consejo Electoral"]


def test_document_card_preserves_letterhead_data_once_and_extracts_authorities() -> None:
    header = (
        "Código:", "UVG.DAF.02.001", "Versión:", "10.0", "Revisó:",
        "Henry Jiménez Soto – Director de Ayudas Financieras", "María Alquijay – Decana de Admisiones",
        "Página 3 de 20", "REGLAMENTO DE AYUDAS FINANCIERAS",
    )
    card = document_card(header, "Reglamento de ayudas financieras")
    assert card is not None
    assert "Código: UVG.DAF.02.001" in card and "Versión: 10.0" in card
    assert "Henry Jiménez Soto – Director de Ayudas Financieras; María Alquijay – Decana de Admisiones" in card
    assert "Página" not in card
    card_chunk = chunk(card, document_id=DOC, section="Ficha del documento")
    persons = [e.name for e in EntityExtractor.extract([card_chunk]) if e.kind is EntityKind.PERSON]
    assert persons == ["Henry Jiménez Soto", "María Alquijay"]


def test_reranker_rewards_focus_entity_and_topic_scoped_aspect() -> None:
    k = 60
    requisitos_becas = retrieved(chunk("Requisitos para la beca.", article=16, article_title="Requisitos"))
    requisitos_clubes = retrieved(chunk("Requisitos para formar un club.", article=88, article_title="Requisitos",
                                        title="Reglamento de grupos estudiantiles"))
    analysis = QueryAnalysis(text="x", sub_queries=("x",), aspect_title_words=("requisitos",), topic_terms=("bec",))
    assert structural_bonus(requisitos_becas, analysis, k) > structural_bonus(requisitos_clubes, analysis, k)


def test_follow_up_evidence_must_mention_the_inherited_focus() -> None:
    analysis = QueryAnalysis(text="x", sub_queries=("x",), required_terms=("segur",))
    assert not is_anchored(retrieved(chunk("La cobertura de la beca es 50%.")), analysis)
    assert is_anchored(retrieved(chunk("El seguro cubre accidentes.")), analysis)


def _turn(**fields) -> TurnInterpretation:
    return TurnInterpretation(message="x", mode=fields.pop("mode", TurnMode.FOLLOW_UP), retrieval_query="x", **fields)


def test_answer_planner_uses_the_evidence_to_choose_the_form() -> None:
    passages = [retrieved(chunk("t", article=n, article_title="Cobertura")) for n in (17, 24, 32)]
    assert answer_planner.plan_style(ResponseStyle.UNSPECIFIED, _turn(aspect="cobertura"), passages) is ResponseStyle.PER_ITEM
    assert answer_planner.plan_style(ResponseStyle.UNSPECIFIED, _turn(mode=TurnMode.NEW, is_overview=True), []) is ResponseStyle.OVERVIEW
    assert answer_planner.plan_style(ResponseStyle.UNSPECIFIED, _turn(mode=TurnMode.DEEPEN), []) is ResponseStyle.EXPLANATION
    assert answer_planner.plan_style(ResponseStyle.STEPS, _turn(aspect="cobertura"), passages) is ResponseStyle.STEPS


def test_classifier_reads_hypotheticals_continuations_and_domain_topics() -> None:
    classify = RuleBasedIntentClassifier().classify
    assert classify(MessageSanitizer.normalize("¿Pierdo la beca si bajo mi promedio?")).intent is ConversationIntent.INSTITUTIONAL_QUERY
    assert classify(MessageSanitizer.normalize("¿Cuál es mi promedio?")).intent is ConversationIntent.PERSONAL_DATA
    assert classify(MessageSanitizer.normalize("Continuemos")).intent is ConversationIntent.CONTINUATION
    assert classify(MessageSanitizer.normalize("Profundiza")).intent is ConversationIntent.FOLLOW_UP
    assert classify(MessageSanitizer.normalize("¿Cómo funcionan las elecciones estudiantiles?")).intent is ConversationIntent.INSTITUTIONAL_QUERY


def test_matrix_tables_that_lost_their_marks_are_annotated() -> None:
    from app.infrastructure.adapters.document_processing.table_annotations import (
        MATRIX_NOTICE,
        annotate_matrix_tables,
    )

    header = (
        "Requisitos Beca Programa Regular Crédito Educativo Beca Potencia- T Liderazgo en Negocios "
        "Juan Bautista Gutiérrez Patrocinador específico\nSer estudiante admitido."
    )
    assert annotate_matrix_tables(header).endswith(MATRIX_NOTICE)
    assert annotate_matrix_tables("Artículo 29. Beca Despega. Cubre hasta un 15%.") == "Artículo 29. Beca Despega. Cubre hasta un 15%."


def test_voice_guard_removes_system_vocabulary_without_touching_content() -> None:
    from app.domain.services.voice_guard import enforce_institutional_voice

    assert enforce_institutional_voice(
        "La normativa no especifica los porcentajes en los fragmentos disponibles. Consulta en Registro."
    ) == "La normativa no especifica los porcentajes. Consulta en Registro."
    assert enforce_institutional_voice("Según la información disponible, cubre 50% [2].") == "Según la normativa, cubre 50%."
    assert enforce_institutional_voice("El Artículo 18 establece 65 puntos.") == "El Artículo 18 establece 65 puntos."


def test_every_piece_of_an_article_with_a_lossy_table_is_annotated() -> None:
    from app.infrastructure.adapters.document_processing.table_annotations import (
        MATRIX_NOTICE,
        annotate_matrix_units,
    )

    header = "Condiciones Beca Programa Regular Crédito Educativo Beca Potencia Liderazgo Patrocinador"
    texts = annotate_matrix_units(
        [header, "Mantener un promedio mínimo de 65 puntos.", "Artículo 20. Otro tema."],
        ["art:18-18", "art:18-18", "art:20-20"],
    )
    assert texts[0].endswith(MATRIX_NOTICE) and texts[1].endswith(MATRIX_NOTICE)
    assert MATRIX_NOTICE not in texts[2]
