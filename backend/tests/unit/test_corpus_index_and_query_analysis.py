from app.domain.services.query_analyzer import QueryAnalyzer
from app.domain.services.rank_fusion import reciprocal_rank_fusion
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk

AID = new_id()
GROUPS = new_id()
CALENDAR = new_id()


def _index() -> InMemoryCorpusIndex:
    index = InMemoryCorpusIndex()
    index.add(
        [
            chunk("Artículo 1. Objetivo General. El programa apoya a estudiantes con limitaciones económicas.",
                  document_id=AID, position=0, chapter="Capítulo 1. Disposiciones generales", article=1,
                  article_title="Objetivo General", page=3),
            chunk("Artículo 12. Horas Beca. Los estudiantes favorecidos con beca prestan horas de servicio.",
                  document_id=AID, position=1, chapter="Capítulo III. Administración", article=12,
                  article_title="Horas Beca", page=6),
            chunk("Artículo 19. Penalizaciones. Se reduce el % de beca por cursos reprobados o retirados.",
                  document_id=AID, position=2, chapter="Capítulo IV. Programas", article=19,
                  article_title="Penalizaciones", page=11),
            chunk("9.0 Acta 06-2025. Se modifica el plazo del crédito educativo.", document_id=AID, position=3,
                  section="Control de Cambios", page=21),
            chunk("Artículo 58. Horario. Las elecciones se realizan el jueves a las 10:00 horas.",
                  document_id=GROUPS, title="Reglamento de grupos estudiantiles", position=0,
                  chapter="Capítulo 2. De las asociaciones", article=58, article_title="Horario", page=20),
            chunk("5 de septiembre: Feria de becas II. 17 de septiembre: último día para pagar la cuota.",
                  document_id=CALENDAR, title="Calendario académico", position=0, page=3),
        ]
    )
    return index


def test_bm25_ranks_literal_matches_and_reports_idf_weighted_coverage() -> None:
    hits = _index().search("¿A qué hora son las elecciones?", 3)
    assert hits[0].chunk.anchor.article_from == 58
    assert hits[0].coverage > 0.5


def test_typos_are_corrected_against_the_corpus_vocabulary() -> None:
    hits = _index().search("penalisaciones de la veca", 2)
    assert hits[0].chunk.anchor.article_from == 19


def test_coordination_factor_keeps_expansions_from_burying_literal_matches() -> None:
    # «ayuda financiera» (expansión de «becas») no debe superar a «Feria de becas».
    hits = _index().search("¿Cuándo es la feria de becas?", 3, expansions=("ayuda financiera", "beca"))
    assert hits[0].chunk.document_id == CALENDAR


def test_document_filter_restricts_results() -> None:
    hits = _index().search("beca", 5, document_ids={CALENDAR})
    assert {hit.chunk.document_id for hit in hits} == {CALENDAR}


def test_catalog_builds_outlines_with_chapters_articles_and_extractive_summary() -> None:
    outline = _index().get_outline(AID)
    assert outline is not None
    assert [division.label for division in outline.divisions] == [
        "Capítulo 1. Disposiciones generales",
        "Capítulo III. Administración",
        "Capítulo IV. Programas",
        "Control de Cambios",
    ]
    assert outline.article_count == 3
    assert outline.summary is not None and outline.summary.startswith("El programa apoya")


def test_removing_a_document_updates_search_and_catalog() -> None:
    index = _index()
    index.remove_document(CALENDAR)
    assert index.get_outline(CALENDAR) is None
    assert all(hit.chunk.document_id != CALENDAR for hit in index.search("feria", 5))


def test_index_reloads_when_the_persistent_collection_changes_size() -> None:
    stored = [chunk("Artículo 1. Objeto. Texto.", document_id=AID)]
    index = InMemoryCorpusIndex(loader=lambda: list(stored), size_probe=lambda: len(stored))
    assert len(index.list_outlines()) == 1
    stored.append(chunk("Feria de becas", document_id=CALENDAR, title="Calendario"))
    assert len(index.list_outlines()) == 2


def test_rrf_rewards_agreement_and_supports_weights() -> None:
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=60)
    assert fused["b"] > fused["a"] > fused["c"]
    weighted = reciprocal_rank_fusion([["a"], ["c"]], k=60, weights=[1.0, 0.5])
    assert weighted["a"] > weighted["c"]


def test_analyzer_resolves_explicit_mentions_articles_and_changes() -> None:
    outlines = _index().list_outlines()
    analysis = QueryAnalyzer.analyze("¿Qué cambios tuvo el reglamento de grupos estudiantiles en el art. 58?", outlines)
    assert analysis.target_documents == (GROUPS,)
    assert analysis.article_numbers == (58,)
    assert analysis.asks_for_changes and "control de cambios" in analysis.expansions


def test_analyzer_uses_conversation_topic_for_deictic_references() -> None:
    outlines = _index().list_outlines()
    analysis = QueryAnalyzer.analyze("¿De qué trata este reglamento?", outlines, conversation_documents=(AID,))
    assert analysis.target_documents == (AID,)


def test_analyzer_splits_multiple_questions_and_strips_pleasantries() -> None:
    analysis = QueryAnalyzer.analyze(
        "Hola, buenas tardes. ¿Cuál es el horario de las elecciones y cuántos miembros tiene un club? Muchas gracias."
    )
    assert analysis.sub_queries == ("Cuál es el horario de las elecciones", "cuántos miembros tiene un club")
    assert "Hola" not in analysis.text and "gracias" not in analysis.text


def test_analyzer_extracts_the_topic_of_navigational_questions() -> None:
    assert QueryAnalyzer.analyze("¿Qué artículos hablan del seguro?").topic == "seguro"
    assert QueryAnalyzer.analyze("¿Dónde habla sobre becas?").topic == "becas"


def test_consequence_questions_expand_towards_penalties() -> None:
    analysis = QueryAnalyzer.analyze("¿Qué pasa si no cumplo con las horas beca?")
    assert "penalizaciones" in analysis.expansions


def test_date_questions_prefer_the_academic_calendar_without_restricting_to_it() -> None:
    index = InMemoryCorpusIndex()
    index.add([
        chunk("5 de septiembre: Feria de becas II.", document_id=CALENDAR, title="Calendario académico"),
        chunk("Artículo 12. Horas beca.", document_id=AID, article=12),
    ])
    outlines = index.list_outlines()
    analysis = QueryAnalyzer.analyze("¿Cuál es la fecha límite para retirar cursos?", outlines)
    assert CALENDAR in analysis.preferred_documents and analysis.target_documents == ()
    assert CALENDAR not in QueryAnalyzer.analyze("¿Qué son las horas beca?", outlines).preferred_documents
