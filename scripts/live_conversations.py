"""Conversaciones en vivo contra el modelo real, con transcripción y auditoría de estilo (Fase 10.1).

Los bancos y el simulador sustituyen el modelo por un registrador: miden todo lo
que el sistema decide alrededor de la llamada, pero no cómo se lee la respuesta.
Este script recorre conversaciones completas con el adaptador real de Anthropic,
guarda la transcripción para leerla turno por turno y calcula señales objetivas
de estilo que un lector exigente notaría:

    aperturas_repetidas   fracción de respuestas que comparten las mismas tres primeras palabras
    apertura_negativa     respuestas que empiezan por lo que falta («La normativa no…», «No hay…»)
    muletillas            frases de relleno por respuesta («según la normativa», «conviene confirmar…»)
    frases_repetidas      oraciones de 8+ palabras repetidas dentro de una misma conversación
    largo_puntual         palabras medias al responder una pregunta corta y puntual
    cierre_con_pregunta   respuestas generadas que terminan en una pregunta del modelo

Uso (cuesta llamadas reales al modelo; requiere ANTHROPIC_API_KEY en .env):
    PYTHONPATH=../backend/src python live_conversations.py --corpus-dir <PDF> --threads live_threads.json --out <carpeta>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
from collections import Counter
from pathlib import Path

from evaluate_conversations import _Conversations, build_corpus
from loguru import logger

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.domain.services.spanish_text import fold
from app.infrastructure.adapters.llm.anthropic_llm_adapter import AnthropicLLMAdapter
from app.infrastructure.adapters.llm.single_call_verification_adapter import (
    SingleCallVerificationAdapter,
)
from app.infrastructure.adapters.nlp.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.infrastructure.config.settings import AnthropicSettings, RagSettings
from app.infrastructure.rag_factory import build_context_assembler, build_retriever
from app.shared.kernel.ids import new_id

FILLERS = {
    "segun_la_normativa": r"\bsegun la normativa\b",
    "de_acuerdo_con": r"\bde acuerdo con\b",
    "la_normativa_no": r"\bla normativa no\b",
    "conviene_confirmar": r"\bconviene (?:que )?(?:confirm|consult|verific)\w*",
    "en_el_campus": r"\b(?:directamente )?en el campus\b",
    "como_estudiante_altiplano": r"\b(?:como estudiante del|en el|para ti como estudiante del) campus altiplano\b",
    "matices": r"\bcon matices\b",
    "la_documentacion": r"\bla documentacion\b",
}
_NEGATIVE = re.compile(r"^(?:la normativa no|el reglamento no|no hay|no existe|no puedo|no encontre|no se establece)")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _api_key(env_path: Path) -> str:
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("ANTHROPIC_API_KEY no está en .env")


def audit(turns: list[dict]) -> dict[str, float]:
    generated = [t for t in turns if t["generated"]]
    answers = [fold(t["answer"]) for t in generated]
    openers = Counter(" ".join(re.findall(r"\w+", a)[:3]) for a in answers)
    repeated_sentences = 0
    by_thread: dict[int, Counter[str]] = {}
    for turn in generated:
        counter = by_thread.setdefault(turn["thread"], Counter())
        for sentence in _SENTENCE.split(fold(turn["answer"])):
            if len(sentence.split()) >= 8:
                counter[sentence.strip()] += 1
    repeated_sentences = sum(c - 1 for counter in by_thread.values() for c in counter.values() if c > 1)
    punctual = [len(t["answer"].split()) for t in generated if len(t["q"].split()) <= 8 and not t["overview"]]
    result = {
        "respuestas_generadas": len(generated),
        "aperturas_repetidas": (openers.most_common(1)[0][1] / len(answers)) if answers else 0.0,
        "apertura_negativa": sum(bool(_NEGATIVE.match(a)) for a in answers) / max(1, len(answers)),
        "frases_repetidas": repeated_sentences,
        "largo_puntual_palabras": statistics.mean(punctual) if punctual else 0.0,
        "cierre_con_pregunta": sum(a.rstrip().endswith("?") for a in answers) / max(1, len(answers)),
    }
    for name, pattern in FILLERS.items():
        result[f"muletilla:{name}"] = sum(len(re.findall(pattern, a)) for a in answers) / max(1, len(answers))
    return result


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--threads", type=Path, required=True, help="JSON: lista de conversaciones (listas de mensajes)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--env", type=Path, default=Path(__file__).resolve().parent.parent / ".env")
    args = parser.parse_args()

    usage: list[str] = []
    logger.remove()
    logger.add(lambda m: usage.append(str(m)) if "tokens entrada" in m or "Turno '" in m else None, level="INFO", format="{message}")

    settings = RagSettings()
    embedding, store, index, documents = await build_corpus(args.corpus_dir, settings)
    verification = SingleCallVerificationAdapter(AnthropicLLMAdapter(AnthropicSettings(api_key=_api_key(args.env))))
    use_case = AnswerStudentQueryUseCase(
        embedding, store, verification, _Conversations(), documents,
        intent_classifier=RuleBasedIntentClassifier(),
        retriever=build_retriever(embedding, store, index, settings),
        context_assembler=build_context_assembler(index, settings),
        corpus_catalog=index,
    )

    threads = json.loads(args.threads.read_text())
    turns: list[dict] = []
    for number, thread in enumerate(threads):
        user_id = new_id()
        for message in thread:
            mark = len(usage)
            response = await use_case.execute(AnswerQueryRequest(user_id=user_id, question=message))
            logs = usage[mark:]
            turns.append({
                "thread": number,
                "q": message,
                "answer": response.answer_text,
                "grounded": response.is_grounded,
                "confidence": response.confidence.value if response.confidence else None,
                "generated": any("tokens entrada" in line for line in logs),
                "overview": any("panorama" in line for line in logs),
                "interpretation": next((line for line in logs if line.startswith("Turno '")), ""),
                "sources": [f"{s.document_title} · {s.section}" for s in response.sources][:4],
            })

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "turns.json").write_text(json.dumps(turns, ensure_ascii=False, indent=2))
    lines: list[str] = []
    for turn in turns:
        if not lines or turn["thread"] != turns[turns.index(turn) - 1]["thread"]:
            lines.append(f"\n\n========== CONVERSACIÓN {turn['thread'] + 1}")
        kind = "modelo" if turn["generated"] else "local"
        lines.append(f"\n### {turn['q']}   [{kind} · fundamentada={turn['grounded']} · {turn['confidence']}]\n{turn['answer']}")
    (args.out / "transcript.md").write_text("\n".join(lines))
    report = audit(turns)
    (args.out / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    for key, value in report.items():
        print(f"  {key:36} {value:.3f}" if isinstance(value, float) else f"  {key:36} {value}")


if __name__ == "__main__":
    asyncio.run(main())
