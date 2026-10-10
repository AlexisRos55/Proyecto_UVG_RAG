from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf as fitz

from app.domain.ports.document_text_extractor_port import (
    DocumentTextExtractorPort,
    ExtractedDocument,
)
from app.shared.exceptions.domain_errors import DocumentProcessingError

_DATE_CELL = re.compile(r"^\d{1,2}(?:\s*[-–al]+\s*\d{1,2})?$")
_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
_MONTH_HEADING = re.compile(rf"^({'|'.join(_MONTHS)})(?:\s+(\d{{4}}))?$")
_ROW_TOLERANCE = 4.0
_MIN_DATED_ROWS = 5
# Desfase máximo entre una fecha y su actividad cuando las columnas no están alineadas.
_OFFSET_TOLERANCE = 12.0


class PyMuPDFExtractorAdapter(DocumentTextExtractorPort):
    """Extracts raw text from PDF files using PyMuPDF (FR-01).

    Las páginas con forma de tabla fechada (calendarios) se reconstruyen por
    filas: el orden de lectura por bloques de PyMuPDF entrega primero la columna
    de fechas completa y después la de actividades, con lo que «17» y «Último
    día para pagar la cuota de agosto» terminaban en fragmentos distintos y la
    pregunta «¿cuándo…?» era irrespondible aunque el dato estuviera indexado.
    """

    def extract_text(self, file_path: Path) -> str:
        return self.extract_document(file_path).full_text

    def extract_document(self, file_path: Path) -> ExtractedDocument:
        if not file_path.exists():
            raise DocumentProcessingError(f"El archivo '{file_path}' no existe")

        try:
            with fitz.open(file_path) as pdf:
                pages_text = tuple(self._page_text(page) for page in pdf)
                title = (pdf.metadata or {}).get("title") or None
        except Exception as exc:
            raise DocumentProcessingError(
                f"No fue posible extraer texto de '{file_path.name}': {exc}"
            ) from exc

        if not any(text.strip() for text in pages_text):
            raise DocumentProcessingError(
                f"'{file_path.name}' no contiene texto extraíble (¿es un PDF escaneado sin OCR?)"
            )
        return ExtractedDocument(pages=pages_text, title=title.strip() if title else None)

    def _page_text(self, page: Any) -> str:
        positioned_rows = self._positioned_rows(page)
        rows = [cells for _, cells in positioned_rows]
        if self._is_dated_table(rows):
            return self._render_dated_table(self._pair_offset_dates(positioned_rows))
        # Página de calendario con la columna de fechas desalineada: se reconoce después
        # de emparejar fechas y actividades, y solo si tiene encabezados de mes.
        paired = self._pair_offset_dates(positioned_rows)
        has_month = any(
            len(cells) == 1 and _MONTH_HEADING.match(unicodedata.normalize("NFKC", cells[0][1].lower()).strip())
            for cells in rows
        )
        if has_month and self._is_dated_table(paired):
            return self._render_dated_table(paired)
        return str(page.get_text())

    @staticmethod
    def _pair_offset_dates(rows: list[tuple[float, list[tuple[float, str]]]]) -> list[list[tuple[float, str]]]:
        """Une cada fecha suelta con la actividad más cercana en altura.

        En algunas páginas la columna de fechas no está alineada con la de
        actividades (la fecha queda unos puntos arriba o abajo): «17» y «Último día
        para pagar la cuota de diciembre» caían en filas distintas y la fecha se
        perdía o se pegaba a la actividad de al lado.
        """
        paired = [list(cells) for _, cells in rows]
        heights = [y for y, _ in rows]
        taken: set[int] = set()
        for index, cells in enumerate(paired):
            if len(cells) != 1 or not _DATE_CELL.match(cells[0][1]):
                continue
            candidates = [
                other for other in (index - 1, index + 1)
                if 0 <= other < len(paired) and other not in taken and paired[other]
                and abs(heights[other] - heights[index]) <= _OFFSET_TOLERANCE
                and not _DATE_CELL.match(paired[other][0][1]) and not _MONTH_HEADING.match(paired[other][0][1].lower())
            ]
            if not candidates:
                continue
            nearest = min(candidates, key=lambda other: abs(heights[other] - heights[index]))
            paired[nearest] = [cells[0], *paired[nearest]]
            paired[index] = []
            taken.add(nearest)
        return [cells for cells in paired if cells]

    @staticmethod
    def _layout_rows(page: Any) -> list[list[tuple[float, str]]]:
        return [cells for _, cells in PyMuPDFExtractorAdapter._positioned_rows(page)]

    @staticmethod
    def _positioned_rows(page: Any) -> list[tuple[float, list[tuple[float, str]]]]:
        """Líneas agrupadas por altura: (altura, [(x, texto)])."""
        positioned: list[tuple[float, float, str]] = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    x0, y0, _, y1 = line["bbox"]
                    positioned.append(((y0 + y1) / 2, x0, text))
        positioned.sort()

        rows: list[tuple[float, list[tuple[float, str]]]] = []
        for y, x, text in positioned:
            if rows and abs(rows[-1][0] - y) <= _ROW_TOLERANCE:
                rows[-1][1].append((x, text))
            else:
                rows.append((y, [(x, text)]))
        return [(y, sorted(cells)) for y, cells in rows]

    @staticmethod
    def _is_dated_table(rows: list[list[tuple[float, str]]]) -> bool:
        multi_cell = [cells for cells in rows if len(cells) >= 2]
        dated = [cells for cells in multi_cell if _DATE_CELL.match(cells[0][1])]
        return len(dated) >= _MIN_DATED_ROWS and len(dated) >= 0.5 * len(multi_cell)

    @staticmethod
    def _render_dated_table(rows: list[list[tuple[float, str]]]) -> str:
        """Cada actividad en una línea autosuficiente: «17 de agosto: Último día…»."""
        output: list[str] = []
        month: str | None = None
        activity_x: float | None = None
        last_was_dated = False
        for cells in rows:
            first = cells[0][1]
            month_match = _MONTH_HEADING.match(unicodedata.normalize("NFKC", first.lower()).strip())
            if len(cells) == 1 and month_match:
                month = " de ".join(part for part in month_match.groups() if part)
                output.append(first)
                last_was_dated = False
                continue
            if len(cells) >= 2 and _DATE_CELL.match(first):
                when = f"{first} de {month}" if month else first
                output.append(f"{when}: {' '.join(text for _, text in cells[1:])}")
                activity_x = cells[1][0]
                last_was_dated = True
                continue
            is_continuation = (
                last_was_dated and len(cells) == 1 and activity_x is not None and cells[0][0] >= activity_x - 2
            )
            if is_continuation:
                output[-1] = f"{output[-1]} {first}"
                continue
            output.append(" ".join(text for _, text in cells))
            last_was_dated = False
        return "\n".join(output)
