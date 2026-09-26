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
        rows = self._layout_rows(page)
        if self._is_dated_table(rows):
            return self._render_dated_table(rows)
        return str(page.get_text())

    @staticmethod
    def _layout_rows(page: Any) -> list[list[tuple[float, str]]]:
        """Líneas agrupadas por altura: cada fila es una lista de (x, texto)."""
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
        return [sorted(cells) for _, cells in rows]

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
