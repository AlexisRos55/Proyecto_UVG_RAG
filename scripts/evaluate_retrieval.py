"""Evaluación offline de la RECUPERACIÓN, sin LLM ni costo de API (Fase 9, ADR-0012).

Complementa a `scripts/evaluate.py` (RAGAS, extremo a extremo y con costo): aquí se
mide únicamente si el contexto que llegaría al modelo contiene la evidencia
necesaria. Permite comparar configuraciones del pipeline —incluida la línea base
congelada— sobre exactamente el mismo corpus, de forma reproducible y gratuita.

Configuraciones (ablación de una variable a la vez):
    baseline          fragmentos fijos 1000/100, solo coseno, contexto sin presupuesto (congelada)
    fixed_hybrid      fragmentos fijos + recuperación híbrida y ensamblado de contexto
    structural_dense  ingesta estructural + solo coseno
    enhanced          ingesta estructural + híbrida + ensamblado (configuración por defecto)

Métricas por configuración:
    hit@1             el primer fragmento contiene evidencia
    recall@5          fracción de hechos cubiertos por los 5 primeros fragmentos
    mrr               rango recíproco del primer fragmento con evidencia
    context_recall    fracción de hechos presentes en el contexto final que ve el modelo
    context_chars     tamaño medio de ese contexto (aproximación del costo en tokens)
    no_evidence_ok    fuera de dominio: fracción sin evidencia admitida (abstención sin LLM)
    false_abstention  en dominio: fracción sin ninguna evidencia admitida

Uso:
    python scripts/evaluate_retrieval.py --corpus-dir <carpeta con los PDF> \
        [--benchmark scripts/retrieval_benchmark.json] [--configs baseline,enhanced] [--details]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.domain.entities.chunk import RetrievedChunk
from app.domain.services.conversation_tracker import ConversationTracker
from app.domain.services.query_analyzer import QueryAnalyzer
from app.domain.services.spanish_text import fold
from app.domain.value_objects.conversation_state import ConversationState
from app.infrastructure.adapters.document_processing.pymupdf_extractor import (
    PyMuPDFExtractorAdapter,
)
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.infrastructure.adapters.search.synchronized_vector_store import SynchronizedVectorStore
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.config.settings import RagSettings
from app.infrastructure.rag_factory import (
    build_context_assembler,
    build_indexing_pipeline,
    build_retriever,
)

DEFAULT_BENCHMARK = Path(__file__).parent / "retrieval_benchmark.json"
CONFIGURATIONS: dict[str, dict[str, object]] = {
    "baseline": {"chunking_strategy": "fixed", "retrieval_mode": "dense", "context_char_budget": 0},
    "fixed_hybrid": {"chunking_strategy": "fixed", "retrieval_mode": "hybrid"},
    "structural_dense": {"chunking_strategy": "structural", "retrieval_mode": "dense", "context_char_budget": 0},
    "enhanced": {},
    # Fase 10: el camino desplegado para una primera pregunta: analizador + la
    # interpretación del rastreador conversacional (tema, aspecto, entidad,
    # comparación), exactamente como lo aplica el caso de uso.
    "conversational": {},
}
_CONVERSATIONAL = {"conversational"}


def _normalize(text: str) -> str:
    return " ".join(fold(text).split())


@dataclass
class CaseResult:
    case_id: str
    category: str
    ranked_hits: list[bool]
    facts_in_top5: float
    facts_in_context: float
    context_chars: int
    admitted: int
    expects_evidence: bool
    latency: float
    missing: list[str] = field(default_factory=list)


class _Corpus:
    """Un índice por estrategia de fragmentación, compartido por las configuraciones que la usan."""

    def __init__(self, corpus_dir: Path, embedding: SentenceTransformersEmbeddingAdapter) -> None:
        self._corpus_dir = corpus_dir
        self._embedding = embedding
        self._built: dict[str, tuple[SynchronizedVectorStore, InMemoryCorpusIndex]] = {}

    async def for_settings(self, settings: RagSettings) -> tuple[SynchronizedVectorStore, InMemoryCorpusIndex]:
        key = settings.chunking_strategy
        if key not in self._built:
            directory = tempfile.mkdtemp(prefix=f"retrieval_eval_{key}_")
            chroma = ChromaVectorStoreAdapter(persist_directory=directory, collection_name=f"eval_{key}")
            index = InMemoryCorpusIndex()
            store = SynchronizedVectorStore(chroma, index)
            pipeline = build_indexing_pipeline(PyMuPDFExtractorAdapter(), self._embedding, store, settings)
            started = time.perf_counter()
            total = 0
            for pdf in sorted(self._corpus_dir.glob("*.pdf")):
                chunks = await pipeline.process(uuid4(), pdf, display_name=pdf.name)
                total += len(chunks)
            print(f"  [{key}] {total} fragmentos indexados en {time.perf_counter() - started:.1f}s")
            self._built[key] = (store, index)
        return self._built[key]


async def evaluate(config: str, settings: RagSettings, corpus: _Corpus, cases: list[dict]) -> list[CaseResult]:
    store, index = await corpus.for_settings(settings)
    lexical = index if settings.retrieval_mode == "hybrid" else None
    retriever = build_retriever(corpus._embedding, store, lexical, settings)
    assembler = build_context_assembler(index, settings)
    outlines = index.list_outlines()

    tracker = ConversationTracker(index.entities(), index.vocabulary, index.co_occur) if config in _CONVERSATIONAL else None
    results: list[CaseResult] = []
    for case in cases:
        started = time.perf_counter()
        scale = 1.0
        if tracker is None:
            analysis = QueryAnalyzer.analyze(case["question"], outlines)
        else:
            state = ConversationState()
            turn = tracker.interpret(case["question"], state)
            query = turn.retrieval_query or case["question"]
            analysis = AnswerStudentQueryUseCase._enrich(QueryAnalyzer.analyze(query, outlines), turn, state)
            scale = AnswerStudentQueryUseCase._context_scale(turn)
        ranked = await retriever.retrieve(analysis)
        context = assembler.assemble(ranked, parts=len(analysis.sub_queries), scale=scale)
        latency = time.perf_counter() - started
        results.append(_score(case, ranked, context, latency))
    return results


def _score(case: dict, ranked: list[RetrievedChunk], context: list[RetrievedChunk], latency: float) -> CaseResult:
    facts = [[_normalize(alternative) for alternative in fact] for fact in case["facts"]]

    def satisfied(texts: list[str]) -> list[bool]:
        joined = [_normalize(text) for text in texts]
        return [any(alt in text for text in joined for alt in fact) for fact in facts]

    ranked_texts = [item.chunk.text for item in ranked]
    ranked_hits = [any(any(alt in _normalize(text) for alt in fact) for fact in facts) for text in ranked_texts]
    top5 = satisfied(ranked_texts[:5])
    in_context = satisfied([item.chunk.text for item in context])
    return CaseResult(
        case_id=case["id"],
        category=case["category"],
        ranked_hits=ranked_hits,
        facts_in_top5=(sum(top5) / len(facts)) if facts else 0.0,
        facts_in_context=(sum(in_context) / len(facts)) if facts else 0.0,
        context_chars=sum(len(item.chunk.text) for item in context),
        admitted=len(ranked),
        expects_evidence=bool(facts),
        latency=latency,
        missing=[case["facts"][i][0] for i, ok in enumerate(in_context) if not ok],
    )


def summarize(results: list[CaseResult]) -> dict[str, float]:
    positives = [r for r in results if r.expects_evidence]
    negatives = [r for r in results if not r.expects_evidence]

    def reciprocal_rank(result: CaseResult) -> float:
        return next((1.0 / rank for rank, hit in enumerate(result.ranked_hits, start=1) if hit), 0.0)

    return {
        "hit@1": statistics.mean(1.0 if r.ranked_hits[:1] == [True] else 0.0 for r in positives),
        "recall@5": statistics.mean(r.facts_in_top5 for r in positives),
        "mrr": statistics.mean(reciprocal_rank(r) for r in positives),
        "context_recall": statistics.mean(r.facts_in_context for r in positives),
        "context_chars": statistics.mean(r.context_chars for r in positives),
        "false_abstention": statistics.mean(1.0 if r.admitted == 0 else 0.0 for r in positives),
        "no_evidence_ok": statistics.mean(1.0 if r.admitted == 0 else 0.0 for r in negatives) if negatives else 1.0,
        "latency_ms": statistics.mean(r.latency for r in results) * 1000,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--configs", default=",".join(CONFIGURATIONS))
    parser.add_argument("--embedding-model", default=None, help="Sustituye RAG_EMBEDDING_MODEL_NAME (experimentos)")
    parser.add_argument("--details", action="store_true", help="Muestra los hechos no recuperados por caso")
    parser.add_argument("--report", type=Path, default=None, help="Guarda el resultado completo en JSON")
    args = parser.parse_args()

    cases = json.loads(args.benchmark.read_text(encoding="utf-8"))["cases"]
    base = RagSettings()
    model_name = args.embedding_model or base.embedding_model_name
    embedding = SentenceTransformersEmbeddingAdapter(model_name=model_name)
    corpus = _Corpus(args.corpus_dir, embedding)

    report: dict[str, dict] = {}
    for config in args.configs.split(","):
        settings = base.model_copy(update={**CONFIGURATIONS[config], "embedding_model_name": model_name})
        print(f"\n== {config}")
        results = await evaluate(config, settings, corpus, cases)
        summary = summarize(results)
        report[config] = {"summary": summary, "cases": [r.__dict__ for r in results]}
        for metric, value in summary.items():
            print(f"  {metric:18} {value:8.3f}")
        if args.details:
            for result in results:
                if result.missing or (not result.expects_evidence and result.admitted):
                    detail = result.missing or [f"{result.admitted} fragmentos admitidos sin deber"]
                    print(f"    - {result.case_id} [{result.category}]: {detail}")

    print("\n== Resumen comparativo")
    metrics = list(next(iter(report.values()))["summary"])
    print(f"  {'métrica':18}" + "".join(f"{name:>18}" for name in report))
    for metric in metrics:
        print(f"  {metric:18}" + "".join(f"{report[name]['summary'][metric]:18.3f}" for name in report))

    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
