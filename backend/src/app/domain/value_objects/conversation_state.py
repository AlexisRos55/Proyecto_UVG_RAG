from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from app.domain.value_objects.corpus_entity import CorpusEntity


@dataclass(frozen=True, slots=True)
class ConversationState:
    """Lo que la conversación tiene «sobre la mesa» antes del turno actual.

    No es memoria del texto: es el foco. Tema activo, entidad activa (la beca,
    la instancia), aspecto preguntado, documentos y artículo dominantes. Todo se
    **deriva** reproduciendo los mensajes persistidos (`ConversationTracker.replay`),
    así que no requiere tabla ni migración y dos ejecuciones sobre la misma
    conversación producen siempre el mismo estado.

    Como `ConversationContext`, nada de esto entra al prompt como afirmación:
    solo orienta qué se busca y cómo se interpreta la pregunta.
    """

    topic: str | None = None
    entity: CorpusEntity | None = None
    aspect: str | None = None
    documents: tuple[UUID, ...] = ()
    article: int | None = None
    campus: str | None = None
    # Carrera mencionada («Ingeniería»): califica las preguntas siguientes.
    career: str | None = None
    last_query: str | None = None
    last_grounded: bool | None = None
    covered_aspects: tuple[str, ...] = ()
    # Entidades nombradas en la última respuesta: candidatas para «esa».
    candidates: tuple[CorpusEntity, ...] = ()
    # La última pregunta pedía un «cuál es más/mejor»: «esa» es la señalada primero.
    ranked: bool = False
    # Memoria de corto plazo, como la de una persona: lo último que preguntó el
    # estudiante (para «¿quién la da?»), las entidades de las que se habló
    # (para «esa beca de antes», «esa oficina») y la comparación en curso.
    last_message: str | None = None
    recent_entities: tuple[CorpusEntity, ...] = ()
    compared: tuple[CorpusEntity, ...] = ()
    # La última lista de opciones que se le dio (para «la primera», «la otra»).
    options: tuple[CorpusEntity, ...] = ()
    # El último intercambio fue social o una pausa: «sigamos» retoma; si no, continúa.
    paused: bool = False
    # Quién escribe cuando no es un estudiante («padre de familia», «docente»…).
    audience: str | None = None
    # Aspectos que la última respuesta ofreció explicar, en orden («Si quieres, también
    # puedo explicarte la cobertura o cómo se solicita»): para «sí», «no» y «la primera».
    offered: tuple[tuple[str, str], ...] = ()

    @property
    def has_focus(self) -> bool:
        return bool(self.topic or self.entity or self.documents)


class TurnMode(str, Enum):
    NEW = "new"                    # pregunta autosuficiente (puede cambiar de tema)
    FOLLOW_UP = "follow_up"        # depende del foco activo («¿cuánto cubre esa?»)
    DEEPEN = "deepen"              # «profundiza», «explícalo mejor»
    RESUME = "resume"              # «continuemos» tras una pausa
    ARTICLE_STEP = "article_step"  # «¿y el siguiente?»


@dataclass(frozen=True, slots=True)
class TurnInterpretation:
    """Cómo entiende el sistema el turno actual antes de buscar.

    `retrieval_query` es la consulta interna optimizada; el mensaje del
    estudiante (`message`) nunca se modifica. `reading` es una glosa breve de la
    interpretación («se refiere a la Beca Despega; pregunta por la cobertura»)
    que acompaña a la pregunta literal en el prompt.
    """

    message: str
    mode: TurnMode
    retrieval_query: str
    reading: str | None = None
    topic: str | None = None
    entity: CorpusEntity | None = None
    aspect: str | None = None
    campus: str | None = None
    career: str | None = None
    article_numbers: tuple[int, ...] = ()
    expansions: tuple[str, ...] = ()
    focus_terms: tuple[str, ...] = ()
    aspect_title_words: tuple[str, ...] = ()
    is_overview: bool = False
    wants_example: bool = False
    # «No entiendo»: la explicación anterior se repite con palabras más sencillas.
    simpler: bool = False
    # El estudiante está desorientado («estoy perdido»): se le orienta, no se busca.
    needs_orientation: bool = False
    # Entidades que se comparan en este turno; cada una se busca por separado.
    compared: tuple[CorpusEntity, ...] = ()
    sub_queries: tuple[str, ...] = ()
    # Una referencia sin nada a qué referirse («¿y eso?» al empezar): se pregunta.
    needs_clarification: bool = False
    # «¿Puedes resumir?»: lo último dicho, en corto.
    wants_summary: bool = False
    # «Continúa»: seguir explicando lo mismo, con lo que faltó.
    continues: bool = False
    audience: str | None = None
    # Cómo se siente quien escribe («angustia», «alegria»): cambia el tono, no la búsqueda.
    mood: str | None = None
    # «Ese reglamento»: la pregunta es sobre el documento en consulta.
    document_reference: bool = False
    # «¿Y allí qué dice de los requisitos?»: se busca dentro del documento en consulta.
    within_document: bool = False
    # «Sí» a un ofrecimiento concreto: se responde lo ofrecido aunque el mensaje sea un acuse.
    accepts_offer: bool = False
    resolution: str = ""
    candidates: tuple[CorpusEntity, ...] = field(default_factory=tuple)
    # Raíces que la evidencia de un seguimiento debe contener (anclaje al tema).
    required_terms: tuple[str, ...] = ()
    # Artículos que definen las entidades del tema: la mejor entrada a un panorama.
    defining_articles: tuple[tuple[UUID, int], ...] = ()
    topic_terms: tuple[str, ...] = ()

    @property
    def depends_on_context(self) -> bool:
        return self.mode is not TurnMode.NEW
