from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.domain.value_objects.corpus_entity import CorpusEntity
from app.domain.value_objects.document_facts import DocumentFacts, DocumentKind


@dataclass(frozen=True, slots=True)
class OutlineArticle:
    number: int
    title: str | None
    page: int | None

    @property
    def label(self) -> str:
        return f"Artículo {self.number}" + (f". {self.title}" if self.title else "")


@dataclass(frozen=True, slots=True)
class OutlineDivision:
    """Un capítulo o una sección de primer nivel, con los artículos que contiene."""

    label: str
    page_start: int | None
    articles: tuple[OutlineArticle, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentOutline:
    """Lo que el sistema sabe de un documento **como documento**, no como fragmentos.

    Es la pieza que permite responder «¿de qué trata este reglamento?» o «¿cuáles
    son sus capítulos?» con datos exactos: se deriva de la estructura detectada
    al indexar, así que no hay nada que el modelo pueda inventar en esas
    respuestas. `summary` es extractiva —el objeto del documento en sus propias
    palabras—, no generada.
    """

    document_id: UUID
    facts: DocumentFacts
    divisions: tuple[OutlineDivision, ...] = ()
    summary: str | None = None
    keywords: tuple[str, ...] = ()
    fragment_count: int = 0
    aliases: tuple[str, ...] = field(default_factory=tuple)
    # Perfil semántico: entidades que el documento nombra (programas, instancias…).
    entities: tuple[CorpusEntity, ...] = field(default_factory=tuple)

    @property
    def title(self) -> str:
        return self.facts.title

    @property
    def kind(self) -> DocumentKind:
        return self.facts.kind

    @property
    def article_count(self) -> int:
        return sum(len(division.articles) for division in self.divisions)

    @property
    def has_structure(self) -> bool:
        return any(division.articles for division in self.divisions)
