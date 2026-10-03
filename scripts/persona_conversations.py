"""Miles de conversaciones por perfil, con oráculos metamórficos (Fase 9.5).

El simulador de la Fase 9.2 comprueba invariantes sobre conversaciones bien
escritas. Aquí se pregunta otra cosa: **¿entiende el sistema lo mismo cuando la
misma conversación la escribe otra persona?** Cada conversación se genera dos
veces con la misma semilla:

- una versión *limpia*, con preguntas canónicas;
- una versión *de perfil*: la misma conversación escrita como lo haría un padre
  de familia, un docente, alguien nervioso, frustrado, que escribe mal, que
  mezcla inglés, que pega documentos, que hace varias preguntas a la vez o que
  contesta «sí», «ok», «dale», «entendido» entre pregunta y pregunta.

Oráculos (sin respuestas escritas a mano):

    equivalencia     cada turno con contenido se interpreta igual que en la versión
                     limpia: mismo modo, tema, aspecto y entidad en foco
    relleno_local    «ok», «entendido», «xd», «👍», «gracias»… no llaman al modelo
    relleno_inerte   y no cambian lo que se entiende en el turno siguiente (cubierto
                     por la equivalencia del turno que sigue)
    afirmacion       «sí», «dale», «va» tras un ofrecimiento: se pregunta por cuál
                     empezar (sin modelo) o se responde lo ofrecido (con modelo);
                     sin ofrecimiento, no llaman al modelo
    negacion         «no», «no gracias» no llaman al modelo
    documento_pegado un artículo pegado con una pregunta no rompe nada y el prompt
                     queda acotado
    multipregunta    dos preguntas en un mensaje llegan al modelo con evidencia
    robustez         ningún turno lanza excepción ni deja la respuesta vacía
    voz              ninguna respuesta local habla de la maquinaria

El modelo generativo se sustituye por el registrador de `evaluate_conversations`
(sin costo de API); lo evaluado es todo lo que el software decide.

Uso:
    PYTHONPATH=../backend/src:. python persona_conversations.py --corpus-dir <PDF> [--conversations 1000] [--seed 11]
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from evaluate_conversations import build_corpus, build_use_case
from stress_conversations import PASTED_ARTICLE

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.domain.services.message_sanitizer import MAX_QUESTION_LENGTH
from app.domain.value_objects.conversation_state import TurnInterpretation
from app.infrastructure.config.settings import RagSettings
from app.shared.kernel.ids import new_id

# --- Plan de conversación canónico ------------------------------------------------------

# (tema, aperturas, seguimientos). Las preguntas son las que escribiría alguien con
# buena ortografía; los perfiles las reescriben.
PLANS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("becas", ("¿Qué becas hay?", "Háblame de las becas", "Quiero información sobre becas"),
     ("¿Cuáles son los requisitos?", "¿Cuánto cubre?", "¿Cómo se solicita?", "¿Qué pasa si bajo mi promedio?",
      "¿Hasta cuándo puedo aplicar?", "¿Quién lo decide?")),
    ("credito", ("Háblame del crédito educativo", "¿Qué es el crédito educativo?"),
     ("¿Qué interés tiene?", "¿Cuáles son los requisitos?", "¿Qué pasa si no pago?", "¿En cuántas cuotas se paga?")),
    ("elecciones", ("¿Cómo funcionan las elecciones estudiantiles?", "Háblame de las elecciones estudiantiles"),
     ("¿Quién puede votar?", "¿Cuáles son los requisitos para ser candidato?", "¿Y si hay empate?")),
    ("clubes", ("¿Cómo se crea un club estudiantil?", "Háblame de los clubes"),
     ("¿Cuántos miembros necesita?", "¿Cada cuánto se renueva?", "¿Qué requisitos hay?")),
    ("admision", ("¿Cómo es el proceso de admisión?", "Háblame de la admisión de primer ingreso"),
     ("¿Qué documentos piden?", "¿Qué es la PAA?", "¿Cuándo es la prueba de admisión?")),
    ("graduacion", ("¿Cuándo es la ceremonia de graduación?", "Háblame de la graduación"),
     ("¿Dónde me registro?", "¿Hasta cuándo puedo registrarme?")),
    ("calendario", ("¿Cuándo inician las clases?", "Háblame del calendario académico"),
     ("¿Cuándo es el último día para retirar cursos?", "¿Cuándo termina el ciclo?")),
)

OPENERS = frozenset(opener for _, openers, _ in PLANS for opener in openers)

# --- Turnos de relleno -------------------------------------------------------------------

_FILLER = ("ok", "Ok", "entendido", "correcto", "exacto", "perfecto", "gracias", "Gracias!", "👍", "🙏", "jaja ok",
           "xd", "ah ok", "ya veo", "sale", "okis", "muchas gracias", "ok gracias")
# «sale» puede aceptar una oferta: se trata como afirmación, no como relleno.
_FILLER = tuple(f for f in _FILLER if f != "sale")
_AFFIRM = ("sí", "si", "dale", "va", "simón", "sí porfa", "claro", "sale")
_DECLINE = ("no", "no gracias", "nel", "no por ahora")
_FRUSTRATION = ("ya me cansé", "no me sirve", "esto no me ayuda", "qué fastidio")

# --- Perfiles ----------------------------------------------------------------------------

_ACCENTS = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
# Erratas que una persona comete con palabras del dominio (a una edición, como en el uso real).
_TYPOS = (("becas", "becaz"), ("requisitos", "requisitoz"), ("admisión", "admicion"), ("graduación", "graduasion"),
          ("elecciones", "eleciones"), ("crédito", "credito"), ("inscripción", "inscripsion"))


def _plain(text: str) -> str:
    return text.translate(_ACCENTS).replace("¿", "").replace("?", "").replace("¡", "").lower()


def _typos(text: str, rng: random.Random) -> str:
    text = _plain(text)
    for right, wrong in _TYPOS:
        if rng.random() < 0.7:
            text = re.sub(rf"\b{_plain(right)}\b", wrong, text)
    text = re.sub(r"\bque\b", "q", text)
    return re.sub(r"\bpor\b", "x", text)


@dataclass(frozen=True)
class Persona:
    name: str
    # Cómo reescribe una pregunta con contenido (índice del turno, texto, rng) → texto.
    rewrite: callable  # type: ignore[valid-type]
    # Probabilidad de intercalar un turno de relleno, una afirmación o una negación.
    filler: float = 0.0
    affirm: float = 0.0
    decline: float = 0.0
    frustration: float = 0.0
    pasted: float = 0.0
    merge: float = 0.0
    fillers: tuple[str, ...] = _FILLER


def _student(i: int, text: str, rng: random.Random) -> str:
    text = _plain(text) if rng.random() < 0.5 else text
    return text + (rng.choice([" porfa", " plis", " xfa", ""]) if rng.random() < 0.4 else "")


def _parent(i: int, text: str, rng: random.Random) -> str:
    if i == 0:
        return f"Buenas tardes, soy papá de un estudiante. {text}"
    return text


def _teacher(i: int, text: str, rng: random.Random) -> str:
    return f"Soy docente. {text}" if i == 0 else text


def _admin(i: int, text: str, rng: random.Random) -> str:
    return f"Trabajo en el área administrativa. {text}" if i == 0 else text


def _nervous(i: int, text: str, rng: random.Random) -> str:
    lead = rng.choice(["Disculpe la molestia, ", "Perdón que pregunte, ", "Mire, disculpe, ", "Oiga, una pregunta, "])
    return lead + text[0].lower() + text[1:] if text[0] != "¿" else lead + text


def _misspeller(i: int, text: str, rng: random.Random) -> str:
    return _typos(text, rng)


def _english(i: int, text: str, rng: random.Random) -> str:
    return text + rng.choice([" please", " pls", "", " thanks"])


def _plain_persona(i: int, text: str, rng: random.Random) -> str:
    return text


PERSONAS: tuple[Persona, ...] = (
    Persona("estudiante", _student, filler=0.25, affirm=0.1),
    Persona("padre", _parent, filler=0.2, decline=0.05),
    Persona("docente", _teacher, filler=0.15),
    Persona("administrativo", _admin, filler=0.1),
    Persona("nervioso", _nervous, filler=0.2),
    Persona("frustrado", _plain_persona, frustration=0.3),
    Persona("escribe_mal", _misspeller, filler=0.2),
    Persona("mezcla_ingles", _english, filler=0.3, fillers=("ok", "thanks", "ok thanks", "thx", "cool")),
    Persona("pega_documentos", _plain_persona, pasted=0.35),
    Persona("varias_preguntas", _plain_persona, merge=0.35),
    Persona("confirma", _plain_persona, filler=0.4, affirm=0.25, decline=0.15),
)


@dataclass(frozen=True)
class Step:
    message: str
    kind: str          # content | filler | affirm | decline | frustration | pasted | merged
    index: int = -1    # índice del turno de contenido en la versión limpia


def plan(rng: random.Random) -> list[str]:
    """Una conversación canónica: dos o tres temas, cada uno con su apertura y seguimientos."""
    questions: list[str] = []
    for _, openers, follow_ups in rng.sample(PLANS, k=rng.randint(2, 3)):
        questions.append(rng.choice(openers))
        questions.extend(rng.sample(follow_ups, k=min(len(follow_ups), rng.randint(1, 3))))
    return questions


def render(questions: list[str], persona: Persona, rng: random.Random) -> list[Step]:
    steps: list[Step] = []
    index = 0
    while index < len(questions):
        text = questions[index]
        if persona.merge and index + 1 < len(questions) and rng.random() < persona.merge:
            # Dos preguntas en un mensaje: no hay turno limpio equivalente; se evalúa aparte.
            second = questions[index + 1]
            steps.append(Step(f"{text} Y además, {second[0].lower() + second[1:] if second[0] != '¿' else second}", "merged"))
            index += 2
            continue
        steps.append(Step(persona.rewrite(index, text, rng), "content", index))
        if persona.pasted and rng.random() < persona.pasted:
            steps.append(Step(PASTED_ARTICLE[: rng.randint(200, 900)] + " ¿Qué significa esto?", "pasted"))
        roll = rng.random()
        if roll < persona.filler:
            steps.append(Step(rng.choice(persona.fillers), "filler"))
        elif roll < persona.filler + persona.affirm:
            steps.append(Step(rng.choice(_AFFIRM), "affirm"))
        elif roll < persona.filler + persona.affirm + persona.decline:
            steps.append(Step(rng.choice(_DECLINE), "decline"))
        elif roll < persona.filler + persona.affirm + persona.decline + persona.frustration:
            steps.append(Step(rng.choice(_FRUSTRATION), "frustration"))
        index += 1
    return steps


# --- Ejecución ---------------------------------------------------------------------------

_MACHINERY = re.compile(r"fragmento|contexto recuperado|informaci[oó]n disponible|base de datos|modelo de lenguaje", re.IGNORECASE)
_PROMPT_LIMIT = 6000 + MAX_QUESTION_LENGTH


def signature(turn: TurnInterpretation | None) -> tuple[str, str | None, str | None, str | None]:
    """Lo que debe coincidir entre versiones: cómo se entendió el turno, no cómo se redactó."""
    if turn is None:
        return ("-", None, None, None)
    return (turn.mode.value, turn.topic, turn.aspect, turn.entity.name if turn.entity else None)


class Recorder:
    """Envuelve `_understand_turn` para registrar la interpretación de cada turno."""

    def __init__(self, use_case: AnswerStudentQueryUseCase) -> None:
        self.last: TurnInterpretation | None = None
        original = use_case._understand_turn

        def wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
            state, turn = original(*args, **kwargs)
            self.last = turn
            return state, turn

        use_case._understand_turn = wrapped  # type: ignore[method-assign]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--conversations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--examples", type=int, default=4)
    parser.add_argument("--persona", default=None, help="Solo este perfil")
    args = parser.parse_args()

    settings = RagSettings()
    embedding, store, index, documents = await build_corpus(args.corpus_dir, settings)
    use_case, verification, _ = build_use_case(embedding, store, index, documents, settings)
    recorder = Recorder(use_case)
    rng = random.Random(args.seed)

    checks: dict[str, list[bool]] = defaultdict(list)
    by_persona: dict[str, list[bool]] = defaultdict(list)
    failures: dict[str, list[str]] = defaultdict(list)
    turns_total = 0
    started = time.perf_counter()

    def record(name: str, ok: bool, detail: str) -> None:
        checks[name].append(ok)
        if not ok:
            failures[name].append(detail)

    async def say(user_id, message: str):  # type: ignore[no-untyped-def]
        nonlocal turns_total
        turns_total += 1
        calls_before = len(verification.calls)
        recorder.last = None
        response = await use_case.execute(AnswerQueryRequest(user_id=user_id, question=message))
        called = len(verification.calls) > calls_before
        return response, called, recorder.last

    for number in range(args.conversations):
        persona = PERSONAS[number % len(PERSONAS)]
        questions = plan(rng)
        steps = render(questions, persona, rng)
        if args.persona and persona.name != args.persona:
            continue  # se generó igual, para conservar la misma secuencia aleatoria

        clean_user = new_id()
        clean: list[tuple[str, str | None, str | None, str | None]] = []
        for question in questions:
            _, _, turn = await say(clean_user, question)
            clean.append(signature(turn))

        user = new_id()
        previous_answer = ""
        # Un artículo pegado o dos preguntas juntas cambian legítimamente el foco: los turnos
        # que siguen dentro del mismo tema ya no tienen equivalente limpio.
        comparable = True
        for step in steps:
            if step.kind in ("pasted", "merged"):
                comparable = False
            elif step.kind == "content" and step.message.endswith(questions[step.index]) and questions[step.index] in OPENERS:
                comparable = True  # una apertura explícita vuelve a fijar el tema
            try:
                response, called, turn = await say(user, step.message)
            except Exception as error:  # noqa: BLE001 — el banco cuenta cualquier fallo
                record("robustez", False, f"[{persona.name} #{number}] «{step.message[:60]}»: {type(error).__name__}: {error}")
                continue
            answer = response.answer_text
            detail = f"[{persona.name} #{number}] «{step.message[:70]}» → {answer[:110]!r}"
            record("robustez", bool(answer.strip()), detail)
            if not called:
                record("voz", not _MACHINERY.search(answer), detail)
            if called:
                record("prompt_acotado", len(verification.calls[-1][0]) <= _PROMPT_LIMIT, detail)
            if step.kind == "content" and comparable:
                ok = signature(turn) == clean[step.index]
                record("equivalencia", ok, f"{detail}\n        limpia={clean[step.index]} perfil={signature(turn)}")
                by_persona[persona.name].append(ok)
            elif step.kind == "filler":
                record("relleno_local", not called, detail)
            elif step.kind == "decline":
                record("negacion", not called, detail)
            elif step.kind == "affirm":
                offered = "puedo explicarte" in previous_answer.lower() or "puedo contarte" in previous_answer.lower()
                # Con ofrecimiento: o se pregunta por cuál empezar (local) o se responde lo ofrecido.
                accepted = (not called and "empezamos" in answer) or called
                record("afirmacion", accepted if offered else not called, detail)
            elif step.kind == "frustration":
                record("frustracion_local", not called, detail)
            elif step.kind == "merged":
                record("multipregunta", called, detail)
            previous_answer = answer

    elapsed = time.perf_counter() - started
    overall = [ok for values in checks.values() for ok in values]
    print(f"Conversaciones: {args.conversations} (×2: limpia y de perfil) · turnos: {turns_total} · {elapsed:.0f} s"
          f" · {1000 * elapsed / max(1, turns_total):.1f} ms/turno")
    for name, values in sorted(checks.items()):
        print(f"  {name:18} {sum(values) / len(values):6.3f}  ({len(values) - sum(values)} fallos de {len(values)})")
    print(f"  {'GLOBAL':18} {sum(overall) / len(overall):6.3f}")
    print("\nEquivalencia por perfil:")
    for name, values in sorted(by_persona.items()):
        print(f"  {name:18} {sum(values) / len(values):6.3f}  ({len(values) - sum(values)} de {len(values)})")
    for name, details in sorted(failures.items()):
        print(f"\n== {name}: {len(details)} fallos. Ejemplos:")
        for example in details[: args.examples]:
            print(f"  - {example}")


if __name__ == "__main__":
    asyncio.run(main())
