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
    1. python scripts/generate_sample_corpus.py   (genera los PDF de ejemplo)
    2. python scripts/ingest.py                    (indexa el corpus de ejemplo)
    3. Variables de entorno: ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CHROMA_PERSIST_DIR

Uso:
    python scripts/evaluate.py
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from pathlib import Path
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

from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.value_objects.verified_answer import VerifiedAnswer
from app.infrastructure.adapters.llm.anthropic_llm_adapter import AnthropicLLMAdapter
from app.infrastructure.adapters.llm.single_call_verification_adapter import (
    SingleCallVerificationAdapter,
)
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.config.settings import (
    get_anthropic_settings,
    get_chroma_settings,
    get_rag_settings,
)
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
REPORT_PATH = Path(__file__).parent / "evaluation_report.json"

# Placeholder documentado (Project Charter, criterios de éxito): el equipo debe reemplazar
# este valor con una medición real del tiempo de atención manual antes de la defensa.
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
    embedding_port: SentenceTransformersEmbeddingAdapter,
    vector_store_port: ChromaVectorStoreAdapter,
    verification_port: SingleCallVerificationAdapter,
    top_k: int,
    min_similarity_threshold: float,
) -> tuple[list[str], VerifiedAnswer | None, float]:
    """Replica FR-06 a FR-10 con visibilidad completa del contexto recuperado (que la
    respuesta HTTP de /chat no expone), necesaria para calcular las métricas de RAGAS.

    top_k/min_similarity_threshold se reciben desde RagSettings (docs/11-reproducibility.md)
    para que esta evaluación use exactamente los mismos parámetros que producción — antes
    este script fijaba sus propios valores locales, desincronizados de
    AnswerStudentQueryUseCase.
    """
    started_at = time.perf_counter()

    query_embedding = await asyncio.to_thread(embedding_port.embed_text, question)
    candidates = await asyncio.to_thread(vector_store_port.search, query_embedding, top_k)
    relevant = [c for c in candidates if c.score.meets_threshold(min_similarity_threshold)]

    if not relevant:
        elapsed = time.perf_counter() - started_at
        return [], None, elapsed

    verified_answer = await verification_port.answer(question, relevant)
    elapsed = time.perf_counter() - started_at
    contexts = [rc.chunk.text for rc in relevant]
    return contexts, verified_answer, elapsed


async def run_evaluation() -> None:
    golden = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
    cases = golden["cases"]

    chroma_settings = get_chroma_settings()
    anthropic_settings = get_anthropic_settings()
    rag_settings = get_rag_settings()

    embedding_port = SentenceTransformersEmbeddingAdapter(model_name=rag_settings.embedding_model_name)
    vector_store_port = ChromaVectorStoreAdapter(
        persist_directory=chroma_settings.chroma_persist_dir,
        collection_name=rag_settings.chroma_collection_name,
    )
    llm_port = AnthropicLLMAdapter(anthropic_settings)
    verification_port = SingleCallVerificationAdapter(llm_port)

    samples: list[SingleTurnSample] = []
    latencies: list[float] = []
    abstention_correct = 0
    rows_for_report: list[dict] = []

    for case in cases:
        question = case["question"]
        contexts, verified_answer, elapsed = await _answer_one(
            question,
            embedding_port,
            vector_store_port,
            verification_port,
            rag_settings.top_k,
            rag_settings.min_similarity_threshold,
        )
        latencies.append(elapsed)

        is_grounded = verified_answer.is_grounded if verified_answer else False
        if is_grounded == case["expect_grounded"]:
            abstention_correct += 1

        answer_text = (
            verified_answer.answer_text
            if verified_answer and verified_answer.is_grounded
            else "No cuento con información suficiente en los documentos oficiales."
        )

        rows_for_report.append(
            {
                "question": question,
                "expect_grounded": case["expect_grounded"],
                "is_grounded": is_grounded,
                "latency_seconds": round(elapsed, 3),
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

    logger.info("Ejecutando RAGAS sobre {} preguntas con contexto esperado...", len(samples))

    judge_llm = LangchainLLMWrapper(
        ChatAnthropic(model=anthropic_settings.model, api_key=anthropic_settings.api_key, temperature=0.0)
    )
    judge_embeddings = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))

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

    report = {
        "generated_at": utc_now().isoformat(),
        "model": anthropic_settings.model,
        "sample_size": len(cases),
        "ragas_scores": ragas_result._repr_dict if hasattr(ragas_result, "_repr_dict") else dict(ragas_result),
        "latency_seconds": {
            "mean": round(statistics.mean(latencies), 3),
            "p50": round(statistics.median(latencies), 3),
            "max": round(max(latencies), 3),
            "manual_baseline_placeholder": MANUAL_BASELINE_LATENCY_SECONDS_PLACEHOLDER,
        },
        "abstention_accuracy": round(abstention_correct / len(cases), 3),
        "cases": rows_for_report,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Reporte de evaluación RAGAS ===")
    print(f"Modelo: {anthropic_settings.model}")
    print(f"Preguntas evaluadas: {len(cases)} ({len(samples)} con contexto esperado)")
    print(f"Métricas RAGAS: {report['ragas_scores']}")
    print(f"Latencia media: {report['latency_seconds']['mean']}s (p50={report['latency_seconds']['p50']}s)")
    print(f"Exactitud de abstención (FR-08): {report['abstention_accuracy'] * 100:.1f}%")
    print(
        "Línea base manual: NO MEDIDA (placeholder). "
        "Complételo con datos reales antes de la defensa (docs/07-backlog.md, US-6.3)."
    )
    print(f"Reporte completo guardado en: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
