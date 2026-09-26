"""Simulación masiva de conversaciones con oráculos de invariantes (Fase 9.2).

El banco de conversaciones etiquetado a mano es pequeño por naturaleza. Este
simulador genera, con semilla fija, cientos de conversaciones largas combinando
aperturas de tema, seguimientos elípticos, referencias («¿y eso?», «explícalo»),
cortesías, saludos, interrupciones fuera de dominio, pausas («continuemos
mañana»), reanudaciones y cambios de tema explícitos. No hay respuestas
esperadas escritas a mano: cada turno se contrasta con **invariantes** que
cualquier asesor humano cumpliría:

    continuidad        un seguimiento busca dentro del tema activo
    cambio_de_tema     un cambio explícito deja atrás el tema anterior
    cortesia           saludos, gracias y despedidas no llaman al modelo
    memoria_saludo     al volver a saludar, se ofrece retomar el tema activo
    memoria_pausa      al despedirse «hasta mañana», se recuerda el tema
    reanudacion        «sigamos» retoma y nombra el tema activo
    fuera_de_dominio   no llama al modelo y no rompe el tema
    abstencion_honesta en un tema sin respaldo documental, se abstiene nombrándolo
    voz                ninguna respuesta determinista usa vocabulario de maquinaria

Fase 10 (humanización) añade:

    orientacion          «estoy perdido» recibe orientación local, sin llamar al modelo
    no_entiendo          «no entiendo» vuelve a explicar el tema activo (o orienta si no lo hay)
    regreso_tema         «volviendo a las becas, …» busca en ese tema, no en el actual
    comparacion          tras comparar dos becas, «¿cuál me conviene?» sigue buscando ambas
    referencia_categoria «esa beca de antes» vuelve a la beca nombrada turnos atrás

El modelo generativo se sustituye por un registrador (sin costo); lo que se
evalúa es todo lo que el sistema decide antes y alrededor de esa llamada.

Uso:
    python scripts/simulate_conversations.py --corpus-dir <PDF> [--conversations 120] [--seed 7] [--examples 3]
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from evaluate_conversations import build_corpus, build_use_case

from app.application.dto.chat_dto import AnswerQueryRequest
from app.domain.services.spanish_text import fold
from app.infrastructure.config.settings import RagSettings
from app.shared.kernel.ids import new_id


@dataclass(frozen=True)
class TopicSpec:
    key: str
    openers: tuple[str, ...]
    anchors: tuple[str, ...]      # alguna debe aparecer en la consulta interna de un seguimiento
    mention: str                  # cómo debe nombrarse al retomar o saludar
    covered: bool = True          # ¿el corpus lo documenta?
    follow_ups: tuple[str, ...] = ()


_GENERIC_FOLLOW_UPS = (
    "¿Cuáles son los requisitos?", "¿Y los requisitos?", "¿Qué pasa si no cumplo?", "¿Quién lo decide?",
    "¿Cómo lo solicito?", "¿Qué condiciones hay?", "Explícalo", "Más sobre eso", "¿Por qué?", "¿Cómo así?",
    "¿Qué significa?", "¿Qué pasa después?", "Dame más detalles", "¿Y eso?", "¿Hay excepciones?",
)

TOPICS = (
    TopicSpec("becas", ("Quiero información sobre becas", "Háblame de las becas", "Becas", "¿Qué becas hay?",
                        "Tengo dudas sobre las becas"), ("beca", "ayuda"), "beca",
              follow_ups=("¿Cuánto cubre?", "¿Cuál cubre más?", "¿Y esa tiene requisitos?", "¿Hasta cuándo puedo aplicar?",
                          "¿Qué pasa si bajo mi promedio?", "¿Cuáles existen?")),
    TopicSpec("credito", ("Háblame del crédito educativo", "¿Qué es el crédito educativo?", "Crédito educativo"),
              ("credito", "educativo"), "crédito", follow_ups=("¿Qué interés tiene?", "¿En cuántas cuotas se paga?")),
    TopicSpec("elecciones", ("¿Cómo funcionan las elecciones estudiantiles?", "Háblame de las elecciones",
                             "Elecciones estudiantiles"), ("eleccion", "electoral"), "elecciones",
              follow_ups=("¿A qué hora son?", "¿Y si hay empate?", "¿Quién gana?")),
    TopicSpec("clubes", ("Quiero crear un club", "Háblame de los clubes", "¿Cómo funcionan los clubes?"),
              ("club", "agrupacion"), "club", follow_ups=("¿Cuántos miembros necesita?", "¿Cada cuánto se renueva?")),
    TopicSpec("horas_beca", ("¿Qué son las horas beca?", "Háblame de las horas beca"), ("horas",), "horas beca",
              follow_ups=("¿Quién las asigna?", "¿Y si no las cumplo?")),
    TopicSpec("graduacion", ("Háblame de la graduación", "¿Cuándo es la ceremonia de graduación?"), ("gradua",),
              "graduación", follow_ups=("¿Dónde me registro?",)),
    TopicSpec("admision", ("¿Cómo es el proceso de admisión?", "Háblame de la admisión de primer ingreso"),
              ("admision", "ingreso", "paa"), "admisión", follow_ups=("¿Qué documentos piden?", "¿Qué es la PAA?")),
    TopicSpec("seguro", ("Háblame del seguro", "¿Qué cubre el seguro estudiantil?", "Seguro médico estudiantil"),
              ("seguro",), "seguro", covered=False,
              follow_ups=("¿Y si ocurre fuera del campus?", "¿Qué exclusiones tiene?", "¿Y enfermedades?")),
)

_THANKS = ("Gracias", "Ok", "Perfecto", "Entendido", "Vale, gracias", "Genial", "Perfecto gracias", "Muy bien")
_GREETINGS = ("Hola", "Buenas tardes", "Hola de nuevo")
_RESUMES = ("Sigamos", "Continuemos", "¿En qué íbamos?", "Retomemos")
_LATER = ("Continuemos mañana", "Luego seguimos", "Hablamos después, gracias")
_OUT_OF_DOMAIN = ("¿Quién ganó el último mundial?", "¿Cuál es la capital de Francia?", "Escríbeme un poema")
_SWITCHES = ("Ahora {x}", "Cambiando de tema, {x}", "Otra pregunta: {x}", "{X}")
_LOST = ("estoy perdido", "No sé qué preguntar", "¿Por dónde empiezo?", "Estoy confundido, orientame")
_CONFUSED = ("no entiendo", "No me quedó claro", "¿Me lo explicas más sencillo?", "No entendí nada")
_COMPARE_OPEN = ("¿Qué diferencia hay entre la Beca Despega y la Beca Trasciende?", "Compara la Beca Despega con la Beca Trasciende")
_COMPARE_FOLLOW = ("¿Y cuál me conviene?", "¿Cuál pide más requisitos?", "¿Y cuál cubre más?", "¿Cuál recomiendas?")
_ENTITY_OPEN = ("¿Qué es la Beca Despega?", "Háblame de la Beca Despega")
_CATEGORY = ("¿Y esa beca de antes pide promedio?", "¿Esa beca de antes tiene penalizaciones?", "Volviendo a esa beca de antes, ¿cuánto cubre?")
# Cómo se nombra cada tema al volver a él («volviendo a las becas, …»).
_NAMES = {
    "becas": "las becas", "credito": "el crédito educativo", "elecciones": "las elecciones", "clubes": "los clubes",
    "horas_beca": "las horas beca", "graduacion": "la graduación", "admision": "la admisión",
}
_MACHINERY = re.compile(r"fragmento|contexto recuperado|informaci[oó]n disponible|no cuento con informaci[oó]n|base de datos|modelo de lenguaje", re.IGNORECASE)


@dataclass(frozen=True)
class Turn:
    message: str
    kind: str
    topic: TopicSpec | None
    previous: TopicSpec | None = None


def generate(rng: random.Random, count: int) -> list[list[Turn]]:
    conversations: list[list[Turn]] = []
    for _ in range(count):
        turns: list[Turn] = []
        if rng.random() < 0.6:
            turns.append(Turn(rng.choice(_GREETINGS), "greeting_first", None))
        if rng.random() < 0.15:
            turns.append(Turn(rng.choice(_LOST), "lost", None))
        previous: TopicSpec | None = None
        named_entity = False
        for topic in rng.sample(TOPICS, k=rng.randint(2, 4)):
            opener = rng.choice(topic.openers)
            if previous is None:
                turns.append(Turn(opener, "opener", topic))
            else:
                lowered = opener if opener.startswith("¿") else opener[0].lower() + opener[1:]
                text = rng.choice(_SWITCHES).format(x=lowered, X=opener)
                turns.append(Turn(text, "switch", topic, previous))
            pool = list(topic.follow_ups) + list(_GENERIC_FOLLOW_UPS)
            if topic.key == "becas" and rng.random() < 0.5:
                turns.append(Turn(rng.choice(_COMPARE_OPEN), "compare_open", topic))
                turns.append(Turn(rng.choice(_COMPARE_FOLLOW), "compare_follow", topic))
            if topic.key == "becas" and rng.random() < 0.5:
                turns.append(Turn(rng.choice(_ENTITY_OPEN), "entity_open", topic))
                named_entity = True
            elif named_entity and topic.key != "becas" and topic.covered and rng.random() < 0.6:
                # Tras cambiar de tema, volver a «esa beca de antes».
                turns.append(Turn(rng.choice(pool), "follow_up", topic))
                turns.append(Turn(rng.choice(_CATEGORY), "category", topic))
                named_entity = False
                previous = next(t for t in TOPICS if t.key == "becas")
                continue
            for _ in range(rng.randint(3, 6)):
                turns.append(Turn(rng.choice(pool), "follow_up", topic))
                roll = rng.random()
                if roll < 0.15:
                    turns.append(Turn(rng.choice(_THANKS), "courtesy", topic))
                elif roll < 0.22:
                    turns.append(Turn(rng.choice(_OUT_OF_DOMAIN), "out_of_domain", topic))
                elif roll < 0.30:
                    turns.append(Turn(rng.choice(_LATER), "later", topic))
                    turns.append(Turn(rng.choice(_GREETINGS), "greeting_again", topic))
                    turns.append(Turn(rng.choice(_RESUMES), "resume", topic))
                elif roll < 0.34 and topic.covered:
                    turns.append(Turn(rng.choice(_CONFUSED), "confused", topic))
                elif roll < 0.37:
                    turns.append(Turn(rng.choice(_LOST), "lost", topic))
            if previous is not None and previous.covered and previous.key in _NAMES and rng.random() < 0.35:
                # «Volviendo a las becas, ¿cuánto cubre?»: regreso explícito al tema anterior.
                question = rng.choice(previous.follow_ups or _GENERIC_FOLLOW_UPS[:2])
                lead = f"Volviendo a {_NAMES[previous.key]}".replace("a el ", "al ")
                lowered = question[:2].lower() + question[2:] if question.startswith("¿") else question[0].lower() + question[1:]
                turns.append(Turn(f"{lead}, {lowered}", "return", previous, topic))
                topic = previous
            previous = topic
        conversations.append(turns)
    return conversations


def _has_anchor(text: str, topic: TopicSpec) -> bool:
    folded = fold(text)
    return any(anchor in folded for anchor in topic.anchors)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--conversations", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--examples", type=int, default=3, help="Ejemplos de fallo a mostrar por invariante")
    args = parser.parse_args()

    settings = RagSettings()
    embedding, store, index, documents = await build_corpus(args.corpus_dir, settings)
    use_case, verification, spy = build_use_case(embedding, store, index, documents, settings)
    conversations = generate(random.Random(args.seed), args.conversations)

    checks: dict[str, list[bool]] = defaultdict(list)
    failures: dict[str, list[str]] = defaultdict(list)
    errors: Counter[str] = Counter()
    total_turns = 0

    def record(name: str, ok: bool, detail: str) -> None:
        checks[name].append(ok)
        if not ok:
            failures[name].append(detail)

    for number, conversation in enumerate(conversations):
        user_id = new_id()
        history: list[str] = []
        for turn in conversation:
            total_turns += 1
            calls_before, queries_before = len(verification.calls), len(spy.queries)
            try:
                response = await use_case.execute(AnswerQueryRequest(user_id=user_id, question=turn.message))
            except Exception as error:  # noqa: BLE001 — el simulador cuenta cualquier fallo
                errors[type(error).__name__] += 1
                record("sin_errores", False, f"#{number} «{turn.message}»: {error}")
                continue
            called = len(verification.calls) > calls_before
            query = " || ".join(spy.queries[queries_before:])
            answer = response.answer_text
            trail = " → ".join(history[-3:] + [f"«{turn.message}»"])
            detail = f"#{number} {trail}\n        consulta: {query[:140]}\n        respuesta: {answer[:140]!r}"
            history.append(f"«{turn.message}»")
            topic = turn.topic

            if turn.kind == "lost":
                record("orientacion", not called and len(answer) > 40, detail)
            elif turn.kind == "confused" and topic:
                oriented = not called and ("paso a paso" in answer or "te ayudo" in answer)
                record("no_entiendo", (called and (_has_anchor(query, topic) or not query)) or oriented, detail)
            elif turn.kind == "return" and topic:
                record("regreso_tema", _has_anchor(query, topic), detail)
            elif turn.kind == "compare_follow":
                folded_query = fold(query)
                record("comparacion", "despeg" in folded_query and "trasciend" in folded_query, detail)
            elif turn.kind == "category":
                record("referencia_categoria", "despeg" in fold(query), detail)
            elif turn.kind in ("courtesy", "greeting_first"):
                record("cortesia", not called and bool(answer.strip()), detail)
            elif turn.kind == "out_of_domain":
                record("fuera_de_dominio", not called, detail)
            elif turn.kind == "greeting_again" and topic:
                record("cortesia", not called, detail)
                record("memoria_saludo", fold(topic.mention) in fold(answer), detail)
            elif turn.kind == "later" and topic:
                record("cortesia", not called, detail)
                record("memoria_pausa", fold(topic.mention) in fold(answer), detail)
            elif turn.kind == "resume" and topic:
                record("reanudacion", fold(topic.mention) in fold(answer), detail)
            elif turn.kind in ("follow_up", "opener", "switch") and topic:
                if not topic.covered:
                    record("abstencion_honesta", response.is_grounded is not True and fold(topic.mention) in fold(answer), detail)
                elif turn.kind == "follow_up":
                    # Un seguimiento se busca dentro del tema; sin búsqueda solo vale si se
                    # explicó el artículo exacto en consulta (llamada al modelo sin recuperar).
                    record("continuidad", _has_anchor(query, topic) or (not query and called), detail)
                if turn.kind == "switch" and turn.previous and query:
                    shared = set(topic.anchors) & set(turn.previous.anchors)
                    record("cambio_de_tema", shared or not _has_anchor(query, turn.previous) or _has_anchor(turn.message, turn.previous), detail)
            if not called:
                record("voz", not _MACHINERY.search(answer), detail)

    print(f"Conversaciones: {len(conversations)} · turnos: {total_turns} · errores: {sum(errors.values())}")
    overall = [ok for values in checks.values() for ok in values]
    for name, values in sorted(checks.items()):
        print(f"  {name:20} {sum(values) / len(values):6.3f}  ({len(values) - sum(values)} fallos de {len(values)})")
    print(f"  {'GLOBAL':20} {sum(overall) / len(overall):6.3f}")
    for name, details in sorted(failures.items()):
        print(f"\n== {name}: {len(details)} fallos. Ejemplos:")
        for example in details[: args.examples]:
            print(f"  - {example}")


if __name__ == "__main__":
    asyncio.run(main())
