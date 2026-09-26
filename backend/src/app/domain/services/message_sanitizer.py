from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MAX_QUESTION_LENGTH = 2000

# Patrones que intentan reescribir las instrucciones del sistema. No se trata de
# bloquear al usuario: se trata de que ese texto no llegue al prompt como si
# fuera una instrucción legítima (NFR-04).
_INJECTION_PATTERNS = (
    re.compile(r"\bignora(?:r|\s+(?:todas\s+)?(?:las\s+)?)?\s*(?:tus\s+)?instruc", re.IGNORECASE),
    re.compile(r"\bolvida(?:r|te)?\s+(?:todo|tus|las)\b", re.IGNORECASE),
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous\s+)?instructions?\b", re.IGNORECASE),
    re.compile(r"\bactúa\s+como\s+(?:si|un|una)\b", re.IGNORECASE),
    re.compile(r"\beres\s+ahora\b", re.IGNORECASE),
    re.compile(r"\bsystem\s*prompt\b", re.IGNORECASE),
    re.compile(r"\bdeveloper\s+mode\b", re.IGNORECASE),
    re.compile(r"^\s*(?:system|assistant|human)\s*:", re.IGNORECASE | re.MULTILINE),
)

# Delimitadores estructurales del prompt. Si el usuario los escribe, dejan de ser
# estructura y pasan a ser texto.
_STRUCTURAL_MARKERS = re.compile(
    r"\[/?Fragmento[^\]]*\]|CONTEXTO RECUPERADO:|FRAGMENTOS OFICIALES:|PREGUNTA DEL ESTUDIANTE:"
    r"|FORMATO DE LA RESPUESTA:|^\s*\[\d{1,3}\]",
    re.MULTILINE,
)

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION_EDGES = re.compile(r"^[¿¡\s.,;:!?]+|[\s.,;:!?]+$")


@dataclass(frozen=True, slots=True)
class SanitizedMessage:
    """Mensaje listo para clasificar y para entrar al prompt.

    `original` conserva el texto tal como lo escribió el estudiante, porque es lo
    que se persiste y se le muestra de vuelta. `normalized` existe solo para
    comparar contra reglas. `safe_for_prompt` es el texto que puede interpolarse
    en el prompt sin que su contenido se confunda con instrucciones.
    """

    original: str
    normalized: str
    safe_for_prompt: str
    has_injection_markers: bool

    @property
    def is_empty(self) -> bool:
        return not self.normalized


class MessageSanitizer:
    """Saneamiento de entrada: primera etapa del agente.

    Cumple NFR-04, que hasta ahora no tenía implementación: la pregunta se
    interpolaba cruda en el prompt y lo único que existía era un límite de
    longitud en el esquema HTTP.
    """

    @staticmethod
    def sanitize(raw_message: str) -> SanitizedMessage:
        original = raw_message.strip()[:MAX_QUESTION_LENGTH]

        has_injection = any(pattern.search(original) for pattern in _INJECTION_PATTERNS)

        # Los marcadores estructurales se neutralizan siempre, haya o no intención:
        # un estudiante podría escribirlos sin malicia y romper el prompt igual.
        safe_for_prompt = _STRUCTURAL_MARKERS.sub("", original).strip()

        return SanitizedMessage(
            original=original,
            normalized=MessageSanitizer.normalize(original),
            safe_for_prompt=safe_for_prompt,
            has_injection_markers=has_injection,
        )

    @staticmethod
    def normalize(text: str) -> str:
        """Forma canónica para comparar: minúsculas, sin acentos ni puntuación de borde.

        Se descartan los acentos a propósito: los estudiantes escriben «que becas
        hay» tanto como «¿qué becas hay?», y las reglas no deben duplicarse por eso.
        """
        lowered = text.lower()
        decomposed = unicodedata.normalize("NFD", lowered)
        without_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
        collapsed = _WHITESPACE.sub(" ", without_accents)
        return _PUNCTUATION_EDGES.sub("", collapsed).strip()
