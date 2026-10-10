from app.domain.services.document_navigator import DocumentNavigator
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk, retrieved

AID = new_id()
AID_DUPLICATE = new_id()
CALENDAR = new_id()


def _setup() -> tuple[DocumentNavigator, InMemoryCorpusIndex]:
    index = InMemoryCorpusIndex()
    rows = [
        chunk("Artículo 1. Objetivo General. El programa apoya a estudiantes talentosos con limitaciones económicas.",
              document_id=AID, position=0, chapter="Capítulo 1. Disposiciones generales", article=1,
              article_title="Objetivo General", page=3),
        chunk("Artículo 17. Cobertura. La beca cubre hasta el 50% de la colegiatura.", document_id=AID, position=1,
              chapter="Capítulo IV. Programas", article=17, article_title="Cobertura", page=9),
        chunk("Artículo 19. Penalizaciones. Se reduce la beca por cursos reprobados.", document_id=AID, position=2,
              chapter="Capítulo IV. Programas", article=19, article_title="Penalizaciones", page=11),
        chunk("5 de septiembre: Feria de becas II.", document_id=CALENDAR, title="Calendario académico", page=3),
    ]
    # Documento duplicado con el mismo título (existe en el corpus real).
    rows.append(chunk(rows[1].text, document_id=AID_DUPLICATE, position=1, chapter="Capítulo IV. Programas",
                      article=17, article_title="Cobertura", page=9))
    index.add(rows)
    names = {AID: "ayudas.pdf", AID_DUPLICATE: "ayudas_copia.pdf", CALENDAR: "calendario.pdf"}
    return DocumentNavigator(index.list_outlines(), names), index


def test_describe_uses_article_one_and_chapters_without_generating() -> None:
    navigator, _ = _setup()
    answer = navigator.describe(AID)
    assert "Según su Artículo 1: «El programa apoya" in answer.text
    assert "Capítulo IV. Programas (arts. 17–19)" in answer.text
    assert answer.sources[0].document_title == "Reglamento de ayudas financieras"


def test_outline_lists_chapters_with_article_ranges_and_pages() -> None:
    navigator, _ = _setup()
    text = navigator.outline(AID).text
    assert "2 capítulos y 3 artículos" in text
    assert "**Capítulo IV. Programas** (artículos 17 a 19, pág. 9)" in text
    assert "Artículo 19. Penalizaciones" in text


def test_locate_groups_hits_by_document_and_merges_duplicates() -> None:
    navigator, index = _setup()
    hits = [retrieved(hit.chunk) for hit in index.search("beca", 10)]
    answer = navigator.locate("becas", hits)
    assert answer.text.count("**Reglamento de ayudas financieras**") == 1
    assert "Capítulo IV · Artículo 17. Cobertura (pág. 9)" in answer.text
    assert "«5 de septiembre: Feria de becas II.»" in answer.text
    assert any(source.section and "Artículo 19" in source.section for source in answer.sources)


def test_clarifying_overview_suggests_real_subtopics() -> None:
    navigator, index = _setup()
    hits = [retrieved(hit.chunk) for hit in index.search("beca", 10)]
    text = navigator.locate("becas", hits, clarify=True).text
    assert "«Becas» aparece en varios apartados" in text
    assert "«cobertura»" in text and "«penalizaciones»" in text


def test_route_names_the_reference_document_and_what_it_covers() -> None:
    navigator, index = _setup()
    hits = [retrieved(hit.chunk) for hit in index.search("beca cobertura penalizaciones", 10)]
    text = navigator.route("becas", hits).text
    assert text.startswith("Para **becas**, el documento de referencia es el **Reglamento de ayudas financieras**")
    assert "los artículos 17 (Cobertura) y 19 (Penalizaciones)" in text or "artículo" in text


def test_ask_which_document_lists_distinct_titles_regulations_first() -> None:
    navigator, _ = _setup()
    answer = navigator.ask_which_document()
    assert answer.is_grounded is None
    assert answer.text.index("Reglamento de ayudas financieras") < answer.text.index("Calendario académico")
    assert answer.text.count("Reglamento de ayudas financieras") == 1


def test_nothing_found_is_reported_as_not_grounded() -> None:
    navigator, _ = _setup()
    assert navigator.locate("astronomía", []).is_grounded is False
