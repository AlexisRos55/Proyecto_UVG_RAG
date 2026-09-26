from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.chunk import Chunk, RetrievedChunk
from app.domain.ports.corpus_catalog_port import CorpusCatalogPort
from app.domain.services.spanish_text import fold
from app.domain.value_objects.similarity_score import SimilarityScore

_MIN_OVERLAP = 20
_MAX_OVERLAP = 220


@dataclass(frozen=True, slots=True)
class AssemblySettings:
    """`char_budget=0` desactiva el presupuesto: se entregan los fragmentos tal cual (línea base)."""

    char_budget: int = 6000
    expand_sections_up_to: int = 1400
    max_passages: int = 8


class ContextAssembler:
    """Convierte fragmentos recuperados en pasajes coherentes y baratos.

    Tres problemas de la versión anterior, que enviaba siempre los diez
    fragmentos más parecidos tal como se habían recuperado:

    - **Duplicados.** El corpus real contiene documentos idénticos subidos dos
      veces; el mismo texto ocupaba dos posiciones del contexto.
    - **Fragmentos cortados.** Un artículo partido en tres llegaba como un
      trozo suelto sin su comienzo. Aquí, si el artículo completo es corto,
      se entrega entero (estrategia «small-to-big»): se busca con piezas
      pequeñas, que embeben mejor, y se responde con la unidad completa.
    - **Solapamientos repetidos.** Dos fragmentos contiguos repetían sus 100
      caracteres de solapamiento; al fusionarlos se elimina la repetición.

    El presupuesto en caracteres sustituye al número fijo de fragmentos: diez
    fragmentos cortos y diez largos no cuestan lo mismo, y lo que importa para
    el costo (NFR-02) y para la atención del modelo es el volumen de texto.
    """

    def __init__(self, catalog: CorpusCatalogPort | None = None, settings: AssemblySettings | None = None) -> None:
        self._catalog = catalog
        self._settings = settings or AssemblySettings()

    def assemble(
        self, ranked: Sequence[RetrievedChunk], parts: int = 1, scale: float = 1.0
    ) -> list[RetrievedChunk]:
        """`parts` > 1 para preguntas múltiples: cada parte recibe su propio presupuesto (máximo tres).

        `scale` es la decisión de contexto adaptativo: un panorama de un tema pide
        más pasajes (1.5); el dato de una entidad concreta, menos (0.7).
        """
        if self._settings.char_budget <= 0:
            return list(ranked)
        multiplier = max(1, min(parts, 3)) * scale
        budget = int(self._settings.char_budget * multiplier)
        max_passages = max(3, round(self._settings.max_passages * multiplier))

        selected: list[RetrievedChunk] = []
        covered: set[UUID] = set()
        seen_texts: set[str] = set()
        spent = 0
        for item in ranked:
            # El límite se aplica aquí, en orden de relevancia. Aplicarlo después
            # de ordenar por posición descartaba justamente el mejor pasaje
            # cuando estaba al final del documento.
            if len(selected) >= max_passages:
                break
            if item.chunk.id in covered:
                continue
            fingerprint = self._fingerprint(item.chunk.text)
            if fingerprint in seen_texts:
                continue
            candidate = self._expand(item)
            cost = len(candidate.chunk.text)
            if selected and spent + cost > budget:
                if spent + len(item.chunk.text) > budget:
                    continue
                candidate = item
                cost = len(item.chunk.text)
            selected.append(candidate)
            covered.update(candidate.origin_ids)
            seen_texts.add(fingerprint)
            spent += cost

        return self._merge_adjacent(selected)

    def _expand(self, item: RetrievedChunk) -> RetrievedChunk:
        anchor = item.chunk.anchor
        if self._catalog is None or anchor is None or anchor.article_from is None:
            return item
        siblings = self._catalog.section_chunks(item.chunk.document_id, anchor.section_key)
        if len(siblings) <= 1:
            return item
        merged_text = self._join_texts([chunk.text for chunk in siblings])
        if len(merged_text) > self._settings.expand_sections_up_to:
            return item
        merged_anchor = siblings[0].anchor
        for sibling in siblings[1:]:
            if merged_anchor is not None and sibling.anchor is not None:
                merged_anchor = merged_anchor.spanning(sibling.anchor)
        return self._passage(siblings, merged_text, merged_anchor, [item])

    def _merge_adjacent(self, passages: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Agrupa por documento (en orden de relevancia) y funde piezas contiguas."""
        document_order: list[UUID] = []
        grouped: dict[UUID, list[RetrievedChunk]] = {}
        for passage in passages:
            if passage.chunk.document_id not in grouped:
                document_order.append(passage.chunk.document_id)
                grouped[passage.chunk.document_id] = []
            grouped[passage.chunk.document_id].append(passage)

        result: list[RetrievedChunk] = []
        for document_id in document_order:
            items = sorted(grouped[document_id], key=lambda p: p.chunk.position)
            run: list[RetrievedChunk] = [items[0]]
            for passage in items[1:]:
                previous = run[-1]
                last_position = previous.chunk.position + len(previous.origin_ids) - 1
                same_unit = (
                    previous.chunk.anchor is not None
                    and passage.chunk.anchor is not None
                    and previous.chunk.anchor.section_key == passage.chunk.anchor.section_key
                )
                if passage.chunk.position == last_position + 1 and same_unit:
                    run.append(passage)
                else:
                    result.append(self._fuse(run))
                    run = [passage]
            result.append(self._fuse(run))
        return result

    def _fuse(self, run: list[RetrievedChunk]) -> RetrievedChunk:
        if len(run) == 1:
            return run[0]
        anchor = run[0].chunk.anchor
        for item in run[1:]:
            if anchor is not None and item.chunk.anchor is not None:
                anchor = anchor.spanning(item.chunk.anchor)
        chunks = [item.chunk for item in run]
        return self._passage(chunks, self._join_texts([c.text for c in chunks]), anchor, run)

    @staticmethod
    def _passage(chunks: Sequence[Chunk], text: str, anchor, scored: Sequence[RetrievedChunk]) -> RetrievedChunk:
        first = chunks[0]
        origin_ids: list[UUID] = []
        for chunk in chunks:
            origin_ids.append(chunk.id)
        for item in scored:
            origin_ids.extend(item.origin_ids)
        return RetrievedChunk(
            chunk=Chunk(
                id=first.id,
                document_id=first.document_id,
                text=text,
                position=first.position,
                anchor=anchor,
                document=first.document,
            ),
            score=SimilarityScore(max(item.score.value for item in scored)),
            lexical_coverage=max(item.lexical_coverage for item in scored),
            fused_score=max(item.fused_score for item in scored),
            source_chunk_ids=tuple(dict.fromkeys(origin_ids)),
        )

    @staticmethod
    def _join_texts(texts: Sequence[str]) -> str:
        """Concatena eliminando el solapamiento de FR-03 entre piezas consecutivas."""
        merged = texts[0] if texts else ""
        for text in texts[1:]:
            overlap = 0
            for size in range(min(_MAX_OVERLAP, len(merged), len(text)), _MIN_OVERLAP - 1, -1):
                if merged.endswith(text[:size]):
                    overlap = size
                    break
            merged = f"{merged}{text[overlap:]}" if overlap else f"{merged}\n{text}"
        return merged

    @staticmethod
    def _fingerprint(text: str) -> str:
        return " ".join(fold(text).split())
