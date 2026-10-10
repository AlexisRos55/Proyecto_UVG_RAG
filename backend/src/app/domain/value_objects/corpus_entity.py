from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class EntityKind(str, Enum):
    """Clases de entidad que el corpus institucional nombra y los estudiantes preguntan."""

    PROGRAM = "programa"          # becas, programas de ayuda, créditos, subsidios
    OFFICE = "instancia"          # oficinas, direcciones, comités, consejos
    CAMPUS = "campus"
    CAREER = "carrera"
    EVENT = "evento"              # actividades fechadas del calendario
    PERSON = "persona"            # autoridades declaradas en la ficha del documento


_FEMININE = frozenset({"oficina", "dirección", "direccion", "unidad", "decanatura", "beca", "maestría", "maestria",
                        "licenciatura", "ingeniería", "ingenieria", "prueba", "ceremonia", "semana", "feria"})


@dataclass(frozen=True, slots=True)
class CorpusEntity:
    """Algo con nombre propio en el corpus: «Beca Despega», «Consejo Electoral».

    `key` es la forma canónica (plegada y lematizada) que identifica la entidad
    aunque el texto la escriba de varias maneras («Becas Trasciende» / «Beca
    Trasciende»). `distinctive` son las palabras que la distinguen de otras de
    su clase: «despega» y no «beca». `defined_in` guarda el artículo cuyo título
    es la entidad, que es donde el corpus la define.
    """

    name: str
    kind: EntityKind
    key: str
    distinctive: tuple[str, ...]
    document_ids: tuple[UUID, ...] = ()
    defined_in: tuple[tuple[UUID, int], ...] = field(default_factory=tuple)
    detail: str | None = None

    @property
    def spoken(self) -> str:
        """Cómo lo nombra una persona en una frase: «la Beca Despega», «el Consejo Electoral»."""
        first = self.name.split()[0].lower() if self.name else ""
        if self.kind is EntityKind.PERSON or first in ("el", "la", "los", "las"):
            return self.name
        if first.endswith("s") and first not in ("campus",):
            article = "las" if first.endswith("as") else "los"
        elif first in _FEMININE or first.endswith(("ción", "cion", "dad")):
            article = "la"
        else:
            article = "el"
        return f"{article} {self.name}"

    @property
    def search_terms(self) -> str:
        return self.name + (f" {self.detail}" if self.detail else "")
