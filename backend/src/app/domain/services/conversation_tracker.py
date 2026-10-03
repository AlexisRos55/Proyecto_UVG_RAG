"""Seguimiento conversacional y resolución de referencias, sin llamar al modelo.

El recuperador solo sabe buscar lo que se le pide. Si el estudiante escribe
«¿Y cuáles son los requisitos?», buscar esa frase tal cual devuelve requisitos de
cualquier cosa: cargos electorales, clubes, admisión. Este servicio decide, antes
de buscar, **de qué** se está hablando:

1. Reconoce en el mensaje temas, aspectos, entidades del corpus y marcadores de
   discurso (anáforas, continuación, navegación por artículos).
2. Decide si el mensaje es autosuficiente o depende del foco activo.
3. Construye la consulta interna: las palabras del estudiante más el foco
   (entidad o tema) y el aspecto preguntado.
4. Tras la respuesta, actualiza el foco con lo que realmente se citó.

Todo es determinista: se puede probar exhaustivamente, cuesta cero tokens y la
misma conversación produce siempre la misma interpretación.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID

from app.domain.entities.message import Message, MessageRole
from app.domain.services.conversation_guide import offered_aspects
from app.domain.services.conversation_lexicon import (
    ACTION_REQUEST,
    AFFIRM,
    ANAPHORA,
    ARTICLE_REFERENCE,
    ARTICLE_STEP,
    AUDIENCES,
    AWARDED,
    BARE_REPLY,
    CAREER_WORDS,
    CATEGORY_REFERENCE,
    CONFUSED,
    CONTINUE,
    COURTESY,
    DECLINE,
    DEEPEN,
    DISCOURSE_WORDS,
    DOCUMENT_REFERENCE,
    ENCLITIC,
    ENGLISH,
    ENGLISH_TOPICS,
    EXAMPLE,
    FINANCIAL_NEED,
    HELP_REQUEST,
    LATER,
    LEAD_IN,
    LOST,
    MOODS,
    MORE_TO_KNOW,
    NEWCOMER,
    ORDINAL,
    ORDINAL_INDEX,
    OVERVIEW_REQUEST,
    PERSONA_CLAUSE,
    PROCLITIC,
    RESUME,
    RETURN_TO,
    SPANISH_HINT,
    SUMMARIZE,
    TOPICS,
    WHY,
    Aspect,
    Topic,
    anchor_terms,
    aspect_by_key,
    aspect_terms,
    detect_aspects,
    detect_topics,
    topic_by_key,
)
from app.domain.services.entity_extractor import find_entities
from app.domain.services.institutional_lexicon import correct_typos, normalize_chat_speak
from app.domain.services.query_analyzer import article_references
from app.domain.services.spanish_text import STOPWORDS, analyze, fold
from app.domain.value_objects.conversation_state import (
    ConversationState,
    TurnInterpretation,
    TurnMode,
)
from app.domain.value_objects.corpus_entity import CorpusEntity, EntityKind

_FOCUSABLE = (EntityKind.PROGRAM, EntityKind.OFFICE, EntityKind.CAREER, EntityKind.PERSON)
# «Esa oficina», «ese programa»: qué clase de entidad señala cada sustantivo.
_CATEGORY_KIND = {
    "beca": EntityKind.PROGRAM, "becas": EntityKind.PROGRAM, "programa": EntityKind.PROGRAM,
    "programas": EntityKind.PROGRAM, "credito": EntityKind.PROGRAM, "creditos": EntityKind.PROGRAM,
    "carrera": EntityKind.CAREER, "carreras": EntityKind.CAREER, "persona": EntityKind.PERSON,
}
# Lo que se recuerda de las entidades mencionadas: suficiente para «la de antes».
_RECENT_ENTITIES = 8
# Una conversación larga no debe olvidar su tema por ser larga: se reproduce el
# historial completo hasta este tope (coste lineal y pequeño). El olvido natural
# llega por el silencio, no por el número de turnos.
_REPLAY_WINDOW = 120
MEMORY_TTL = timedelta(days=7)
_MAX_OVERVIEW_EXPANSIONS = 8
# Mensajes de pocas palabras sin tema propio se leen como continuación del foco.
_SHORT_MESSAGE_WORDS = 4
# Interjecciones al inicio y cortesías o emojis al final que no cambian la intención.
_FRAME = re.compile(
    r"^(?:(?:ja(?:ja)+\w*|je(?:je)+|ok(?:ay)?|bueno|mmm+|ah|eh|oye|mira|pues|va|dale|ya)[\s,.!]+)+"
    r"|[\s,.!]*(?:(?:por\s+favor|porfa|plis|pls|gracias|please|thanks|thank\s+you|thx)[\s.!]*|[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]+[\s.!]*)+$"
)
# «¿Cuáles existen?», «¿qué opciones hay?»: enumerar lo que ofrece el tema en curso.
_ENUMERATE = re.compile(
    r"^(?:y\s+)?(?:cuales|que)\s+(?:existen|hay|son|ofrecen|ofrece|tienen|manejan)(?:\s+(?:aqui|en\s+la\s+(?:u|universidad)))?$"
    r"|^(?:y\s+)?(?:que|cuales)\s+(?:opciones|tipos|programas|modalidades)\s+(?:hay|existen|tienen|ofrecen)$"
)
_NAMES_AID = re.compile(r"\b(?:becas?|ayudas?|apoyos?|credito|financiamiento|prestamo)\b")
# «¿Esa cuál era?», «¿cuál era?»: pide recordar una opción concreta.
_WHICH_WAS_IT = re.compile(r"^(?:y\s+)?(?:esa|ese|aquella|aquel)?\s*cual\s+(?:era|es|fue|dijiste)$")
# «¿Y cuánto?», «cuánto es», sin decir de qué.
_BARE_AMOUNT = re.compile(r"^(?:y\s+)?(?:entonces\s+)?cuanto(?:\s+(?:es|seria|sale))?$")
_COVERAGE_TOPICS = frozenset(["becas", "credito", "seguro", "horas_beca"])
# Muletillas de chat y de trato: no aportan nada a la búsqueda.
_FILLER_WORDS = re.compile(
    r"\b(?:mire|mira|fijese|fijate|oiga|oye|vea|ve|porfa|por\s+favor|xfa|pls|plis|plz|ja(?:ja)+\w*|je(?:je)+\w*|xd+|tons|pues)\b[\s,]*",
    re.IGNORECASE,
)
_SYMBOLS = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]+")
# «Allí», «ahí», «en ese reglamento»: el documento que se está consultando.
_THERE = re.compile(r"\b(?:alli|ahi)\b|\ben\s+(?:ese|este|el\s+mismo|dicho)\s+(?:reglamento|documento|calendario|folleto)\b")
# Palabras que nombran el documento o el acto de leerlo, no el asunto preguntado.
_DOCUMENT_WORDS = frozenset(["reglamento", "documento", "calendario", "folleto", "dice", "dicen", "habla", "menciona", "establece", "trata", "alli", "ahi", "mas"])
# Preguntas por la ficha del documento (quién lo aprobó, versión, vigencia): no por su contenido.
_RECORD_QUESTION = re.compile(r"\b(?:aprob\w*|autoriz\w*|elabor\w*|revis[oó]\w*|version\w*|vigen\w*|codigo|paginas|actualiz\w*|fecha\s+de\s+emision)\b")
# Muletillas que no son contenido de la pregunta.
_FILLER = re.compile(r"ja(?:ja)+\w*|je(?:je)+|porfa|plis|pls|mmm+|xd")
# A partir de aquí un mensaje se trata como largo (relato del estudiante, no una pregunta corta).
_LONG_MESSAGE_WORDS = 25
_MAX_STORY_QUESTIONS = 4
_WORD = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+")
# Palabras que solo expresan el aspecto preguntado, no un tema nuevo.
ASPECT_WORDS = re.compile(
    r"^(?:cubre\w*|cobertura|porcentaje|monto|requisitos?|plazos?|fechas?|hora|horario|cuesta|costo|precio|dura\w*"
    r"|duracion|pasos?|proceso|solicit\w+|aplic\w+|tramit\w+|condiciones?|mantener|decide\w*|aprueba\w*"
    r"|asigna\w*|personas|miembros?|integrantes?|significa|consiste|pierdo|perder|pasa|dan|da|otorga\w*"
    # Palabras «meta»: cómo seguir la conversación, no de qué hablar.
    r"|detalles?|ejemplos?|excepcion\w*|informacion|dudas?|opciones?|casos?|tipos?|diferencias?|ventajas?"
    r"|beneficios?|despues|primero|mejor(?:es)?|recomi?end\w*|conviene\w*|existen?|cual(?:es)?|revisar|algo"
    r"|todo|tiene|necesit\w*|puedo|aplicar\w*|autorizacion|tarda\w*|renueva\w*|gana)$"
)


@dataclass(frozen=True, slots=True)
class ReplayCheckpoint:
    """Estado tras los primeros `consumed` mensajes de una conversación.

    Permite reproducir solo lo nuevo en cada turno: sin él, una conversación de
    n turnos reinterpreta su historial completo en cada uno (coste cuadrático).
    """

    consumed: int
    last_message_id: UUID
    state: ConversationState
    previous_time: datetime | None


@dataclass(frozen=True, slots=True)
class _Signals:
    """Lo que dice el mensaje, calculado una vez y compartido por todas las reglas."""

    message: str
    folded: str
    topics: list[Topic]
    aspects: list[Aspect]
    mentioned: list[CorpusEntity]
    campus: str | None
    content: list[str]
    # Palabras con contenido que no son aspecto ni ordinal: lo que el mensaje aporta de suyo.
    bare: list[str]

    @property
    def aspect(self) -> Aspect | None:
        return self.aspects[0] if self.aspects else None


class ConversationTracker:
    def __init__(
        self,
        entities: Sequence[CorpusEntity] = (),
        vocabulary: Callable[[Collection[UUID]], frozenset[str]] | None = None,
        co_occur: Callable[[Collection[str], Collection[str]], bool] | None = None,
    ) -> None:
        self._entities = list(entities)
        self._title_words: tuple[str, ...] = ()
        self._vocabulary = vocabulary
        self._co_occur = co_occur
        self._focusable = [e for e in self._entities if e.kind in _FOCUSABLE]

    # --- Reconstrucción del estado -------------------------------------------------

    def replay(self, history: Sequence[Message]) -> ConversationState:
        """Estado tras los mensajes persistidos (ventana de los últimos turnos).

        Los intercambios sociales o de cortesía (respuesta local: sin
        fundamentación que evaluar ni fuentes) no tocan el foco. Por eso
        «Gracias» y «Hola» no borran el tema: el estudiante puede decir
        «continuemos» y seguir donde estaba.
        """
        return self.replay_from(history, None)[0]

    def replay_from(
        self, history: Sequence[Message], checkpoint: ReplayCheckpoint | None
    ) -> tuple[ConversationState, ReplayCheckpoint | None]:
        """`replay` incremental: parte del punto de control si sigue siendo válido.

        Es exactamente equivalente a reproducir todo: el punto de control solo se
        usa mientras la ventana no recorta el historial y si el historial lo
        contiene tal cual; y solo se emite cuando el historial termina en una
        respuesta (así ningún mensaje ya procesado cambia de pareja después).
        """
        messages = list(history)
        window = messages[-_REPLAY_WINDOW:]
        state, previous_time, start = ConversationState(), None, 0
        if (
            checkpoint is not None and len(messages) <= _REPLAY_WINDOW and 0 < checkpoint.consumed <= len(messages)
            and messages[checkpoint.consumed - 1].id == checkpoint.last_message_id
        ):
            state, previous_time, start = checkpoint.state, checkpoint.previous_time, checkpoint.consumed
        for index in range(start, len(window)):
            message = window[index]
            # Tras una semana sin conversar, el foco anterior ya no se ofrece como
            # continuación: el estudiante vuelve con otra necesidad.
            if previous_time is not None and message.created_at - previous_time > MEMORY_TTL:
                state = ConversationState()
            previous_time = message.created_at
            if message.role is not MessageRole.STUDENT:
                continue
            reply = next((m for m in window[index + 1 :] if m.role is MessageRole.ASSISTANT), None)
            if reply is None or (reply.is_grounded is None and not reply.sources):
                # Un intercambio social es una pausa: «sigamos» después de él retoma el tema.
                # Una orientación local también puede ofrecer algo («puedo explicarte…»).
                state = replace(state, paused=True, offered=offered_aspects(reply.content) if reply else ())
                continue
            state = self.advance(state, self.interpret(correct_typos(message.content), state), reply)
        resumable = messages and len(messages) <= _REPLAY_WINDOW and messages[-1].role is MessageRole.ASSISTANT
        return state, (ReplayCheckpoint(len(messages), messages[-1].id, state, previous_time) if resumable else None)

    def advance(
        self, state: ConversationState, turn: TurnInterpretation, reply: Message | None
    ) -> ConversationState:
        if turn.mode is TurnMode.RESUME:
            return state

        topic_changed = turn.topic is not None and turn.topic != state.topic
        cited_documents = tuple(dict.fromkeys(s.document_id for s in (reply.sources if reply else ()) if s.document_id))
        cited_articles = {
            int(match.group(1))
            for source in (reply.sources if reply else ())
            for match in [re.search(r"Artículo (\d+)", source.section or "")]
            if match
        }
        article = (
            turn.article_numbers[0]
            if len(turn.article_numbers) == 1
            else next(iter(cited_articles))
            if len(cited_articles) == 1
            else None
        )
        candidates: tuple[CorpusEntity, ...] = ()
        if reply and reply.is_grounded:
            folded_reply = fold(reply.content)
            # En una respuesta, una opción cuenta solo si se nombra completa: «ayuda
            # financiera» no nombra a la Dirección ni al Comité de Ayudas Financieras.
            found = [e for e in find_entities(reply.content, self._focusable) if _named_in(e, folded_reply)]
            # En orden de aparición: tras «¿cuál cubre más?», la primera nombrada es la respuesta.
            candidates = tuple(sorted(found, key=lambda e: _first_position(folded_reply, e)))
        covered = () if topic_changed else state.covered_aspects
        # Solo cuenta como «ya visto» lo que se respondió: una abstención no lo es.
        if turn.aspect and turn.aspect not in covered and (reply is None or reply.is_grounded is not False):
            covered = (*covered, turn.aspect)
        remembered = [e for e in (turn.entity, *turn.compared) if e is not None]
        if len(candidates) == 1 and turn.entity is None:
            # Lo que se hablaba pesa más que lo que solo se mencionó de paso.
            remembered.append(candidates[0])
        recent = tuple(dict.fromkeys((*remembered, *state.recent_entities)))[:_RECENT_ENTITIES]
        listed = self._comparable(replace(state, candidates=candidates, topic=turn.topic or state.topic))
        options = listed if len(listed) >= 2 else (() if topic_changed else state.options)
        return ConversationState(
            topic=turn.topic or state.topic,
            entity=turn.entity,
            aspect=turn.aspect,
            documents=cited_documents or (() if topic_changed else state.documents),
            article=article,
            campus=turn.campus or (None if topic_changed else state.campus),
            career=turn.career or (None if topic_changed else state.career),
            last_query=turn.retrieval_query,
            last_grounded=reply.is_grounded if reply else None,
            covered_aspects=covered,
            candidates=candidates,
            ranked=bool(RANKING_QUESTION.search(normalize_chat_speak(fold(turn.message)))),
            last_message=turn.message,
            recent_entities=recent,
            compared=turn.compared,
            options=options,
            audience=turn.audience or state.audience,
            offered=offered_aspects(reply.content) if reply else (),
        )

    # --- Interpretación del turno actual ---------------------------------------------

    def interpret(self, message: str, state: ConversationState) -> TurnInterpretation:
        """Interpreta el turno; quien se presenta («soy papá de un estudiante») define el trato, no la búsqueda."""
        folded = fold(message)
        if len(ENGLISH.findall(folded)) >= 2 and len(SPANISH_HINT.findall(folded)) <= 1 and not detect_topics(folded):
            # Pregunta en inglés: se responde en español y se orienta al tema que nombre.
            hinted = next((key for key, pattern in ENGLISH_TOPICS if re.search(pattern, folded)), None)
            turn = self._build(message, TurnMode.NEW, "", state, f"mensaje en inglés: {hinted or ''}")
            return replace(turn, needs_clarification=True)
        audience = next((name for name, pattern in AUDIENCES if pattern.search(folded)), None)
        core = LEAD_IN.sub("", message, count=1).strip() or message
        if len(core.split()) > _LONG_MESSAGE_WORDS:
            # Mensaje largo: el saludo y el «gracias de antemano» no se buscan.
            core = COURTESY.sub(" ", fold(core)).strip() or core
        if audience:
            stripped = PERSONA_CLAUSE.sub("", core).strip()
            introduction = stripped == core and re.match(
                r"^\s*(?:(?:hola|buen(?:as|os)?\s+\w+|buen\s+dia)[,.!\s]+)*(?:soy|trabajo)\b", fold(core)
            )
            # «Soy docente. Háblame del crédito educativo»: tras la presentación viene una petición.
            asks = stripped != core and bool(detect_topics(fold(stripped)) or OVERVIEW_REQUEST.search(fold(stripped)))
            if not stripped or (not stripped.endswith("?") and not asks and (
                introduction or (not detect_aspects(fold(stripped)) and len(stripped.split()) <= 6)
            )):
                # «Soy mamá de una estudiante de primer ingreso»: se presenta, todavía no pregunta.
                turn = self._build(message, TurnMode.NEW, "", state, f"presentación de {audience}")
                return replace(turn, audience=audience, needs_clarification=True)
            # Tras la presentación, la fórmula de entrada tampoco es la pregunta: «…Quiero saber si…».
            stripped = LEAD_IN.sub("", stripped, count=1).strip() or stripped
            core = re.sub(r"\bmi\s+(?:hijo|hija)\b", "el estudiante", stripped, flags=re.IGNORECASE)
        turn = self._interpret(core, state)
        mood = next((name for name, pattern in MOODS if pattern.search(folded) or pattern.search(message)), None)
        return replace(turn, message=message, audience=audience or state.audience, mood=mood)

    def as_follow_up(self, message: str, state: ConversationState) -> TurnInterpretation:
        """La misma pregunta leída como seguimiento del tema activo.

        Para cuando se interpretó como pregunta nueva sin tema propio y la
        búsqueda no encontró nada: «¿me devuelven el dinero?» tras hablar de retiros.
        """
        core = LEAD_IN.sub("", message, count=1).strip() or message
        folded = normalize_chat_speak(fold(core)).strip(" ¿?¡!.")
        aspects = detect_aspects(folded)
        turn = self._follow_up(core, state, aspects[0] if aspects else None, self._content_words(core), None, anaphoric=True)
        return replace(turn, message=message, audience=state.audience)

    def _interpret(self, message: str, state: ConversationState) -> TurnInterpretation:
        """Las reglas se prueban en orden: la primera que reconoce el turno lo interpreta.

        El orden importa y está pensado de lo más específico a lo general: una
        pausa («continuemos mañana») antes que «continúa»; una referencia sin
        antecedente antes que cualquier búsqueda; la decisión entre seguimiento y
        pregunta nueva, al final.
        """
        signals = self._signals(message)
        for rule in (
            self._pause, self._action, self._offer_reply, self._summary, self._continuation, self._lost, self._confusion, self._return,
            self._unanchored, self._article_or_document, self._ordinal, self._dangling_choice, self._resume, self._deepen,
            self._article_navigation, self._career_reference, self._category_entity,
            self._bare_reply, self._bare_amount, self._enumerate,
        ):
            turn = rule(signals, state)
            if turn is not None:
                return turn
        return self._follow_up_or_new(signals, state)

    def _signals(self, message: str) -> _Signals:
        folded = normalize_chat_speak(fold(message)).strip(" ¿?¡!.")
        # «jaja continuemos», «dame más detalles porfa 🙏»: el marco no cambia lo que se pide.
        folded = _FRAME.sub("", folded).strip(" ¿?¡!.,") or folded
        aspects = detect_aspects(folded)
        if AWARDED.search(folded):
            # «Me dieron la beca, ¿y ahora qué hago?»: lo primero es lo que hay que cumplir para mantenerla.
            aspects = sorted(aspects, key=lambda a: a.key != "condiciones")
        content = self._content_words(message)
        # Todos los aspectos detectados orientan el reordenamiento: «¿pierdo la beca si
        # bajo mi promedio?» es a la vez consecuencias y condiciones (promedio mínimo).
        self._title_words = tuple(dict.fromkeys(w for a in aspects for w in a.title_words))
        return _Signals(
            message=message,
            folded=folded,
            topics=detect_topics(folded),
            aspects=aspects,
            mentioned=_distinct_mentions(find_entities(message, self._focusable), folded),
            campus=next((e.name for e in find_entities(message, self._entities, [EntityKind.CAMPUS])), None),
            content=content,
            bare=[w for w in content if not ASPECT_WORDS.search(fold(w)) and not ORDINAL.search(fold(w))],
        )

    # --- Reglas de interpretación (cada una devuelve None si no aplica) ---------------

    def _pause(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not LATER.search(s.folded):
            return None
        # Despedida con intención de volver: la atiende el catálogo local.
        return self._build(s.message, TurnMode.NEW, "", state, "despedida con continuidad")

    def _action(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not ACTION_REQUEST.search(s.folded):
            return None
        # «¿Me puedes inscribir?»: el asistente no hace trámites; lo dice y ofrece explicar el proceso.
        topic = s.topics[0].key if s.topics else (state.topic or "")
        return replace(self._build(s.message, TurnMode.NEW, "", state, f"pide un trámite: {topic}"), needs_clarification=True)

    def _offer_reply(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        """«Sí», «no» o «la primera» justo después de «Si quieres, también puedo explicarte…»."""
        if not state.offered:
            return None
        if DECLINE.match(s.folded):
            return replace(self._build(s.message, TurnMode.NEW, "", state, "rechaza lo ofrecido"), needs_clarification=True)
        ordinal = ORDINAL.search(s.folded)
        chosen: str | None = None
        if AFFIRM.match(s.folded):
            if len(state.offered) > 1:
                phrases = "|".join(phrase for _, phrase in state.offered)
                turn = self._build(s.message, TurnMode.NEW, "", state, f"elige entre lo ofrecido: {phrases}")
                return replace(turn, needs_clarification=True)
            chosen = state.offered[0][0]
        elif ordinal and ordinal.group("ordinal") and len(state.options) < 2 and not s.bare and not s.topics and not s.mentioned:
            index = ORDINAL_INDEX.get(ordinal.group("ordinal"))
            chosen = state.offered[index][0] if index is not None and index < len(state.offered) else None
        aspect = aspect_by_key(chosen)
        if aspect is None:
            return None
        # Lo ofrecido, sobre el foco en curso: la búsqueda es la de un seguimiento con ese aspecto.
        self._title_words = aspect.title_words
        turn = self._follow_up(s.message, state, aspect, [], s.campus, anaphoric=False, carry=False)
        return replace(turn, accepts_offer=True, resolution=f"acepta lo ofrecido: {aspect.phrase}")

    def _summary(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not SUMMARIZE.match(s.folded):
            return None
        # Con un tema en curso se resume ese tema, aunque la última respuesta fuera una abstención.
        if state.last_query and (state.last_grounded or state.has_focus):
            topic = topic_by_key(state.topic)
            # Tras una abstención no hay explicación que resumir: se resume el tema.
            query = state.last_query if state.last_grounded or topic is None else topic.retrieval_terms
            if not state.last_grounded:
                state = replace(state, aspect=None)
            turn = self._build(
                s.message, TurnMode.DEEPEN, query, state, "pide resumir lo anterior",
                reading=f"Pide un resumen breve de lo que le explicaste sobre {self._focus_label(state.entity, state.topic)}.",
                article_numbers=(state.article,) if state.article else (),
            )
            return replace(turn, wants_summary=True)
        return replace(self._build(s.message, TurnMode.NEW, "", state, "resumir sin nada previo"), needs_clarification=True)

    def _continuation(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if MORE_TO_KNOW.match(s.folded) and state.has_focus:
            # «¿Qué más debo saber?»: lo que falte del tema en foco, sin repetir lo explicado.
            topic = topic_by_key(state.topic)
            focus = state.entity.name if state.entity else (topic.retrieval_terms if topic else state.last_query or "")
            seen = [p for p in (aspect_by_key(k) for k in state.covered_aspects) if p is not None]
            reading = f"Pregunta qué más debe saber sobre {self._focus_label(state.entity, state.topic)}"
            reading += f"; ya se le explicó {_join_names([a.phrase for a in seen])}: no lo repitas." if seen else "."
            turn = self._build(s.message, TurnMode.FOLLOW_UP, focus, state, "pide lo que falta del tema", reading=reading)
            return replace(turn, entity=state.entity)
        if not (CONTINUE.match(s.folded) and not state.paused and state.last_grounded and state.last_query):
            return None
        # Justo después de una respuesta, «continúa» pide seguir, no retomar un tema.
        turn = self._build(
            s.message, TurnMode.DEEPEN, state.last_query, state, "pide seguir con la explicación",
            reading=(
                f"Pide que sigas con la explicación sobre {self._focus_label(state.entity, state.topic)}: "
                "añade lo que faltó, sin repetir lo que ya dijiste."
            ),
            article_numbers=(state.article,) if state.article else (),
        )
        return replace(turn, continues=True)

    def _lost(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not (LOST.search(s.folded) or HELP_REQUEST.match(s.folded)):
            return None
        if s.topics or s.mentioned or (s.aspect and state.has_focus):
            # «Me van a quitar la beca, no sé qué hacer»: dijo qué le preocupa; se responde eso.
            return None
        # «Estoy perdido»: buscar esas palabras no ayuda; orientar, sí.
        who = "estudiante nuevo desorientado" if NEWCOMER.search(s.folded) else "estudiante desorientado"
        return replace(self._build(s.message, TurnMode.NEW, "", state, who), needs_orientation=True)

    def _confusion(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not CONFUSED.match(s.folded):
            return None
        if state.last_query and state.last_grounded:
            # «No entiendo»: se vuelve a explicar lo mismo, más sencillo.
            focus = self._focus_label(state.entity, state.topic)
            turn = self._build(
                s.message, TurnMode.DEEPEN, state.last_query, state, "no entendió la explicación anterior",
                reading=(
                    f"El estudiante no entendió tu explicación anterior sobre {focus}: explícalo de nuevo, "
                    "más breve y con palabras sencillas, como se lo explicarías a alguien que llega nuevo."
                ),
                article_numbers=(state.article,) if state.article else (),
            )
            return replace(turn, simpler=True)
        return replace(self._build(s.message, TurnMode.NEW, "", state, "no entiende y no hay tema"), needs_orientation=True)

    def _return(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        back = RETURN_TO.match(s.folded)
        return self._return_to(s.message, back.group("rest"), state) if back else None

    def _unanchored(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        """«¿Y eso?» o «requisitos» al empezar: no hay a qué referirse; un asesor pregunta."""
        if state.has_focus or s.topics or s.mentioned or s.bare:
            return None
        pointing = bool(ANAPHORA.search(s.folded) or ORDINAL.search(s.folded) or re.fullmatch(r"(?:y\s+)?cual(?:es)?", s.folded))
        if pointing:
            return replace(self._build(s.message, TurnMode.NEW, "", state, "referencia sin antecedente"), needs_clarification=True)
        if s.aspect is not None and len(s.content) <= 2:
            turn = self._build(s.message, TurnMode.NEW, "", state, f"aspecto sin tema: {s.aspect.key}")
            return replace(turn, needs_clarification=True)
        return None

    def _article_or_document(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if ARTICLE_REFERENCE.search(s.folded):
            if state.article:
                number = state.article
                return self._build(
                    s.message, TurnMode.ARTICLE_STEP, f"Artículo {number}", state, f"el artículo {number} en consulta",
                    article_numbers=(number,), reading=f"Se refiere al Artículo {number} que se estaba consultando.",
                )
            if state.documents:
                return replace(self._build(s.message, TurnMode.NEW, "", state, "artículo sin número"), needs_clarification=True)
        pointing = DOCUMENT_REFERENCE.search(s.folded) or _THERE.search(s.folded)
        if pointing and state.documents:
            words = [w for w in s.content if fold(w) not in _DOCUMENT_WORDS]
            if (s.aspect or words) and not _RECORD_QUESTION.search(s.folded):
                # «¿Y allí qué dice de los requisitos?»: el asunto, buscado dentro del documento en consulta.
                aspect = s.aspect
                turn = self._build(
                    s.message, TurnMode.FOLLOW_UP, " ".join(words), state, "pregunta dentro del documento en consulta",
                    aspect=aspect, expansions=(aspect.retrieval_terms,) if aspect else (),
                    reading="Pregunta por lo que dice el documento que se estaba consultando"
                    + (f" sobre {aspect.phrase}." if aspect else "."),
                )
                return replace(turn, entity=None, required_terms=(), within_document=True)
        if DOCUMENT_REFERENCE.search(s.folded) and state.documents:
            # «¿Ese reglamento quién lo aprobó?»: se pregunta por el documento en consulta.
            words = [w for w in s.content if fold(w) not in ("reglamento", "documento", "calendario", "folleto")]
            turn = self._build(
                s.message, TurnMode.FOLLOW_UP, " ".join(words) or s.message, state, "pregunta por el documento en consulta",
                reading="Pregunta por el documento que se estaba consultando (su ficha: quién lo elaboró, revisó o autorizó, versión, vigencia).",
            )
            return replace(turn, topic=None, entity=None, required_terms=(), topic_terms=(), document_reference=True)
        return None

    def _ordinal(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        ordinal = ORDINAL.search(s.folded)
        if not ordinal or len(state.options) < 2 or s.mentioned or s.topics or len(s.bare) > 2:
            return None
        chosen = self._ordinal_choice(ordinal.group("ordinal") or ordinal.group("other"), state)
        if chosen is None:
            return None
        shifted = replace(
            state, entity=chosen, candidates=(), compared=(), topic=self._topic_of(chosen) or state.topic, last_query=None
        )
        turn = self._follow_up(s.message, shifted, s.aspect, s.content, s.campus, anaphoric=True, carry=False)
        others = [o.spoken for o in state.options if o != chosen]
        reading = (
            f"Pregunta de seguimiento: se refiere a {chosen.spoken}, una de las opciones de la lista anterior. "
            f"Lo que comparte con {_join_names(others)} ya se explicó: destaca lo que la distingue y no lo repitas."
        )
        return replace(turn, reading=reading, resolution=f"«{s.message.strip()}» es {chosen.spoken}, de la lista anterior")

    def _dangling_choice(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        """«¿Y la otra?», «¿esa cuál era?» cuando no se dio ninguna lista: un asesor pregunta a cuál."""
        choosing = ORDINAL.search(s.folded) or _WHICH_WAS_IT.match(s.folded)
        if not choosing or state.entity is not None or len(state.options) >= 2 or state.candidates:
            return None
        if s.bare or s.topics or s.mentioned or s.aspect or not state.topic:
            return None
        turn = self._build(s.message, TurnMode.NEW, "", state, f"referencia sin opciones: {state.topic}")
        return replace(turn, needs_clarification=True)

    def _resume(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        # «Continuemos con la inscripción» trae tema propio: no es retomar el anterior;
        # «sigamos con las becas», cuando ya se hablaba de becas, sí lo es.
        same_topic = all(t.key == state.topic for t in s.topics)
        if RESUME.match(s.folded) and state.has_focus and same_topic and not s.mentioned:
            return self._build(s.message, TurnMode.RESUME, state.last_query or "", state, "retoma el tema activo")
        return None

    def _deepen(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not ((DEEPEN.match(s.folded) or WHY.match(s.folded) or EXAMPLE.match(s.folded)) and state.last_query):
            return None
        focus = self._focus_label(state.entity, state.topic)
        wants_example = bool(EXAMPLE.match(s.folded))
        reading = (
            f"El estudiante pide un ejemplo de cómo se aplica lo explicado sobre {focus}."
            if wants_example
            else f"El estudiante pide ampliar o justificar la explicación anterior sobre {focus}."
        )
        turn = self._build(
            s.message, TurnMode.DEEPEN, state.last_query, state, "pide ampliar la respuesta anterior",
            reading=reading, article_numbers=(state.article,) if state.article else (),
        )
        return replace(turn, wants_example=wants_example)

    def _article_navigation(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        step = ARTICLE_STEP.search(s.folded)
        if step and state.article and len(s.content) <= 3:
            number = state.article + (1 if step.group(1) in ("siguiente", "proximo") else -1)
            return self._build(
                s.message, TurnMode.ARTICLE_STEP, f"Artículo {number}", state, f"artículo {number} del documento activo",
                article_numbers=(number,), reading=f"Se refiere al Artículo {number} del mismo documento.",
            )
        # «Artículo 20» sin nombrar documento ni tema: navegar dentro del documento en consulta.
        references = article_references(s.folded)
        if references and not s.topics and not s.mentioned and state.documents:
            return self._build(
                s.message, TurnMode.ARTICLE_STEP, f"Artículo {references[0]}", state,
                f"artículo {references[0]} del documento en consulta", article_numbers=references,
                reading=f"Se refiere al Artículo {references[0]} del documento que se está consultando.",
            )
        return None

    def _career_reference(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if not (re.search(r"\b(?:esa|ese|esta|dicha|la\s+misma)\s+carrera\b", s.folded) and state.career and not s.mentioned):
            return None
        if s.topics and s.topics[0].key not in (state.topic, "carreras"):
            # «¿Hay becas para esa carrera?» hablando de Informática: becas, para esa carrera.
            topic = s.topics[0]
            turn = self._new_turn(s.message, s.folded, topic.key, None, s.aspect, s.campus, s.content)
            return replace(
                turn,
                mode=TurnMode.FOLLOW_UP,
                retrieval_query=f"{' '.join(s.content)} {topic.retrieval_terms} {state.career}".strip(),
                reading=f"Pregunta de seguimiento: «esa carrera» es {state.career}; pregunta por {topic.label} para esa carrera.",
                career=state.career,
                is_overview=False,
            )
        # «¿Cuánto cuesta esa carrera?»: la carrera de la que se hablaba.
        turn = self._follow_up(s.message, replace(state, entity=None), s.aspect, s.content, s.campus, anaphoric=True, carry=False)
        return replace(
            turn,
            retrieval_query=f"{turn.retrieval_query} {state.career}".strip(),
            reading=f"Pregunta de seguimiento: «esa carrera» es {state.career}." + (f" Pregunta por {s.aspect.phrase}." if s.aspect else ""),
            career=state.career,
        )

    def _category_entity(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        if s.mentioned:
            return None
        referred = self._category_reference(s.folded, state)
        if referred is None:
            return None
        # «Esa beca de antes», «esa oficina»: la entidad ya nombrada de esa clase,
        # aunque la conversación haya pasado por otro tema.
        shifted = replace(
            state, entity=referred, topic=self._topic_of(referred) or state.topic,
            candidates=(), compared=(), documents=referred.document_ids or state.documents,
        )
        # El pronombre del mismo mensaje («¿quién lo integra?») es esa entidad: no se arrastra nada más.
        turn = self._follow_up(s.message, shifted, s.aspect, s.content, s.campus, anaphoric=True, carry=False)
        return replace(turn, resolution=f"«{s.message.strip()}» se refiere a {referred.spoken}, nombrada antes")

    def _bare_reply(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        """«No», «xd», «👍»: no hay pregunta que seguir; lo atiende la política local."""
        if not BARE_REPLY.match(s.folded):
            return None
        if MOODS[1][1].search(s.folded):
            # «¡Qué emoción!»: se comparte la alegría, no se contesta «De acuerdo».
            return replace(self._build(s.message, TurnMode.NEW, "", state, "comparte una alegría"), needs_clarification=True)
        return self._build(s.message, TurnMode.NEW, "", state, "mensaje sin contenido")

    def _bare_amount(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        """«¿Y cuánto?»: en una beca o un crédito es cuánto cubre; en lo demás, cuánto cuesta."""
        if s.aspect is not None or not _BARE_AMOUNT.match(s.folded) or not state.has_focus:
            return None
        aspect = aspect_by_key("cobertura" if state.topic in _COVERAGE_TOPICS or state.entity else "costo")
        if aspect is None:
            return None
        self._title_words = aspect.title_words
        return self._follow_up(s.message, state, aspect, s.content, s.campus, anaphoric=False)

    def _enumerate(self, s: _Signals, state: ConversationState) -> TurnInterpretation | None:
        """«¿Cuáles existen?» tras abrir un tema: el panorama del tema (con los artículos que
        definen cada opción), no la consulta anterior repetida."""
        topic = topic_by_key(state.topic)
        if not _ENUMERATE.match(s.folded) or topic is None or state.entity is not None or s.topics or s.mentioned:
            return None
        turn = self._new_turn(s.message, fold(topic.retrieval_terms), topic.key, None, None, s.campus, [])
        return replace(turn, mode=TurnMode.FOLLOW_UP, resolution=f"enumera las opciones de {topic.label}",
                       reading=f"Pregunta de seguimiento: pide la lista de opciones de {topic.label}.")

    def _follow_up_or_new(self, s: _Signals, state: ConversationState) -> TurnInterpretation:
        """La decisión general: comparación, seguimiento del foco o pregunta nueva."""
        message, folded, topics, aspects, mentioned = s.message, s.folded, s.topics, s.aspects, s.mentioned
        content, campus, aspect = s.content, s.campus, s.aspect
        if len(mentioned) >= 2:
            return self._comparison(message, mentioned, aspect, campus, content, state)

        entity = mentioned[0] if mentioned else None
        own_topic = topics[0].key if topics else self._topic_of(entity)

        # «la beca» cuando ya se habla de una beca concreta: es la misma, no una nueva.
        binds_active_entity = bool(
            state.entity is not None
            and entity is None
            and topics
            and all(t.key == state.topic for t in topics)
            and self._definite_reference(folded, topics)
        )
        anaphoric = bool(ANAPHORA.search(folded) or ENCLITIC.search(folded) or PROCLITIC.search(folded))
        # «¿Cuál pide más requisitos?» sin nombrar opciones: elige entre las que están
        # en juego (la comparación o las nombradas en la respuesta anterior).
        # «¿Cuáles existen?» enumera; solo un «cuál es más/mejor/conviene» elige.
        selects = bool(RANKING_QUESTION.search(folded)) and not mentioned
        anaphoric = anaphoric or (
            selects and (len(state.compared) >= 2 or len(self._comparable(state)) >= 2 or len(state.options) >= 2)
        )
        elliptical = folded.startswith("y ") or len(content) <= _SHORT_MESSAGE_WORDS
        # Un pronombre que apunta atrás («¿en cuántas cuotas lo pago?») pesa más que
        # una palabra temática genérica («cuotas»); no más que una entidad nombrada.
        self_contained = bool(entity or (topics and not (anaphoric and state.topic))) and not binds_active_entity
        # «¿Qué pasa si no cumplo?»: «cumplo» expresa el aspecto preguntado, no un asunto nuevo.
        spans = [m.span() for a in aspects for m in a.trigger.finditer(folded)]
        subject_words = [w for w in content if not any(start <= folded.find(fold(w)) < end for start, end in spans)]
        new_subject = not anaphoric and not folded.startswith("y ") and self._introduces_new_subject(subject_words, state)

        options = state.compared if len(state.compared) >= 2 else (self._comparable(state) or state.options)
        if len(options) < 2:
            options = state.options
        if selects and len(options) >= 2 and not ANAPHORA.search(folded):
            # «¿Cuál recomendarías revisar primero?»: elegir entre las opciones en juego es
            # compararlas, no suponer que se habla de una sola.
            return self._comparison(message, list(options)[:4], aspect, campus, content, state, follow_up=True)
        if state.has_focus and not self_contained and not new_subject and (anaphoric or aspects or elliptical):
            return self._follow_up(message, state, aspect, content, campus, anaphoric)
        if binds_active_entity:
            return self._follow_up(message, state, aspect, content, campus, anaphoric=True)

        if aspect is None and folded.startswith("y ") and state.aspect and (topics or mentioned) and len(s.bare) <= 3:
            # «¿Y la graduación?» tras «¿cuándo inician las clases?»: la misma pregunta, otro asunto.
            inherited = aspect = aspect_by_key(state.aspect)
            if inherited is not None:
                self._title_words = inherited.title_words
            if inherited is not None and state.last_message:
                turn = self._new_turn(message, folded, own_topic, entity, inherited, campus, content)
                own = topic_by_key(own_topic)
                subject = entity.spoken if entity else (own.label if own else "eso")
                return replace(
                    turn,
                    mode=TurnMode.FOLLOW_UP,
                    expansions=(*turn.expansions, inherited.retrieval_terms),
                    reading=f"Pregunta lo mismo que antes («{state.last_message.strip()}»), ahora sobre {subject}.",
                    resolution=f"misma pregunta que la anterior, ahora sobre {subject}",
                )
        two_questions = message.count("?") >= 2 or bool(re.search(r"\by\s+(?:cuando|cuanto\w*|como|que|quien\w*|donde|cual\w*)\b", folded))
        return self._new_turn(message, folded, own_topic, entity, aspect, campus, content, multi_topic=len(topics) > 1 and two_questions)

    # --- Construcción de interpretaciones ---------------------------------------------

    def _follow_up(
        self,
        message: str,
        state: ConversationState,
        aspect: Aspect | None,
        content: list[str],
        campus: str | None,
        anaphoric: bool,
        carry: bool = True,
    ) -> TurnInterpretation:
        entity = state.entity
        resolution = "continúa el foco activo"
        # «¿Cuánto cubre esa?» tras una respuesta que nombró una sola beca: es esa.
        # Si nombró varias, se responde sobre todas en lugar de adivinar una.
        # Sin tema activo, cualquier entidad nombrada vale; con tema, solo las suyas
        # («¿quién lo decide?» no debe saltar a una oficina citada de paso).
        same_topic_candidates = [
            c for c in state.candidates if c in self._comparable(state) or (state.topic is None and c in state.candidates)
        ] or [c for c in state.candidates if state.topic is None or self._topic_of(c) == state.topic]
        # Solo un demostrativo («esa», «ese») señala una opción nombrada; un pronombre átono
        # («¿quién lo decide?») habla del asunto, no de la opción que se citó de paso.
        demonstrative = bool(ANAPHORA.search(fold(message)))
        if entity is None and anaphoric and demonstrative and len(same_topic_candidates) == 1:
            entity = same_topic_candidates[0]
            resolution = f"«{message.strip()}» se refiere a {entity.name}, nombrada en la respuesta anterior"
        elif entity is None and state.ranked and same_topic_candidates and (demonstrative or not _PLURAL.search(fold(message))):
            # «¿Y esa tiene requisitos?» tras «¿cuál cubre más?»: la señalada como respuesta.
            entity = same_topic_candidates[0]
            resolution = f"«{message.strip()}» se refiere a {entity.name}, la señalada en la comparación anterior"
        if entity is None and state.compared and not self._points_to_one(message):
            # «¿Y cuál me conviene?» tras comparar dos becas: siguen siendo las dos.
            return self._comparison(message, list(state.compared), aspect, campus, content, state, follow_up=True)
        topic = topic_by_key(state.topic)
        focus = entity.name if entity else (topic.retrieval_terms if topic else (state.last_query or ""))
        if entity is not None and topic is not None and not set(anchor_terms(topic)) & set(analyze(entity.name)):
            # «Programa Regular» no dice que es una beca: el tema acompaña a la entidad.
            focus = f"{entity.name} {topic.category_words[0] if topic.category_words else topic.retrieval_terms}"
        career = self._career(message)
        if career and state.last_query and all(CAREER_WORDS.search(fold(w)) or len(w) <= 4 for w in content):
            # «¿Y para Tecnología?»: la pregunta anterior, con la carrera sustituida.
            previous = state.last_query
            if state.career:
                previous = re.sub(re.escape(state.career), "", previous, flags=re.IGNORECASE)
            return self._build(
                message, TurnMode.FOLLOW_UP, f"{previous} {career}".strip(), state,
                f"misma pregunta que la anterior, ahora para {career}",
                entity=entity, topic=state.topic, aspect=aspect, campus=campus or state.campus,
                reading=f"Pregunta de seguimiento: la misma consulta anterior, ahora para {career}.",
                career=career,
            )
        own_nouns = [w for w in content if len(w) >= 4 and not ASPECT_WORDS.search(fold(w)) and not CAREER_WORDS.search(fold(w))]
        if entity is None and topic is None and own_nouns:
            # Tema sin nombre reconocido y el mensaje trae sus propias palabras: se
            # busca con ellas, sin arrastrar la pregunta anterior completa.
            focus = ""
        # Si el pronombre ya se resolvió a una entidad nombrada, no se arrastra nada más.
        carried = self._carried_object(message, content, state) if carry and (entity is None or entity == state.entity) else []
        if state.topic == "carreras" and state.career and not career:
            # «¿Y cuánto cuesta?» hablando de Informática: la carrera es el sujeto implícito.
            carried = [*carried, state.career]
        parts = [" ".join(content), " ".join(carried), focus]
        if not content and not aspect and state.last_query:
            parts.append(state.last_query)
        query = join_query(parts)
        # Los términos del aspecto son sinónimos, no palabras del estudiante: van
        # como expansión (peso reducido, fuera del denominador de cobertura) para
        # no diluir la evidencia de lo que realmente se escribió.
        aspect_expansions = (aspect_terms(aspect, state.topic),) if aspect else ()
        reading = f"Pregunta de seguimiento: se refiere a {self._focus_label(entity, state.topic)}"
        if aspect:
            reading += f"; pregunta por {aspect.phrase}"
        if campus or state.campus:
            reading += f" (en {campus or state.campus})"
        if carried and state.last_message:
            reading += f"; el pronombre retoma lo que preguntó justo antes («{state.last_message.strip()}»)"
        return self._build(
            message,
            TurnMode.FOLLOW_UP,
            query,
            state,
            resolution,
            entity=entity,
            topic=state.topic,
            aspect=aspect,
            campus=campus or state.campus,
            reading=reading + ".",
            expansions=aspect_expansions,
            career=career or state.career,
        )

    def _new_turn(
        self,
        message: str,
        folded: str,
        topic_key: str | None,
        entity: CorpusEntity | None,
        aspect: Aspect | None,
        campus: str | None,
        content: list[str],
        multi_topic: bool = False,
    ) -> TurnInterpretation:
        topic = topic_by_key(topic_key)
        # «No me alcanza para pagar la carrera» también pide un panorama: qué opciones hay.
        # La necesidad dicha sin nombrar la ayuda («soy de bajos recursos») pide ver las opciones;
        # si ya la nombra («¿dan apoyo económico a…?») es una pregunta concreta.
        indirect_need = bool(FINANCIAL_NEED.search(folded)) and not _NAMES_AID.search(folded)
        is_overview = bool(topic) and entity is None and aspect is None and (
            bool(OVERVIEW_REQUEST.search(folded)) or len(content) <= 2 or indirect_need
        )
        # «Háblame de las becas AVE»: el panorama de esa familia de programas.
        entity_overview = entity is not None and aspect is None and bool(OVERVIEW_REQUEST.search(folded))
        # Sin sinónimos del aspecto en una pregunta autosuficiente: medido en el banco de
        # recuperación, desplazan la evidencia que las palabras del estudiante ya encuentran.
        expansions: tuple[str, ...] = ()
        defining: tuple[tuple[UUID, int], ...] = ()
        # Las muletillas («mire, fíjese que…», «xfa») no están en ningún reglamento: diluyen la búsqueda.
        query = without_fillers(message)
        if entity_overview and entity is not None:
            query = join_query([" ".join(content), entity.search_terms])
            defining = entity.defined_in
        if is_overview and topic is not None:
            # Expansión desde el corpus: «becas» → los programas que el corpus
            # realmente nombra (Programa Regular, Beca Despega, Becas CONADER…);
            # «carreras» → las carreras que nombran los folletos.
            kind = EntityKind.CAREER if topic.key == "carreras" else EntityKind.PROGRAM
            members = [
                e for e in (self._entities if kind is EntityKind.CAREER else self._focusable)
                if e.kind is kind and (kind is EntityKind.CAREER or self._topic_of(e) == topic.key)
            ]
            expansions = tuple(e.name for e in members)[:_MAX_OVERVIEW_EXPANSIONS]
            # Y los artículos que definen cada uno: la mejor entrada a un panorama.
            defining = tuple(pair for e in members for pair in e.defined_in)
            paraphrase = _paraphrase_words(folded, topic)
            own = [w for w in content if fold(w) not in paraphrase]
            query = join_query([" ".join(own), topic.retrieval_terms])
        # Sin entidades definidas (clubes), los títulos que nombran el tema
        # («Clasificación de los clubes») cumplen ese papel.
        overview_titles = topic.category_words if (is_overview and topic is not None and not defining) else ()
        return TurnInterpretation(
            message=message,
            mode=TurnMode.NEW,
            retrieval_query=query,
            topic=topic_key,
            entity=entity,
            aspect=aspect.key if aspect else None,
            campus=campus,
            career=self._career(message),
            # Nombrar un tema también ancla su evidencia: «seguro médico estudiantil»
            # no debe responderse con artículos de grupos estudiantiles.
            # Dos temas en un mensaje («el interés del crédito y la ceremonia de graduación»):
            # anclar al primero descartaría la evidencia del segundo.
            required_terms=() if multi_topic else self._required_terms(entity, topic_key),
            article_numbers=article_references(folded),
            expansions=expansions,
            focus_terms=tuple(entity.distinctive) if entity else (),
            aspect_title_words=self._title_words or overview_titles,
            defining_articles=defining,
            topic_terms=anchor_terms(topic) if topic else (),
            is_overview=is_overview or entity_overview,
            resolution="consulta autosuficiente" + (" de panorama" if is_overview or entity_overview else ""),
            sub_queries=self._story_queries(folded, topic, entity, content),
        )

    @staticmethod
    def _story_queries(
        folded: str, topic: Topic | None, entity: CorpusEntity | None, content: list[str]
    ) -> tuple[str, ...]:
        """Un relato largo trae varias preguntas sobre un tema: una búsqueda por cada una.

        «…no sabemos cómo funcionan las becas, si hay que pagar algo, cuándo se
        solicitan y qué papeles piden…» son cuatro preguntas; buscar el relato
        entero mezcla palabras que no están en ningún reglamento («municipio lejano»).
        """
        if len(content) <= _LONG_MESSAGE_WORDS // 2 or (topic is None and entity is None):
            return ()
        subject = entity.search_terms if entity else (topic.retrieval_terms if topic else "")
        aspects = detect_aspects(folded)[:_MAX_STORY_QUESTIONS]
        return tuple(f"{subject} {aspect.retrieval_terms}" for aspect in aspects) or (subject,)

    def _build(
        self,
        message: str,
        mode: TurnMode,
        query: str,
        state: ConversationState,
        resolution: str,
        *,
        entity: CorpusEntity | None = None,
        topic: str | None = None,
        aspect: Aspect | None = None,
        campus: str | None = None,
        article_numbers: tuple[int, ...] = (),
        reading: str | None = None,
        expansions: tuple[str, ...] = (),
        career: str | None = None,
    ) -> TurnInterpretation:
        entity = entity if entity is not None else (state.entity if mode is not TurnMode.NEW else None)
        topic_key = topic or state.topic
        return TurnInterpretation(
            message=message,
            mode=mode,
            retrieval_query=query,
            reading=re.sub(r"\b([Aa]) el\b", r"\1l", re.sub(r"\b([Dd])e el\b", r"\1el", reading)) if reading else reading,
            topic=topic_key,
            entity=entity,
            aspect=aspect.key if aspect else (state.aspect if mode is TurnMode.DEEPEN else None),
            campus=campus or state.campus,
            career=career or state.career,
            article_numbers=article_numbers,
            expansions=expansions,
            focus_terms=tuple(entity.distinctive) if entity else (),
            aspect_title_words=self._title_words or (aspect.title_words if aspect else ()),
            resolution=resolution,
            candidates=state.candidates,
            required_terms=self._required_terms(entity, topic_key) if mode in (TurnMode.FOLLOW_UP, TurnMode.DEEPEN) else (),
            topic_terms=self._required_terms(None, topic_key),
        )

    def _comparison(
        self,
        message: str,
        entities: Sequence[CorpusEntity],
        aspect: Aspect | None,
        campus: str | None,
        content: list[str],
        state: ConversationState,
        follow_up: bool = False,
    ) -> TurnInterpretation:
        """Dos o más entidades a la vez: cada una se busca por separado y se comparan.

        Buscar «diferencia entre la Beca Despega y la Beca Trasciende» de una sola
        vez trae la evidencia de la que más se parezca a la frase; la otra queda
        fuera y la comparación sale coja.
        """
        compared = tuple(dict.fromkeys(entities))
        own = [w for w in content if not any(set(analyze(w)) & set(e.distinctive) for e in compared)]
        own = [w for w in own if fold(w) not in ("beca", "becas", "programa", "programas")]
        words = " ".join(own)
        names = " y ".join(e.spoken for e in compared)
        reading = f"Compara {names}" + (f"; pregunta por {aspect.phrase}" if aspect else "")
        if follow_up:
            reading = f"Pregunta de seguimiento sobre la comparación anterior: {reading[0].lower()}{reading[1:]}"
        topic_key = self._topic_of(compared[0]) or state.topic
        required = tuple(dict.fromkeys(t for e in compared for t in e.distinctive))
        return TurnInterpretation(
            message=message,
            mode=TurnMode.FOLLOW_UP if follow_up else TurnMode.NEW,
            retrieval_query=f"{words} {' '.join(e.name for e in compared)}".strip(),
            reading=reading + ".",
            topic=topic_key,
            entity=None,
            aspect=aspect.key if aspect else None,
            campus=campus or state.campus,
            career=self._career(message) or state.career,
            expansions=(aspect.retrieval_terms,) if aspect else (),
            aspect_title_words=self._title_words or (aspect.title_words if aspect else ()),
            resolution=f"compara {names}",
            required_terms=required,
            topic_terms=self._required_terms(None, topic_key),
            defining_articles=tuple(pair for e in compared for pair in e.defined_in),
            compared=compared,
            sub_queries=tuple(f"{e.name} {words}".strip() for e in compared),
        )

    def _return_to(self, message: str, rest: str, state: ConversationState) -> TurnInterpretation | None:
        """«Volviendo a las elecciones, ¿y si hay empate?»: el resto se lee dentro de ese tema."""
        # «Volviendo al crédito»: basta con la palabra clave del tema.
        head = rest.split(",", 1)[0]
        topics = detect_topics(rest) or [t for t in TOPICS if re.search(rf"\b{t.key}\b", head)]
        if not topics or CATEGORY_REFERENCE.search(rest):
            return None  # «volviendo a esa beca de antes» señala una beca concreta, no el tema
        topic = topics[0]
        remainder = rest.split(",", 1)[1] if "," in rest else topic.trigger.sub(" ", rest, count=1)
        if not self._content_words(remainder) and not detect_aspects(remainder):
            return None  # «Volviendo a las becas» a secas: un panorama del tema, como pregunta nueva.
        # Se vuelve al tema que el estudiante nombra, no a una entidad citada de paso en él.
        returned = ConversationState(
            topic=topic.key, last_query=topic.retrieval_terms, last_grounded=True,
            recent_entities=state.recent_entities, campus=state.campus, career=state.career,
        )
        turn = self.interpret(remainder.strip(" ,"), returned)
        return replace(turn, message=message, resolution=f"regresa a {topic.label}: {turn.resolution}")

    def _category_reference(self, folded: str, state: ConversationState) -> CorpusEntity | None:
        match = CATEGORY_REFERENCE.search(folded)
        if match is None:
            return None
        noun = match.group("noun")
        kind = _CATEGORY_KIND.get(noun, EntityKind.OFFICE if noun not in ("campus",) else None)
        if kind is None:
            return None
        noun_stems = set(analyze(noun))
        earlier = "antes" in folded or "anterior" in folded
        pool = [e for e in state.candidates if e.kind is kind] if not earlier else []
        if len(pool) == 1 or (pool and state.ranked):
            return pool[0]
        # «Ese consejo»: si el sustantivo es parte del nombre, se prefiere la entidad que lo lleva.
        remembered = [e for e in state.recent_entities if e.kind is kind]
        named = [e for e in remembered if noun_stems & set(analyze(e.name))]
        choice = next(iter(named or remembered), None)
        if choice is None or (choice == state.entity and not earlier):
            return None  # ya es el foco: el seguimiento normal lo resuelve
        return choice

    @staticmethod
    def _ordinal_choice(ordinal: str, state: ConversationState) -> CorpusEntity | None:
        options = list(state.options)
        if ordinal in ("otro", "otra"):
            # «La otra»: con dos opciones, la que no está en foco; con más, la siguiente.
            if state.entity in options:
                return options[(options.index(state.entity) + 1) % len(options)]
            return options[1] if len(options) >= 2 else None
        index = ORDINAL_INDEX.get(ordinal)
        if index is None or index >= len(options):
            return None
        return options[index]

    @staticmethod
    def _comparable(state: ConversationState) -> tuple[CorpusEntity, ...]:
        """Opciones entre las que se puede elegir: de la misma clase y del tema en curso.

        Una respuesta sobre becas puede nombrar de paso una oficina («Registro
        Académico»); «¿cuál recomiendas?» no la incluye entre las opciones.
        """
        if not state.candidates:
            return ()
        kinds = [c.kind for c in state.candidates]
        kind = EntityKind.PROGRAM if EntityKind.PROGRAM in kinds else kinds[0]
        topic = topic_by_key(state.topic)
        umbrella = set(anchor_terms(topic)) if topic else set()
        return tuple(
            c for c in state.candidates
            if c.kind is kind and (state.topic is None or topic_of(c) in (state.topic, None))
            # «Programa de Ayudas Financieras» es el tema entero, no una de sus opciones.
            and not (umbrella and set(c.distinctive) <= umbrella)
        )

    @staticmethod
    def _points_to_one(message: str) -> bool:
        """«¿Y esa tiene penalizaciones?» elige una; «¿cuál me conviene?» sigue comparando."""
        folded = fold(message)
        return bool(re.search(r"\b(?:esa|ese|la\s+primera|la\s+segunda|la\s+otra|el\s+otro)\b", folded)) and not re.search(
            r"\b(?:ambas|ambos|las\s+dos|los\s+dos|cual)\b", folded
        )

    def _carried_object(self, message: str, content: list[str], state: ConversationState) -> list[str]:
        """«¿Quién la da?» tras «¿Necesito autorización?»: «la» es la autorización.

        Solo con un pronombre átono (no con «¿y los requisitos?», que trae su propio
        objeto) y solo las palabras que la pregunta anterior aportaba al tema.
        """
        folded = fold(message)
        if not state.last_message or not (PROCLITIC.search(folded) or ENCLITIC.search(folded)):
            return []
        topic = topic_by_key(state.topic)
        topic_stems = set(analyze(topic.retrieval_terms)) if topic else set()
        own = {fold(w) for w in content}
        return [
            word for word in self._content_words(state.last_message)
            if fold(word) not in own and len(word) >= 5 and not (set(analyze(word)) & topic_stems) and _looks_like_noun(word)
        ][:3]

    # --- Auxiliares --------------------------------------------------------------------

    @staticmethod
    def _content_words(message: str) -> list[str]:
        """Palabras del estudiante que aportan contenido (sin anáforas ni fórmulas de petición)."""
        kept: list[str] = []
        for word in _WORD.findall(message):
            folded = fold(word)
            if folded in STOPWORDS or folded in DISCOURSE_WORDS or ANAPHORA.fullmatch(folded) or _FILLER.fullmatch(folded):
                continue
            if len(folded) <= 2 and not folded.isdigit():
                continue
            # «solicitarla» busca como «solicitar»: el pronombre ya lo resuelve el foco.
            if ENCLITIC.fullmatch(folded):
                word = re.sub(r"(?:la|lo|las|los)$", "", word)
            kept.append(word)
        return kept

    def _introduces_new_subject(self, content: list[str], state: ConversationState) -> bool:
        """¿Trae el mensaje un sustantivo ajeno a lo que se está hablando?

        «¿Cuántas personas debe tener la directiva?» tras hablar de clubes sigue
        el tema: «directiva» aparece en el reglamento que se está consultando.
        «¿Cuánto cuesta el parqueo?» tras hablar de elecciones no: «parqueo» no
        aparece en ese reglamento. Sin documentos en juego, cualquier sustantivo
        nuevo sin tema reconocido se toma como pregunta nueva.
        """
        nouns = [
            word for word in content
            if len(word) >= 4 and not ASPECT_WORDS.search(fold(word)) and not CAREER_WORDS.search(fold(word))
        ]
        if not nouns:
            return False
        if state.last_grounded is False:
            # Un tema sin respaldo documental no tiene coocurrencias con qué comparar:
            # sus seguimientos siguen siendo de él («¿qué exclusiones tiene?»).
            return False
        focus_terms = self._required_terms(state.entity, state.topic)
        if self._co_occur is not None and focus_terms:
            # Prueba fina: ¿alguna de sus palabras comparte fragmento con el foco?
            return all(not self._co_occur(analyze(word), focus_terms) for word in nouns)
        if self._vocabulary is not None and state.documents:
            known = self._vocabulary(state.documents)
            # Todas ajenas: sin etiquetador gramatical, un verbo nuevo («necesita»)
            # no debe bastar para declarar un cambio de tema.
            return all(not (set(analyze(word)) & known) for word in nouns)
        return state.topic is None and state.entity is None

    @staticmethod
    def _definite_reference(folded: str, topics: Sequence[Topic]) -> bool:
        words = "|".join(re.escape(w) for t in topics for w in t.category_words) or "beca"
        return bool(re.search(rf"\b(?:la|el|mi|esa|ese|dicha|dicho|esta|este)\s+(?:{words})\b", folded))

    @staticmethod
    def _career(message: str) -> str | None:
        match = CAREER_WORDS.search(fold(message))
        if match is None:
            return None
        # Se conserva la forma escrita por el estudiante («Tecnología»), con tildes.
        for word in _WORD.findall(message):
            if fold(word) == match.group(1).split()[0]:
                return word
        return match.group(1)

    @staticmethod
    def _required_terms(entity: CorpusEntity | None, topic_key: str | None) -> tuple[str, ...]:
        """Lo que la evidencia de un seguimiento debe mencionar para seguir en el tema.

        Sin esto, «¿y cuánto cubre?» tras preguntar por el seguro estudiantil
        encontraría los artículos de cobertura de las becas —comparten «cobertura»—
        y la conversación saltaría de tema en silencio.
        """
        if entity is not None:
            return entity.distinctive
        topic = topic_by_key(topic_key)
        return anchor_terms(topic) if topic else ()

    @staticmethod
    def _topic_of(entity: CorpusEntity | None) -> str | None:
        return topic_of(entity)

    @staticmethod
    def _focus_label(entity: CorpusEntity | None, topic_key: str | None) -> str:
        if entity is not None:
            return entity.spoken
        topic = topic_by_key(topic_key)
        return topic.label if topic else "el tema anterior"


RANKING_QUESTION = re.compile(
    r"\bcual(?:es)?\s+(?:\w+\s+){0,3}(?:mas|mejor(?:es)?|mayor(?:es)?|menos|menor(?:es)?)\b"
    r"|\bcual\s+(?:me\s+)?(?:recomiendas|recomendarias|conviene)\b"
)


def _first_position(folded_text: str, entity: CorpusEntity) -> int:
    positions = [folded_text.find(fold(word)) for word in entity.distinctive]
    found = [p for p in positions if p >= 0]
    return min(found) if found else len(folded_text)


# «¿Qué requisitos tienen?» pregunta por todas; «¿qué requisitos tiene?», por la señalada.
_PLURAL = re.compile(r"\b(?:tienen|piden|cubren|duran|cuestan|exigen|ambas|ambos|todas|todos|cada\s+una|esas|esos|estas|estos)\b")


def _join_names(names: Sequence[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " y " + names[-1] if names else "las demás"


def _distinct_mentions(mentioned: Sequence[CorpusEntity], folded_text: str) -> list[CorpusEntity]:
    """«Comité de Ayudas Financieras» no menciona también a la Dirección ni a la Unidad.

    Varias entidades comparten palabras distintivas («ayudas financieras»); si el
    mensaje nombra una completa, solo esa cuenta. Si no nombra ninguna completa,
    las que comparten las mismas palabras cuentan como una sola.
    """
    named = [e for e in mentioned if _named_in(e, folded_text)]
    if named:
        return named
    unique: dict[tuple[str, ...], CorpusEntity] = {}
    for entity in mentioned:
        unique.setdefault(tuple(sorted(entity.distinctive)), entity)
    return list(unique.values())


def _named_in(entity: CorpusEntity, folded_text: str) -> bool:
    """¿El texto nombra la entidad completa? («Beca Trasciende» vale por «Becas Trasciende»)."""
    name = fold(entity.name)
    return name in folded_text or re.sub(r"^becas\b", "beca", name) in folded_text


def _looks_like_noun(word: str) -> bool:
    """Sustantivo probable, sin etiquetador: «autorización», «requisitos»; no «decide», «solicito»."""
    folded = fold(word)
    if re.search(r"(?:cion|sion|dad|miento|ncia|aje|ura|tud)e?s?$", folded):
        return True
    return not ASPECT_WORDS.search(folded) and not re.search(r"(?:ar|er|ir|an|en|a|e|o)$", folded)


def topic_of(entity: CorpusEntity | None) -> str | None:
    """Tema al que pertenece una entidad del corpus («Beca Despega» → becas)."""
    if entity is None:
        return None
    topics = detect_topics(fold(entity.name))
    if topics:
        return topics[0].key
    # Los programas que extrae el corpus son de ayuda financiera salvo que su
    # nombre diga otra cosa («Programa Regular», «Programa de Talento»).
    return "becas" if entity.kind is EntityKind.PROGRAM else None


def focus_label(state: ConversationState) -> str | None:
    """Etiqueta legible del foco activo, para saludos y recapitulaciones.

    Se nombra lo que le importa al estudiante: la beca concreta si hay una en
    foco; si no, el tema («las elecciones estudiantiles»), no una instancia que
    solo se mencionó de paso («Consejo Electoral»).
    """
    topic = topic_by_key(state.topic)
    if state.entity is not None and (state.entity.kind in (EntityKind.PROGRAM, EntityKind.CAREER) or topic is None):
        if topic is not None and fold(state.entity.name) in fold(topic.label):
            # «Crédito Educativo» es el tema mismo: se nombra como tema, «el crédito educativo».
            return topic.label
        if (
            state.entity.kind is EntityKind.PROGRAM and topic is not None
            and not set(anchor_terms(topic)) & set(analyze(state.entity.name))
        ):
            # «el Programa Regular de becas y ayudas financieras»: el nombre solo no dice de qué se hablaba.
            return f"{state.entity.spoken} de {re.sub(r'^(?:las|los|el|la) ', '', topic.label)}"
        return state.entity.spoken
    return topic.label if topic else None


def join_query(parts: Sequence[str]) -> str:
    """Une las partes de una consulta sin repetir lo que ya está.

    Una parte posterior (foco, consulta anterior) que ya está contenida entera no
    se añade: así una cadena de elipsis («¿y cuánto?», «¿y cuándo?») no hace
    crecer la consulta turno a turno. Las que aportan algo entran completas,
    para no partir nombres («Beca Despega»).
    """
    seen: set[str] = set()
    kept: list[str] = []
    for part in parts:
        words = part.split()
        folded = {fold(w).strip("¿?¡!.,;:") for w in words} - {""}
        if not words or (kept and folded <= seen):
            continue
        seen |= folded
        kept.extend(words)
    return " ".join(kept).strip()


def without_fillers(message: str) -> str:
    """«mire fíjese que quiero una beca xfa» → «que quiero una beca»; nunca deja la consulta vacía."""
    message = _SYMBOLS.sub(" ", message)  # «¡¡Me dieron la beca!! 🎉🎉»: los emojis no se buscan
    folded = fold(message)
    if not _FILLER_WORDS.search(folded):
        return " ".join(message.split())
    # Se recorre el texto plegado (misma longitud que el original) para conservar tildes y mayúsculas.
    pieces, last = [], 0
    for match in _FILLER_WORDS.finditer(folded):
        pieces.append(message[last : match.start()])
        last = match.end()
    pieces.append(message[last:])
    cleaned = " ".join("".join(pieces).split()).strip(" ,")
    return cleaned or message.strip()


def _paraphrase_words(folded: str, topic: Topic) -> set[str]:
    """Palabras con que el estudiante nombró el tema sin usar su vocabulario.

    «Me quiero salir de un curso» es el retiro de cursos; «salir» no aparece en
    ningún reglamento y solo restaría cobertura léxica. Si la mención ya usa las
    palabras del tema («retirar un curso», «becas»), no es paráfrasis y se conserva.
    """
    mention = topic.trigger.search(folded)
    if mention is None or set(analyze(mention.group(0))) & set(anchor_terms(topic)):
        return set()
    return set(re.findall(r"[a-z0-9]+", mention.group(0)))
