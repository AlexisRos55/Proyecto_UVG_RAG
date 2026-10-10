"""Extracción y reconocimiento de entidades del corpus (comprensión documental).

Durante la ingesta, cada documento aporta entidades con nombre propio: programas
de ayuda («Beca Despega»), instancias («Consejo Electoral»), campus, carreras,
eventos fechados y autoridades. El mismo catálogo sirve después para reconocerlas
en las preguntas y en las respuestas, que es lo que permite a la conversación
saber que «esa» es la Beca Despega.

Las reglas se derivaron del corpus real y se consolidan por frecuencia: un nombre
truncado por un salto de línea («Oficina de Vida») se descarta si existe su
forma completa y más frecuente («Oficina de Vida Estudiantil»).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence

from app.domain.entities.chunk import Chunk
from app.domain.services.document_outline_builder import CARD_SECTION
from app.domain.services.spanish_text import STOPWORDS, analyze, fold
from app.domain.value_objects.corpus_entity import CorpusEntity, EntityKind

_CAP = r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ\-]+"
_PROGRAM = re.compile(rf"\b(Becas?|Programa|Crédito|Subsidio)\s+((?:(?:de|del|en|por)\s+)?{_CAP}(?:\s+(?:(?:de|en|del)\s+)?{_CAP}){{0,3}})")
_OFFICE = re.compile(
    rf"\b(Oficina|Dirección|Departamento|Unidad|Comité|Consejo|Registro|Clínica|Decanatura|Área)\s+"
    rf"((?:(?:de|del|de\s+la)\s+)?{_CAP}(?:\s+(?:(?:de|y|del)\s+)?{_CAP}){{0,4}})"
)
_CAMPUS = re.compile(r"\bCampus\s+(Central|Sur|Altiplano|Externos?)\b")
_CAREER = re.compile(
    rf"\b(Licenciatura|Ingeniería|Técnico\s+Universitario|Profesorado|Maestría)\s+en\s+"
    rf"((?:{_CAP}|de|la|para|y|en|del)(?:\s+(?:{_CAP}|de|la|para|y|en|del)){{1,7}})"
)
_EVENT = re.compile(r"(\d{1,2}(?:\s*-\s*\d{1,2})?\s+de\s+[a-záéíóú]+(?:\s+de\s+\d{4})?):\s*([^\n]{6,120})")
_PERSON = re.compile(rf"({_CAP}(?:\s+{_CAP}){{1,3}})\s*[–-]\s*((?:Director|Directora|Decan[oa]|Rector|Vicerrector\w*|Secretari[oa]|Coordinador\w*)[^|;\n]{{0,60}})")

_CATEGORY_STEMS = frozenset(analyze("beca becas programa credito subsidio oficina direccion departamento unidad comite consejo registro clinica decanatura area campus"))
# Palabras demasiado comunes para identificar por sí solas una entidad.
_WEAK_DISTINCTIVE = frozenset(analyze("regular especial general central academico estudiantil estudiantes universidad valle guatemala"))
_TRAILING_CONNECTORS = re.compile(
    r"(?:\s+(?:de|del|la|para|y|en|por|UVG|ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE"
    r"|OCTUBRE|NOVIEMBRE|DICIEMBRE))+$|-+$"
)
_JUNK_PROGRAM = re.compile(r"^(?:Programa|Beca|Crédito|Dr|Ing|Lic)\b")


def entity_key(name: str) -> str:
    return " ".join(analyze(name))


def _distinctive(name: str) -> tuple[str, ...]:
    return tuple(stem for stem in dict.fromkeys(analyze(name)) if stem not in _CATEGORY_STEMS)


class EntityExtractor:
    """Deriva entidades de los fragmentos indexados. Puro y determinista."""

    @staticmethod
    def extract(chunks: Sequence[Chunk]) -> list[CorpusEntity]:
        found: dict[tuple[EntityKind, str], dict] = {}
        counts: Counter[tuple[EntityKind, str]] = Counter()

        def add(kind: EntityKind, raw_name: str, chunk: Chunk, detail: str | None = None) -> None:
            name = " ".join(_TRAILING_CONNECTORS.sub("", raw_name.strip(" .,;:")).split())
            if len(name) < 5:
                return
            key = entity_key(name)
            # Un nombre que solo es la palabra de su clase («Becas») no identifica nada
            # y, además, pasaría por prefijo de todas las demás becas.
            if not key or not _distinctive(name):
                return
            slot = found.setdefault((kind, key), {"names": Counter(), "documents": [], "defined": [], "detail": detail})
            slot["names"][name] += 1
            if chunk.document_id not in slot["documents"]:
                slot["documents"].append(chunk.document_id)
            anchor = chunk.anchor
            if anchor and anchor.article_title and entity_key(anchor.article_title) == key and anchor.article_from is not None:
                pair = (chunk.document_id, anchor.article_from)
                if pair not in slot["defined"]:
                    slot["defined"].append(pair)
            counts[(kind, key)] += 1

        for chunk in chunks:
            text = chunk.text
            title = chunk.anchor.article_title if chunk.anchor else None
            if title and re.match(r"^(Becas?|Programa|Crédito|Subsidio)\b", title):
                add(EntityKind.PROGRAM, title, chunk)
            for match in _PROGRAM.finditer(text):
                if not _JUNK_PROGRAM.match(match.group(2)):
                    add(EntityKind.PROGRAM, f"{match.group(1)} {match.group(2)}", chunk)
            for match in _OFFICE.finditer(text):
                add(EntityKind.OFFICE, f"{match.group(1)} {match.group(2)}", chunk)
            for match in _CAMPUS.finditer(text):
                add(EntityKind.CAMPUS, f"Campus {match.group(1)}", chunk)
            for match in _CAREER.finditer(text):
                add(EntityKind.CAREER, f"{match.group(1)} en {match.group(2)}", chunk)
            for match in _EVENT.finditer(text):
                activity = re.split(r"\s+\d{1,2}(?:\s*-\s*\d{1,2})?\s+de\s+[a-záéíóú]+", match.group(2))[0]
                add(EntityKind.EVENT, activity, chunk, detail=match.group(1))
            if chunk.anchor and chunk.anchor.section == CARD_SECTION:
                for match in _PERSON.finditer(text):
                    add(EntityKind.PERSON, match.group(1), chunk, detail=match.group(2).strip())

        return EntityExtractor._consolidate(found, counts)

    @staticmethod
    def _consolidate(found: dict, counts: Counter) -> list[CorpusEntity]:
        entities: list[CorpusEntity] = []
        keys_by_kind: dict[EntityKind, list[str]] = defaultdict(list)
        for kind, key in found:
            keys_by_kind[kind].append(key)

        for (kind, key), slot in found.items():
            # Dos nombres donde uno prolonga al otro: se conserva el más frecuente.
            # Así se descarta tanto el truncado por un salto de línea («Oficina de
            # Vida», 4 veces, frente a «… Estudiantil», 38) como el que arrastra la
            # celda vecina de una tabla («Crédito Educativo Apoyo Especial Juan», 1,
            # frente a «Crédito Educativo», 3). En empate gana el más corto.
            own = counts[(kind, key)]
            truncated = any(
                other != key
                and (
                    (other.startswith(key + " ") and counts[(kind, other)] > own)
                    or (key.startswith(other + " ") and counts[(kind, other)] >= own)
                )
                for other in keys_by_kind[kind]
            )
            # Instancias mencionadas una sola vez suelen ser ruido de diagramas.
            rare_office = kind is EntityKind.OFFICE and counts[(kind, key)] < 2 and not slot["defined"]
            distinctive = _distinctive(slot["names"].most_common(1)[0][0])
            if truncated or rare_office or not distinctive:
                continue
            entities.append(
                CorpusEntity(
                    name=slot["names"].most_common(1)[0][0],
                    kind=kind,
                    key=key,
                    distinctive=distinctive,
                    document_ids=tuple(slot["documents"]),
                    defined_in=tuple(slot["defined"]),
                    detail=slot["detail"],
                )
            )
        entities.sort(key=lambda e: (e.kind.value, -counts[(e.kind, e.key)], e.name))
        return entities


def find_entities(text: str, entities: Iterable[CorpusEntity], kinds: Iterable[EntityKind] | None = None) -> list[CorpusEntity]:
    """Entidades mencionadas en un texto, de la más específica a la menos.

    Una entidad se reconoce cuando aparecen todas sus palabras distintivas. Si
    solo tiene una y es común («regular»), se exige además la palabra de su
    clase («programa regular»), para no convertir cualquier «regular» en una beca.
    """
    allowed = set(kinds) if kinds is not None else None
    stems = set(analyze(text))
    folded = fold(text)
    matches: list[tuple[int, CorpusEntity]] = []
    for entity in entities:
        if allowed is not None and entity.kind not in allowed:
            continue
        distinctive = set(entity.distinctive) - STOPWORDS
        if not distinctive or not distinctive <= stems:
            continue
        only = next(iter(distinctive)) if len(distinctive) == 1 else None
        # Una instancia con una sola palabra propia («Consejo Directivo») exige su
        # palabra de clase: «junta directiva» no es el Consejo Directivo.
        weak = only is not None and (
            entity.kind is EntityKind.OFFICE or only in _WEAK_DISTINCTIVE or len(only) < 5
        )
        if weak and not (stems & _CATEGORY_STEMS) and fold(entity.name) not in folded:
            continue
        matches.append((len(distinctive), entity))
    matches.sort(key=lambda item: item[0], reverse=True)
    # Si una entidad más específica ya cubre las palabras de otra, la genérica sobra.
    chosen: list[CorpusEntity] = []
    for _, entity in matches:
        if any(set(entity.distinctive) < set(other.distinctive) for other in chosen):
            continue
        if entity.key not in {c.key for c in chosen}:
            chosen.append(entity)
    return chosen

