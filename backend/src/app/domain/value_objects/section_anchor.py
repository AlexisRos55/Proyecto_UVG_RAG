from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SectionAnchor:
    """Ubicación de un fragmento dentro de la estructura de su documento.

    Es lo que convierte una cita de «reglamento.pdf» en «Reglamento de ayudas
    financieras · Capítulo IV · Artículo 18. Condiciones · pág. 10». Todos los
    campos son opcionales porque no todos los documentos tienen artículos: un
    folleto informativo solo tiene páginas, y eso también es una ubicación.

    Las páginas son las del archivo PDF (1 = primera hoja), no las impresas en
    el pie: son las que cualquier visor muestra y, por tanto, las verificables.
    """

    chapter: str | None = None
    section: str | None = None
    article_from: int | None = None
    article_to: int | None = None
    article_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None

    def __post_init__(self) -> None:
        if self.article_to is not None and self.article_from is None:
            raise ValueError("article_to requiere article_from")
        if (
            self.article_from is not None
            and self.article_to is not None
            and self.article_to < self.article_from
        ):
            raise ValueError("El rango de artículos está invertido")
        if self.page_start is not None and self.page_end is not None and self.page_end < self.page_start:
            raise ValueError("El rango de páginas está invertido")

    @property
    def article_label(self) -> str | None:
        if self.article_from is None:
            return None
        if self.article_to is None or self.article_to == self.article_from:
            title = f". {self.article_title}" if self.article_title else ""
            return f"Artículo {self.article_from}{title}"
        return f"Artículos {self.article_from} a {self.article_to}"

    @property
    def page_label(self) -> str | None:
        if self.page_start is None:
            return None
        if self.page_end is None or self.page_end == self.page_start:
            return f"pág. {self.page_start}"
        return f"págs. {self.page_start}–{self.page_end}"

    @property
    def location_label(self) -> str | None:
        """Ruta estructural sin páginas: «Capítulo IV · Artículo 18. Condiciones».

        Cuando hay artículo se omite la sección intermedia: el artículo ya es la
        referencia que un lector busca, y la sección alarga la cita sin ayudar.
        """
        parts: list[str] = []
        if self.chapter:
            parts.append(self.chapter)
        if self.article_label:
            parts.append(self.article_label)
        elif self.section:
            parts.append(self.section)
        return " · ".join(parts) or None

    @property
    def chapter_number(self) -> str | None:
        """«Capítulo IV. Programas de ayudas…» → «Capítulo IV»."""
        return self.chapter.split(".", 1)[0].strip() if self.chapter else None

    @property
    def citation_label(self) -> str | None:
        """Versión breve para citas: «Capítulo IV · Artículo 18. Condiciones».

        El título completo del capítulo se conserva en `location_label`, que es
        el que ven el embedding y el modelo: ahí sí aporta (distingue «campus
        central» de «campus externos»). En una tarjeta de fuente solo alarga.
        """
        parts: list[str] = []
        if self.article_label:
            if self.chapter_number:
                parts.append(self.chapter_number)
            parts.append(self.article_label)
        elif self.section:
            if self.chapter_number:
                parts.append(self.chapter_number)
            parts.append(self.section)
        elif self.chapter:
            parts.append(self.chapter)
        return " · ".join(parts) or None

    @property
    def section_key(self) -> str:
        """Identidad de la unidad estructural, para agrupar fragmentos hermanos."""
        if self.article_from is not None:
            return f"art:{self.article_from}-{self.article_to or self.article_from}"
        return f"sec:{self.chapter or ''}|{self.section or ''}"

    def covers_article(self, number: int) -> bool:
        if self.article_from is None:
            return False
        return self.article_from <= number <= (self.article_to or self.article_from)

    def spanning(self, other: SectionAnchor) -> SectionAnchor:
        """Anclaje que cubre a ambos: se usa al fusionar fragmentos contiguos."""
        starts = [p for p in (self.page_start, other.page_start) if p is not None]
        ends = [p for p in (self.page_end, other.page_end, self.page_start, other.page_start) if p is not None]
        articles = [
            a
            for a in (self.article_from, self.article_to, other.article_from, other.article_to)
            if a is not None
        ]
        same_article = self.section_key == other.section_key
        return SectionAnchor(
            chapter=self.chapter if self.chapter == other.chapter else self.chapter or other.chapter,
            section=self.section if self.section == other.section else None,
            article_from=min(articles) if articles else None,
            article_to=max(articles) if articles else None,
            article_title=self.article_title if same_article else None,
            page_start=min(starts) if starts else None,
            page_end=max(ends) if ends else None,
        )
