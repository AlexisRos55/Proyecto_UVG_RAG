"""Cómo acompaña el asistente: ofrecer el siguiente paso, abstenerse con utilidad, retomar.

Tres principios, tomados de cómo conversa un buen asesor (y de los mejores
asistentes generales), no de su redacción:

1. **Solo se ofrece lo que se puede cumplir.** Las sugerencias («también puedo
   explicarte los requisitos…») se construyen con los aspectos que la normativa
   realmente trata para ese tema, detectados en los títulos de sus artículos.
2. **Una abstención también orienta.** Decir qué sí establece la normativa sobre
   el tema convierte un «no sé» en un camino.
3. **No repetirse.** La segunda abstención seguida sobre el mismo tema es breve.

Servicio puro: recibe los títulos de artículo y el foco ya resueltos.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.domain.services.conversation_lexicon import ASPECTS, aspect_by_key
from app.domain.services.spanish_text import analyze, fold

# Cómo se nombra cada aspecto al ofrecerlo («también puedo explicarte …»).
_OFFER_PHRASES = {
    "requisitos": "los requisitos",
    "cobertura": "la cobertura",
    "condiciones": "las condiciones para mantenerla",
    "consecuencias": "las penalizaciones",
    "procedimiento": "cómo se solicita",
    "plazo": "los plazos",
    "horario": "los horarios",
    "duracion": "la duración",
    "responsables": "quién lo decide",
    "integrantes": "quiénes lo integran",
}
# Cómo se nombra el dato que falta, como sintagma nominal: «la cobertura de …».
_MISSING_PHRASES = {
    "requisitos": "los requisitos",
    "cobertura": "la cobertura",
    "condiciones": "las condiciones",
    "consecuencias": "las consecuencias",
    "procedimiento": "el procedimiento",
    "plazo": "los plazos",
    "horario": "el horario",
    "duracion": "la duración",
    "costo": "el costo",
    "responsables": "quién decide sobre lo relativo a",
    "integrantes": "la integración",
    "definicion": "una definición",
}
# Una pregunta de ejemplo por aspecto: una abstención útil deja la siguiente
# pregunta escrita, lista para usar.
_EXAMPLE_QUESTIONS = {
    "requisitos": "¿Cuáles son los requisitos de {focus}?",
    "cobertura": "¿Cuánto {cubre} {focus}?",
    "procedimiento": "¿Cómo se {solicita} {focus}?",
    "condiciones": "¿Qué debo cumplir para mantener {focus}?",
    "consecuencias": "¿Qué pasa si incumplo las condiciones de {focus}?",
    "plazo": "¿Cuáles son las fechas de {focus}?",
    "responsables": "¿Quién decide sobre {focus}?",
    "integrantes": "¿Quiénes integran {focus}?",
    "duracion": "¿Cuánto {dura} {focus}?",
}
# Cómo se ofrece un aspecto al abrir un tema: en términos de lo que el
# estudiante quiere lograr, no del título del artículo.
_GOAL_PHRASES = {
    "requisitos": "qué se necesita",
    "cobertura": "cuánto cubre cada opción",
    "procedimiento": "cómo se tramita",
    "condiciones": "qué hay que cumplir",
    "consecuencias": "qué pasa si se incumple alguna condición",
    "plazo": "las fechas clave",
    "horario": "los horarios",
    "duracion": "cuánto dura",
    "responsables": "quién decide",
    "integrantes": "quiénes lo integran",
}
# Menú para el estudiante que no sabe por dónde empezar: temas que el corpus
# cubre, cada uno con una pregunta que se puede responder tal cual.
TOPIC_MENU = (
    ("becas", "¿Qué becas hay para estudiantes del Altiplano?"),
    ("calendario", "¿Cuándo inician las clases del primer ciclo?"),
    ("admision", "¿Cómo es el proceso de admisión?"),
    ("elecciones", "¿Cómo funcionan las elecciones estudiantiles?"),
    ("clubes", "¿Cómo se crea un club estudiantil?"),
    ("credito", "¿Cómo funciona el crédito educativo?"),
    ("carreras", "¿Qué carreras ofrece el campus?"),
)
_OFFER_ORDER = ("requisitos", "cobertura", "procedimiento", "condiciones", "consecuencias", "plazo", "horario",
                "duracion", "responsables", "integrantes")
_MAX_OFFERS = 3
# Un cierre que ya ofrece o pregunta («¿Quieres conocer más…?», «…puedo ayudarte.»).
_TRAILING_OFFER = re.compile(
    r"\?\s*$|\b(si (quieres|deseas|te interesa|necesitas)|puedo (ayudarte|explicarte|contarte)|"
    r"te gustar[ií]a|quieres (conocer|saber))\b",
    re.IGNORECASE,
)


def available_aspects(article_titles: Sequence[str]) -> list[str]:
    """Aspectos que la normativa trata para un tema, según los títulos de sus artículos."""
    found: set[str] = set()
    for title in article_titles:
        folded = fold(title)
        for aspect in ASPECTS:
            if any(word in folded for word in aspect.title_words):
                found.add(aspect.key)
    return [key for key in _OFFER_ORDER if key in found]


def not_in_answer(available: Sequence[str], answer: str) -> list[str]:
    """Aspectos que la respuesta no trató ya: ofrecer lo recién explicado suena a plantilla."""
    folded = fold(answer)
    # Prefijos de raíz: «incumples» e «incumplimiento» son el mismo concepto.
    stems = {stem[:6] for stem in analyze(answer)}
    pending = []
    for key in available:
        aspect = aspect_by_key(key)
        if aspect is None:
            continue
        # Por el título del aspecto («cobertura») o por sus sinónimos («porcentaje», «incumplimiento»).
        mentioned = (
            any(word in folded for word in aspect.title_words)
            or bool({stem[:6] for stem in analyze(aspect.retrieval_terms)} & stems)
            # El mismo patrón que reconoce el aspecto en una pregunta («cubre», «incumples»);
            # salvo el de plazos, cuyo «cuando» aparece en cualquier explicación.
            or (key != "plazo" and bool(aspect.trigger.search(folded)))
        )
        if not mentioned:
            pending.append(key)
    return pending


def offer_line(available: Sequence[str], exclude: Sequence[str]) -> str:
    """«Si quieres, también puedo explicarte los requisitos, la cobertura o cómo se solicita.»"""
    options = [_OFFER_PHRASES[key] for key in available if key not in exclude and key in _OFFER_PHRASES]
    if not options:
        return ""
    return f"Si quieres, también puedo explicarte {_enumerate(options[:_MAX_OFFERS], 'o')}."


def close_with_offer(answer: str, offer: str) -> str:
    """Una sola invitación al final: la del sistema reemplaza a la del modelo.

    Aunque se le pide que no cierre con preguntas, el modelo a veces termina con
    «¿Quieres conocer más…?». Dos ofrecimientos seguidos suenan a formulario; el
    del sistema gana porque solo nombra lo que la normativa realmente trata.
    """
    if not offer:
        return answer
    paragraphs = answer.rstrip().split("\n\n")
    if len(paragraphs) > 1 and len(paragraphs[-1]) < 240 and _TRAILING_OFFER.search(paragraphs[-1]):
        paragraphs.pop()
    return "\n\n".join(paragraphs) + f"\n\n{offer}"


def overview_offer(available: Sequence[str], exclude: Sequence[str], has_options: bool) -> str:
    """Cierre de un panorama: el siguiente paso según lo que el estudiante quiera lograr.

    «¿Por dónde seguimos? Puedo contarte qué necesitas para aplicar, cuánto cubre
    cada opción o cómo se solicita. Si me cuentas tu situación, te digo cuál se
    ajusta mejor a ti.» La segunda frase solo si hay varias opciones entre las que
    elegir: es lo que haría un asesor antes de recomendar.
    """
    goals = [_GOAL_PHRASES[key] for key in available if key not in exclude and key in _GOAL_PHRASES]
    if not goals:
        return ""
    line = f"¿Por dónde seguimos? Puedo contarte {_enumerate(goals[:_MAX_OFFERS], 'o')}."
    if has_options:
        line += " Si me cuentas tu situación, te digo cuál se ajusta mejor a ti."
    return line


def orientation(focus: str | None, available: Sequence[str], menu: Sequence[tuple[str, str]]) -> str:
    """Para quien no sabe qué preguntar: caminos concretos, no una petición de «más detalle»."""
    lines: list[str] = []
    if focus and available:
        options = [_GOAL_PHRASES[key] for key in available if key in _GOAL_PHRASES][:_MAX_OFFERS]
        lines.append(
            f"Vamos paso a paso. Estábamos viendo {focus}: puedo explicarte {_enumerate(options, 'o')}, "
            "o empezamos por otro tema."
        )
    else:
        lines.append("Claro, te ayudo. Cuéntame qué necesitas resolver; si te sirve, estos son los temas en los que más puedo orientarte:")
    if menu and not (focus and available):
        lines.append("\n".join(f"- **{label[0].upper()}{label[1:]}**: por ejemplo, «{question}»" for label, question in menu))
        lines.append("Escríbeme cualquiera de esas preguntas, o cuéntame qué quieres resolver y lo buscamos juntos.")
    return "\n\n".join(lines)


def example_question(aspect_key: str, focus: str) -> str | None:
    template = _EXAMPLE_QUESTIONS.get(aspect_key)
    if not template:
        return None
    plural = focus.startswith(("las ", "los "))
    verbs = {"cubre": "cubren", "solicita": "solicitan", "dura": "duran"}
    forms = {singular: (plural_form if plural else singular) for singular, plural_form in verbs.items()}
    return _contract(template.format(focus=focus, **forms))


def _contract(text: str) -> str:
    """«de el» → «del», «a el» → «al»."""
    return re.sub(r"\ba el\b", "al", re.sub(r"\bde el\b", "del", text))


def abstention(
    focus: str,
    aspect_key: str | None,
    available: Sequence[str],
    repeated: bool,
    corpus_overview: str | None = None,
    streak: int = 0,
    *,
    covered: Sequence[str] = (),
    document: str | None = None,
    office: str | None = None,
    alternatives: Sequence[tuple[str, str]] = (),
    incidental: bool = False,
) -> str:
    """Abstención que orienta. `incidental`: el tema no tiene documento ni capítulo
    propio, solo aparece de paso en artículos de otro tema (el cambio de carrera en
    los artículos de cobertura de las becas)."""
    aspect = aspect_by_key(aspect_key)
    missing = _MISSING_PHRASES.get(aspect_key or "")
    if missing and missing.endswith(" a"):
        what = f"{missing} {focus}"
    elif missing:
        what = _of(missing, focus)
    else:
        what = f"ese detalle específico sobre {focus}"
    detail = missing or (aspect.phrase if aspect else "ese detalle")
    if repeated and streak >= 3:
        # A partir de la cuarta, repetir la redirección completa sería un eco.
        variants = (
            f"Eso tampoco lo recoge la documentación oficial que tengo sobre {focus}; conviene confirmarlo en el campus.",
            f"Tampoco tengo respaldo oficial para {_of('ese punto', focus)}. Si quieres, cambiamos a otro tema en el que sí pueda ayudarte.",
        )
        return variants[streak % 2]
    if repeated and streak >= 2:
        # Tercera vez sin respaldo: insistir sería inútil. Se redirige a lo que sí hay,
        # sin prometer lo que no se puede cumplir.
        if alternatives:
            scope = f" Puedo ayudarte, en cambio, con {_enumerate([label for label, _ in alternatives[:_MAX_OFFERS]], 'o')}."
        else:
            scope = f" Puedo ayudarte, en cambio, con {corpus_overview}." if corpus_overview else ""
        return (
            f"Sobre {focus} no tengo documentación oficial, así que no puedo confirmarte {detail}. "
            f"Lo más seguro es consultarlo directamente en el campus.{scope}"
        )
    if repeated:
        return f"Sobre {focus} tampoco encontré {detail} en la normativa que consulto."
    if available:
        described = [_OFFER_PHRASES[key] for key in available if key != aspect_key and key in _OFFER_PHRASES][:_MAX_OFFERS]
        where = f"el {document}" if document else "la normativa"
        if incidental and document:
            # Decir con precisión dónde aparece el tema evita ofrecer lo que no hay.
            text = (
                f"El {document} menciona {focus} solo de paso, en sus artículos sobre "
                f"{_enumerate(described, 'y')}, y no establece {what}."
            ) if described else f"No encontré en {where} una disposición que establezca {what}."
        else:
            text = f"No encontré en {where} una disposición que establezca {what}."
            if described:
                text += f" Sí describe {_enumerate(described, 'y')}."
        paragraphs = [text]
        if office:
            paragraphs.append(f"Para confirmar ese punto, conviene consultarlo con {office}, la instancia que el documento menciona para este tema.")
        # Lo siguiente útil: un aspecto que aún no se ha tratado, con la pregunta ya escrita.
        pending = [key for key in available if key != aspect_key and key not in covered and key in _EXAMPLE_QUESTIONS]
        if pending and not incidental:
            question = example_question(pending[0], focus)
            paragraphs.append(f"Si te sirve, seguimos con {_OFFER_PHRASES.get(pending[0], pending[0])}: por ejemplo, «{question}»")
        return "\n\n".join(paragraphs)
    paragraphs = [
        (
            f"{focus[0].upper()}{focus[1:]} no forma parte de la documentación oficial con la que trabajo, "
            "así que no puedo confirmarte nada sobre ese tema; lo más directo es preguntarlo en el campus."
        )
    ]
    if alternatives:
        labels = [label for label, _ in alternatives[:_MAX_OFFERS]]
        paragraphs.append(
            f"En cambio, puedo ayudarte con {_enumerate(labels, 'o')}. Por ejemplo: «{alternatives[0][1]}»"
        )
    elif corpus_overview:
        paragraphs.append(f"Los documentos que consulto tratan sobre {corpus_overview}.")
    return "\n\n".join(paragraphs)


def unmatched(alternatives: Sequence[tuple[str, str]], struggling: bool) -> str:
    """Sin tema reconocido y sin nada en la normativa: pedir otras palabras y abrir caminos."""
    text = (
        "No logré relacionar tu mensaje con la normativa oficial. Si me lo cuentas con otras palabras "
        "(qué quieres hacer o qué te preocupa), lo busco de nuevo."
    )
    if alternatives:
        labels = [label for label, _ in alternatives[:_MAX_OFFERS]]
        text += f"\n\nTambién puedo orientarte con {_enumerate(labels, 'o')}. Por ejemplo: «{alternatives[0][1]}»"
    if struggling:
        text += (
            "\n\nSi seguimos sin dar con ello, puede que ese detalle viva en un procedimiento interno y no en "
            "el reglamento: en ese caso, lo más directo es preguntarlo en el campus."
        )
    return text


def resume(focus: str, covered: Sequence[str], available: Sequence[str]) -> str:
    """«Claro, sigamos con las becas. Hasta ahora vimos… Si quieres, puedo contarte…»"""
    seen = [_OFFER_PHRASES.get(key, aspect.phrase) for key in covered if (aspect := aspect_by_key(key))]
    lines = [f"Claro, sigamos con {focus}."]
    if seen:
        lines.append(f"Hasta ahora vimos {_enumerate(seen, 'y')}.")
    pending = [key for key in available if key not in covered]
    offer = offer_line(pending, ())
    lines.append(offer[:-1] + ". ¿Qué te interesa?" if offer else "¿Qué más quieres saber?")
    return " ".join(lines)


def _of(noun_phrase: str, focus: str) -> str:
    """«la cobertura» + «el crédito educativo» → «la cobertura del crédito educativo»."""
    if focus.startswith("el "):
        return f"{noun_phrase} del {focus[3:]}"
    return f"{noun_phrase} de {focus}"


def _enumerate(items: Sequence[str], conjunction: str) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {conjunction} " + items[-1]
