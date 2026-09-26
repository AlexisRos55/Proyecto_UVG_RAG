from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.domain.services.document_naming import KNOWN_ACRONYMS
from app.domain.services.spanish_text import fold, sentence_case
from app.domain.value_objects.section_anchor import SectionAnchor

_CHAPTER = re.compile(
    r"^(cap[ií]tulo|t[ií]tulo)\s+([IVXLC]+|\d+)\b\s*[.:\-–]?\s*(.*)$", re.IGNORECASE
)
# El separador tras el número es obligatorio: distingue el encabezado
# «Artículo 5. Retiro» de una referencia en prosa («Artículo 5 del reglamento…»).
_ARTICLE = re.compile(r"^art[ií]culo\s+(\d{1,3})\s*[.:\-–]\s*(.*)$", re.IGNORECASE)
_ENUMERATOR_ONLY = re.compile(r"^(?:[•o\-–·▪◦]|[a-zA-Z]\.|\d{1,2}[.)]|[ivx]{1,4}\.)$")
# Sin «o » como viñeta: en un renglón partido suele ser la conjunción. Las
# entradas de calendario («17 de agosto: …») también abren línea propia.
_STARTS_ENUMERATION = re.compile(
    r"^(?:[•\-–·▪◦]\s|[a-zA-Z][.)]\s|\d{1,2}[.)]\s|[ivx]{1,4}\.\s"
    r"|\d{1,2}(?:\s*-\s*\d{1,2})?\s+de\s+[a-záéíóú]+(?:\s+de\s+\d{4})?:)"
)
_TERMINATOR = re.compile(r"[.:;!?]$")
_WHITESPACE = re.compile(r"[ \t ]+")
_NAMED_SECTIONS = frozenset(
    {
        "control de cambios",
        "definiciones",
        "considerandos",
        "disposiciones transitorias",
        "disposiciones finales",
        "anexos",
        "glosario",
        "exclusiones",
        "cobertura",
    }
)
# Secciones que pertenecen al documento entero y no al último capítulo abierto.
_DOCUMENT_LEVEL_SECTIONS = frozenset({"control de cambios", "anexos", "glosario"})


@dataclass(slots=True)
class _Line:
    """Línea lógica. `breaks` marca dónde cambia de página dentro de la línea:
    una oración que cruza un salto de página debe citar ambas páginas."""

    text: str
    page: int
    breaks: list[tuple[int, int]] = field(default_factory=list)

    def append(self, fragment: str, page: int, joiner: str) -> None:
        if page != (self.breaks[-1][1] if self.breaks else self.page):
            self.breaks.append((len(self.text) + len(joiner), page))
        self.text = f"{self.text}{joiner}{fragment}"

    @property
    def last_page(self) -> int:
        return self.breaks[-1][1] if self.breaks else self.page


@dataclass(slots=True)
class StructuralUnit:
    """Una unidad con sentido propio —un artículo, una sección— y sus páginas.

    `line_offsets` guarda dónde empieza cada línea lógica dentro de `text` y en
    qué página estaba, para que al partir una unidad larga cada trozo pueda
    citar su propia página y no la de todo el artículo.
    """

    anchor: SectionAnchor
    text: str
    line_offsets: list[tuple[int, int]] = field(default_factory=list)

    def pages_for_span(self, start: int, end: int) -> tuple[int | None, int | None]:
        pages = [
            page
            for index, (offset, page) in enumerate(self.line_offsets)
            if offset < end
            and (index + 1 == len(self.line_offsets) or self.line_offsets[index + 1][0] > start)
        ]
        if not pages:
            return self.anchor.page_start, self.anchor.page_end
        return min(pages), max(pages)


class DocumentStructureParser:
    """Reconstruye la jerarquía capítulo → sección → artículo de un documento normativo.

    Es deliberadamente conservador: solo reconoce como encabezado lo que tiene
    una forma inequívoca (numeración de capítulo o artículo, mayúsculas
    sostenidas, títulos normativos conocidos). Un documento sin estructura
    —un folleto, un calendario— no se fuerza: sale como unidades por página,
    que siguen siendo citables por número de página.
    """

    def parse(self, pages: tuple[str, ...]) -> list[StructuralUnit]:
        lines = self._reflow(pages)
        has_articles = any(_ARTICLE.match(line.text) for line in lines)

        units: list[StructuralUnit] = []
        chapter: str | None = None
        section: str | None = None
        article: int | None = None
        article_title: str | None = None
        buffer: list[_Line] = []
        expecting_chapter_title = False

        def flush() -> None:
            text_lines = [line for line in buffer if line.text]
            if not text_lines:
                buffer.clear()
                return
            offsets: list[tuple[int, int]] = []
            cursor = 0
            for line in text_lines:
                offsets.append((cursor, line.page))
                offsets.extend((cursor + relative, page) for relative, page in line.breaks)
                cursor += len(line.text) + 1
            pages_seen = [page for _, page in offsets]
            units.append(
                StructuralUnit(
                    anchor=SectionAnchor(
                        chapter=chapter,
                        section=section,
                        article_from=article,
                        article_title=article_title,
                        page_start=min(pages_seen),
                        page_end=max(pages_seen),
                    ),
                    text="\n".join(line.text for line in text_lines),
                    line_offsets=offsets,
                )
            )
            buffer.clear()

        chapter_title_lines = 0
        last_title_length = 0
        for index, line in enumerate(lines):
            chapter_match = _CHAPTER.match(line.text)
            if chapter_match and self._is_mistyped_article(chapter_match, article):
                # Errata del propio documento: «Capítulo 35. Procedimiento. Las
                # solicitudes…» justo después del Artículo 34. Tratarlo como
                # capítulo borraría el capítulo real de todos los artículos siguientes.
                flush()
                article = int(chapter_match.group(2))
                article_title = self._article_title(chapter_match.group(3))
                buffer.append(_Line(f"Artículo {article}. {chapter_match.group(3)}", line.page))
                continue
            if chapter_match:
                flush()
                word = "Capítulo" if fold(chapter_match.group(1)).startswith("cap") else "Título"
                chapter = f"{word} {chapter_match.group(2).upper()}"
                rest = chapter_match.group(3).strip(" .:-–")
                if rest:
                    chapter = f"{chapter}. {self._heading_case(rest)}"
                expecting_chapter_title = not rest
                chapter_title_lines = 0
                section, article, article_title = None, None, None
                continue

            # Un título de capítulo puede ocupar dos renglones en mayúsculas, pero
            # solo se continúa si el primero es largo: si no, el segundo renglón
            # en mayúsculas es una sección, no la cola del título.
            wraps = chapter_title_lines == 0 or (chapter_title_lines == 1 and last_title_length >= 45)
            if expecting_chapter_title and wraps and self._is_upper_heading(line.text):
                heading = self._heading_case(line.text)
                if chapter_title_lines == 0:
                    chapter = f"{chapter}. {heading}"
                else:
                    chapter = f"{chapter} {heading[:1].lower()}{heading[1:]}"
                chapter_title_lines += 1
                last_title_length = len(line.text)
                continue
            expecting_chapter_title = False

            article_match = _ARTICLE.match(line.text)
            if article_match:
                flush()
                article = int(article_match.group(1))
                article_title = self._article_title(article_match.group(2))
                buffer.append(line)
                continue

            if self._is_section_heading(line.text, has_articles, lines, index):
                flush()
                if fold(line.text).strip(" .:") in _DOCUMENT_LEVEL_SECTIONS:
                    chapter = None
                section = self._heading_case(line.text.rstrip("."))
                article, article_title = None, None
                continue

            buffer.append(line)

        flush()
        return units

    # --- Reconstrucción de líneas lógicas ----------------------------------------

    def _reflow(self, pages: tuple[str, ...]) -> list[_Line]:
        """Une las líneas físicas del PDF en líneas lógicas.

        PyMuPDF devuelve una línea por renglón visual: una oración de tres
        renglones llega partida en tres, y una viñeta llega como «•» en una línea
        y su texto en la siguiente. Sin esta reconstrucción, cada salto de línea
        corta una frase por la mitad en el fragmento y en el embedding.
        """
        logical: list[_Line] = []
        pending_marker: str | None = None
        for page_number, page in enumerate(pages, start=1):
            for raw in unicodedata.normalize("NFKC", page).splitlines():
                text = _WHITESPACE.sub(" ", raw).strip()
                if not text:
                    continue
                if _ENUMERATOR_ONLY.match(text):
                    pending_marker = text
                    continue
                if pending_marker:
                    text = f"{pending_marker} {text}"
                    pending_marker = None
                    logical.append(_Line(text, page_number))
                    continue
                if logical and self._continues(logical[-1].text, text):
                    previous = logical[-1]
                    if previous.text.endswith("-") and previous.text[-2:-1].isalpha() and text[:1].islower():
                        previous.text = previous.text[:-1]
                        previous.append(text, page_number, "")
                    else:
                        previous.append(text, page_number, " ")
                    continue
                logical.append(_Line(text, page_number))
        return logical

    def _continues(self, previous: str, current: str) -> bool:
        """Una línea continúa la anterior salvo que algo marque un corte lógico."""
        starts_new_unit = bool(
            _CHAPTER.match(current) or _ARTICLE.match(current) or _STARTS_ENUMERATION.match(current)
        )
        return not (
            _TERMINATOR.search(previous)
            or starts_new_unit
            or self._is_heading_line(previous)
            or self._is_heading_line(current)
        )

    def _is_heading_line(self, text: str) -> bool:
        return self._is_upper_heading(text) or fold(text).strip(" .:") in _NAMED_SECTIONS

    # --- Reconocimiento de encabezados -------------------------------------------

    @staticmethod
    def _is_upper_heading(text: str) -> bool:
        letters = [ch for ch in text if ch.isalpha()]
        if len(letters) < 8 or len(text) > 140:
            return False
        return sum(ch.isupper() for ch in letters) / len(letters) >= 0.85

    def _is_section_heading(
        self, text: str, has_articles: bool, lines: list[_Line], index: int
    ) -> bool:
        folded = fold(text).strip(" .:")
        if folded in _NAMED_SECTIONS:
            return True
        if self._is_upper_heading(text) and len(text.split()) >= 2:
            return True
        # «Titulillos» de documentos sin articulado («Beca Deportiva.» seguido de
        # su párrafo). En un reglamento con artículos esta forma sería una
        # oración corta cualquiera, así que ahí no se aplica.
        if has_articles or index + 1 >= len(lines):
            return False
        words = text.rstrip(".").split()
        return (
            text.endswith(".")
            and 1 <= len(words) <= 6
            and text[:1].isupper()
            and not any(ch.isdigit() for ch in text)
            and len(lines[index + 1].text) > len(text)
        )

    @staticmethod
    def _is_mistyped_article(match: re.Match[str], current_article: int | None) -> bool:
        number = match.group(2)
        return (
            current_article is not None
            and number.isdigit()
            and int(number) == current_article + 1
            and len(match.group(3)) > 60
        )

    @staticmethod
    def _article_title(rest: str) -> str | None:
        """«Condiciones. Para mantener…» → «Condiciones»; «Definiciones» → «Definiciones»."""
        rest = rest.strip()
        if not rest:
            return None
        match = re.match(r"^([^.:]{2,80})[.:](?:\s|$)", rest)
        candidate = match.group(1) if match else (rest if len(rest) <= 80 else None)
        if candidate is None or len(candidate.split()) > 10:
            return None
        return DocumentStructureParser._heading_case(candidate.strip())

    @staticmethod
    def _heading_case(text: str) -> str:
        letters = [ch for ch in text if ch.isalpha()]
        if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.6:
            return sentence_case(text, KNOWN_ACRONYMS)
        return text[:1].upper() + text[1:]
