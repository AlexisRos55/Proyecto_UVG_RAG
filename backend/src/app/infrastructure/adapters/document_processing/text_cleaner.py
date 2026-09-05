from __future__ import annotations

import re


class RegexTextCleaner:
    """Removes common PDF-extraction artifacts from raw text (FR-02).

    Not behind a port: it has no external technology dependency to swap, it is a
    pure, deterministic transformation grouped here for pipeline cohesion (see
    infrastructure/adapters/document_processing/README.md).
    """

    _MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
    _TRAILING_WHITESPACE = re.compile(r"[ \t]+\n")
    _PAGE_NUMBER_LINE = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$", re.MULTILINE)
    _HYPHENATED_LINEBREAK = re.compile(r"(\w)-\n(\w)")
    _MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")

    def clean(self, raw_text: str) -> str:
        text = self._HYPHENATED_LINEBREAK.sub(r"\1\2", raw_text)
        text = self._PAGE_NUMBER_LINE.sub("", text)
        text = self._TRAILING_WHITESPACE.sub("\n", text)
        text = self._MULTIPLE_SPACES.sub(" ", text)
        text = self._MULTIPLE_BLANK_LINES.sub("\n\n", text)
        return text.strip()
