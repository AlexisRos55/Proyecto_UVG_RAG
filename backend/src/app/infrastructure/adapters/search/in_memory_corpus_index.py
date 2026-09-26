from __future__ import annotations

import math
import re
import threading
from collections import Counter, defaultdict
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import replace
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.ports.corpus_catalog_port import CorpusCatalogPort
from app.domain.ports.lexical_search_port import LexicalHit, LexicalSearchPort
from app.domain.services.document_outline_builder import DocumentOutlineBuilder
from app.domain.services.entity_extractor import EntityExtractor
from app.domain.services.spanish_text import STOPWORDS, analyze, fold, light_stem
from app.domain.value_objects.corpus_entity import CorpusEntity
from app.domain.value_objects.document_outline import DocumentOutline

_EXPANSION_WEIGHT = 0.6
_KEYWORDS_PER_DOCUMENT = 8
_SURFACE_WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}")


class InMemoryCorpusIndex(LexicalSearchPort, CorpusCatalogPort):
    """Índice BM25 y catálogo documental en memoria, reconstruible desde ChromaDB.

    No introduce un segundo almacén persistente: ChromaDB ya guarda el texto y
    los metadatos de cada fragmento, así que este índice se reconstruye desde
    ahí al arrancar (milisegundos para el corpus actual) y se mantiene al día a
    través de `SynchronizedVectorStore`. Si otro proceso modifica la colección
    —`scripts/ingest.py`, por ejemplo—, `size_probe` detecta el cambio de tamaño
    y el índice se recarga antes de la siguiente búsqueda.

    Los parámetros BM25 son los estándar de la literatura (k1=1.2, b=0.75): no
    hay un conjunto etiquetado suficientemente grande para ajustarlos sin
    sobreajustar, y los valores por defecto son robustos en textos normativos.
    """

    def __init__(
        self,
        loader: Callable[[], Iterable[Chunk]] | None = None,
        size_probe: Callable[[], int] | None = None,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        self._loader = loader
        self._size_probe = size_probe
        self._k1 = k1
        self._b = b
        self._lock = threading.RLock()
        self._chunks: dict[UUID, Chunk] = {}
        self._dirty = True
        self._loaded = loader is None
        # Estructuras derivadas; se reconstruyen de una vez cuando `_dirty`.
        self._order: list[Chunk] = []
        self._postings: dict[str, list[tuple[int, int]]] = {}
        self._lengths: list[int] = []
        self._average_length = 1.0
        self._document_vectors: dict[UUID, dict[str, float]] = {}
        self._surface: dict[str, str] = {}
        self._outlines: dict[UUID, DocumentOutline] = {}
        self._sections: dict[tuple[UUID, str], list[Chunk]] = {}
        self._entities: list[CorpusEntity] = []
        self._document_terms: dict[UUID, frozenset[str]] = {}

    # --- Mantenimiento -------------------------------------------------------------

    def add(self, chunks: Sequence[Chunk]) -> None:
        with self._lock:
            for chunk in chunks:
                self._chunks[chunk.id] = chunk
            self._dirty = True

    def remove_document(self, document_id: UUID) -> None:
        with self._lock:
            self._chunks = {cid: c for cid, c in self._chunks.items() if c.document_id != document_id}
            self._dirty = True

    def reload(self) -> None:
        if self._loader is None:
            return
        chunks = list(self._loader())
        with self._lock:
            self._chunks = {chunk.id: chunk for chunk in chunks}
            self._dirty = True
            self._loaded = True

    def _ensure_fresh(self) -> None:
        stale = not self._loaded or (
            self._size_probe is not None and self._size_probe() != len(self._chunks)
        )
        if stale:
            self.reload()
        with self._lock:
            if self._dirty:
                self._rebuild()

    def _rebuild(self) -> None:
        self._order = sorted(self._chunks.values(), key=lambda c: (str(c.document_id), c.position))
        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        lengths: list[int] = []
        document_terms: dict[UUID, Counter[str]] = defaultdict(Counter)
        surface_votes: dict[str, Counter[str]] = defaultdict(Counter)

        for index, chunk in enumerate(self._order):
            # El encabezado se indexa junto al texto: «Artículo 18. Condiciones»
            # debe encontrarse aunque el cuerpo del artículo no repita la palabra.
            terms = analyze(f"{chunk.heading}\n{chunk.text}")
            counts = Counter(terms)
            for term, frequency in counts.items():
                postings[term].append((index, frequency))
            lengths.append(len(terms))
            document_terms[chunk.document_id].update(analyze(chunk.text))
            for word in _SURFACE_WORD.findall(chunk.text):
                lowered = word.lower()
                if fold(lowered) not in STOPWORDS:
                    surface_votes[light_stem(fold(lowered))][lowered] += 1

        self._postings = dict(postings)
        self._lengths = lengths
        self._average_length = (sum(lengths) / len(lengths)) if lengths else 1.0
        self._surface = {stem: votes.most_common(1)[0][0] for stem, votes in surface_votes.items()}
        self._document_vectors = self._tfidf(document_terms)
        self._document_terms = {document_id: frozenset(counts) for document_id, counts in document_terms.items()}
        sections: dict[tuple[UUID, str], list[Chunk]] = defaultdict(list)
        for item in self._order:
            if item.anchor is not None:
                sections[(item.document_id, item.anchor.section_key)].append(item)
        self._sections = dict(sections)
        self._entities = EntityExtractor.extract(self._order)
        self._outlines = {}
        self._dirty = False

    @staticmethod
    def _tfidf(document_terms: dict[UUID, Counter[str]]) -> dict[UUID, dict[str, float]]:
        total = len(document_terms)
        frequency: Counter[str] = Counter()
        for counts in document_terms.values():
            frequency.update(counts.keys())
        vectors: dict[UUID, dict[str, float]] = {}
        for document_id, counts in document_terms.items():
            vector = {
                term: (1 + math.log(count)) * math.log((1 + total) / (1 + frequency[term]))
                for term, count in counts.items()
                if not term.isdigit() and len(term) > 3
            }
            norm = math.sqrt(sum(weight * weight for weight in vector.values())) or 1.0
            vectors[document_id] = {term: weight / norm for term, weight in vector.items() if weight > 0}
        return vectors

    # --- LexicalSearchPort ---------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int,
        *,
        expansions: Sequence[str] = (),
        document_ids: Collection[UUID] | None = None,
    ) -> list[LexicalHit]:
        self._ensure_fresh()
        with self._lock:
            if not self._order:
                return []
            query_terms = list(dict.fromkeys(self.correct(term) for term in analyze(query)))
            expansion_terms = [
                term
                for term in dict.fromkeys(t for phrase in expansions for t in analyze(phrase))
                if term not in query_terms
            ]
            weighted = [(term, 1.0) for term in query_terms] + [(t, _EXPANSION_WEIGHT) for t in expansion_terms]

            scores: dict[int, float] = defaultdict(float)
            matched: dict[int, set[str]] = defaultdict(set)
            for term, weight in weighted:
                idf = self._idf(term)
                for index, frequency in self._postings.get(term, ()):
                    if document_ids is not None and self._order[index].document_id not in document_ids:
                        continue
                    normalizer = frequency + self._k1 * (1 - self._b + self._b * self._lengths[index] / self._average_length)
                    scores[index] += weight * idf * frequency * (self._k1 + 1) / normalizer
                    matched[index].add(term)

            informative = sum(self._idf(term) for term in query_terms) or 1.0
            hits: list[LexicalHit] = []
            for index, score in scores.items():
                coverage = min(1.0, sum(self._idf(t) for t in matched[index] if t in query_terms) / informative)
                # Factor de coordinación (como el `coord` clásico de Lucene): un
                # fragmento que repite mucho un sinónimo no debe superar a uno que
                # contiene las palabras que escribió el estudiante. Sin él, «feria
                # de becas» perdía frente a artículos que repiten «ayuda financiera».
                hits.append(
                    LexicalHit(chunk=self._order[index], score=score * (0.25 + 0.75 * coverage), coverage=coverage)
                )
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:top_k]

    def _idf(self, term: str) -> float:
        total = len(self._order)
        frequency = len(self._postings.get(term, ()))
        return math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))

    def correct(self, term: str) -> str:
        """Corrige un término fuera de vocabulario al más cercano y frecuente.

        Solo actúa si el término no existe en el corpus: nunca «corrige» una
        palabra válida hacia otra. La tolerancia crece con la longitud (una
        edición hasta 6 letras, dos a partir de 7), que es donde las erratas
        tipográficas dejan de producir otra palabra real.
        """
        if term in self._postings or len(term) < 4 or term.isdigit():
            return term
        budget = 1 if len(term) <= 6 else 2
        best: tuple[int, int, str] | None = None
        for candidate, postings in self._postings.items():
            if candidate[0] != term[0] or abs(len(candidate) - len(term)) > budget:
                continue
            distance = _damerau_levenshtein(term, candidate, budget)
            if distance <= budget:
                key = (distance, -len(postings), candidate)
                if best is None or key < best:
                    best = key
        return best[2] if best else term

    # --- CorpusCatalogPort ---------------------------------------------------------

    def list_outlines(self) -> list[DocumentOutline]:
        self._ensure_fresh()
        with self._lock:
            document_ids = list(dict.fromkeys(chunk.document_id for chunk in self._order))
            return [self._outline(document_id) for document_id in document_ids]

    def get_outline(self, document_id: UUID) -> DocumentOutline | None:
        self._ensure_fresh()
        with self._lock:
            if not any(chunk.document_id == document_id for chunk in self._order):
                return None
            return self._outline(document_id)

    def section_chunks(self, document_id: UUID, section_key: str) -> list[Chunk]:
        self._ensure_fresh()
        with self._lock:
            return list(self._sections.get((document_id, section_key), ()))

    def vocabulary(self, document_ids: Collection[UUID]) -> frozenset[str]:
        self._ensure_fresh()
        with self._lock:
            return frozenset(term for document_id in document_ids for term in self._document_terms.get(document_id, ()))

    def co_occur(self, terms: Collection[str], context_terms: Collection[str]) -> bool:
        self._ensure_fresh()
        with self._lock:
            context_chunks = {index for term in context_terms for index, _ in self._postings.get(term, ())}
            return any(index in context_chunks for term in terms for index, _ in self._postings.get(term, ()))

    def article_chunks(self, document_id: UUID, number: int) -> list[Chunk]:
        self._ensure_fresh()
        with self._lock:
            return [
                chunk
                for chunk in self._order
                if chunk.document_id == document_id and chunk.anchor and chunk.anchor.covers_article(number)
            ]

    def entities(self) -> list[CorpusEntity]:
        self._ensure_fresh()
        with self._lock:
            return list(self._entities)

    def related_documents(
        self, document_id: UUID, limit: int = 3
    ) -> list[tuple[DocumentOutline, tuple[str, ...]]]:
        self._ensure_fresh()
        with self._lock:
            source = self._document_vectors.get(document_id)
            if not source:
                return []
            own_title = fold(self._outline(document_id).title)
            scored: list[tuple[float, UUID, tuple[str, ...]]] = []
            for other_id, vector in self._document_vectors.items():
                if other_id == document_id or fold(self._outline(other_id).title) == own_title:
                    continue
                shared = sorted(
                    (source[t] * vector[t], t) for t in source.keys() & vector.keys()
                )
                similarity = sum(weight for weight, _ in shared)
                if similarity > 0.05:
                    terms = tuple(self._surface.get(t, t) for _, t in reversed(shared[-4:]))
                    scored.append((similarity, other_id, terms))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [(self._outline(other_id), terms) for _, other_id, terms in scored[:limit]]

    def _outline(self, document_id: UUID) -> DocumentOutline:
        cached = self._outlines.get(document_id)
        if cached is not None:
            return cached
        chunks = [chunk for chunk in self._order if chunk.document_id == document_id]
        vector = self._document_vectors.get(document_id, {})
        top_terms = sorted(vector.items(), key=lambda item: item[1], reverse=True)[:_KEYWORDS_PER_DOCUMENT]
        outline = DocumentOutlineBuilder.build(
            document_id, chunks, keywords=tuple(self._surface.get(term, term) for term, _ in top_terms)
        )
        outline = replace(outline, entities=tuple(e for e in self._entities if document_id in e.document_ids))
        self._outlines[document_id] = outline
        return outline


def _damerau_levenshtein(left: str, right: str, budget: int) -> int:
    """Distancia de edición con transposiciones, con corte temprano al superar `budget`."""
    previous_previous: list[int] = []
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and left_char == right[j - 2] and left[i - 2] == right_char:
                current[j] = min(current[j], previous_previous[j - 2] + 1)
        if min(current) > budget:
            return budget + 1
        previous_previous, previous = previous, current
    return previous[-1]
