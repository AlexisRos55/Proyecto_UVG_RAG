from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.services.spanish_text import fold


class DocumentKind(str, Enum):
    """Tipo documental, deducido del título. Decide cómo se presenta el documento."""

    REGULATION = "reglamento"
    CALENDAR = "calendario"
    PROCESS = "proceso"
    PROGRAM = "programa"
    GENERAL = "documento"

    @property
    def label(self) -> str:
        return {
            DocumentKind.REGULATION: "Reglamento",
            DocumentKind.CALENDAR: "Calendario",
            DocumentKind.PROCESS: "Proceso",
            DocumentKind.PROGRAM: "Programa académico",
            DocumentKind.GENERAL: "Documento oficial",
        }[self]

    @classmethod
    def from_title(cls, title: str) -> DocumentKind:
        folded = fold(title)
        if any(word in folded for word in ("reglamento", "normativ", "politica", "codigo de")):
            return cls.REGULATION
        if "calendario" in folded:
            return cls.CALENDAR
        if any(word in folded for word in ("proceso", "procedimiento", "admision", "inscripcion")):
            return cls.PROCESS
        if any(
            word in folded
            for word in ("licenciatura", "ingenieria", "maestria", "profesorado", "tecnico", "facultad", "carrera")
        ):
            return cls.PROGRAM
        return cls.GENERAL


@dataclass(frozen=True, slots=True)
class DocumentFacts:
    """Hechos de nivel documento que viajan con cada fragmento indexado.

    Se repiten en cada fragmento a propósito: así el índice vectorial es la única
    fuente de verdad y el catálogo documental puede reconstruirse desde él sin
    una tabla adicional que pudiera desincronizarse.
    """

    title: str
    code: str | None = None
    version: str | None = None
    effective_date: str | None = None
    page_count: int | None = None

    @property
    def kind(self) -> DocumentKind:
        return DocumentKind.from_title(self.title)

    @property
    def reference(self) -> str:
        """«Reglamento de ayudas financieras (UVG.DAF.02.001, versión 10.0)»."""
        details = [part for part in (self.code, f"versión {self.version}" if self.version else None) if part]
        return f"{self.title} ({', '.join(details)})" if details else self.title
