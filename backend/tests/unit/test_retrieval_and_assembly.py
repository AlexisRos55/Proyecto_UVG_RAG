import pytest

from app.application.services.context_assembler import AssemblySettings, ContextAssembler
from app.application.services.knowledge_retriever import KnowledgeRetriever, RetrievalSettings
from app.domain.entities.chunk import RetrievedChunk
from app.domain.services.query_analyzer import QueryAnalyzer
from app.domain.value_objects.similarity_score import SimilarityScore
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.shared.kernel.ids import new_id
from tests.fakes.corpus_builders import chunk, retrieved
from tests.fakes.fake_rag_ports import FakeEmbeddingPort, FakeVectorStorePort

DOC = new_id()


def _retriever(dense: list[RetrievedChunk], index: InMemoryCorpusIndex | None, **settings) -> KnowledgeRetriever:
    return KnowledgeRetriever(
        FakeEmbeddingPort(), FakeVectorStorePort(seeded_results=dense), index, RetrievalSettings(**settings)
    )


@pytest.mark.asyncio
async def test_dense_mode_reproduces_the_frozen_baseline() -> None:
    kept = retrieved(chunk("relevante"), score=0.5)
    dropped = retrieved(chunk("irrelevante"), score=0.2)
    result = await _retriever([kept, dropped], None, hybrid=False).retrieve(QueryAnalyzer.analyze("x"))
    assert result == [kept]


@pytest.mark.asyncio
async def test_query_without_strong_evidence_abstains_before_the_llm() -> None:
    # Coseno 0.45 supera el umbral congelado (0.35) pero no es evidencia fuerte:
    # es justo lo que ocurría con «¿Cuál es la capital de Francia?» en el corpus real.
    index = InMemoryCorpusIndex()
    noise = chunk("Artículo 38. Capital de la asociación.", document_id=DOC)
    index.add([noise])
    result = await _retriever([retrieved(noise, score=0.45)], index).retrieve(
        QueryAnalyzer.analyze("¿Cuál es la capital de Francia?")
    )
    assert result == []


@pytest.mark.asyncio
async def test_lexical_evidence_admits_what_the_english_embedding_misses() -> None:
    index = InMemoryCorpusIndex()
    answer = chunk("5 de septiembre: Feria de becas II.", document_id=DOC)
    index.add([answer, chunk("Otro texto sin relación.", document_id=DOC, position=1)])
    result = await _retriever([], index).retrieve(QueryAnalyzer.analyze("¿Cuándo es la feria de becas?"))
    assert [item.chunk.id for item in result] == [answer.id]
    assert result[0].lexical_coverage == 1.0


@pytest.mark.asyncio
async def test_cited_article_is_admitted_and_boosted() -> None:
    index = InMemoryCorpusIndex()
    article = chunk("Texto del artículo.", document_id=DOC, article=58)
    other = chunk("Artículo sobre elecciones y votos.", document_id=DOC, article=10, position=1)
    index.add([article, other])
    result = await _retriever([retrieved(other, 0.6), retrieved(article, 0.2)], index).retrieve(
        QueryAnalyzer.analyze("¿Qué dice el artículo 58 sobre elecciones?")
    )
    assert result[0].chunk.id == article.id


@pytest.mark.asyncio
async def test_each_part_of_a_multi_part_question_gets_its_own_evidence() -> None:
    index = InMemoryCorpusIndex()
    schedule = chunk("Las elecciones son el jueves a las 10:00 horas.", document_id=DOC)
    club = chunk("La junta directiva del club tiene un mínimo de cinco integrantes.", document_id=DOC, position=1)
    index.add([schedule, club])
    analysis = QueryAnalyzer.analyze("¿A qué hora son las elecciones? ¿Cuántos integrantes tiene la junta del club?")
    result = await _retriever([], index, top_k=1).retrieve(analysis)
    assert {item.chunk.id for item in result} == {schedule.id, club.id}


def test_assembler_keeps_the_best_passage_even_when_it_is_last_in_the_document() -> None:
    # Regresión: el recorte a `max_passages` se aplicaba tras ordenar por
    # posición y descartaba el pasaje más relevante (Artículo 37 del corpus real).
    best = retrieved(chunk("Artículo 37. Casos no previstos.", document_id=DOC, position=99, article=37), 0.9)
    others = [retrieved(chunk(f"Texto {i}", document_id=DOC, position=i, article=i), 0.5) for i in range(10)]
    passages = ContextAssembler(settings=AssemblySettings(max_passages=3)).assemble([best, *others])
    assert best.chunk.id in {p.chunk.id for p in passages}
    assert len(passages) == 3


def test_assembler_drops_duplicates_and_respects_the_budget() -> None:
    first = retrieved(chunk("A" * 400, document_id=DOC))
    duplicate = retrieved(chunk("A" * 400, document_id=new_id()))
    third = retrieved(chunk("B" * 400, document_id=DOC, position=5))
    passages = ContextAssembler(settings=AssemblySettings(char_budget=500)).assemble([first, duplicate, third])
    assert [p.chunk.text for p in passages] == ["A" * 400]


def test_assembler_merges_adjacent_pieces_without_repeating_the_overlap() -> None:
    left = chunk("El estudiante debe presentar la solicitud en Registro Académico", document_id=DOC, position=0, article=5)
    right = chunk("en Registro Académico con treinta días de anticipación.", document_id=DOC, position=1, article=5)
    passages = ContextAssembler().assemble([retrieved(left), retrieved(right)])
    assert len(passages) == 1
    assert passages[0].chunk.text == (
        "El estudiante debe presentar la solicitud en Registro Académico con treinta días de anticipación."
    )
    assert set(passages[0].origin_ids) == {left.id, right.id}


def test_assembler_expands_a_short_article_to_its_full_text() -> None:
    index = InMemoryCorpusIndex()
    first = chunk("Artículo 19. Penalizaciones. Primera parte.", document_id=DOC, position=0, article=19)
    second = chunk("Segunda parte del mismo artículo.", document_id=DOC, position=1, article=19)
    index.add([first, second])
    passages = ContextAssembler(catalog=index).assemble([retrieved(second)])
    assert "Primera parte" in passages[0].chunk.text and "Segunda parte" in passages[0].chunk.text


def test_zero_budget_passes_chunks_through_unchanged() -> None:
    items = [RetrievedChunk(chunk=chunk("x"), score=SimilarityScore(0.4))]
    assert ContextAssembler(settings=AssemblySettings(char_budget=0)).assemble(items) == items
