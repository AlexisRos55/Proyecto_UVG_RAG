from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.value_objects.conversation_intent import ConversationIntent

if TYPE_CHECKING:  # pragma: no cover - solo para tipado
    from collections.abc import Sequence

    from app.domain.entities.message import Message


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Memoria de sesión: estado de la conversación, nunca su contenido.

    Se *deriva* de los mensajes ya persistidos, de modo que no requiere tabla ni
    migración nuevas. Ninguno de estos campos entra jamás en el prompt de
    generación: inyectar historial permitiría al modelo fundamentar una
    afirmación en su propia salida anterior en lugar de en un documento, y la
    verificación no podría distinguirlo.
    """

    already_introduced: bool = False
    last_intent: ConversationIntent | None = None
    last_resolved_query: str | None = None
    topic_documents: tuple[str, ...] = ()
    consecutive_abstentions: int = 0
    turn_count: int = 0

    @property
    def is_first_turn(self) -> bool:
        return self.turn_count == 0

    @property
    def is_struggling(self) -> bool:
        """Dos abstenciones seguidas sugieren que el problema es cómo se pregunta."""
        return self.consecutive_abstentions >= 2

    @classmethod
    def from_messages(cls, messages: Sequence[Message]) -> ConversationContext:
        """Reconstruye el estado a partir del historial persistido.

        Deliberadamente no almacena el texto de las respuestas: solo la última
        pregunta del estudiante (para resolver referencias con sus propias
        palabras) y los documentos citados (para la noción de tema actual).
        """
        from app.domain.entities.message import MessageRole

        student_messages = [m for m in messages if m.role == MessageRole.STUDENT]
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]

        consecutive_abstentions = 0
        for message in reversed(assistant_messages):
            if message.is_grounded is False:
                consecutive_abstentions += 1
            else:
                break

        topic_documents: tuple[str, ...] = ()
        for message in reversed(assistant_messages):
            if message.is_grounded and message.source_document_names:
                topic_documents = tuple(message.source_document_names)
                break

        return cls(
            already_introduced=len(assistant_messages) > 0,
            last_intent=None,
            last_resolved_query=student_messages[-1].content if student_messages else None,
            topic_documents=topic_documents,
            consecutive_abstentions=consecutive_abstentions,
            turn_count=len(student_messages),
        )
