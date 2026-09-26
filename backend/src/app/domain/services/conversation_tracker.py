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
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from app.domain.entities.message import Message, MessageRole
from app.domain.services.conversation_lexicon import (
    ANAPHORA,
    ARTICLE_STEP,
    CAREER_WORDS,
    CATEGORY_REFERENCE,
    CONFUSED,
    DEEPEN,
    DISCOURSE_WORDS,
    ENCLITIC,
    EXAMPLE,
    FINANCIAL_NEED,
    HELP_REQUEST,
    LATER,
    LOST,
    OVERVIEW_REQUEST,
    PROCLITIC,
    RESUME,
    RETURN_TO,
    WHY,
    Aspect,
    Topic,
    anchor_terms,
    aspect_by_key,
    detect_aspects,
    detect_topics,
    topic_by_key,
)
from app.domain.services.entity_extractor import find_entities
from app.domain.services.institutional_lexicon import normalize_chat_speak
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
_WORD = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+")
# Palabras que solo expresan el aspecto preguntado, no un tema nuevo.
ASPECT_WORDS = re.compile(
    r"^(?:cubre\w*|cobertura|porcentaje|monto|requisitos?|plazos?|fechas?|hora|horario|cuesta|costo|precio|dura\w*"
    r"|duracion|pasos?|proceso|solicit\w+|aplic\w+|tramit\w+|condiciones?|mantener|decide\w*|aprueba\w*"
    r"|asigna\w*|personas|miembros?|integrantes?|significa|consiste|pierdo|perder|pasa|dan|da|otorga\w*"
    # Palabras «meta»: cómo seguir la conversación, no de qué hablar.
    r"|detalles?|ejemplos?|excepcion\w*|informacion|dudas?|opciones?|casos?|tipos?|diferencias?|ventajas?"
    r"|beneficios?|despues|primero|mejor(?:es)?|recomend\w*|conviene\w*|existen?|cual(?:es)?|revisar|algo"
    r"|todo|tiene|necesit\w*|puedo|aplicar\w*|autorizacion|tarda\w*|renueva\w*|gana)$"
)


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
        state = ConversationState()
        window = list(history)[-_REPLAY_WINDOW:]
        previous_time = None
        for index, message in enumerate(window):
            # Tras una semana sin conversar, el foco anterior ya no se ofrece como
            # continuación: el estudiante vuelve con otra necesidad.
            if previous_time is not None and message.created_at - previous_time > MEMORY_TTL:
                state = ConversationState()
            previous_time = message.created_at
            if message.role is not MessageRole.STUDENT:
                continue
            reply = next((m for m in window[index + 1 :] if m.role is MessageRole.ASSISTANT), None)
            if reply is None or (reply.is_grounded is None and not reply.sources):
                continue
            state = self.advance(state, self.interpret(message.content, state), reply)
        return state

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
        if len(candidates) == 1:
            remembered.append(candidates[0])
        recent = tuple(dict.fromkeys((*remembered, *state.recent_entities)))[:_RECENT_ENTITIES]
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
        )

    # --- Interpretación del turno actual ---------------------------------------------

    def interpret(self, message: str, state: ConversationState) -> TurnInterpretation:
        folded = normalize_chat_speak(fold(message)).strip(" ¿?¡!.")
        topics = detect_topics(folded)
        aspects = detect_aspects(folded)
        mentioned = find_entities(message, self._focusable)
        campus = next((e.name for e in find_entities(message, self._entities, [EntityKind.CAMPUS])), None)
        content = self._content_words(message)
        aspect = aspects[0] if aspects else None
        # Todos los aspectos detectados orientan el reordenamiento: «¿pierdo la beca si
        # bajo mi promedio?» es a la vez consecuencias y condiciones (promedio mínimo).
        self._title_words = tuple(dict.fromkeys(w for a in aspects for w in a.title_words))

        if LATER.search(folded):
            # Despedida con intención de volver: la atiende el catálogo local.
            return self._build(message, TurnMode.NEW, "", state, "despedida con continuidad")

        if LOST.search(folded) or HELP_REQUEST.match(folded):
            # «Estoy perdido»: buscar esas palabras no ayuda; orientar, sí.
            return replace(self._build(message, TurnMode.NEW, "", state, "estudiante desorientado"), needs_orientation=True)

        if CONFUSED.match(folded):
            if state.last_query and state.last_grounded:
                # «No entiendo»: se vuelve a explicar lo mismo, más sencillo.
                focus = self._focus_label(state.entity, state.topic)
                turn = self._build(
                    message, TurnMode.DEEPEN, state.last_query, state, "no entendió la explicación anterior",
                    reading=(
                        f"El estudiante no entendió tu explicación anterior sobre {focus}: explícalo de nuevo, "
                        "más breve y con palabras sencillas, como se lo explicarías a alguien que llega nuevo."
                    ),
                    article_numbers=(state.article,) if state.article else (),
                )
                return replace(turn, simpler=True)
            return replace(self._build(message, TurnMode.NEW, "", state, "no entiende y no hay tema"), needs_orientation=True)

        back = RETURN_TO.match(folded)
        if back:
            returned = self._return_to(message, back.group("rest"), state)
            if returned is not None:
                return returned

        # «Continuemos con la inscripción» trae tema propio: no es retomar el anterior;
        # «sigamos con las becas», cuando ya se hablaba de becas, sí lo es.
        same_topic = all(t.key == state.topic for t in topics)
        if RESUME.match(folded) and state.has_focus and same_topic and not mentioned:
            return self._build(message, TurnMode.RESUME, state.last_query or "", state, "retoma el tema activo")

        if (DEEPEN.match(folded) or WHY.match(folded) or EXAMPLE.match(folded)) and state.last_query:
            focus = self._focus_label(state.entity, state.topic)
            wants_example = bool(EXAMPLE.match(folded))
            reading = (
                f"El estudiante pide un ejemplo de cómo se aplica lo explicado sobre {focus}."
                if wants_example
                else f"El estudiante pide ampliar o justificar la explicación anterior sobre {focus}."
            )
            turn = self._build(
                message, TurnMode.DEEPEN, state.last_query, state, "pide ampliar la respuesta anterior",
                reading=reading, article_numbers=(state.article,) if state.article else (),
            )
            return replace(turn, wants_example=wants_example)

        step = ARTICLE_STEP.search(folded)
        if step and state.article and len(content) <= 3:
            number = state.article + (1 if step.group(1) in ("siguiente", "proximo") else -1)
            return self._build(
                message, TurnMode.ARTICLE_STEP, f"Artículo {number}", state, f"artículo {number} del documento activo",
                article_numbers=(number,), reading=f"Se refiere al Artículo {number} del mismo documento.",
            )

        # «Artículo 20» sin nombrar documento ni tema: navegar dentro del documento en consulta.
        references = article_references(folded)
        if references and not topics and not mentioned and state.documents:
            return self._build(
                message, TurnMode.ARTICLE_STEP, f"Artículo {references[0]}", state,
                f"artículo {references[0]} del documento en consulta", article_numbers=references,
                reading=f"Se refiere al Artículo {references[0]} del documento que se está consultando.",
            )

        if not mentioned:
            referred = self._category_reference(folded, state)
            if referred is not None:
                # «Esa beca de antes», «esa oficina»: la entidad ya nombrada de esa clase,
                # aunque la conversación haya pasado por otro tema.
                shifted = replace(
                    state, entity=referred, topic=self._topic_of(referred) or state.topic,
                    candidates=(), compared=(), documents=referred.document_ids or state.documents,
                )
                # El pronombre del mismo mensaje («¿quién lo integra?») es esa entidad: no se arrastra nada más.
                turn = self._follow_up(message, shifted, aspect, content, campus, anaphoric=True, carry=False)
                return replace(turn, resolution=f"«{message.strip()}» se refiere a {referred.spoken}, nombrada antes")

        if len(mentioned) >= 2:
            return self._comparison(message, mentioned, aspect, campus, content, state)

        entity = mentioned[0] if mentioned else None
        own_topic = topics[0].key if topics else self._topic_of(entity)

        # «la beca» cuando ya se habla de una beca concreta: es la misma, no una nueva.
        binds_active_entity = (
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
        anaphoric = anaphoric or (selects and (len(state.compared) >= 2 or len(self._comparable(state)) >= 2))
        elliptical = folded.startswith("y ") or len(content) <= _SHORT_MESSAGE_WORDS
        # Un pronombre que apunta atrás («¿en cuántas cuotas lo pago?») pesa más que
        # una palabra temática genérica («cuotas»); no más que una entidad nombrada.
        self_contained = bool(entity or (topics and not (anaphoric and state.topic))) and not binds_active_entity
        new_subject = not anaphoric and not folded.startswith("y ") and self._introduces_new_subject(content, state)

        options = state.compared if len(state.compared) >= 2 else self._comparable(state)
        if selects and len(options) >= 2 and not ANAPHORA.search(folded):
            # «¿Cuál recomendarías revisar primero?»: elegir entre las opciones en juego es
            # compararlas, no suponer que se habla de una sola.
            return self._comparison(message, list(options)[:4], aspect, campus, content, state, follow_up=True)
        if state.has_focus and not self_contained and not new_subject and (anaphoric or aspects or elliptical):
            return self._follow_up(message, state, aspect, content, campus, anaphoric)
        if binds_active_entity:
            return self._follow_up(message, state, aspect, content, campus, anaphoric=True)

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
        same_topic_candidates = [c for c in state.candidates if state.topic is None or self._topic_of(c) == state.topic]
        # Solo un demostrativo («esa», «ese») señala una opción nombrada; un pronombre átono
        # («¿quién lo decide?») habla del asunto, no de la opción que se citó de paso.
        demonstrative = bool(ANAPHORA.search(fold(message)))
        if entity is None and anaphoric and demonstrative and len(same_topic_candidates) == 1:
            entity = same_topic_candidates[0]
            resolution = f"«{message.strip()}» se refiere a {entity.name}, nombrada en la respuesta anterior"
        elif entity is None and anaphoric and demonstrative and state.ranked and same_topic_candidates:
            # «¿Y esa tiene requisitos?» tras «¿cuál cubre más?»: la señalada como respuesta.
            entity = same_topic_candidates[0]
            resolution = f"«{message.strip()}» se refiere a {entity.name}, la señalada en la comparación anterior"
        if entity is None and state.compared and not self._points_to_one(message):
            # «¿Y cuál me conviene?» tras comparar dos becas: siguen siendo las dos.
            return self._comparison(message, list(state.compared), aspect, campus, content, state, follow_up=True)
        topic = topic_by_key(state.topic)
        focus = entity.name if entity else (topic.retrieval_terms if topic else (state.last_query or ""))
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
        parts = [" ".join(content), " ".join(carried), focus]
        if not content and not aspect and state.last_query:
            parts.append(state.last_query)
        query = " ".join(part for part in parts if part).strip()
        # Los términos del aspecto son sinónimos, no palabras del estudiante: van
        # como expansión (peso reducido, fuera del denominador de cobertura) para
        # no diluir la evidencia de lo que realmente se escribió.
        aspect_expansions = (aspect.retrieval_terms,) if aspect else ()
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
        is_overview = bool(topic) and entity is None and aspect is None and (
            bool(OVERVIEW_REQUEST.search(folded)) or len(content) <= 2 or bool(FINANCIAL_NEED.search(folded))
        )
        # Sin sinónimos del aspecto en una pregunta autosuficiente: medido en el banco de
        # recuperación, desplazan la evidencia que las palabras del estudiante ya encuentran.
        expansions: tuple[str, ...] = ()
        defining: tuple[tuple[UUID, int], ...] = ()
        query = message.strip()
        if is_overview and topic is not None:
            # Expansión desde el corpus: «becas» → los programas que el corpus
            # realmente nombra (Programa Regular, Beca Despega, Becas CONADER…).
            members = [e for e in self._focusable if e.kind is EntityKind.PROGRAM and self._topic_of(e) == topic.key]
            expansions = tuple(e.name for e in members)[:_MAX_OVERVIEW_EXPANSIONS]
            # Y los artículos que definen cada uno: la mejor entrada a un panorama.
            defining = tuple(pair for e in members for pair in e.defined_in)
            query = f"{' '.join(content)} {topic.retrieval_terms}".strip()
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
            is_overview=is_overview,
            resolution="consulta autosuficiente" + (" de panorama" if is_overview else ""),
        )

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
            reading=reading,
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
        topics = detect_topics(rest)
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
        pool = [e for e in state.candidates if e.kind is kind] if "antes" not in folded else []
        if len(pool) == 1 or (pool and state.ranked):
            return pool[0]
        # «Ese consejo»: si el sustantivo es parte del nombre, se prefiere la entidad que lo lleva.
        remembered = [e for e in state.recent_entities if e.kind is kind]
        named = [e for e in remembered if noun_stems & set(analyze(e.name))]
        choice = next(iter(named or remembered), None)
        if choice is None or (choice == state.entity and "antes" not in folded):
            return None  # ya es el foco: el seguimiento normal lo resuelve
        return choice

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
        return tuple(
            c for c in state.candidates
            if c.kind is kind and (state.topic is None or topic_of(c) in (state.topic, None))
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
            if folded in STOPWORDS or folded in DISCOURSE_WORDS or ANAPHORA.fullmatch(folded):
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
        return state.entity.spoken
    return topic.label if topic else None


def pending_aspects(state: ConversationState) -> list[str]:
    """Aspectos habituales del tema activo que aún no se han tratado."""
    usual = ("requisitos", "cobertura", "condiciones", "consecuencias", "procedimiento", "plazo")
    return [aspect.phrase for key in usual if key not in state.covered_aspects and (aspect := aspect_by_key(key))]

