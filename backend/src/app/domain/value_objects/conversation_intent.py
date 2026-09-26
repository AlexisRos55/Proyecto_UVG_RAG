from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConversationIntent(Enum):
    """Taxonomía de intenciones del asistente institucional.

    Cerrada a propósito: el dominio es acotado (consultas de estudiantes sobre
    normativa, en español y con mensajes cortos), lo que permite clasificar de
    forma determinista y medible en vez de gastar una llamada al modelo.
    """

    # --- Social: mantiene el canal, no aporta información ---
    GREETING = "greeting"
    FAREWELL = "farewell"
    THANKS = "thanks"
    ACKNOWLEDGEMENT = "acknowledgement"
    SMALL_TALK = "small_talk"
    FRUSTRATION = "frustration"

    # --- Meta: preguntas sobre el propio asistente ---
    IDENTITY = "identity"
    CAPABILITIES = "capabilities"
    DOCUMENT_SCOPE = "document_scope"
    HOW_IT_WORKS = "how_it_works"
    USAGE_HELP = "usage_help"
    PRIVACY = "privacy"

    # --- Dominio real ---
    INSTITUTIONAL_QUERY = "institutional_query"
    FOLLOW_UP = "follow_up"
    # «Continuemos», «¿en qué íbamos?»: retomar el tema activo tras una pausa.
    CONTINUATION = "continuation"

    # --- Navegación documental (ADR-0013): preguntas sobre los documentos
    # como documentos, no sobre un dato dentro de ellos ---
    DOCUMENT_OVERVIEW = "document_overview"
    DOCUMENT_STRUCTURE = "document_structure"
    TOPIC_LOCATION = "topic_location"
    DOCUMENT_ROUTING = "document_routing"
    RELATED_DOCUMENTS = "related_documents"

    # --- Problemático ---
    AMBIGUOUS = "ambiguous"
    NOISE = "noise"
    OUT_OF_DOMAIN = "out_of_domain"
    PERSONAL_DATA = "personal_data"
    PROMPT_INJECTION = "prompt_injection"

    @property
    def needs_retrieval(self) -> bool:
        """Solo el dominio real justifica recuperar documentos y generar."""
        return self in {ConversationIntent.INSTITUTIONAL_QUERY, ConversationIntent.FOLLOW_UP}

    @property
    def is_navigational(self) -> bool:
        """Se responde con el catálogo del corpus, de forma determinista y sin generar."""
        return self in _NAVIGATIONAL


@dataclass(frozen=True, slots=True)
class IntentClassification:
    """Resultado de la clasificación, con su propia confianza.

    Esta confianza es distinta de `VerificationConfidence`: mide cuán seguro está
    el clasificador de haber entendido *qué* se pregunta, no cuán fundamentada
    está la respuesta. Gobierna la regla de seguridad de `ResponsePolicy`.
    """

    intent: ConversationIntent
    confidence: float
    matched_rule: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"La confianza debe estar entre 0.0 y 1.0, recibido: {self.confidence}")


_NAVIGATIONAL = frozenset(
    {
        ConversationIntent.DOCUMENT_OVERVIEW,
        ConversationIntent.DOCUMENT_STRUCTURE,
        ConversationIntent.TOPIC_LOCATION,
        ConversationIntent.DOCUMENT_ROUTING,
        ConversationIntent.RELATED_DOCUMENTS,
    }
)
