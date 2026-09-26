from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from app.domain.entities.chunk import Chunk


class DocumentIndexerPort(ABC):
    """Convierte un archivo en fragmentos indexados (FR-01 a FR-05).

    Existe para que los casos de uso de ingesta y reindexación dependan de una
    abstracción y no del pipeline concreto de infraestructura, como exige la
    regla de dependencia (docs/04-software-architecture.md, sección 2). Lo
    implementa `DocumentIndexingPipeline`.
    """

    @abstractmethod
    async def process(self, document_id: UUID, file_path: Path, display_name: str | None = None) -> list[Chunk]:
        """Extrae, fragmenta, embebe e indexa el documento; devuelve los fragmentos creados."""
