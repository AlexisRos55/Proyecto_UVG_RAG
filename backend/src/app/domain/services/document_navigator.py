"""Respuestas sobre los documentos como documentos (ADR-0013).

«¿De qué trata este reglamento?», «¿cuáles son sus capítulos?», «¿dónde habla
de becas?», «¿qué documento debo consultar?». Ninguna de estas preguntas pide
un dato dentro de un fragmento: piden conocer el corpus. Responderlas con
recuperación por similitud y un modelo generativo sería caro e impreciso —el
modelo solo vería diez fragmentos sueltos y tendría que adivinar la estructura—;
responderlas con el índice documental es exacto, citable y no cuesta tokens.

Este servicio es puro: recibe índices y resultados de búsqueda ya obtenidos y
devuelve texto y fuentes. No consulta nada por su cuenta.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.domain.entities.chunk import RetrievedChunk
from app.domain.services.spanish_text import analyze, fold
from app.domain.value_objects.document_facts import DocumentKind
from app.domain.value_objects.document_outline import DocumentOutline, OutlineDivision
from app.domain.value_objects.source_reference import SourceReference

_MAX_LOCATIONS = 8
_MAX_ROUTED_DOCUMENTS = 4
_MAX_LISTED_ARTICLES = 45
# Sin «:»: en el calendario «5 de septiembre: Feria de becas» es una sola unidad.
_SENTENCE = re.compile(r"(?<=[.;!?])\s+|\n")
_KIND_ORDER = {
    DocumentKind.REGULATION: 0,
    DocumentKind.PROCESS: 1,
    DocumentKind.CALENDAR: 2,
    DocumentKind.PROGRAM: 3,
    DocumentKind.GENERAL: 4,
}


@dataclass(frozen=True, slots=True)
class NavigationAnswer:
    text: str
    sources: tuple[SourceReference, ...] = field(default_factory=tuple)
    is_grounded: bool | None = True


class DocumentNavigator:
    def __init__(self, outlines: Sequence[DocumentOutline], filenames: Mapping[UUID, str]) -> None:
        self._outlines = {outline.document_id: outline for outline in outlines}
        self._filenames = filenames

    # --- Selección del documento -------------------------------------------------

    def ask_which_document(self, lead: str | None = None) -> NavigationAnswer:
        """Cuando la pregunta alude a «el documento» sin decir cuál."""
        titles = self._distinct_titles()
        if not titles:
            return NavigationAnswer(
                "Todavía no hay documentos cargados, así que aún no puedo describir ninguno.",
                is_grounded=None,
            )
        listing = "\n".join(f"- {title}" for title in titles[:12])
        intro = lead or "¿Sobre cuál documento? Estos son los que consulto:"
        return NavigationAnswer(f"{intro}\n\n{listing}", is_grounded=None)

    # --- Descripción y estructura -----------------------------------------------

    def describe(self, document_id: UUID) -> NavigationAnswer:
        outline = self._outlines[document_id]
        parts = [self._title_line(outline)]
        if outline.summary:
            origin = "su Artículo 1" if outline.has_structure else "su presentación"
            parts.append(f"Según {origin}: «{outline.summary}»")
        chapters = [d for d in outline.divisions if d.articles]
        if chapters:
            parts.append(
                f"Se organiza en {self._count(len(chapters), 'capítulo')} y "
                f"{self._count(outline.article_count, 'artículo')}. Sus temas principales son:\n\n"
                + "\n".join(f"- {self._division_theme(d)}" for d in chapters)
            )
            extras = [d.label for d in outline.divisions if not d.articles]
            if extras:
                parts.append("Incluye además: " + ", ".join(extras) + ".")
        elif outline.keywords:
            parts.append("Trata principalmente sobre: " + ", ".join(outline.keywords[:6]) + ".")
        parts.append(
            "Si quieres, te explico cualquiera de estos temas o busco algo concreto dentro del documento."
        )
        return NavigationAnswer("\n\n".join(parts), sources=(self._document_source(outline),))

    def outline(self, document_id: UUID) -> NavigationAnswer:
        outline = self._outlines[document_id]
        chapters = [d for d in outline.divisions if d.articles]
        if not chapters:
            return self.describe(document_id)

        lines: list[str] = []
        list_articles = outline.article_count <= _MAX_LISTED_ARTICLES
        for index, division in enumerate(chapters, start=1):
            first, last = division.articles[0].number, division.articles[-1].number
            span = f"artículo {first}" if first == last else f"artículos {first} a {last}"
            page = f", pág. {division.page_start}" if division.page_start else ""
            lines.append(f"{index}. **{division.label}** ({span}{page})")
            if list_articles:
                lines.extend(f"   - {article.label}" for article in division.articles)
        extras = [d for d in outline.divisions if not d.articles]
        tail = (
            "\n\nAl final incluye: " + ", ".join(
                f"{d.label}" + (f" (pág. {d.page_start})" if d.page_start else "") for d in extras
            ) + "."
            if extras
            else ""
        )
        closing = (
            ""
            if list_articles
            else "\n\n¿Quieres que te detalle los artículos de alguno de estos capítulos?"
        )
        text = (
            f"El **{outline.title}** tiene {self._count(len(chapters), 'capítulo')} y "
            f"{self._count(outline.article_count, 'artículo')}:\n\n" + "\n".join(lines) + tail + closing
        )
        return NavigationAnswer(text, sources=(self._document_source(outline),))

    def relate(
        self, document_id: UUID, related: Sequence[tuple[DocumentOutline, tuple[str, ...]]]
    ) -> NavigationAnswer:
        outline = self._outlines[document_id]
        if not related:
            return NavigationAnswer(
                f"No encontré otros documentos que traten los mismos temas que el **{outline.title}**.",
                sources=(self._document_source(outline),),
            )
        lines = [
            f"- **{other.title}** — comparten temas como {', '.join(terms[:3])}."
            if terms
            else f"- **{other.title}**"
            for other, terms in related
        ]
        text = f"Relacionados con el **{outline.title}**:\n\n" + "\n".join(lines)
        sources = (self._document_source(outline), *(self._document_source(other) for other, _ in related))
        return NavigationAnswer(text, sources=sources)

    # --- Localización y enrutamiento ---------------------------------------------

    def locate(self, topic: str, hits: Sequence[RetrievedChunk], clarify: bool = False) -> NavigationAnswer:
        """Dónde trata la normativa un tema, apartado por apartado."""
        if not hits:
            return self._nothing_found(topic)
        label = topic or "ese tema"
        grouped = self._group_by_document(hits)
        blocks: list[str] = []
        sources: list[SourceReference] = []
        shown = 0
        for outline, items in grouped:
            lines: list[str] = []
            for item in items:
                if shown >= _MAX_LOCATIONS:
                    break
                lines.append(f"- {self._location_line(item, topic)}")
                sources.append(self._chunk_source(item))
                shown += 1
            if lines:
                blocks.append(f"**{outline.title}**\n" + "\n".join(lines))

        lead = (
            f"«{label[:1].upper()}{label[1:]}» aparece en varios apartados de la normativa. Lo principal:"
            if clarify
            else f"La normativa trata **{label}** en estos apartados:"
        )
        suggestions = self._suggestions(hits) if clarify else []
        closing = (
            "¿Qué te interesa saber? Por ejemplo: " + ", ".join(f"«{s}»" for s in suggestions) + "."
            if suggestions
            else "Pregúntame por cualquiera de ellos y te explico qué establece."
        )
        text = f"{lead}\n\n" + "\n\n".join(blocks) + f"\n\n{closing}"
        return NavigationAnswer(text, sources=self._dedupe(sources))

    def route(self, topic: str, hits: Sequence[RetrievedChunk]) -> NavigationAnswer:
        """Qué documento consultar para un tema, empezando por el que más lo regula."""
        if not hits:
            return self._nothing_found(topic)
        label = topic or "ese tema"
        grouped = self._group_by_document(hits)[:_MAX_ROUTED_DOCUMENTS]
        primary_outline, primary_items = grouped[0]
        focus = self._focus(primary_items)
        text = f"Para **{label}**, el documento de referencia es el **{primary_outline.title}**"
        text += f": lo trata en {focus}." if focus else "."
        sources = [self._document_source(primary_outline)]
        if len(grouped) > 1:
            others = []
            for outline, items in grouped[1:]:
                detail = self._focus(items) or self._snippet(items[0], topic)
                others.append(f"- **{outline.title}**" + (f" — {detail}" if detail else ""))
                sources.append(self._document_source(outline))
            text += "\n\nTambién lo mencionan:\n\n" + "\n".join(others)
        text += "\n\nSi me dices qué necesitas saber exactamente, te respondo con lo que establece."
        return NavigationAnswer(text, sources=self._dedupe(sources))

    # --- Auxiliares -----------------------------------------------------------------

    def _group_by_document(
        self, hits: Sequence[RetrievedChunk]
    ) -> list[tuple[DocumentOutline, list[RetrievedChunk]]]:
        """Agrupa por documento (fusionando duplicados con el mismo título) en orden de relevancia."""
        order: list[str] = []
        groups: dict[str, tuple[DocumentOutline, list[RetrievedChunk], float]] = {}
        for rank, item in enumerate(hits):
            outline = self._outlines.get(item.chunk.document_id)
            if outline is None:
                continue
            key = fold(outline.title)
            if key not in groups:
                order.append(key)
                groups[key] = (outline, [], 0.0)
            current_outline, items, score = groups[key]
            # Aportación decreciente dentro de cada documento (1, ½, ¼…): un
            # documento con muchas menciones de paso no debe superar al que
            # trata el tema en su mejor fragmento. Medido en el corpus: por
            # «graduación», el reglamento de becas (gastos de graduación) ganaba
            # al calendario (ceremonia de graduación).
            weight = (1.0 / (rank + 1)) * (0.5 ** len(items))
            if not any(self._same_location(item, other) for other in items):
                items.append(item)
            groups[key] = (current_outline, items, score + weight)
        ranked = sorted(order, key=lambda key: groups[key][2], reverse=True)
        return [(groups[key][0], groups[key][1]) for key in ranked]

    @staticmethod
    def _same_location(left: RetrievedChunk, right: RetrievedChunk) -> bool:
        a, b = left.chunk.anchor, right.chunk.anchor
        if a is None or b is None:
            return left.chunk.text == right.chunk.text
        return a.citation_label == b.citation_label and a.citation_label is not None

    def _location_line(self, item: RetrievedChunk, topic: str) -> str:
        anchor = item.chunk.anchor
        location = anchor.citation_label if anchor else None
        page = anchor.page_label if anchor else None
        if location:
            return f"{location}" + (f" ({page})" if page else "")
        snippet = self._snippet(item, topic)
        return f"«{snippet}»" + (f" ({page})" if page else "")

    @staticmethod
    def _snippet(item: RetrievedChunk, topic: str) -> str:
        """La oración del fragmento que contiene el tema, recortada."""
        terms = set(analyze(topic))
        sentences = [s.strip() for s in _SENTENCE.split(item.chunk.text) if len(s.strip()) > 12]
        if not sentences:
            return ""
        best = max(sentences, key=lambda sentence: len(terms & set(analyze(sentence))))
        return best if len(best) <= 110 else best[:107].rsplit(" ", 1)[0] + "…"

    @staticmethod
    def _focus(items: Sequence[RetrievedChunk]) -> str:
        """Dónde se concentra un tema: «los artículos 17 (Cobertura) y 18 (Condiciones)»."""
        articles: dict[int, str | None] = {}
        chapter: str | None = None
        for item in items:
            anchor = item.chunk.anchor
            if anchor is None:
                continue
            chapter = chapter or anchor.chapter
            if anchor.article_from is not None and anchor.article_from not in articles:
                single = anchor.article_to in (None, anchor.article_from)
                articles[anchor.article_from] = anchor.article_title if single else None
            if len(articles) == 3:
                break
        if not articles:
            return chapter or ""
        described = [f"{number} ({title})" if title else str(number) for number, title in articles.items()]
        if len(described) == 1:
            return f"el artículo {described[0]}"
        return "los artículos " + ", ".join(described[:-1]) + " y " + described[-1]

    @staticmethod
    def _suggestions(hits: Sequence[RetrievedChunk]) -> list[str]:
        """Subtemas reales del corpus (títulos de artículo), no sugerencias genéricas."""
        seen: list[str] = []
        for item in hits:
            anchor = item.chunk.anchor
            title = anchor.article_title if anchor else None
            if title and title.lower() not in (s.lower() for s in seen) and len(title) <= 40:
                seen.append(title.lower())
            if len(seen) == 4:
                break
        return seen

    def _nothing_found(self, topic: str) -> NavigationAnswer:
        label = f"«{topic}»" if topic else "ese tema"
        return NavigationAnswer(
            f"No encontré {label} en los documentos oficiales que consulto. "
            "Si lo escribes de otra forma, lo busco de nuevo.",
            is_grounded=False,
        )

    def _title_line(self, outline: DocumentOutline) -> str:
        facts = outline.facts
        details = [part for part in (facts.code, f"versión {facts.version}" if facts.version else None) if part]
        suffix = f" ({', '.join(details)})" if details else ""
        pages = f", {facts.page_count} páginas" if facts.page_count else ""
        return f"**{outline.title}**{suffix} — {outline.kind.label.lower()}{pages}."

    @staticmethod
    def _division_theme(division: OutlineDivision) -> str:
        first, last = division.articles[0].number, division.articles[-1].number
        span = f"art. {first}" if first == last else f"arts. {first}–{last}"
        return f"{division.label} ({span})"

    def _document_source(self, outline: DocumentOutline) -> SourceReference:
        return SourceReference(
            document_name=self._filenames.get(outline.document_id, outline.title),
            document_id=outline.document_id,
            document_title=outline.title,
        )

    def _chunk_source(self, item: RetrievedChunk) -> SourceReference:
        outline = self._outlines.get(item.chunk.document_id)
        return SourceReference.at(
            document_name=self._filenames.get(item.chunk.document_id, outline.title if outline else ""),
            document_id=item.chunk.document_id,
            document_title=outline.title if outline else None,
            anchor=item.chunk.anchor,
        )

    def _distinct_titles(self) -> list[str]:
        unique: dict[str, DocumentOutline] = {}
        for outline in self._outlines.values():
            unique.setdefault(fold(outline.title), outline)
        ordered = sorted(unique.values(), key=lambda o: (_KIND_ORDER[o.kind], o.title))
        return [outline.title for outline in ordered]

    @staticmethod
    def _dedupe(sources: Sequence[SourceReference]) -> tuple[SourceReference, ...]:
        unique: dict[tuple[str, str, int | None], SourceReference] = {}
        for source in sources:
            unique.setdefault(source.dedup_key, source)
        return tuple(unique.values())

    @staticmethod
    def _count(value: int, noun: str) -> str:
        return f"{value} {noun}{'' if value == 1 else 's'}"
