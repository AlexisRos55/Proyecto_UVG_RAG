from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.value_objects.corpus_entity import CorpusEntity
from app.domain.value_objects.document_outline import DocumentOutline


class CorpusCatalogPort(ABC):
    """Conocimiento del corpus a nivel documento (ADR-0013).

    La búsqueda por similitud responde «¿qué fragmento se parece a la
    pregunta?». Este puerto responde otra cosa: qué documentos hay, cómo están
    organizados y cuáles se relacionan entre sí. Separarlo de `VectorStorePort`
    (Interface Segregation) permite que un caso de uso lo consulte sin saber
    nada de vectores.
    """

    @abstractmethod
    def list_outlines(self) -> list[DocumentOutline]:
        """Todos los documentos indexados, con su estructura."""

    @abstractmethod
    def get_outline(self, document_id: UUID) -> DocumentOutline | None: ...

    @abstractmethod
    def section_chunks(self, document_id: UUID, section_key: str) -> list[Chunk]:
        """Fragmentos de la misma unidad estructural, en orden de aparición."""

    @abstractmethod
    def related_documents(self, document_id: UUID, limit: int = 3) -> list[tuple[DocumentOutline, tuple[str, ...]]]:
        """Documentos con vocabulario temático afín y los términos que comparten."""

    @abstractmethod
    def entities(self) -> list[CorpusEntity]:
        """Entidades con nombre propio del corpus: programas, instancias, campus, carreras, eventos."""

    @abstractmethod
    def vocabulary(self, document_ids: Collection[UUID]) -> frozenset[str]:
        """Raíces léxicas que aparecen en esos documentos.

        Permite saber si una palabra nueva pertenece al tema en curso («directiva»
        en el reglamento de grupos estudiantiles) o introduce otro («parqueo»).
        """

    @abstractmethod
    def co_occur(self, terms: Collection[str], context_terms: Collection[str]) -> bool:
        """¿Aparece alguna raíz de `terms` en un mismo fragmento con alguna de `context_terms`?

        Es la prueba fina de pertenencia a un tema: «directiva» comparte
        fragmentos con «club»; «parqueo» nunca comparte uno con «elecciones».
        """

    @abstractmethod
    def article_chunks(self, document_id: UUID, number: int) -> list[Chunk]:
        """Fragmentos que forman un artículo concreto de un documento, en orden.

        Cuando el estudiante nombra el artículo («Artículo 20», «¿y el siguiente?»)
        no hay nada que buscar: se sabe exactamente qué texto pide.
        """
