import pytest

from app.domain.services.document_naming import repair_mojibake, resolve_title, title_from_filename
from app.domain.services.spanish_text import analyze, fold, light_stem, sentence_case


def test_fold_removes_accents_and_typographic_ligatures() -> None:
    # PyMuPDF entrega la ligadura «ﬁ»; sin NFKC «suficiencia» nunca coincidiría.
    assert fold("Exámenes de suﬁciencia") == "examenes de suficiencia"


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("becas", "beca"),
        ("inscripciones", "inscripcion"),
        ("retirar", "retiro"),
        ("pagar", "pago"),
        ("lugares", "lugar"),
        ("financieras", "financiero"),
    ],
)
def test_light_stem_unifies_number_gender_and_infinitive(left: str, right: str) -> None:
    assert light_stem(left) == light_stem(right)


def test_light_stem_does_not_treat_short_er_nouns_as_infinitives() -> None:
    # «primer ingreso» y «primero» deben seguir coincidiendo.
    assert light_stem("primer") == light_stem("primero")


def test_analyze_drops_stopwords_and_interrogatives() -> None:
    assert analyze("¿Cuándo es la feria de becas?") == ["feri", "bec"]


def test_sentence_case_keeps_acronyms_and_roman_numerals_only_after_divisions() -> None:
    assert sentence_case("CAPITULO IV PROGRAMAS AVE", frozenset({"AVE"})) == "Capitulo IV programas AVE"
    assert sentence_case("DERECHO CIVIL") == "Derecho civil"


def test_repair_mojibake_fixes_cp437_names_and_never_touches_sane_ones() -> None:
    assert repair_mojibake("Educaci¢n F°sica 2025") == "Educación Física 2025"
    assert repair_mojibake("Proceso de Admisión") == "Proceso de Admisión"


def test_title_from_filename_strips_storage_prefix_code_and_version() -> None:
    name = "24b8330cd5d342c4906514008bb252b6_UVG.DAF.02.001 Reglamento ayudas financieras V 10.0  (27-5-26).pdf"
    assert title_from_filename(name) == "Reglamento ayudas financieras"


def test_resolve_title_prefers_letterhead_then_metadata_then_filename() -> None:
    header = ("UNIVERSIDAD DEL VALLE DE GUATEMALA", "REGLAMENTO DE GRUPOS ESTUDIANTILES")
    assert resolve_title("x.pdf", "Otra cosa", header) == "Reglamento de grupos estudiantiles"
    assert resolve_title("x.pdf", "Calendario Académico V3") == "Calendario Académico"
    assert resolve_title("Informática 2025.pdf", "Microsoft Word - borrador") == "Informática 2025"
