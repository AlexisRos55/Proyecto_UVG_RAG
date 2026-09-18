from __future__ import annotations

from typing import Protocol

from app.domain.value_objects.conversation_intent import IntentClassification


class IntentClassifierPort(Protocol):
    """Determina qué se le está preguntando al asistente.

    Existe como puerto y no como función suelta para poder sustituir la
    estrategia sin tocar el caso de uso (ADR-0001). La implementación actual es
    determinista por decisión de diseño: una basada en modelo costaría una
    llamada por consulta —chocando con ADR-0005 y NFR-02— y sería irreproducible,
    lo que impediría reportar precisión y exhaustividad sobre un conjunto
    etiquetado.
    """

    def classify(self, normalized_message: str) -> IntentClassification:
        """Clasifica un mensaje ya saneado y normalizado.

        Nunca lanza: ante un mensaje que no encaja en ninguna regla debe devolver
        `INSTITUTIONAL_QUERY` con confianza baja, de modo que la política enrute
        hacia el comportamiento actual en lugar de hacia una respuesta enlatada.
        """
        ...
