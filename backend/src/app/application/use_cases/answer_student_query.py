from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from uuid import UUID

from loguru import logger

from app.application.dto.chat_dto import AnswerQueryRequest, AnswerQueryResponse
from app.application.services.context_assembler import AssemblySettings, ContextAssembler
from app.application.services.knowledge_retriever import KnowledgeRetriever, RetrievalSettings
from app.domain.entities.chunk import RetrievedChunk
from app.domain.entities.message import Message, MessageRole
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.ports.corpus_catalog_port import CorpusCatalogPort
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.intent_classifier_port import IntentClassifierPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.domain.services import answer_planner, conversation_guide, response_policy
from app.domain.services.conversation_lexicon import anchor_terms, detect_topics, topic_by_key
from app.domain.services.conversation_tracker import (
    ConversationTracker,
    focus_label,
    topic_of,
)
from app.domain.services.document_navigator import DocumentNavigator, NavigationAnswer
from app.domain.services.entity_extractor import find_entities
from app.domain.services.local_skill_catalog import LocalSkillCatalog
from app.domain.services.message_sanitizer import MessageSanitizer, SanitizedMessage
from app.domain.services.query_analyzer import QueryAnalysis, QueryAnalyzer
from app.domain.services.spanish_text import fold
from app.domain.services.voice_guard import enforce_institutional_voice, lead_with_what_applies
from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent, IntentClassification
from app.domain.value_objects.conversation_state import (
    ConversationState,
    TurnInterpretation,
    TurnMode,
)
from app.domain.value_objects.corpus_entity import EntityKind
from app.domain.value_objects.document_facts import DocumentKind
from app.domain.value_objects.document_outline import DocumentOutline
from app.domain.value_objects.response_plan import ResponsePlan, ResponseStyle, SkillName
from app.domain.value_objects.similarity_score import SimilarityScore
from app.domain.value_objects.source_reference import SourceReference
from app.domain.value_objects.verified_answer import (
    AnswerCoverage,
    VerificationConfidence,
    VerifiedAnswer,
)
from app.shared.exceptions.domain_errors import LLMGenerationError, VerificationFailedError
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

# Las dos abstenciones son situaciones distintas y la acción útil del estudiante
# también: ante la primera conviene reformular; ante la segunda, el dato
# probablemente no está en el corpus. Antes ambas compartían un único texto.
NO_RETRIEVAL_MESSAGE = (
    "No encontré normativa oficial que hable de eso.\n\n"
    "Puede que el tema no esté cubierto por los reglamentos que manejo, o que con otras "
    "palabras sí lo encuentre. Intenta ser más específico: por ejemplo, en lugar de "
    "«becas», «requisitos de la Beca Despega»."
)

NOT_GROUNDED_MESSAGE = (
    "Hay normativa relacionada con tu consulta, pero no dice lo suficiente como para que "
    "te lo confirme.\n\n"
    "Prefiero no darte un dato que pueda estar equivocado. Para algo así conviene "
    "confirmarlo directamente con la oficina que lleva el tema en el campus."
)

# Se conserva el nombre anterior: `scripts/evaluate.py` y las pruebas existentes
# lo importan, y ADR-0011 exige que las adiciones sean aditivas.
NO_INFORMATION_MESSAGE = NO_RETRIEVAL_MESSAGE

GENERATION_FAILED_MESSAGE = (
    "No pude completar la respuesta en este momento.\n\n"
    "Intenta de nuevo en unos segundos. Si vuelve a ocurrir, prueba con una pregunta más "
    "concreta: por ejemplo, sobre un solo programa o un solo requisito."
)

_STRUGGLING_HINT = (
    "\n\nSi seguimos sin dar con ello, puede que convenga preguntarlo directamente en el "
    "campus: a veces el detalle que buscas vive en un procedimiento interno y no en el "
    "reglamento."
)

# Matiz por nivel de confianza autoinformada. La señal ya se calculaba en cada consulta
# y se descartaba: no se inventa una métrica nueva, se empieza a usar la que ya se paga.
# Es autoinformada por el modelo, no una probabilidad calibrada — de ahí que el texto
# hable de "la normativa" y no de un porcentaje de certeza.
#
# La confianza alta no lleva matiz: añadir una coletilla a cada respuesta correcta la
# convertiría en ruido y le quitaría fuerza justo cuando sí importa.
_CONFIDENCE_CAVEATS = {
    VerificationConfidence.MEDIUM: (
        "\n\nLa normativa cubre tu consulta, aunque con matices. Si vas a tomar una "
        "decisión con esto, confirma los detalles en el campus."
    ),
    VerificationConfidence.LOW: (
        "\n\nEn este punto la normativa es parcial y prefiero que lo verifiques antes de "
        "actuar: consulta directamente con la oficina que lleva el tema."
    ),
}

# Cuánto de la respuesta anterior acompaña a un seguimiento: lo justo para que el
# modelo no repita lo ya dicho y entienda a qué se refiere un pronombre.
_THREAD_EXCERPT_CHARS = 320

_CHOICE_STYLES = frozenset({ResponseStyle.RANKING, ResponseStyle.RECOMMENDATION, ResponseStyle.COMPARISON})

_DOCUMENT_BOUND_SKILLS = frozenset(
    {SkillName.DESCRIBE_DOCUMENT, SkillName.OUTLINE_DOCUMENT, SkillName.RELATE_DOCUMENTS}
)


@dataclass(frozen=True)
class _TopicProfile:
    """Lo que la normativa trata de un tema, en qué documento y qué instancia lo lleva."""

    aspects: list[str] = field(default_factory=list)
    document: str | None = None
    office: str | None = None
    # El tema solo aparece de paso en artículos de otro (sin documento ni capítulo propio).
    incidental: bool = False


class AnswerStudentQueryUseCase:
    """Orchestrates FR-06 to FR-10 and FR-14: retrieve, verify, answer, persist.

    Depends only on ports (Dependency Inversion, ADR-0001). Does not depend on
    LLMPort directly: verification (including the underlying LLM call) is fully
    delegated to VerificationStrategyPort (ADR-0005).

    Desde la capa de agencia, además orquesta la deliberación previa: sanea,
    clasifica la intención y decide qué habilidad ejecutar. Toda esa deliberación
    es determinista y ocurre **antes** de la única llamada generativa, por lo que
    el coste marginal del agente es cero tokens (ADR-0005, NFR-02, US-2.2).

    Desde la Fase 9 (ADR-0012 a ADR-0014) la recuperación es híbrida, el
    contexto se ensambla con presupuesto y las preguntas sobre los documentos
    como tales («¿de qué trata?», «¿dónde habla de…?») se resuelven con el
    catálogo del corpus, sin llamada al modelo. Todos los colaboradores nuevos
    son opcionales: sin ellos el caso de uso se comporta exactamente como la
    línea base congelada, que es lo que usan `scripts/evaluate.py` y las
    pruebas anteriores a esta fase.
    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_store_port: VectorStorePort,
        verification_port: VerificationStrategyPort,
        conversation_repository: ConversationRepositoryPort,
        document_repository: DocumentRepositoryPort,
        top_k: int = 10,
        min_similarity_threshold: float = 0.35,
        intent_classifier: IntentClassifierPort | None = None,
        *,
        retriever: KnowledgeRetriever | None = None,
        context_assembler: ContextAssembler | None = None,
        corpus_catalog: CorpusCatalogPort | None = None,
        conversation_intelligence: bool = True,
    ) -> None:
        self._verification_port = verification_port
        self._conversation_repository = conversation_repository
        self._document_repository = document_repository
        self._intent_classifier = intent_classifier
        self._retriever = retriever or KnowledgeRetriever(
            embedding_port,
            vector_store_port,
            lexical_search=None,
            settings=RetrievalSettings(top_k=top_k, min_similarity=min_similarity_threshold, hybrid=False),
        )
        self._context_assembler = context_assembler or ContextAssembler(
            catalog=None, settings=AssemblySettings(char_budget=0)
        )
        self._catalog = corpus_catalog
        # La capa conversacional necesita el catálogo (entidades y documentos).
        self._conversation_intelligence = conversation_intelligence and corpus_catalog is not None
        # Perfil de cada tema (aspectos, documento, instancia) y menú de temas
        # cubiertos: búsquedas locales, recalculadas solo si cambia el corpus.
        self._profiles: dict[tuple[str, int], _TopicProfile] = {}
        self._menu_cache: tuple[int, list[tuple[str, str]]] | None = None

    async def execute(self, request: AnswerQueryRequest) -> AnswerQueryResponse:
        started_at = time.perf_counter()
        logger.info("Pregunta recibida: '{}'", request.question)

        conversation = await self._conversation_repository.get_or_create_active_conversation(
            request.user_id
        )

        # E0 · Saneamiento. Cumple NFR-04: hasta ahora la pregunta se interpolaba
        # cruda en el prompt sin ninguna validación más allá de la longitud.
        sanitized = MessageSanitizer.sanitize(request.question)

        # El historial se lee ANTES de registrar el turno actual, y vía `get_history`
        # porque `get_or_create_active_conversation` devuelve la conversación sin
        # mensajes por rendimiento. Se evita así añadir un método al puerto.
        history = await self._load_history(request.user_id, conversation.id)

        student_message = Message(
            id=new_id(),
            conversation_id=conversation.id,
            role=MessageRole.STUDENT,
            content=request.question,
            created_at=utc_now(),
        )
        await self._conversation_repository.add_message(conversation.id, student_message)

        plan, context = self._deliberate(sanitized, history)
        outlines = self._catalog.list_outlines() if self._catalog else []

        # E2b · Capa de inteligencia de recuperación: estado de la conversación,
        # resolución de referencias y reescritura de la consulta, antes de buscar.
        state, turn = self._understand_turn(sanitized, history)
        plan = self._align_plan(plan, turn, sanitized)

        if turn is not None and turn.needs_orientation:
            # «Estoy perdido», «no sé qué preguntar»: caminos concretos, sin buscar.
            focus = focus_label(state) if state.last_grounded else None
            available = [a for a in await self._topic_aspects(state.topic) if a not in state.covered_aspects] if focus else []
            text = conversation_guide.orientation(focus, available, await self._covered_menu())
            return await self._persist_navigation(NavigationAnswer(text, is_grounded=None), conversation.id, started_at)

        if plan.skill is SkillName.RESUME_CONVERSATION and state.has_focus:
            titles = {o.document_id: o.title for o in outlines}
            fallback = next((f"el {titles[d]}" for d in state.documents if d in titles), "el tema anterior")
            # «Sigamos con las becas» nombra el tema; se retoma con ese nombre,
            # no con la beca concreta que estaba en foco.
            named = next((t for t in detect_topics(fold(sanitized.safe_for_prompt)) if t.key == state.topic), None)
            text = conversation_guide.resume(
                (named.label if named else focus_label(state)) or fallback, state.covered_aspects, await self._topic_aspects(state.topic)
            )
            return await self._persist_navigation(NavigationAnswer(text, is_grounded=None), conversation.id, started_at)

        # E3a · Habilidad local: se resuelve sin recuperación ni modelo.
        if plan.is_local:
            if plan.skill is SkillName.DISAMBIGUATE and self._catalog is not None:
                # Una consulta de una o dos palabras («becas») no se despacha con
                # una petición genérica de detalle: se muestra dónde trata el
                # corpus ese tema y qué subtemas tiene, que es mejor guía.
                overview = await self._topic_overview(sanitized.safe_for_prompt, outlines, context)
                if overview is not None:
                    return await self._persist_navigation(overview, conversation.id, started_at)
            return await self._answer_locally(
                plan=plan,
                context=context,
                sanitized=sanitized,
                conversation_id=conversation.id,
                started_at=started_at,
                outlines=outlines,
                active_focus=self._memory_label(state, outlines),
                domains=[label for label, _ in await self._covered_menu()],
            )

        query = plan.resolved_query or sanitized.safe_for_prompt
        conversation_documents = state.documents or context.topic_document_ids
        analysis = self._enrich(QueryAnalyzer.analyze(query, outlines, conversation_documents), turn, state)

        # E3b · Navegación documental: preguntas sobre los documentos como tales.
        if plan.skill.is_navigational and self._catalog is not None:
            answer = await self._navigate(plan, analysis, outlines, context)
            return await self._persist_navigation(answer, conversation.id, started_at)

        # Al modelo le llega la pregunta literal del estudiante; si depende de la
        # conversación, acompañada de cómo se interpretó («se refiere a…»).
        question = query
        if turn is not None:
            question = sanitized.safe_for_prompt
            reading = self._article_reading(turn, analysis, outlines) or turn.reading
            if turn.depends_on_context and reading:
                question = f"{question}\n\n({reading})"
            thread = self._thread(turn, history)
            if thread:
                question = f"{question}\n\n{thread}"
        return await self._answer_grounded(
            plan, analysis, question, context, conversation.id, started_at, turn, state, outlines
        )

    # --- Respuesta fundamentada (una llamada al modelo) -------------------------------

    async def _answer_grounded(
        self,
        plan: ResponsePlan,
        analysis: QueryAnalysis,
        query: str,
        context: ConversationContext,
        conversation_id: UUID,
        started_at: float,
        turn: TurnInterpretation | None = None,
        state: ConversationState | None = None,
        outlines: Sequence[DocumentOutline] = (),
    ) -> AnswerQueryResponse:
        state = state or ConversationState()
        retrieval_started_at = time.perf_counter()
        ranked = self._exact_article(analysis, turn) or await self._retriever.retrieve(analysis)
        passages = self._context_assembler.assemble(
            ranked, parts=len(analysis.sub_queries), scale=self._context_scale(turn)
        )
        retrieval_seconds = time.perf_counter() - retrieval_started_at

        if not passages:
            logger.info(
                "Sin contexto relevante (conversation_id={}, retrieval={:.2f}s); el asistente se abstiene.",
                conversation_id,
                retrieval_seconds,
            )
            return await self._persist_and_build_response(
                conversation_id=conversation_id,
                answer_text=await self._abstention(turn, state, context, outlines, NO_RETRIEVAL_MESSAGE),
                is_grounded=False,
                confidence=VerificationConfidence.LOW,
                source_chunk_ids=(),
                sources=(),
                started_at=started_at,
                retrieval_seconds=retrieval_seconds,
            )

        # Varias preguntas en un mensaje: cada una en su sección, antes que
        # cualquier otra forma (si no, alguna quedaría sin responder).
        comparing = turn is not None and bool(turn.compared)
        if comparing and plan.style in (ResponseStyle.UNSPECIFIED, ResponseStyle.DIRECT, ResponseStyle.LIST):
            style = ResponseStyle.COMPARISON
        elif analysis.is_multi_part and plan.style in (ResponseStyle.UNSPECIFIED, ResponseStyle.DIRECT):
            style = ResponseStyle.SECTIONED
        else:
            style = answer_planner.plan_style(plan.style, turn, passages)

        generation_started_at = time.perf_counter()
        try:
            verified_answer = await self._verification_port.answer(query, passages, style.directive)
        except (LLMGenerationError, VerificationFailedError) as error:
            # Un fallo del proveedor no debe llegar al estudiante como un error
            # técnico ni dejar su pregunta sin respuesta en el historial.
            logger.error("La generación falló (conversation_id={}): {}", conversation_id, error)
            return await self._persist_and_build_response(
                conversation_id=conversation_id,
                answer_text=GENERATION_FAILED_MESSAGE,
                is_grounded=False,
                confidence=None,
                source_chunk_ids=(),
                sources=(),
                started_at=started_at,
                retrieval_seconds=retrieval_seconds,
            )
        generation_seconds = time.perf_counter() - generation_started_at
        self._log_usage(verified_answer, passages)

        if not verified_answer.is_grounded or verified_answer.coverage is AnswerCoverage.NONE:
            logger.info(
                "Verificación marcó la respuesta como no fundamentada (conversation_id={}); el asistente se abstiene.",
                conversation_id,
            )
            return await self._persist_and_build_response(
                conversation_id=conversation_id,
                answer_text=await self._abstention(
                    turn, state, context, outlines, NOT_GROUNDED_MESSAGE + self._nearest_hint(passages)
                ),
                is_grounded=False,
                confidence=verified_answer.confidence,
                source_chunk_ids=(),
                sources=(),
                started_at=started_at,
                retrieval_seconds=retrieval_seconds,
                generation_seconds=generation_seconds,
            )

        cited = self._cited_passages(verified_answer, passages)
        sources = await self._resolve_sources(cited)
        confidence = verified_answer.confidence
        if verified_answer.coverage is AnswerCoverage.PARTIAL and confidence is VerificationConfidence.HIGH:
            # Una respuesta fiel pero incompleta no puede presentarse con confianza alta.
            confidence = VerificationConfidence.MEDIUM
        # En una respuesta parcial el modelo ya cierra diciendo qué falta; el
        # matiz genérico duplicaría el aviso con menos precisión.
        caveat = "" if verified_answer.coverage is AnswerCoverage.PARTIAL else _CONFIDENCE_CAVEATS.get(confidence, "")

        # Anticipación: al abrir un tema, ofrecer lo que la normativa también trata.
        offer = ""
        opens_topic = turn is not None and turn.topic and (turn.mode is TurnMode.NEW or turn.is_overview)
        if opens_topic and not caveat and verified_answer.coverage is AnswerCoverage.COMPLETE and turn is not None and not turn.compared:
            available = conversation_guide.not_in_answer(await self._topic_aspects(turn.topic), verified_answer.answer_text)
            exclude = (turn.aspect or "", *state.covered_aspects)
            if turn.is_overview:
                offer = conversation_guide.overview_offer(available, exclude, self._has_options(turn.topic))
            else:
                offer = conversation_guide.offer_line(available, exclude)
        return await self._persist_and_build_response(
            conversation_id=conversation_id,
            answer_text=conversation_guide.close_with_offer(self._voice(verified_answer.answer_text, style) + caveat, offer),
            is_grounded=True,
            confidence=confidence,
            source_chunk_ids=tuple(dict.fromkeys(cid for passage in cited for cid in passage.origin_ids)),
            sources=sources,
            started_at=started_at,
            retrieval_seconds=retrieval_seconds,
            generation_seconds=generation_seconds,
        )

    @staticmethod
    def _voice(text: str, style: ResponseStyle) -> str:
        text = enforce_institutional_voice(text)
        # Ante una pregunta de elección, primero la opción; lo que la normativa no dice, al final.
        return lead_with_what_applies(text) if style in _CHOICE_STYLES else text

    @staticmethod
    def _cited_passages(answer: VerifiedAnswer, passages: Sequence[RetrievedChunk]) -> list[RetrievedChunk]:
        """Solo se citan los pasajes en que el modelo dice apoyarse.

        Antes se citaban todos los documentos recuperados, incluidos los que no
        aportaron nada. Si el modelo no informa qué usó (o informa algo fuera de
        rango), se vuelve al comportamiento anterior: citar todo lo entregado.
        """
        cited = [passages[index - 1] for index in answer.cited_fragments if 1 <= index <= len(passages)]
        return cited or list(passages)

    @staticmethod
    def _nearest_hint(passages: Sequence[RetrievedChunk]) -> str:
        """En la abstención, señalar dónde está lo más cercano es más útil que solo abstenerse."""
        for passage in passages:
            chunk = passage.chunk
            if chunk.document and chunk.anchor and chunk.anchor.citation_label:
                return (
                    f"\n\nLo más cercano que encontré está en el {chunk.document.title} "
                    f"({chunk.anchor.citation_label}), por si quieres revisarlo."
                )
        return ""

    @staticmethod
    def _log_usage(answer: VerifiedAnswer, passages: Sequence[RetrievedChunk]) -> None:
        if answer.input_tokens is None:
            return
        logger.info(
            "Generación: {} pasajes ({} caracteres de contexto), tokens entrada={} salida={}, cobertura={}, citados={}",
            len(passages),
            sum(len(p.chunk.text) for p in passages),
            answer.input_tokens,
            answer.output_tokens,
            answer.coverage.value,
            list(answer.cited_fragments),
        )

    # --- Navegación documental (sin llamada al modelo) ---------------------------------

    async def _navigate(
        self,
        plan: ResponsePlan,
        analysis: QueryAnalysis,
        outlines: Sequence[DocumentOutline],
        context: ConversationContext,
    ) -> NavigationAnswer:
        assert self._catalog is not None
        navigator = DocumentNavigator(outlines, await self._filenames())
        skill = plan.skill

        if skill in _DOCUMENT_BOUND_SKILLS:
            target = self._single_target(analysis, outlines, context)
            if target is None:
                return navigator.ask_which_document()
            if skill is SkillName.DESCRIBE_DOCUMENT:
                return navigator.describe(target)
            if skill is SkillName.OUTLINE_DOCUMENT:
                return navigator.outline(target)
            return navigator.relate(target, self._catalog.related_documents(target))

        topic = analysis.topic or analysis.text
        hits = await self._retriever.retrieve(replace(analysis, text=topic, sub_queries=(topic,)))
        if skill is SkillName.RECOMMEND_DOCUMENTS:
            return navigator.route(topic, hits)
        return navigator.locate(topic, hits)

    async def _topic_overview(
        self, topic: str, outlines: Sequence[DocumentOutline], context: ConversationContext
    ) -> NavigationAnswer | None:
        analysis = QueryAnalyzer.analyze(topic, outlines, context.topic_document_ids)
        hits = await self._retriever.retrieve(analysis)
        if not hits:
            return None
        navigator = DocumentNavigator(outlines, await self._filenames())
        return navigator.locate(topic.strip(" ¿?.!¡"), hits, clarify=True)

    @staticmethod
    def _single_target(
        analysis: QueryAnalysis, outlines: Sequence[DocumentOutline], context: ConversationContext
    ) -> UUID | None:
        """El documento al que alude la pregunta: el nombrado, el de la conversación o el único."""
        for candidates in (analysis.target_documents, context.topic_document_ids):
            titles = {fold(o.title) for o in outlines if o.document_id in candidates}
            # Documentos duplicados (mismo título) cuentan como uno solo.
            if candidates and len(titles) <= 1:
                return candidates[0]
        distinct = {fold(outline.title): outline.document_id for outline in outlines}
        return next(iter(distinct.values())) if len(distinct) == 1 else None

    async def _persist_navigation(
        self, answer: NavigationAnswer, conversation_id: UUID, started_at: float
    ) -> AnswerQueryResponse:
        return await self._persist_and_build_response(
            conversation_id=conversation_id,
            answer_text=answer.text,
            is_grounded=answer.is_grounded,
            # Respuestas extraídas del índice, no generadas: su confianza no es
            # autoinformada por un modelo, depende solo de que haya fuentes.
            confidence=VerificationConfidence.HIGH if answer.is_grounded else None,
            source_chunk_ids=(),
            sources=answer.sources,
            started_at=started_at,
        )

    # --- Capa de inteligencia de recuperación -----------------------------------------

    def _understand_turn(
        self, sanitized: SanitizedMessage, history: Sequence[Message]
    ) -> tuple[ConversationState, TurnInterpretation | None]:
        if not self._conversation_intelligence or self._intent_classifier is None:
            return ConversationState(), None
        assert self._catalog is not None
        tracker = ConversationTracker(self._catalog.entities(), self._catalog.vocabulary, self._catalog.co_occur)
        state = tracker.replay(history)
        turn = tracker.interpret(sanitized.safe_for_prompt, state)
        logger.info(
            "Turno '{}' ({}) → consulta interna: '{}'",
            turn.mode.value,
            turn.resolution,
            turn.retrieval_query,
        )
        return state, turn

    @staticmethod
    def _align_plan(
        plan: ResponsePlan, turn: TurnInterpretation | None, sanitized: SanitizedMessage
    ) -> ResponsePlan:
        """Ajusta la decisión de la política con lo que se entendió de la conversación.

        El clasificador ve el mensaje aislado: «Requisitos» le parece ambiguo y
        «¿cuánto cubre?», ruido. Con un tema activo son preguntas completas.
        """
        if turn is None:
            return plan
        if turn.mode is TurnMode.RESUME:
            return replace(plan, skill=SkillName.RESUME_CONVERSATION)
        if turn.is_overview and plan.skill in (SkillName.DISAMBIGUATE, SkillName.HANDLE_NOISE):
            # «Becas» a secas: un asesor da el panorama del tema, no un índice de apartados.
            return ResponsePlan(
                skill=SkillName.GROUNDED_ANSWER,
                intent=ConversationIntent.INSTITUTIONAL_QUERY,
                style=ResponseStyle.OVERVIEW,
                resolved_query=turn.retrieval_query,
            )
        answerable = plan.skill in (SkillName.GROUNDED_ANSWER, SkillName.DISAMBIGUATE, SkillName.HANDLE_NOISE)
        if turn.depends_on_context and answerable:
            style = plan.style
            if style is ResponseStyle.UNSPECIFIED:
                style = response_policy.detect_style(sanitized.normalized)
            return ResponsePlan(
                skill=SkillName.GROUNDED_ANSWER,
                intent=ConversationIntent.FOLLOW_UP,
                style=style,
                resolved_query=turn.retrieval_query,
            )
        if plan.skill is SkillName.GROUNDED_ANSWER:
            # Pregunta autosuficiente: se busca con la consulta optimizada (en un
            # panorama, el tema y sus términos), nunca con la pregunta anterior
            # antepuesta por una coincidencia anafórica superficial.
            return replace(plan, resolved_query=turn.retrieval_query)
        return plan

    @staticmethod
    def _enrich(
        analysis: QueryAnalysis, turn: TurnInterpretation | None, state: ConversationState
    ) -> QueryAnalysis:
        if turn is None:
            return analysis
        targets = analysis.target_documents
        # «Artículo 20» o «¿y el siguiente?» sin nombrar documento: el que se está consultando.
        bare_article = turn.article_numbers and turn.topic is None and turn.entity is None
        deepening_article = turn.mode is TurnMode.DEEPEN and turn.article_numbers
        if (turn.mode is TurnMode.ARTICLE_STEP or bare_article or deepening_article) and not targets and state.documents:
            targets = state.documents[:1]
        return replace(
            analysis,
            expansions=tuple(dict.fromkeys((*analysis.expansions, *turn.expansions))),
            article_numbers=tuple(dict.fromkeys((*turn.article_numbers, *analysis.article_numbers))),
            target_documents=targets,
            focus_terms=turn.focus_terms,
            aspect_title_words=turn.aspect_title_words,
            required_terms=turn.required_terms,
            defining_articles=turn.defining_articles,
            topic_terms=turn.topic_terms,
            # Una consulta reescrita no se vuelve a partir en subpreguntas; una
            # comparación, en cambio, busca cada entidad por separado.
            sub_queries=turn.sub_queries
            or (analysis.sub_queries if turn.mode is TurnMode.NEW else (analysis.text,)),
        )

    @staticmethod
    def _context_scale(turn: TurnInterpretation | None) -> float:
        """Contexto adaptativo: un panorama necesita más; un dato de una entidad, menos."""
        if turn is None:
            return 1.0
        if turn.is_overview:
            return 1.5
        if turn.entity is not None and turn.aspect is not None:
            return 0.7
        return 1.0

    def _exact_article(self, analysis: QueryAnalysis, turn: TurnInterpretation | None) -> list[RetrievedChunk]:
        """«Artículo 20», «¿y el siguiente?», «explícalo»: el artículo exacto, sin buscar."""
        navigating = turn is not None and turn.mode in (TurnMode.ARTICLE_STEP, TurnMode.DEEPEN)
        if not navigating or self._catalog is None or len(analysis.target_documents) != 1 or not analysis.article_numbers:
            return []
        chunks = self._catalog.article_chunks(analysis.target_documents[0], analysis.article_numbers[0])
        return [RetrievedChunk(chunk=chunk, score=SimilarityScore(1.0)) for chunk in chunks]

    @staticmethod
    def _article_reading(
        turn: TurnInterpretation, analysis: QueryAnalysis, outlines: Sequence[DocumentOutline]
    ) -> str | None:
        """«¿Y el anterior?» no le dice nada al modelo; «explica el Artículo 20 de…», sí."""
        if turn.mode not in (TurnMode.ARTICLE_STEP, TurnMode.DEEPEN) or not analysis.article_numbers:
            return None
        titles = {o.document_id: o.title for o in outlines}
        document = next((titles[d] for d in analysis.target_documents if d in titles), None)
        where = f" del {document}" if document else ""
        number = analysis.article_numbers[0]
        if turn.wants_example:
            return f"Pide un ejemplo práctico de cómo se aplica el Artículo {number}{where}."
        if turn.mode is TurnMode.DEEPEN:
            return f"Pide que le expliques con más claridad el Artículo {number}{where}."
        return f"Se refiere al Artículo {number}{where}: explica qué establece."

    @staticmethod
    def _memory_label(state: ConversationState, outlines: Sequence[DocumentOutline]) -> str | None:
        """Lo que se recuerda al saludar o despedirse: el tema, o el documento consultado."""
        if not state.has_focus:
            return None
        titles = {o.document_id: o.title for o in outlines}
        return focus_label(state) or next((f"el {titles[d]}" for d in state.documents if d in titles), None)

    async def _topic_aspects(self, topic_key: str | None) -> list[str]:
        return (await self._topic_profile(topic_key)).aspects

    async def _topic_profile(self, topic_key: str | None) -> _TopicProfile:
        """Lo que la normativa trata de un tema, dónde y quién lo lleva.

        Una búsqueda local, sin modelo: permite ofrecer solo lo que se puede
        responder y, al abstenerse, decir qué documento sí trata el tema y qué
        instancia menciona para él (la que más nombra su normativa).
        """
        topic = topic_by_key(topic_key)
        if topic is None or self._catalog is None:
            return _TopicProfile()
        key = (topic.key, len(self._catalog.list_outlines()))
        if key not in self._profiles:
            self._profiles[key] = await self._build_profile(topic_key)
        return self._profiles[key]

    async def _build_profile(self, topic_key: str | None) -> _TopicProfile:
        topic = topic_by_key(topic_key)
        if topic is None or self._catalog is None:
            return _TopicProfile()
        probe = QueryAnalysis(
            text=topic.retrieval_terms, sub_queries=(topic.retrieval_terms,), required_terms=anchor_terms(topic)
        )
        hits = await self._retriever.retrieve(probe)
        # Si el documento (o un capítulo) trata el tema, cuentan todos sus
        # artículos: la oferta refleja lo que el documento cubre. Si el tema es
        # un apartado de otro documento (el cambio de carrera dentro del reglamento
        # de ayudas), solo cuentan los artículos recuperados: ofrecer «la cobertura»
        # del reglamento entero hablando del cambio de carrera sería prometer de más.
        titles: list[str] = []
        incidental = True
        for document_id in dict.fromkeys(h.chunk.document_id for h in hits):
            outline = self._catalog.get_outline(document_id)
            if outline is None:
                continue
            whole = bool(topic.trigger.search(fold(outline.title)))
            chapters = [d for d in outline.divisions if whole or topic.trigger.search(fold(d.label))]
            if chapters:
                incidental = False
                titles += [a.title for d in chapters for a in d.articles if a.title]
            else:
                titles += [h.chunk.heading for h in hits if h.chunk.document_id == document_id and h.chunk.heading]
        documents = [h.chunk.document_id for h in hits]
        main = min(dict.fromkeys(documents), key=lambda d: (-documents.count(d), documents.index(d))) if documents else None
        outline = self._catalog.get_outline(main) if main else None
        offices = [e for e in self._catalog.entities() if e.kind is EntityKind.OFFICE]
        mentions = [e for h in hits for e in find_entities(h.chunk.text, offices)]
        # La más nombrada; en empate, la que aparece primero (determinista entre ejecuciones).
        top = min(dict.fromkeys(mentions), key=lambda e: (-mentions.count(e), mentions.index(e))) if mentions else None
        office = top.spoken if top else None
        return _TopicProfile(
            conversation_guide.available_aspects(titles), outline.title if outline else None, office, incidental and bool(hits)
        )

    async def _covered_menu(self) -> list[tuple[str, str]]:
        """Temas que el corpus realmente cubre, con una pregunta de ejemplo cada uno."""
        if self._catalog is None:
            return []
        size = len(self._catalog.list_outlines())
        if self._menu_cache is None or self._menu_cache[0] != size:
            menu = []
            for key, question in conversation_guide.TOPIC_MENU:
                topic = topic_by_key(key)
                if topic is not None and (await self._topic_profile(key)).document is not None:
                    menu.append((topic.label, question))
            self._menu_cache = (size, menu)
        return self._menu_cache[1]

    def _has_options(self, topic_key: str | None) -> bool:
        """¿Hay varias opciones entre las que elegir (varias becas, varios programas)?"""
        if self._catalog is None:
            return False
        programs = [e for e in self._catalog.entities() if e.kind is EntityKind.PROGRAM and e.defined_in]
        return sum(1 for e in programs if topic_of(e) == topic_key) >= 2

    @staticmethod
    def _thread(turn: TurnInterpretation, history: Sequence[Message]) -> str | None:
        """El hilo inmediato, para que el modelo no se repita ni pierda el pronombre.

        No es fuente: el modelo sigue respondiendo solo con los fragmentos
        (ADR-0005). Es lo que una persona tiene presente sin pensarlo: qué le
        preguntaron hace un momento y qué contestó.
        """
        if not turn.depends_on_context:
            return None
        previous = next((m for m in reversed(history) if m.role is MessageRole.ASSISTANT), None)
        asked = next((m for m in reversed(history) if m.role is MessageRole.STUDENT), None)
        if previous is None or asked is None or not previous.is_grounded:
            return None
        excerpt = " ".join(previous.content.split())
        if len(excerpt) > _THREAD_EXCERPT_CHARS:
            cut = excerpt[:_THREAD_EXCERPT_CHARS]
            excerpt = cut[: cut.rfind(" ")] + "…"
        return (
            "HILO DE LA CONVERSACIÓN (no es fuente; úsalo solo para entender las referencias y no repetirte): "
            f"el estudiante preguntó antes «{asked.content.strip()}» y le respondiste: «{excerpt}». "
            "No repitas lo que ya dijiste: avanza con lo nuevo que se pregunta."
        )

    async def _abstention(
        self,
        turn: TurnInterpretation | None,
        state: ConversationState,
        context: ConversationContext,
        outlines: Sequence[DocumentOutline],
        default: str,
    ) -> str:
        """Abstención que orienta: qué no está, qué sí trata la normativa y qué hacer."""
        focus = self._turn_focus(turn)
        if turn is None or focus is None:
            menu = await self._covered_menu()
            if default == NO_RETRIEVAL_MESSAGE and menu:
                # Sin tema reconocido: pedir otras palabras y abrir caminos concretos.
                return conversation_guide.unmatched(menu, context.is_struggling)
            return self._abstention_text(default, context)
        repeated = state.last_grounded is False and state.topic == turn.topic and turn.depends_on_context
        profile = await self._topic_profile(turn.topic)
        menu = [(label, question) for label, question in await self._covered_menu() if label != focus]
        return conversation_guide.abstention(
            focus,
            turn.aspect,
            profile.aspects,
            repeated,
            self._corpus_overview(outlines),
            streak=context.consecutive_abstentions,
            covered=state.covered_aspects,
            document=profile.document,
            office=profile.office,
            alternatives=menu,
            incidental=profile.incidental,
        )

    @staticmethod
    def _turn_focus(turn: TurnInterpretation | None) -> str | None:
        if turn is None:
            return None
        if turn.entity is not None:
            return turn.entity.spoken
        topic = topic_by_key(turn.topic)
        return topic.label if topic else None

    @staticmethod
    def _corpus_overview(outlines: Sequence[DocumentOutline]) -> str | None:
        """«el reglamento de ayudas financieras, …, el calendario académico y los programas académicos»."""
        seen: dict[str, str] = {}
        programs = False
        for outline in outlines:
            if outline.kind in (DocumentKind.PROGRAM, DocumentKind.GENERAL):
                programs = True
                continue
            seen.setdefault(fold(outline.title), f"el {outline.title}")
        items = list(seen.values()) + (["los programas académicos de la universidad"] if programs else [])
        if not items:
            return None
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]

    # --- Deliberación y habilidades locales --------------------------------------------

    async def _load_history(self, user_id: UUID, conversation_id: UUID) -> Sequence[Message]:
        """Mensajes de la conversación activa, para derivar el contexto de sesión.

        Sin clasificador no hay deliberación, así que no se paga la consulta: el
        comportamiento y el coste quedan idénticos a los de antes del agente.
        """
        if self._intent_classifier is None:
            return ()
        conversations = await self._conversation_repository.get_history(user_id)
        for candidate in conversations:
            if candidate.id == conversation_id:
                # Copia: algunos repositorios devuelven la lista viva, que recibiría
                # el turno actual y haría pasar la pregunta presente por «la anterior».
                return tuple(candidate.messages)
        return ()

    def _deliberate(
        self, sanitized: SanitizedMessage, history: Sequence[Message]
    ) -> tuple[ResponsePlan, ConversationContext]:
        """E1 + E2: comprensión y política. Determinista y sin coste."""
        context = ConversationContext.from_messages(history)

        if self._intent_classifier is None:
            # Sin clasificador el caso de uso conserva su comportamiento original.
            return (
                ResponsePlan(
                    skill=SkillName.GROUNDED_ANSWER,
                    intent=ConversationIntent.INSTITUTIONAL_QUERY,
                    resolved_query=sanitized.safe_for_prompt,
                ),
                context,
            )

        if sanitized.has_injection_markers:
            classification = IntentClassification(
                ConversationIntent.PROMPT_INJECTION, 1.0, "sanitizer"
            )
        else:
            classification = self._intent_classifier.classify(sanitized.normalized)

        plan = response_policy.decide(
            classification, context, sanitized.normalized, sanitized.safe_for_prompt
        )
        if plan.skill.is_navigational and self._catalog is None:
            # Sin catálogo documental la navegación no es posible: se responde
            # como consulta fundamentada, que es el comportamiento anterior.
            plan = replace(plan, skill=SkillName.GROUNDED_ANSWER)
        logger.info(
            "Intención '{}' (confianza {:.2f}) → habilidad '{}' [{}]",
            classification.intent.value,
            classification.confidence,
            plan.skill.value,
            "local" if plan.is_local else "navegación" if plan.skill.is_navigational else "fundamentada",
        )
        return plan, context

    async def _answer_locally(
        self,
        *,
        plan: ResponsePlan,
        context: ConversationContext,
        sanitized: SanitizedMessage,
        conversation_id: UUID,
        started_at: float,
        outlines: Sequence[DocumentOutline] = (),
        active_focus: str | None = None,
        domains: Sequence[str] = (),
    ) -> AnswerQueryResponse:
        document_names: tuple[str, ...] = ()
        if plan.skill is SkillName.DECLARE_DOCUMENT_SCOPE:
            if outlines:
                # Títulos que declaran los propios documentos, sin duplicados.
                document_names = tuple({fold(o.title): o.title for o in outlines}.values())
            else:
                documents = await self._document_repository.list_all()
                document_names = tuple(document.filename for document in documents)

        answer_text = LocalSkillCatalog.respond(
            plan,
            context,
            original_message=sanitized.original,
            document_names=document_names,
            active_focus=active_focus,
            domains=domains,
        )

        # `is_grounded=None` distingue "no aplica" de "no fundamentada": estas
        # respuestas no son afirmaciones sobre la normativa, así que no tiene
        # sentido evaluarlas contra documentos ni adjuntarles fuentes.
        return await self._persist_and_build_response(
            conversation_id=conversation_id,
            answer_text=answer_text,
            is_grounded=None,
            confidence=None,
            source_chunk_ids=(),
            sources=(),
            started_at=started_at,
        )

    @staticmethod
    def _abstention_text(base: str, context: ConversationContext) -> str:
        """Tras dos abstenciones seguidas, orientar es más útil que repetir."""
        return base + (_STRUGGLING_HINT if context.is_struggling else "")

    # --- Fuentes y persistencia ----------------------------------------------------------

    async def _filenames(self) -> dict[UUID, str]:
        return {document.id: document.filename for document in await self._document_repository.list_all()}

    async def _resolve_sources(self, passages: Sequence[RetrievedChunk]) -> tuple[SourceReference, ...]:
        """Una referencia por ubicación citada: documento, apartado y páginas.

        Los pasajes llegan agrupados por documento en orden de relevancia, de
        modo que el orden de las fuentes también lo es. Las referencias a
        documentos que ya no existen en el repositorio se omiten, como antes.
        """
        filenames = await self._filenames()
        unique: dict[tuple[str, str, int | None], SourceReference] = {}
        for passage in passages:
            chunk = passage.chunk
            filename = filenames.get(chunk.document_id)
            if filename is None:
                continue
            reference = SourceReference.at(
                document_name=filename,
                document_id=chunk.document_id,
                document_title=chunk.document.title if chunk.document else None,
                anchor=chunk.anchor,
            )
            unique.setdefault(reference.dedup_key, reference)
        return tuple(unique.values())

    async def _persist_and_build_response(
        self,
        *,
        conversation_id: UUID,
        answer_text: str,
        is_grounded: bool | None,
        confidence: VerificationConfidence | None,
        source_chunk_ids: tuple[UUID, ...],
        sources: tuple[SourceReference, ...],
        started_at: float,
        retrieval_seconds: float | None = None,
        generation_seconds: float | None = None,
    ) -> AnswerQueryResponse:
        assistant_message = Message(
            id=new_id(),
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer_text,
            created_at=utc_now(),
            is_grounded=is_grounded,
            confidence=confidence,
            source_chunk_ids=source_chunk_ids,
            source_document_names=tuple(dict.fromkeys(s.document_name for s in sources)),
            sources=sources,
        )
        await self._conversation_repository.add_message(conversation_id, assistant_message)

        total_seconds = time.perf_counter() - started_at
        logger.info(
            "Consulta completada en {:.2f}s (retrieval={}, generation={})",
            total_seconds,
            f"{retrieval_seconds:.2f}s" if retrieval_seconds is not None else "n/a",
            f"{generation_seconds:.2f}s" if generation_seconds is not None else "n/a",
        )

        return AnswerQueryResponse(
            message_id=assistant_message.id,
            conversation_id=conversation_id,
            answer_text=answer_text,
            is_grounded=is_grounded,
            confidence=confidence,
            created_at=assistant_message.created_at,
            sources=sources,
        )

