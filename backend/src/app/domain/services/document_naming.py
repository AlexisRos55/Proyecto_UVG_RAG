"""Títulos legibles para documentos institucionales.

El título es lo primero que ve el estudiante en una cita y lo que el analizador
de consultas usa para reconocer «el reglamento de grupos estudiantiles». Por
eso se resuelve una sola vez, al indexar, con la mejor fuente disponible.
"""

from __future__ import annotations

import re
import unicodedata

from app.domain.services.spanish_text import fold, sentence_case

# Parte del corpus real llegó con los nombres de archivo corrompidos: bytes CP437
# leídos como MacRoman («Educaci¢n F°sica»). Es la misma tabla, verificada contra
# el corpus, que usa el frontend (frontend/src/shared/lib/document-name.ts).
_MOJIBAKE = {
    "Å": "ü", "Ç": "é", "ê": "É", "ö": "Ü", "†": "á", "°": "í", "¢": "ó",
    "£": "ú", "§": "ñ", "•": "Ñ", "¶": "ª", "ß": "º", "®": "¿", "≠": "¡",
    "Æ": "«", "Ø": "»", "¯": "°",
}
_ACCENTED = re.compile(r"[áéíóúüñÁÉÍÓÚÜÑ]")

_STORAGE_PREFIX = re.compile(r"^[0-9a-f]{32}_")
_EXTENSION = re.compile(r"\.(pdf|docx?|txt|md)$", re.IGNORECASE)
_INSTITUTIONAL_CODE = re.compile(r"^UVG(?:\.[A-Z]{1,4}){1,3}(?:\.\d{2,3})*\s*", re.IGNORECASE)
_VERSION_SUFFIX = re.compile(r"\s*[-–]?\s*\bv(?:ersi[oó]n)?\.?\s*\d+(?:\.\d+)*\s*(?:\([^)]*\))?\s*$", re.IGNORECASE)
_TRAILING_DATE = re.compile(r"\s*\(\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s*\)\s*$")
_PARENTHETICAL_STATUS = re.compile(r"\s*\((?:en\s+aprobaci[oó]n|borrador|draft)\)\s*$", re.IGNORECASE)
_TRAILING_NOISE = re.compile(r"\s+(?:f|final|uvga)\s*$", re.IGNORECASE)
_GENERIC_METADATA = re.compile(r"^(?:microsoft\s+word|untitled|sin\s+t[ií]tulo|documento\d*)\b", re.IGNORECASE)

_TITLE_KEYWORDS = ("reglamento", "normativo", "politica", "manual", "calendario", "codigo", "procedimiento")

# Siglas que deben sobrevivir a la conversión de mayúsculas sostenidas.
KNOWN_ACRONYMS = frozenset(
    {"UVG", "AVE", "PAA", "DGD", "FJBG", "CE", "DAF", "CUAE", "AEUVG", "AESUR", "SIS", "VEA", "CIT", "ITEC", "CEA", "PBX"}
)


def repair_mojibake(name: str) -> str:
    normalized = unicodedata.normalize("NFC", name)
    if not any(glyph in normalized for glyph in _MOJIBAKE) or _ACCENTED.search(normalized):
        return normalized
    return unicodedata.normalize("NFC", "".join(_MOJIBAKE.get(ch, ch) for ch in normalized))


def title_from_filename(filename: str) -> str:
    name = repair_mojibake(filename)
    name = _STORAGE_PREFIX.sub("", name)
    name = _EXTENSION.sub("", name)
    return _polish(_INSTITUTIONAL_CODE.sub("", name))


def resolve_title(
    filename: str,
    embedded_title: str | None = None,
    header_lines: tuple[str, ...] = (),
) -> str:
    """Elige el título con esta preferencia: membrete, metadatos del PDF, nombre de archivo.

    El membrete va primero porque es lo que el propio documento declara ser
    («REGLAMENTO DE GRUPOS ESTUDIANTILES»); los metadatos a veces faltan o son
    genéricos, y el nombre de archivo es el que más ruido arrastra.
    """
    for line in header_lines:
        folded = fold(line)
        if any(keyword in folded for keyword in _TITLE_KEYWORDS) and 8 <= len(line) <= 120:
            return _polish(line)
    if embedded_title and not _GENERIC_METADATA.match(embedded_title.strip()):
        polished = _polish(embedded_title)
        if len(polished) >= 4:
            return polished
    return title_from_filename(filename)


def _polish(raw: str) -> str:
    text = " ".join(raw.replace("_", " ").split())
    for pattern in (_PARENTHETICAL_STATUS, _TRAILING_DATE, _VERSION_SUFFIX, _TRAILING_NOISE):
        text = pattern.sub("", text).strip()
    letters = [ch for ch in text if ch.isalpha()]
    uppercase_share = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0
    # Solo se normaliza la capitalización cuando el título está mayoritariamente
    # en mayúsculas: «Proceso de Admisión e Inscripción» ya viene bien escrito.
    if uppercase_share > 0.5:
        text = sentence_case(text, KNOWN_ACRONYMS)
    return text[:1].upper() + text[1:]
