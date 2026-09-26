from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.domain.services.institutional_lexicon import expansions_for, normalize_chat_speak
from app.domain.services.spanish_text import analyze, content_words, fold, tokenize
from app.domain.value_objects.document_facts import DocumentKind
from app.domain.value_objects.document_outline import DocumentOutline

_ARTICLE_REFERENCE = re.compile(r"\bart(?:iculos?|s?\.)?\s*(\d{1,3})(?:\s*(?:y|,|a|al)\s*(\d{1,3}))?\b")
_CHANGES = re.compile(
    r"\bque\s+cambios\b|\bcambios\s+(?:tuvo|hubo|recientes|se\s+hicieron)\b|\bultima\s+version\b"
    r"|\bhistorial\s+de\s+(?:cambios|versiones)\b|\bcontrol\s+de\s+cambios\b|\bmodificaciones\b"
    r"|\bque\s+se\s+(?:modifico|actualizo|cambio)\b"
)
_DEICTIC_DOCUMENT = re.compile(
    r"\b(?:este|ese|esta|esa|dicho|dicha|mismo|misma|el|la)\s+(?:documento|reglamento|calendario|archivo|pdf|folleto|normativa)\b"
    r"(?!\s+de\b)"
)
# Preguntas por una fecha: su fuente de autoridad es el calendario académico.
_DATE_QUESTION = re.compile(
    r"\bcuando\b|\bfecha\w*|\bultimo\s+dia\b|\bplazo\s+(?:para|de|maximo)\b|\bdia\s+(?:de|del)\b|\bhasta\s+que\s+dia\b"
)
_DOCUMENT_TYPE_WORDS = frozenset({"reglamento", "documento", "calendario", "normativa", "guia", "folleto", "proceso", "manual"})
# Palabras de título que no distinguen un documento de otro en este corpus.
_GENERIC_TITLE_STEMS = frozenset(
    analyze(
        "reglamento documento universidad valle guatemala uvg campus altiplano general "
        "programa 2024 2025 2026 2027 version guia folleto uvga"
    )
)
# Vocabulario de navegación: se retira para quedarse con el tema de la pregunta.
_NAVIGATION_WORDS = frozenset(
    fold(word)
    for word in ["donde", "dónde", "habla", "hablan", "hablen", "trata", "tratan", "menciona", "mencionan", "aparece", "aparecen", "dice", "dicen", "regula", "regulan", "establece", "establecen", "explica", "consultar", "consulto", "consulte", "encontrar", "encuentro", "buscar", "articulo", "artículo", "articulos", "artículos", "capitulo", "capítulo", "capitulos", "capítulos", "seccion", "sección", "secciones", "apartado", "apartados", "parte", "partes", "pagina", "página", "paginas", "documento", "documentos", "reglamento", "reglamentos", "normativa", "normativas", "cuales", "cuáles", "cual", "cuál", "debo", "tengo", "puedo", "informacion", "información", "relacionados", "relacionado", "temas", "principales"]
)
_QUESTION_SPLIT = re.compile(
    r"\?\s*(?:¿|\b)|(?<=[.;])\s+(?=¿)|\s+(?:y\s+adem[aá]s|adem[aá]s|y\s+tambi[eé]n)\s+"
    # «…de las elecciones y cuántos miembros…»: una «y» seguida de otra pregunta.
    # Admite una preposición intermedia: «…la beca y a qué hora son…».
    r"|\s+y\s+(?=(?:(?:a|en|de|con|para|por|desde|hasta)\s+)?"
    r"(?:cu[aá]nt|cu[aá]l|qu[eé]\b|c[oó]mo\b|cu[aá]ndo\b|d[oó]nde\b|qui[eé]n)\w*)",
    re.IGNORECASE,
)
_MAX_SUB_QUERIES = 3
_SENTENCE = re.compile(r"(?<=[.!?;])\s+")
_PLEASANTRY_WORDS = frozenset(
    ["hola", "buenas", "buenos", "tardes", "dias", "noches", "saludos", "gracias", "muchas", "muchisimas", "agradezco", "favor", "saludo", "cordial", "atentamente", "espero", "bien"]
)


@dataclass(frozen=True, slots=True)
class QueryAnalysis:
    """Lo que el sistema entiende de una consulta antes de buscar.

    `target_documents` restringe la búsqueda (el estudiante nombró el
    documento); `preferred_documents` solo la inclina (lo sugiere un sinónimo o
    el tema de la conversación). Confundir ambas cosas llevaría a descartar
    evidencia de otros documentos por una coincidencia débil.
    """

    text: str
    sub_queries: tuple[str, ...]
    expansions: tuple[str, ...] = ()
    article_numbers: tuple[int, ...] = ()
    target_documents: tuple[UUID, ...] = ()
    preferred_documents: tuple[UUID, ...] = ()
    topic: str = ""
    asks_for_changes: bool = False
    matched_title_words: frozenset[str] = field(default_factory=frozenset)
    # Señales de la capa conversacional (vacías en una consulta aislada).
    focus_terms: tuple[str, ...] = ()
    aspect_title_words: tuple[str, ...] = ()
    required_terms: tuple[str, ...] = ()
    defining_articles: tuple[tuple[UUID, int], ...] = ()
    # Raíces del tema de la pregunta: el aspecto solo puntúa evidencia de ese tema.
    topic_terms: tuple[str, ...] = ()

    @property
    def is_multi_part(self) -> bool:
        return len(self.sub_queries) > 1


def article_references(folded: str) -> tuple[int, ...]:
    """«art. 18», «artículos 7 y 8», «artículos 7 a 10» → números citados."""
    numbers: list[int] = []
    for match in _ARTICLE_REFERENCE.finditer(folded):
        first = int(match.group(1))
        numbers.append(first)
        if match.group(2):
            second = int(match.group(2))
            numbers.extend(range(first + 1, second + 1) if 0 < second - first <= 10 else [second])
    return tuple(dict.fromkeys(numbers))


class QueryAnalyzer:
    """Comprensión determinista de la consulta: cero tokens, reproducible y medible."""

    @staticmethod
    def analyze(
        query: str,
        outlines: Sequence[DocumentOutline] = (),
        conversation_documents: Sequence[UUID] = (),
    ) -> QueryAnalysis:
        folded = normalize_chat_speak(fold(query))
        asks_for_changes = bool(_CHANGES.search(folded))
        expansions = list(expansions_for(folded))
        if asks_for_changes:
            expansions += ["control de cambios", "version", "acta"]

        targets, preferred, title_words = QueryAnalyzer._document_mentions(
            folded, expansions, outlines, conversation_documents
        )
        if _DATE_QUESTION.search(folded):
            # Priorización de fuentes por tipo de pregunta: para «¿cuándo…?» manda el
            # calendario. Es preferencia (media posición), nunca filtro: si el
            # reglamento fija el plazo, su evidencia más fuerte sigue ganando.
            calendars = tuple(o.document_id for o in outlines if o.kind is DocumentKind.CALENDAR)
            preferred = tuple(dict.fromkeys((*preferred, *(c for c in calendars if c not in targets))))
        retrieval_text = QueryAnalyzer._without_pleasantries(query)
        return QueryAnalysis(
            text=retrieval_text,
            sub_queries=QueryAnalyzer._decompose(retrieval_text),
            expansions=tuple(dict.fromkeys(expansions)),
            article_numbers=article_references(folded),
            target_documents=targets,
            preferred_documents=preferred,
            topic=QueryAnalyzer._topic(query, title_words),
            asks_for_changes=asks_for_changes,
            matched_title_words=title_words,
        )

    @staticmethod
    def _document_mentions(
        folded: str,
        expansions: Sequence[str],
        outlines: Sequence[DocumentOutline],
        conversation_documents: Sequence[UUID],
    ) -> tuple[tuple[UUID, ...], tuple[UUID, ...], frozenset[str]]:
        query_stems = set(analyze(folded))
        names_document_type = any(word in _DOCUMENT_TYPE_WORDS for word in tokenize(folded))

        explicit: list[UUID] = []
        soft: list[UUID] = []
        title_words: set[str] = set()
        for outline in outlines:
            distinctive = set(analyze(outline.title)) - _GENERIC_TITLE_STEMS
            if outline.facts.code and fold(outline.facts.code) in folded:
                explicit.append(outline.document_id)
                continue
            if not distinctive:
                continue
            direct = distinctive & query_stems
            share = len(direct) / len(distinctive)
            if share >= 0.5 and (names_document_type or (share == 1 and len(distinctive) >= 2)):
                explicit.append(outline.document_id)
                title_words |= direct
            elif share >= 0.5:
                # Mención directa pero sin nombrar el tipo de documento
                # («requisitos de Informática»): inclina, no restringe. Las
                # coincidencias vía sinónimos no cuentan: medido en el corpus,
                # «becas» → «ayudas financieras» sepultaba la «Feria de becas»
                # del calendario bajo artículos del reglamento.
                soft.append(outline.document_id)

        if not explicit and _DEICTIC_DOCUMENT.search(folded) and conversation_documents:
            explicit.extend(conversation_documents)
        elif not explicit and len(outlines) == 1 and names_document_type:
            explicit.append(outlines[0].document_id)

        preferred = [doc for doc in soft + list(conversation_documents) if doc not in explicit]
        return tuple(dict.fromkeys(explicit)), tuple(dict.fromkeys(preferred)), frozenset(title_words)

    @staticmethod
    def _without_pleasantries(query: str) -> str:
        """Retira oraciones que solo son cortesía («Hola, buenas tardes.», «Muchas gracias.»).

        En una consulta larga, el saludo diluye el embedding de la pregunta real.
        Solo se retiran oraciones compuestas **enteramente** de fórmulas de
        cortesía: cualquier palabra con contenido conserva la oración.
        """
        sentences = _SENTENCE.split(query.strip())
        kept = [
            sentence
            for sentence in sentences
            if not set(tokenize(sentence)) <= _PLEASANTRY_WORDS or not tokenize(sentence)
        ]
        return " ".join(kept).strip() or query.strip()

    @staticmethod
    def _decompose(query: str) -> tuple[str, ...]:
        """Separa preguntas múltiples para que cada una obtenga su propia evidencia.

        Sin esto, la recuperación de «¿qué cubre el seguro y cuándo se paga la
        cuota?» favorece a la parte con más vocabulario compartido con el corpus
        y la otra llega al modelo sin un solo fragmento que la respalde.
        """
        parts = [part.strip(" ¿?.;,") for part in _QUESTION_SPLIT.split(query)]
        meaningful = [part for part in parts if len(content_words(part)) >= 2]
        if len(meaningful) <= 1:
            return (query.strip(),)
        return tuple(meaningful[:_MAX_SUB_QUERIES])

    @staticmethod
    def _topic(query: str, title_words: frozenset[str]) -> str:
        """«¿Qué artículos hablan del seguro?» → «seguro»."""
        words = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", query)
        kept = [
            word
            for word in words
            if fold(word) not in _NAVIGATION_WORDS
            and fold(word) not in {"que", "sobre", "del", "de", "la", "el", "los", "las", "en", "y", "a", "al", "se", "hay", "son", "me", "mi"}
            and not ({stem for stem in analyze(word)} & title_words)
        ]
        return " ".join(kept).strip()
