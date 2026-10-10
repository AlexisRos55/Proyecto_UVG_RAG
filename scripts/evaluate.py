"""Evaluación RAGAS del pipeline RAG (EPIC-6, ADR-0010).

Mide la tríada RAG (fidelidad, precisión de contexto, exhaustividad de contexto, relevancia
de respuesta) más latencia por consulta, usando los adaptadores REALES de producción
(ChromaVectorStoreAdapter, SentenceTransformersEmbeddingAdapter, AnthropicLLMAdapter,
SingleCallVerificationAdapter) contra el conjunto de referencia en golden_dataset.json.

Nota de arquitectura (no contradice ADR-0002): este script usa `langchain-anthropic` y
`langchain-huggingface` únicamente como adaptadores internos exigidos por la librería `ragas`
para actuar como juez LLM y para calcular embeddings de las métricas. ADR-0002 prohíbe
LangChain en el PIPELINE DE PRODUCCIÓN (app.infrastructure.adapters.llm.*); esta es una
herramienta de evaluación offline, fuera de ese pipeline, y ragas ya depende de LangChain
internamente sin importar qué wrapper se use.

Requisitos previos:
    1. El corpus oficial de UVG Altiplano indexado en ChromaDB: golden_dataset.json pregunta
       sobre esos documentos, no sobre el corpus de ejemplo de generate_sample_corpus.py
       (python scripts/ingest.py <carpeta con los PDF oficiales>, o el arranque del backend).
    2. Variables de entorno: ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CHROMA_PERSIST_DIR

Uso:
    python scripts/evaluate.py                     # 3 repeticiones por pregunta (protocolo, Fase V)
    python scripts/evaluate.py --repeticiones 1    # corrida rápida de prueba

Cada pregunta se ejecuta N veces (por defecto 3): con temperatura 0.0 la API no garantiza
respuestas idénticas, y la latencia varía con la red. El reporte guarda cada repetición, el
promedio por pregunta de latencia y de cada métrica RAGAS, y la exactitud de abstención. Los
promedios por pregunta son la unidad de análisis de `scripts/analyze.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)

from app.application.services.context_assembler import ContextAssembler
from app.application.services.knowledge_retriever import KnowledgeRetriever
from app.application.use_cases.answer_student_query import (
    NO_RETRIEVAL_MESSAGE,
    NOT_GROUNDED_MESSAGE,
)
from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.services.query_analyzer import QueryAnalyzer
from app.domain.value_objects.verified_answer import AnswerCoverage, VerifiedAnswer
from app.infrastructure.adapters.llm.anthropic_llm_adapter import AnthropicLLMAdapter
from app.infrastructure.adapters.llm.single_call_verification_adapter import (
    SingleCallVerificationAdapter,
)
from app.infrastructure.adapters.search.in_memory_corpus_index import InMemoryCorpusIndex
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.config.settings import (
    get_anthropic_settings,
    get_chroma_settings,
    get_rag_settings,
)
from app.infrastructure.rag_factory import build_context_assembler, build_retriever
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
REPORT_PATH = Path(__file__).parent / "evaluation_report.json"
DEFAULT_REPETITIONS = 3

# La línea base de atención manual (Project Charter, criterios de éxito; US-6.3) no se mide
# aquí: sale de la pregunta [T1] de la encuesta y se contrasta en scripts/analyze.py (H₁b).
# La clave se conserva en el reporte por compatibilidad con reportes anteriores.
MANUAL_BASELINE_LATENCY_SECONDS_PLACEHOLDER = None


class _NullConversationRepository(ConversationRepositoryPort):
    """No persiste nada: la evaluación no necesita historial de conversación real."""

    async def get_or_create_active_conversation(self, user_id: UUID) -> Conversation:
        return Conversation(id=new_id(), user_id=user_id, created_at=utc_now())

    async def add_message(self, conversation_id: UUID, message: Message) -> None:
        return None

    async def get_history(self, user_id: UUID) -> list[Conversation]:
        return []


async def _answer_one(
    question: str,
    retriever: KnowledgeRetriever,
    assembler: ContextAssembler,
    corpus_index: InMemoryCorpusIndex,
    verification_port: SingleCallVerificationAdapter,
) -> tuple[list[str], VerifiedAnswer | None, float]:
    """Replica la ruta fundamentada de producción (análisis, recuperación híbrida,
    ensamblado y verificación) con visibilidad completa del contexto, que la respuesta
    HTTP de /chat no expone y RAGAS necesita.

    Los componentes se construyen con `rag_factory`, igual que en el backend: lo que
    se evalúa es, por construcción, lo que se despliega (docs/11-reproducibility.md).
    """
    started_at = time.perf_counter()

    analysis = QueryAnalyzer.analyze(question, corpus_index.list_outlines())
    ranked = await retriever.retrieve(analysis)
    passages = assembler.assemble(ranked, parts=len(analysis.sub_queries))

    if not passages:
        elapsed = time.perf_counter() - started_at
        return [], None, elapsed

    verified_answer = await verification_port.answer(question, passages)
    elapsed = time.perf_counter() - started_at
    contexts = [p.chunk.text for p in passages]
    return contexts, verified_answer, elapsed


def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(statistics.mean(clean), 4) if clean else None


def _ragas_scores_by_sample(ragas_result: object) -> list[dict[str, float | None]]:
    """Puntuaciones RAGAS de cada muestra, en el mismo orden en que se enviaron.

    Se toman las columnas numéricas de `to_pandas()` (una por métrica), sin fijar sus
    nombres: dependen de la versión de ragas (p. ej. `answer_relevancy`, `context_recall`).
    """
    frame = ragas_result.to_pandas()  # type: ignore[attr-defined]
    input_columns = {"user_input", "retrieved_contexts", "response", "reference"}
    metric_columns = [
        column
        for column in frame.columns
        if column not in input_columns and str(frame[column].dtype).startswith(("float", "int"))
    ]
    rows: list[dict[str, float | None]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                column: (None if row[column] != row[column] else float(row[column]))  # NaN -> None
                for column in metric_columns
            }
        )
    return rows


def _attach_ragas_scores(
    case_rows: list[dict[str, Any]],
    sample_owner: list[tuple[int, int]],
    per_sample: list[dict[str, float | None]],
) -> None:
    """Reparte las puntuaciones de cada muestra a su repetición y deja en cada pregunta el
    promedio de cada métrica sobre sus repeticiones (la unidad de análisis de analyze.py)."""
    collected: dict[int, dict[str, list[float | None]]] = {}
    for (case_index, repetition), scores in zip(sample_owner, per_sample, strict=True):
        for metric, value in scores.items():
            collected.setdefault(case_index, {}).setdefault(metric, []).append(value)
            case_rows[case_index]["runs"][repetition - 1].setdefault("ragas", {})[metric] = value
    for case_index, metrics in collected.items():
        case_rows[case_index]["ragas"] = {
            metric: _mean(values) for metric, values in metrics.items()
        }


async def run_evaluation(
    repetitions: int = DEFAULT_REPETITIONS,
    dataset_path: Path = GOLDEN_DATASET_PATH,
    report_path: Path = REPORT_PATH,
) -> None:
    golden = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = golden["cases"]

    chroma_settings = get_chroma_settings()
    anthropic_settings = get_anthropic_settings()
    rag_settings = get_rag_settings()

    embedding_port = SentenceTransformersEmbeddingAdapter(
        model_name=rag_settings.embedding_model_name
    )
    vector_store_port = ChromaVectorStoreAdapter(
        persist_directory=chroma_settings.chroma_persist_dir,
        collection_name=rag_settings.chroma_collection_name,
    )
    corpus_index = InMemoryCorpusIndex(
        loader=vector_store_port.iter_chunks, size_probe=vector_store_port.count
    )
    lexical = corpus_index if rag_settings.retrieval_mode == "hybrid" else None
    retriever = build_retriever(embedding_port, vector_store_port, lexical, rag_settings)
    assembler = build_context_assembler(corpus_index, rag_settings)
    llm_port = AnthropicLLMAdapter(anthropic_settings)
    verification_port = SingleCallVerificationAdapter(llm_port)

    samples: list[SingleTurnSample] = []
    # (índice de caso, número de repetición) de cada muestra enviada a RAGAS, en orden.
    sample_owner: list[tuple[int, int]] = []
    input_tokens: list[int] = []
    case_rows: list[dict[str, Any]] = []

    for case_index, case in enumerate(cases):
        question = case["question"]
        runs: list[dict[str, Any]] = []
        for repetition in range(1, repetitions + 1):
            logger.info(
                "Pregunta {}/{} · repetición {}/{}",
                case_index + 1,
                len(cases),
                repetition,
                repetitions,
            )
            contexts, verified_answer, elapsed = await _answer_one(
                question, retriever, assembler, corpus_index, verification_port
            )
            if verified_answer and verified_answer.input_tokens is not None:
                input_tokens.append(verified_answer.input_tokens)

            is_grounded = bool(
                verified_answer
                and verified_answer.is_grounded
                and verified_answer.coverage is not AnswerCoverage.NONE
            )

            # Mismos textos de abstención que ve el estudiante (una sola fuente de verdad).
            if is_grounded and verified_answer:
                answer_text = verified_answer.answer_text
            else:
                answer_text = NOT_GROUNDED_MESSAGE if verified_answer else NO_RETRIEVAL_MESSAGE

            runs.append(
                {
                    "repetition": repetition,
                    "latency_seconds": round(elapsed, 3),
                    "is_grounded": is_grounded,
                    "decision_correct": is_grounded == case["expect_grounded"],
                    "confidence": verified_answer.confidence.value if verified_answer else None,
                    "coverage": verified_answer.coverage.value if verified_answer else None,
                    "input_tokens": verified_answer.input_tokens if verified_answer else None,
                    "retrieved_chunks": len(contexts),
                    "answer": answer_text,
                }
            )

            # RAGAS solo tiene sentido para preguntas que sí deberían responderse con contexto:
            # para las de abstención esperada, la métrica relevante es la corrección de la
            # decisión de abstenerse (ya contabilizada arriba), no fidelidad/relevancia de una
            # respuesta que deliberadamente no se debe dar.
            if case["expect_grounded"]:
                samples.append(
                    SingleTurnSample(
                        user_input=question,
                        retrieved_contexts=contexts or [""],
                        response=answer_text,
                        reference=case["reference_answer"],
                    )
                )
                sample_owner.append((case_index, repetition))

        case_rows.append(
            {
                "id": case.get("id", f"Q{case_index + 1:02d}"),
                "type": case.get("type"),
                "question": question,
                "expect_grounded": case["expect_grounded"],
                "latency_mean_seconds": _mean([r["latency_seconds"] for r in runs]),
                "decision_accuracy": _mean([1.0 if r["decision_correct"] else 0.0 for r in runs]),
                "runs": runs,
                "ragas": {},
            }
        )

    logger.info("Ejecutando RAGAS sobre {} muestras con contexto esperado...", len(samples))

    judge_llm = LangchainLLMWrapper(
        ChatAnthropic(
            model=anthropic_settings.model, api_key=anthropic_settings.api_key, temperature=0.0
        )
    )
    judge_embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )

    ragas_result = evaluate(
        dataset=EvaluationDataset(samples=samples),
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextPrecisionWithReference(),
            LLMContextRecall(),
        ],
        llm=judge_llm,
        embeddings=judge_embeddings,
    )

    _attach_ragas_scores(case_rows, sample_owner, _ragas_scores_by_sample(ragas_result))

    metric_names = sorted({m for row in case_rows for m in row["ragas"]})
    answerable = [row for row in case_rows if row["expect_grounded"]]
    out_of_corpus = [row for row in case_rows if not row["expect_grounded"]]
    latencies = [
        row["latency_mean_seconds"] for row in case_rows if row["latency_mean_seconds"] is not None
    ]

    report: dict[str, Any] = {
        "generated_at": utc_now().isoformat(),
        "model": anthropic_settings.model,
        "judge_model": anthropic_settings.model,
        "dataset": {"file": dataset_path.name, "version": golden.get("version")},
        "repetitions": repetitions,
        "sample_size": len(cases),
        "answerable_cases": len(answerable),
        # Media, sobre las preguntas respondibles, del promedio por pregunta de cada métrica.
        "ragas_scores": {
            metric: _mean([row["ragas"].get(metric) for row in answerable])
            for metric in metric_names
        },
        "latency_seconds": {
            "mean": round(statistics.mean(latencies), 3),
            "p50": round(statistics.median(latencies), 3),
            "max": round(max(latencies), 3),
            "manual_baseline_placeholder": MANUAL_BASELINE_LATENCY_SECONDS_PLACEHOLDER,
        },
        "abstention_accuracy": _mean([row["decision_accuracy"] for row in case_rows]),
        # La misma exactitud, separada: responder lo que sí está y abstenerse de lo que no.
        "decision_accuracy_by_group": {
            "answerable": _mean([row["decision_accuracy"] for row in answerable]),
            "out_of_corpus": _mean([row["decision_accuracy"] for row in out_of_corpus]),
        },
        # NFR-02: tokens de entrada por llamada efectivamente realizada.
        "input_tokens_per_call": {
            "mean": round(statistics.mean(input_tokens), 1) if input_tokens else None,
            "calls": len(input_tokens),
        },
        "pipeline": rag_settings.model_dump(),
        "cases": case_rows,
    }

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Reporte de evaluación RAGAS ===")
    print(f"Modelo: {anthropic_settings.model} · repeticiones por pregunta: {repetitions}")
    print(f"Preguntas evaluadas: {len(cases)} ({len(answerable)} con contexto esperado)")
    print(f"Métricas RAGAS (media por pregunta): {report['ragas_scores']}")
    print(
        f"Latencia media: {report['latency_seconds']['mean']}s "
        f"(p50={report['latency_seconds']['p50']}s)"
    )
    print(f"Exactitud de abstención (FR-08): {(report['abstention_accuracy'] or 0) * 100:.1f}%")
    print(
        "Línea base manual: no se mide aquí; sale de la encuesta ([T1]) y se contrasta con "
        "scripts/analyze.py --encuesta (H₁b)."
    )
    print(f"Reporte completo guardado en: {report_path}")
    print(f"Siguiente paso: python scripts/analyze.py --reporte {report_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluación RAGAS del asistente RAG UVG Altiplano")
    parser.add_argument(
        "--repeticiones",
        type=int,
        default=DEFAULT_REPETITIONS,
        help=f"Ejecuciones por pregunta (defecto: {DEFAULT_REPETITIONS})",
    )
    parser.add_argument(
        "--dataset", type=Path, default=GOLDEN_DATASET_PATH, help="Banco de preguntas (JSON)"
    )
    parser.add_argument("--salida", type=Path, default=REPORT_PATH, help="Ruta del reporte JSON")
    args = parser.parse_args()
    if args.repeticiones < 1:
        parser.error("--repeticiones debe ser al menos 1")
    return args


if __name__ == "__main__":
    _args = _parse_args()
    asyncio.run(run_evaluation(_args.repeticiones, _args.dataset, _args.salida))
