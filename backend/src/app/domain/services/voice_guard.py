"""Última línea de defensa de la voz institucional: sin llamadas al modelo.

El prompt prohíbe que la respuesta mencione la maquinaria del sistema («los
fragmentos», «la información disponible»), y casi siempre se cumple. Casi: en la
prueba en vivo de la Fase 9 apareció «no especifica los porcentajes en los
fragmentos disponibles». Una regla de prompt es una petición; esto es una
garantía. Solo se retiran o sustituyen fórmulas cerradas, nunca contenido.
"""

from __future__ import annotations

import re
from functools import partial

_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\s+en\s+(?:los|estos)\s+fragmentos(?:\s+(?:disponibles|proporcionados|recuperados|entregados))?", re.IGNORECASE), ""),
    (re.compile(r"\s+en\s+(?:el|este)\s+contexto(?:\s+(?:disponible|proporcionado|recuperado))?", re.IGNORECASE), ""),
    (re.compile(r"\b(?:según|de\s+acuerdo\s+con)\s+(?:los|estos)\s+fragmentos\b", re.IGNORECASE), "según la normativa"),
    (re.compile(r"\b(?:según|de\s+acuerdo\s+con)\s+la\s+información\s+(?:disponible|proporcionada)\b", re.IGNORECASE), "según la normativa"),
    (re.compile(r"\blos\s+documentos\s+recuperados\b", re.IGNORECASE), "la normativa"),
    (re.compile(r"\s*\[\d{1,2}\](?!\()", re.IGNORECASE), ""),
)


# «La normativa no establece…» como primera frase: un asesor empieza por lo que sí aplica.
_NEGATIVE_OPENING = re.compile(
    r"^(?:la\s+normativa|el\s+reglamento|el\s+documento)\s+no\s+|^no\s+(?:hay|existe|existen|puedo|se\s+establece|establece)\b",
    re.IGNORECASE,
)
# El puente que suele seguir («Lo que sí aplica es que…») sobra cuando la frase negativa ya no va delante.
_AFFIRMATIVE_BRIDGE = re.compile(
    r"^(?:lo\s+que\s+s[ií]\s+(?:\w+\s+){1,3}es\s+(?:que\s+)?|sin\s+embargo,\s+|no\s+obstante,\s+|en\s+cambio,\s+)",
    re.IGNORECASE,
)
_REFERRAL = re.compile(r"\b(?:conviene|consult|confirm|verific)", re.IGNORECASE)
_MAX_OPENING_CHARS = 320


def enforce_institutional_voice(text: str) -> str:
    for pattern, replacement in _REWRITES:
        text = pattern.sub(partial(_keep_case, replacement=replacement), text)
    return text


def lead_with_what_applies(text: str) -> str:
    """Mueve al final una primera frase negativa («La normativa no establece…»).

    Solo para preguntas de elección («¿cuál me conviene?»): quien pide una opción
    espera una opción primero. Cuando se pregunta justo por lo que falta («¿cuál
    es el proceso?»), decir que no está es la respuesta directa y va delante.
    El prompt lo pide y el modelo a veces no lo cumple. Solo se reordena: ningún
    contenido se añade ni se quita, salvo el conector que la frase dejaba colgando.
    """
    paragraphs = text.split("\n\n")
    if len(paragraphs) < 3:
        return text
    first, second = paragraphs[0].strip(), paragraphs[1]
    if len(first) > _MAX_OPENING_CHARS or not _NEGATIVE_OPENING.match(first) or first.startswith(("-", "|", "#")):
        return text
    if second.lstrip().startswith(("-", "|", "#", "1.")):
        return text  # empezar por una lista o una tabla sin presentación suena peor
    bridge = _AFFIRMATIVE_BRIDGE.match(second)
    if bridge:
        second = second[bridge.end():]
        second = second[:1].upper() + second[1:]
    rest = [second, *paragraphs[2:]]
    # Lo que falta va al final, pero antes de la recomendación de a dónde acudir.
    position = len(rest) - 1 if _REFERRAL.search(rest[-1]) else len(rest)
    rest.insert(position, first)
    return "\n\n".join(rest)


def _keep_case(match: re.Match[str], *, replacement: str) -> str:
    """Respeta la mayúscula inicial si la fórmula abría la oración."""
    at_sentence_start = match.start() == 0 or match.string[: match.start()].rstrip().endswith((".", "!", "?", ":"))
    if replacement and at_sentence_start and match.group(0)[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement
