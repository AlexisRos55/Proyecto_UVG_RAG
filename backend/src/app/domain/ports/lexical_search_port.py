from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.chunk import Chunk


@dataclass(frozen=True, slots=True)
class LexicalHit:
    """Coincidencia léxica con su evidencia.

    `coverage` es la fracción de la información de la consulta —ponderada por
    IDF— que aparece en el fragmento. Es la señal que permite decidir si una
    coincidencia léxica basta como evidencia (FR-08) sin depender del puntaje
    BM25, que no está acotado y no es comparable entre consultas.
    """

    chunk: Chunk
    score: float
    coverage: float


class LexicalSearchPort(ABC):
    """Recuperación por términos exactos, complementaria a la semántica (ADR-0012).

    Existe porque el modelo de embeddings fijado por el asesor (all-MiniLM-L6-v2)
    se entrenó en inglés: ante «Artículo 18», «horas beca» o una sigla como
    «PAA», la similitud de coseno es poco fiable y la coincidencia literal es
    justamente la evidencia que falta.
    """

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int,
        *,
        expansions: Sequence[str] = (),
        document_ids: Collection[UUID] | None = None,
    ) -> list[LexicalHit]:
        """Los `top_k` fragmentos con mayor puntaje BM25 para `query`.

        `expansions` son sinónimos o desarrollos de siglas: suman evidencia con
        menor peso que los términos que escribió el estudiante.
        """
