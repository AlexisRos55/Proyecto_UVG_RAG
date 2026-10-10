"""Hilos largos y adversariales (20 a 50 turnos): ¿se rompe la conversación? (Fase final).

Cada hilo abre un tema y lo exprime con las preguntas que más fácilmente rompen el
seguimiento: «¿y cuánto?», «¿y cuándo?», «¿y la otra?», «¿esa cuál era?», «¿esa
también aplica?», «¿qué pasa si no cumplo?», «¿por qué?», «¿me das un ejemplo?»,
«¿me lo explicas más fácil?», «¿y si soy menor de edad?», «¿y si soy extranjero?»,
«¿qué más debo saber?», intercaladas con acuses («sí», «ok», «dale», «👍», «xd»…),
cambios de tema y regresos. Sin modelo: se usa el registrador de
`evaluate_conversations`.

Oráculos:

    seguimiento_en_tema   todo seguimiento busca dentro del tema activo (sus anclas en la consulta)
    acuse_local           los acuses no llaman al modelo; «sí», «dale», «va» tras un ofrecimiento
                          lo aceptan (responden lo ofrecido o preguntan por cuál empezar)
    consulta_acotada      la consulta interna no crece: menos de 40 palabras propias
    sin_repetir_local     nunca la misma respuesta local dos veces seguidas
    robustez              sin excepciones ni respuestas vacías

Además informa llamadas al modelo por hilo y turnos resueltos localmente.

Uso:
    PYTHONPATH=../backend/src:. python long_conversations.py --corpus-dir <PDF> [--threads 300] [--seed 5]
"""

from __future__ import annotations

import argparse
import asyncio
import random
import time
from collections import defaultdict
from pathlib import Path

from evaluate_conversations import build_corpus, build_use_case

from app.application.dto.chat_dto import AnswerQueryRequest
from app.domain.services.spanish_text import fold
from app.infrastructure.config.settings import RagSettings
from app.shared.kernel.ids import new_id

# Tema → (aperturas, anclas que la consulta de un seguimiento debe contener).
THEMES = {
    "becas": (("¿Qué becas hay?", "Háblame de las becas", "Quiero una beca"), ("beca", "ayuda", "programa")),
    "credito": (("Háblame del crédito educativo", "¿Cómo funciona el crédito educativo?"), ("credito",)),
    "clubes": (("Háblame de los clubes", "¿Cómo se crea un club?"), ("club", "agrupacion")),
    "elecciones": (("¿Cómo son las elecciones estudiantiles?",), ("eleccion", "electoral", "votacion")),
    "admision": (("¿Cómo es el proceso de admisión?", "quiero estudiar en la UVG"), ("admision", "ingreso")),
    "graduacion": (("¿Cuándo es la ceremonia de graduación?", "me quiero graduar"), ("gradua",)),
}
ADVERSARIAL = (
    "¿y cuánto?", "¿y cuándo?", "¿y la otra?", "¿esa cuál era?", "¿esa también aplica para mí?", "¿qué pasa si no cumplo?",
    "¿por qué?", "¿me das un ejemplo?", "¿me lo explicas más fácil?", "¿y si soy menor de edad?", "¿y si soy extranjero?",
    "¿qué más debo saber?", "¿y los requisitos?", "¿quién lo decide?", "¿dónde se solicita?", "¿y eso?", "explícalo",
    "no entiendo", "¿cuál me conviene?", "resúmelo",
)
ACKS = ("ok", "sí", "dale", "va", "exacto", "simón", "nel", "xd", "👍", "🙏", "jaja", "jeje", "no", "entendido", "gracias")
AFFIRMATIONS = frozenset(["sí", "dale", "va", "simón"])
MAX_QUERY_WORDS = 40


def thread(rng: random.Random) -> list[tuple[str, str, str | None]]:
    """(mensaje, tipo, tema esperado) — de 20 a 50 turnos."""
    length = rng.randint(20, 50)
    keys = list(THEMES)
    topic = rng.choice(keys)
    turns: list[tuple[str, str, str | None]] = [(rng.choice(THEMES[topic][0]), "opener", topic)]
    while len(turns) < length:
        roll = rng.random()
        if roll < 0.62:
            turns.append((rng.choice(ADVERSARIAL), "follow", topic))
        elif roll < 0.9:
            turns.append((rng.choice(ACKS), "ack", topic))
        else:
            topic = rng.choice([k for k in keys if k != topic])
            turns.append((rng.choice(THEMES[topic][0]), "opener", topic))
    return turns


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=300)
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--examples", type=int, default=5)
    parser.add_argument("--all-failures", action="store_true")
    args = parser.parse_args()

    settings = RagSettings()
    embedding, store, index, documents = await build_corpus(args.corpus_dir, settings)
    use_case, verification, spy = build_use_case(embedding, store, index, documents, settings)
    rng = random.Random(args.seed)

    checks: dict[str, list[bool]] = defaultdict(list)
    failures: dict[str, list[str]] = defaultdict(list)
    calls_per_thread: list[int] = []
    turns_total = local_total = 0
    started = time.perf_counter()

    def record(name: str, ok: bool, detail: str) -> None:
        checks[name].append(ok)
        if not ok:
            failures[name].append(detail)

    for number in range(args.threads):
        user = new_id()
        calls_at_start = len(verification.calls)
        previous_local = previous_answer = ""
        history: list[str] = []
        for message, kind, topic in thread(rng):
            turns_total += 1
            calls_before, queries_before = len(verification.calls), len(spy.queries)
            try:
                response = await use_case.execute(AnswerQueryRequest(user_id=user, question=message))
            except Exception as error:  # noqa: BLE001 — el banco cuenta cualquier fallo
                record("robustez", False, f"#{number} «{message}»: {type(error).__name__}: {error}")
                continue
            called = len(verification.calls) > calls_before
            queries = spy.queries[queries_before:]
            answer = response.answer_text
            trail = " → ".join(history[-3:] + [f"«{message}»"])
            detail = f"#{number} [{topic}] {trail}\n        consulta: {' || '.join(queries)[:150]}\n        respuesta: {answer[:120]!r}"
            history.append(f"«{message}»")
            record("robustez", bool(answer.strip()), detail)
            if kind == "ack":
                offered = "puedo explicarte" in previous_answer.lower() or "puedo contarte" in previous_answer.lower()
                accepted = message in AFFIRMATIONS and offered and (called or "empezamos" in answer)
                record("acuse_local", not called or accepted, detail)
            previous_answer = answer
            # Solo turnos que buscaron evidencia para responder (con modelo o abstención): una
            # aclaración local no busca, y las búsquedas que se vean son sondas internas de perfil.
            if kind == "follow" and queries and topic and (called or response.is_grounded is False):
                folded = fold(" ".join(queries))
                record("seguimiento_en_tema", any(anchor in folded for anchor in THEMES[topic][1]), detail)
            for query in queries:
                record("consulta_acotada", len(query.split(" | ")[0].split()) < MAX_QUERY_WORDS, detail)
            if not called:
                local_total += 1
                record("sin_repetir_local", answer != previous_local, detail)
                previous_local = answer
            else:
                previous_local = ""
        calls_per_thread.append(len(verification.calls) - calls_at_start)

    elapsed = time.perf_counter() - started
    overall = [ok for values in checks.values() for ok in values]
    print(f"Hilos: {args.threads} · turnos: {turns_total} (media {turns_total / args.threads:.1f} por hilo) · {elapsed:.0f} s")
    print(f"Llamadas al modelo: {sum(calls_per_thread)} ({sum(calls_per_thread) / turns_total:.2f} por turno) · "
          f"turnos locales: {local_total} ({local_total / turns_total:.0%})")
    for name, values in sorted(checks.items()):
        print(f"  {name:20} {sum(values) / len(values):6.3f}  ({len(values) - sum(values)} fallos de {len(values)})")
    print(f"  {'GLOBAL':20} {sum(overall) / len(overall):6.3f}")
    for name, details in sorted(failures.items()):
        print(f"\n== {name}: {len(details)} fallos. Ejemplos:")
        for example in (details if args.all_failures else details[: args.examples]):
            print(f"  - {example}")


if __name__ == "__main__":
    asyncio.run(main())
