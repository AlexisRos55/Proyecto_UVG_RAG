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

from app.domain.services.conversation_lexicon import ASPECTS, aspect_by_key, topic_by_key
from app.domain.services.spanish_text import analyze, fold

# Cómo se nombra cada aspecto al ofrecerlo («también puedo explicarte …»).
_OFFER_PHRASES = {
    "requisitos": "los requisitos",
    "cobertura": "la cobertura",
    "condiciones": "las condiciones que hay que cumplir",
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
# Cómo se nombra un aspecto al describir lo que un documento sí trata (sin verbos de oferta).
_DESCRIBED_PHRASES = {
    "requisitos": "los requisitos", "cobertura": "la cobertura", "procedimiento": "el procedimiento",
    "condiciones": "las condiciones", "consecuencias": "las penalizaciones", "plazo": "los plazos",
    "horario": "los horarios", "duracion": "la duración", "responsables": "quién decide",
    "integrantes": "quiénes lo integran",
}
# Clave de tema de cada etiqueta del menú (para orientar un mensaje en inglés).
_MENU_KEYS = {
    "las becas y ayudas financieras": "becas", "el calendario académico": "calendario", "la admisión": "admision",
    "las elecciones estudiantiles": "elecciones", "los clubes y agrupaciones": "clubes",
    "el crédito educativo": "credito", "las carreras": "carreras",
}
_OFFER_ORDER = ("requisitos", "cobertura", "procedimiento", "condiciones", "consecuencias", "plazo", "horario",
                "duracion", "responsables", "integrantes")
_MAX_OFFERS = 3
# Un cierre que ya ofrece o pregunta («¿Quieres conocer más…?», «…puedo ayudarte.»).
_TRAILING_OFFER = re.compile(
    r"\?\s*$|\b(si (quieres|deseas|te interesa|necesitas)|puedo (ayudarte|explicarte|contarte)|"
    r"te gustar[ií]a|quieres (conocer|saber))\b",
    re.IGNORECASE,
)


# El ofrecimiento con que cierra una respuesta: «…puedo explicarte A, B o C.»
_OFFER_CLAUSE = re.compile(r"\bpuedo\s+(?:explicarte|contarte)\s+(?P<items>[^.?]+)", re.IGNORECASE)


def offered_aspects(reply: str) -> tuple[tuple[str, str], ...]:
    """Qué ofreció el último párrafo de una respuesta: (aspecto, frase con que se ofreció), en orden.

    Es la inversa de `offer_line`, `overview_offer`, `orientation` y `resume`: así
    «sí» o «la primera» se resuelven contra lo que de verdad se ofreció.
    """
    last = reply.rstrip().rsplit("\n\n", 1)[-1]
    clause = _OFFER_CLAUSE.search(last)
    if clause is None:
        return ()
    items = fold(clause.group("items"))
    best: dict[str, tuple[int, int, str]] = {}
    for table in (_OFFER_PHRASES, _GOAL_PHRASES, _DESCRIBED_PHRASES, {"cobertura": "qué cubre"}):
        for key, phrase in table.items():
            position = items.find(fold(phrase))
            # La frase más larga en la primera posición: «cuánto cubre cada opción», no «qué cubre».
            if position >= 0 and (key not in best or (position, -len(phrase)) < best[key][:2]):
                best[key] = (position, -len(phrase), phrase)
    return tuple((key, phrase) for key, (_, _, phrase) in sorted(best.items(), key=lambda item: item[1][:2]))


def choose_offer(phrases: Sequence[str]) -> str:
    """«Sí» a varias opciones: un asesor pregunta por cuál empezar, con las mismas palabras que ofreció."""
    return f"Con gusto. ¿Por cuál empezamos: {_enumerate(list(phrases), 'o')}?"


def ask_again(previous: str) -> str:
    """La misma aclaración por segunda vez, dicha de otra forma y más corta."""
    if "¿Por cuál empezamos" in previous:
        return "Elige una y empezamos: " + previous.split(":", 1)[1].strip().rstrip("?") + "."
    return "Para no adivinar, necesito un dato más: dime a qué te refieres (el nombre de la beca, el trámite o el tema) y lo busco."


def accept_close() -> str:
    """«No» a un ofrecimiento: se respeta, sin insistir."""
    return "Está bien. Si te surge otra duda, aquí estoy."


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
    goals = [_goal(key, has_options) for key in available if key not in exclude and key in _GOAL_PHRASES]
    if not goals:
        return ""
    line = f"¿Por dónde seguimos? Puedo contarte {_enumerate(goals[:_MAX_OFFERS], 'o')}."
    if has_options:
        line += " Si me cuentas tu situación, te digo cuál se ajusta mejor a ti."
    return line


def _goal(key: str, has_options: bool) -> str:
    """«cuánto cubre cada opción» solo tiene sentido cuando hay opciones (becas); si no, «qué cubre»."""
    if key == "cobertura" and not has_options:
        return "qué cubre"
    return _GOAL_PHRASES[key]


# Lo primero que suele necesitar quien recién llega a la universidad.
_NEWCOMER_ORDER = ("admision", "calendario", "carreras", "becas")


def orientation(
    focus: str | None,
    available: Sequence[str],
    menu: Sequence[tuple[str, str]],
    mood: str | None = None,
    newcomer: bool = False,
) -> str:
    """Para quien no sabe qué preguntar: caminos concretos, no una petición de «más detalle».

    Con angustia, la primera frase es de calma; a quien recién llega se le da la
    bienvenida y se le muestra primero lo que suele necesitar (admisión, calendario).
    """
    lines: list[str] = []
    calm = mood == "angustia"
    if focus and available:
        options = [_goal(key, False) for key in available if key in _GOAL_PHRASES][:_MAX_OFFERS]
        lines.append(
            f"{'Vamos por partes, con calma.' if calm else 'Vamos paso a paso.'} Estábamos viendo {focus}: "
            f"puedo explicarte {_enumerate(options, 'o')}, o empezamos por otro tema."
        )
    elif newcomer:
        menu = _for_newcomers(menu)
        lines.append("Te doy la bienvenida. Para empezar, esto es lo que más le sirve a quien recién llega:")
    else:
        opener = "Vamos por partes, con calma, que entre los dos lo resolvemos." if calm else "Claro, te ayudo."
        lines.append(f"{opener} Cuéntame qué necesitas resolver; si te sirve, estos son los temas en los que más puedo orientarte:")
    if menu and not (focus and available):
        lines.append("\n".join(f"- **{label[0].upper()}{label[1:]}**: por ejemplo, «{question}»" for label, question in menu))
        lines.append("Escríbeme cualquiera de esas preguntas, o cuéntame qué quieres resolver y lo buscamos juntos.")
    return "\n\n".join(lines)


def is_orientation(text: str) -> bool:
    """¿Era una orientación la respuesta anterior? (para no darla dos veces seguidas)."""
    return (
        "o empezamos por otro tema" in text
        or ("lo buscamos juntos." in text and "temas en los que" in text)
        or text.startswith("Te doy la bienvenida")
    )


def _for_newcomers(menu: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    rank = {key: index for index, key in enumerate(_NEWCOMER_ORDER)}
    return sorted(menu, key=lambda item: rank.get(_MENU_KEYS.get(item[0], ""), len(rank)))


def recommend_first(
    focus: str | None, available: Sequence[str], menu: Sequence[tuple[str, str]], newcomer: bool = False
) -> str:
    """La orientación pedida por segunda vez: un asesor ya no da la lista, recomienda un paso."""
    menu = _for_newcomers(menu) if newcomer else menu
    if focus and available:
        question = example_question(available[0], focus)
        if question:
            return f"Te propongo empezar por {_GOAL_PHRASES.get(available[0], available[0])}. Escríbeme, por ejemplo: «{question}»"
    if menu:
        label, question = menu[0]
        return f"Te propongo empezar por {label}. Escríbeme, por ejemplo: «{question}», y lo vemos juntos."
    return "Cuéntame en una frase qué quieres resolver y lo buscamos juntos."


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
    structured: bool = True,
    asked: str | None = None,
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
    elif asked:
        # Sin aspecto reconocido, se nombra lo que el estudiante preguntó, con sus palabras.
        what = f"«{asked}»"
    else:
        what = f"ese detalle específico sobre {focus}"
    # «quién decide sobre lo relativo a» solo funciona seguido del foco; sola, la frase del aspecto.
    detail = (missing if missing and not missing.endswith(" a") else None) or (aspect.phrase if aspect else "ese detalle")
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
            f"Lo más conveniente es consultarlo directamente en el campus.{scope}"
        )
    if repeated and not available and not document:
        # El tema entero no está documentado: no se «buscó en la normativa» cada detalle.
        return f"Como te comentaba, {focus} no está en la documentación que consulto, así que tampoco puedo confirmarte {detail}."
    if repeated:
        return f"Sobre {focus} tampoco encontré {detail} en la normativa que consulto."
    if available:
        described = [_DESCRIBED_PHRASES[key] for key in available if key != aspect_key and key in _DESCRIBED_PHRASES][:_MAX_OFFERS]
        where = f"el {document}" if document else "la normativa"
        if incidental and document:
            # Decir con precisión dónde aparece el tema evita ofrecer lo que no hay.
            text = (
                f"El {document} menciona {focus} solo de paso, en sus artículos sobre "
                f"{_enumerate(described, 'y')}, y no responde a {what}."
                if asked and not missing
                else f"El {document} menciona {focus} solo de paso, en sus artículos sobre "
                f"{_enumerate(described, 'y')}, y no establece {what}."
            ) if described and structured else _not_found(where, what, bool(asked and not missing))
        else:
            text = _not_found(where, what, bool(asked and not missing))
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
    if document:
        # El tema sí tiene documento, pero no el dato: se dice dónde se buscó.
        paragraphs = [_not_found(f"el {document}", what, bool(asked and not missing))]
        if office:
            paragraphs.append(f"Para confirmarlo, conviene consultarlo con {office}, la instancia que el documento menciona.")
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


def unmatched(alternatives: Sequence[tuple[str, str]], struggling: bool, retrieved: bool = False) -> str:
    """Sin tema reconocido: pedir otras palabras y abrir caminos.

    `retrieved`: hubo normativa parecida, pero no respondía la pregunta. Se dice
    así, sin mandar al estudiante a un artículo que no le sirve.
    """
    if retrieved:
        text = (
            "Encontré normativa parecida, pero ninguna disposición responde exactamente a eso. "
            "Si me dices qué quieres resolver (por ejemplo, un trámite, una fecha o un requisito), lo busco con más precisión."
        )
    else:
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


_ASPECT_EXAMPLES = {
    "requisitos": "de una beca, de la inscripción o para crear un club",
    "plazo": "de la inscripción, del pago de cuotas o de la graduación",
    "cobertura": "de una beca o del crédito educativo",
    "costo": "de la inscripción o de la mensualidad de una carrera",
    "procedimiento": "para solicitar una beca, inscribirte o crear un club",
    "duracion": "de una carrera, de una beca o de un cargo estudiantil",
    "consecuencias": "de reprobar un curso, de retirarte o de no cumplir con una beca",
}


def not_a_record(topic_label: str, example: str | None) -> str:
    """El tema es del dominio, pero lo preguntado es un caso o un registro, no normativa."""
    text = (
        "Eso no lo recoge la documentación que consulto: tengo los reglamentos y documentos oficiales, "
        f"no registros de casos o resultados. Sobre {topic_label} sí puedo explicarte cómo funcionan."
    )
    return text + (f" Por ejemplo: «{example}»" if example else "")


_Alternatives = Sequence[tuple[str, str]]


def _clarify_action(detail: str, document: str | None, alternatives: _Alternatives) -> str:
    key = {"inscripcion": "admision", "pagos": "calendario", "retiro": "calendario"}.get(detail, detail)
    example = next((q for label, q in alternatives if key and key == _MENU_KEYS.get(label)), None)
    return (
        "No puedo hacer trámites por ti: no tengo acceso a los sistemas de la universidad. "
        "Lo que sí puedo es explicarte cómo es el proceso, qué piden y en qué fechas, para que lo hagas sin tropiezos."
        + (f" Por ejemplo: «{example}»" if example else "")
    )


def _clarify_no_options(detail: str, document: str | None, alternatives: _Alternatives) -> str:
    topic = topic_by_key(detail)
    about = f" Hasta ahora hablamos de {topic.label} en general" if topic else " Todavía no te he dado opciones"
    return f"¿A cuál te refieres?{about}; si me dices el nombre, lo busco."


def _clarify_english(detail: str, document: str | None, alternatives: _Alternatives) -> str:
    example = next((q for label, q in alternatives if detail and detail in _MENU_KEYS.get(label, "")), None)
    if example is None and alternatives:
        example = alternatives[0][1]
    return (
        "Por ahora respondo en español, con base en la normativa oficial de UVG Altiplano. "
        + (f"Puedes preguntarme, por ejemplo: «{example}»" if example else "¿En qué te ayudo?")
    )


def _clarify_introduction(detail: str, document: str | None, alternatives: _Alternatives) -> str:
    options = _enumerate([label for label, _ in alternatives[:_MAX_OFFERS]], "o") if alternatives else ""
    return "Con gusto le ayudo. ¿Qué le gustaría saber?" + (f" Puedo orientarle, por ejemplo, sobre {options}." if options else "")


def _clarify_aspect(detail: str, document: str | None, alternatives: _Alternatives) -> str:
    aspect = aspect_by_key(detail)
    examples = _ASPECT_EXAMPLES.get(detail)
    what = _MISSING_PHRASES.get(detail, aspect.phrase if aspect else "eso")
    return f"¿{what[0].upper()}{what[1:]} de qué?" + (f" Por ejemplo, {examples}." if examples else "")


# Motivo de la aclaración (como lo nombra el rastreador) → cómo la diría un asesor.
_CLARIFICATIONS = (
    ("pide un trámite", _clarify_action),
    ("referencia sin opciones", _clarify_no_options),
    ("elige entre lo ofrecido", lambda detail, *_: choose_offer(detail.split("|"))),
    ("rechaza lo ofrecido", lambda *_: accept_close()),
    ("mensaje en inglés", _clarify_english),
    ("presentación de", _clarify_introduction),
    ("aspecto sin tema", _clarify_aspect),
    ("comparte una alegría", lambda *_: "¡Qué gusto! Me alegra mucho. Si quieres, seguimos con lo que necesitas saber."),
)


def clarify(reason: str, document: str | None, alternatives: _Alternatives) -> str:
    """Una pregunta corta cuando no hay a qué referirse, como haría una persona."""
    for prefix, handler in _CLARIFICATIONS:
        if reason.startswith(prefix):
            return handler(reason.split(":", 1)[1].strip() if ":" in reason else "", document, alternatives)
    if "artículo" in reason:
        where = f" del {document}" if document else ""
        return f"¿Qué artículo{where} quieres revisar? Dime el número; por ejemplo, «Artículo 20»."
    if "resumir" in reason:
        return "Con gusto lo resumo, pero todavía no te he explicado nada en esta conversación. ¿Sobre qué tema quieres el resumen?"
    text = "¿A qué te refieres? Todavía no hemos hablado de un tema en esta conversación."
    if alternatives:
        labels = [label for label, _ in alternatives[:_MAX_OFFERS]]
        text += f" Puedo ayudarte con {_enumerate(labels, 'o')}; por ejemplo: «{alternatives[0][1]}»"
    return text


# Cierre que manda a confirmar en el campus: útil una vez, ruido si se repite en cada respuesta.
_REFERRAL = re.compile(r"\b(?:conviene|consult\w*|confirm\w*|verific\w*|acerca\w*)\b.*\bcampus\b", re.IGNORECASE)


def drop_repeated_referral(answer: str, previous_answer: str) -> str:
    """Quita el último párrafo «confírmalo en el campus» si la respuesta anterior ya lo dijo."""
    paragraphs = answer.rstrip().split("\n\n")
    if len(paragraphs) < 2 or not previous_answer:
        return answer
    last = paragraphs[-1]
    if len(last) > 260 or not _REFERRAL.search(last) or not _REFERRAL.search(previous_answer):
        return answer
    if _MISSING.search(last):
        # Lo que falta se sigue diciendo; solo sobra volver a mandar al campus.
        trimmed = _REFERRAL_CLAUSE.sub(".", last)
        return "\n\n".join([*paragraphs[:-1], trimmed]) if trimmed != last else answer
    return "\n\n".join(paragraphs[:-1])


_MISSING = re.compile(r"\bno\s+(?:aparece\w*|establece\w*|especifica\w*|detalla\w*|indica\w*|fija\w*)\b", re.IGNORECASE)
_REFERRAL_CLAUSE = re.compile(r"[;,]\s*(?:por\s+lo\s+que\s+|así\s+que\s+)?(?:conviene|consult|confirm|verific)[^.;]*campus[^.;]*\.", re.IGNORECASE)


def resume(focus: str, covered: Sequence[str], available: Sequence[str]) -> str:
    """«Claro, sigamos con las becas. Hasta ahora vimos… Si quieres, puedo contarte…»"""
    # Lo ya visto se nombra con frases neutras: «las condiciones», no «para mantenerla».
    seen = [_DESCRIBED_PHRASES.get(key, aspect.phrase) for key in covered if (aspect := aspect_by_key(key))]
    lines = [f"Claro, sigamos con {focus}."]
    if seen:
        lines.append(f"Hasta ahora vimos {_enumerate(seen, 'y')}.")
    pending = [key for key in available if key not in covered]
    offer = offer_line(pending, ())
    lines.append(offer[:-1] + ". ¿Qué te interesa?" if offer else "¿Qué más quieres saber?")
    return " ".join(lines)


def _not_found(where: str, what: str, question: bool) -> str:
    if question:
        return f"No encontré en {where} nada que responda a {what}."
    return f"No encontré en {where} una disposición que establezca {what}."


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
