from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.domain.services.spanish_text import fold

# Un encabezado se reconoce por repetirse: si una línea aparece en la mayoría de
# las páginas, es membrete y no contenido. El umbral deja margen para portadas e
# índices, que no llevan membrete.
_MIN_PAGES_FOR_DETECTION = 3
_MIN_PAGE_SHARE = 0.6

_DIGITS = re.compile(r"\d+")
_PAGE_COUNTER = re.compile(r"^\s*p[aá]gina\s+\d+\s+de\s+\d+\s*$", re.IGNORECASE)
_TOC_LEADER = re.compile(r"\.{4,}\s*\d*\s*$")
_TOC_TITLE = re.compile(r"^\s*(?:contenido|[ií]ndice|tabla\s+de\s+contenidos?)\s*$", re.IGNORECASE)
_FIELD_LABELS = {"codigo": "code", "version": "version", "vigencia": "effective_date"}


@dataclass(frozen=True, slots=True)
class BoilerplateResult:
    pages: tuple[str, ...]
    header_lines: tuple[str, ...] = ()
    fields: dict[str, str] = field(default_factory=dict)


class PageBoilerplateRemover:
    """Retira membretes repetidos, contadores de página e índices con puntos guía.

    Cumple FR-02 («remoción de encabezados y pies de página») de verdad: la
    limpieza original por expresiones regulares no podía reconocer un membrete
    de 20 líneas, así que en los reglamentos reales casi la mitad de cada
    fragmento de 1000 caracteres era ese mismo bloque repetido —el mismo nombre
    del rector en cada vector—, lo que acercaba entre sí embeddings de artículos
    que no tienen nada que ver.

    Antes de descartar el membrete se leen de él los datos que sí son valiosos:
    código, versión y vigencia del documento.
    """

    def remove(self, pages: tuple[str, ...]) -> BoilerplateResult:
        split_pages = [page.splitlines() for page in pages]
        repeated = self._repeated_lines(split_pages)

        header_lines: list[str] = []
        fields: dict[str, str] = {}
        cleaned: list[str] = []
        for lines in split_pages:
            kept: list[str] = []
            for index, line in enumerate(lines):
                key = self._key(line)
                if key in repeated or self._is_header_value(lines, index, repeated):
                    if len(header_lines) < 60 and line.strip() and line.strip() not in header_lines:
                        header_lines.append(line.strip())
                    self._capture_field(lines, index, fields)
                    continue
                if _PAGE_COUNTER.match(line) or _TOC_LEADER.search(line) or _TOC_TITLE.match(line):
                    continue
                kept.append(line)
            cleaned.append("\n".join(kept))

        return BoilerplateResult(pages=tuple(cleaned), header_lines=tuple(header_lines), fields=fields)

    @staticmethod
    def _key(line: str) -> str:
        return _DIGITS.sub("#", " ".join(fold(line).split()))

    def _repeated_lines(self, split_pages: list[list[str]]) -> set[str]:
        if len(split_pages) < _MIN_PAGES_FOR_DETECTION:
            return set()
        page_frequency: Counter[str] = Counter()
        for lines in split_pages:
            page_frequency.update({self._key(line) for line in lines if line.strip()})
        threshold = max(2, int(len(split_pages) * _MIN_PAGE_SHARE))
        # Viñetas e incisos sueltos («a.», «•») también se repiten en casi todas
        # las páginas de un reglamento, pero son estructura del contenido: solo
        # cuenta como membrete una línea con al menos cuatro letras.
        return {
            key
            for key, count in page_frequency.items()
            if count >= threshold and sum(ch.isalpha() for ch in key) >= 4
        }

    def _is_header_value(self, lines: list[str], index: int, repeated: set[str]) -> bool:
        """Valores numéricos del membrete («20», «10.0») encerrados entre líneas de membrete.

        No pueden detectarse por repetición —un calendario repite «15» en cada
        mes y eso es contenido—, pero sí por posición: en el membrete, un número
        suelto siempre está rodeado de etiquetas repetidas.
        """
        if not repeated or any(ch.isalpha() for ch in lines[index]) or not lines[index].strip():
            return False
        neighbours = [self._nearest(lines, index, step) for step in (-1, 1)]
        return all(neighbour is not None and self._key(neighbour) in repeated for neighbour in neighbours)

    @staticmethod
    def _nearest(lines: list[str], index: int, step: int) -> str | None:
        cursor = index + step
        while 0 <= cursor < len(lines):
            if lines[cursor].strip():
                return lines[cursor]
            cursor += step
        return None

    @staticmethod
    def _capture_field(lines: list[str], index: int, fields: dict[str, str]) -> None:
        """Membretes tipo formulario: «Versión:» en una línea y «10.0» en la siguiente.

        Un campo vacío («Vigencia:» sin fecha) no debe tomar como valor la
        siguiente etiqueta del membrete ni el contador de página.
        """
        label = fold(lines[index]).strip().rstrip(":").strip()
        target = _FIELD_LABELS.get(label)
        if target is None or target in fields:
            return
        for candidate in lines[index + 1 : index + 3]:
            value = candidate.strip()
            if not value:
                continue
            if value.endswith(":") or _PAGE_COUNTER.match(value):
                return
            fields[target] = value
            return


_CARD_LABELS = ("codigo", "paginas", "version", "vigencia", "elaboro", "reviso", "autorizo", "aprobo")
_ROLE_SEPARATOR = re.compile(r"\s[–-]\s")


def document_card(header_lines: tuple[str, ...], title: str) -> str | None:
    """«Ficha del documento»: el membrete, una sola vez y legible.

    El membrete se retira de cada página porque repetido es ruido, pero contiene
    datos que sí se consultan —código, versión, vigencia y quién elaboró, revisó
    y autorizó el documento—. Se conservan en un único fragmento para que
    «¿quién revisó este reglamento?» siga siendo respondible y citable.
    """
    fields: list[tuple[str, list[str]]] = []
    for line in header_lines:
        folded = fold(line).strip().rstrip(":").strip()
        if line.strip().endswith(":") and folded in _CARD_LABELS:
            fields.append((line.strip().rstrip(":").strip(), []))
        elif fields and not _PAGE_COUNTER.match(line) and fold(line) != fold(title):
            fields[-1][1].append(line.strip())
    rendered = [f"{label}: {_join_card_values(values)}" for label, values in fields if values]
    if len(rendered) < 2:
        return None
    return f"Ficha del documento {title}.\n" + "\n".join(rendered)


def _join_card_values(values: list[str]) -> str:
    """Una persona por entrada («Nombre – Cargo»); los renglones partidos se reúnen."""
    entries: list[str] = []
    for value in values:
        if entries and not _ROLE_SEPARATOR.search(value) and "|" not in value:
            entries[-1] = f"{entries[-1]} {value}"
        else:
            entries.extend(part.strip() for part in value.split("|") if part.strip())
    return "; ".join(entries)
