"""Limpieza de membretes, reconstrucción de estructura y fragmentación estructural (ADR-0012)."""

from app.infrastructure.adapters.document_processing.page_boilerplate import PageBoilerplateRemover
from app.infrastructure.adapters.document_processing.structural_chunking_service import (
    StructuralChunkingService,
)
from app.infrastructure.adapters.document_processing.structure_parser import DocumentStructureParser

_HEADER = (
    "UNIVERSIDAD DEL VALLE DE GUATEMALA\nCódigo:\nUVG.DAF.02.001\nPáginas:\n20\n"
    "REGLAMENTO DE AYUDAS FINANCIERAS\nVersión:\n10.0\nVigencia:\n\nPágina {n} de 20\n"
)


def _pages(*bodies: str) -> tuple[str, ...]:
    return tuple(_HEADER.format(n=index) + body for index, body in enumerate(bodies, start=1))


def test_letterhead_repeated_on_most_pages_is_removed_and_its_fields_captured() -> None:
    result = PageBoilerplateRemover().remove(
        _pages("Artículo 1. Objeto.", "a.\nPrimer inciso", "Artículo 2. Alcance.")
    )

    joined = "\n".join(result.pages)
    assert "UNIVERSIDAD DEL VALLE" not in joined
    assert "Página" not in joined
    # Los valores numéricos del membrete también se retiran por su posición…
    assert "\n20\n" not in f"\n{joined}\n" and "10.0" not in joined
    # …pero los incisos sueltos, que también se repiten, se conservan.
    assert "a." in joined
    assert result.fields == {"code": "UVG.DAF.02.001", "version": "10.0"}
    assert "REGLAMENTO DE AYUDAS FINANCIERAS" in result.header_lines


def test_short_documents_are_not_stripped_by_repetition() -> None:
    pages = ("Folleto\nBecas disponibles", "Folleto\nContacto")
    assert PageBoilerplateRemover().remove(pages).pages == pages


def test_table_of_contents_lines_are_removed() -> None:
    result = PageBoilerplateRemover().remove(("Contenido\nCAPITULO 1 ........ 2\nTexto real",))
    assert result.pages == ("Texto real",)


def test_parser_recovers_chapters_articles_titles_and_pages() -> None:
    units = DocumentStructureParser().parse(
        (
            "CAPITULO 1\nDISPOSICIONES GENERALES\nArtículo 1. Objetivo General. El programa\ntiene como objetivo apoyar.",
            "Artículo 2. Alcance. Aplica a todos\nlos campus.\nCAPITULO II\nRÉGIMEN FINANCIERO\nArtículo 3. Fondo. Se constituye.",
        )
    )

    labels = [unit.anchor.location_label for unit in units]
    assert labels == [
        "Capítulo 1. Disposiciones generales · Artículo 1. Objetivo General",
        "Capítulo 1. Disposiciones generales · Artículo 2. Alcance",
        "Capítulo II. Régimen financiero · Artículo 3. Fondo",
    ]
    # Las líneas partidas del PDF se reconstruyen en una sola oración.
    assert "El programa tiene como objetivo apoyar." in units[0].text
    assert (units[1].anchor.page_start, units[2].anchor.page_start) == (2, 2)


def test_two_line_chapter_titles_are_joined() -> None:
    units = DocumentStructureParser().parse(
        (
            ("CAPITULO VI\nAYUDA FINANCIERA PARA ESTUDIANTES DE PROGRAMAS OFRECIDOS POR\n"
            "APRENDIZAJE VIRTUAL DE EXCELENCIA -AVE-\nArtículo 27. Generalidades. Texto."),
        )
    )
    assert units[0].anchor.chapter == (
        "Capítulo VI. Ayuda financiera para estudiantes de programas ofrecidos por "
        "aprendizaje virtual de excelencia -AVE-"
    )


def test_mistyped_chapter_continuing_the_article_sequence_is_read_as_an_article() -> None:
    # Errata real del corpus: «Capítulo 35. Procedimiento…» justo tras el Artículo 34.
    units = DocumentStructureParser().parse(
        (
            ("CAPITULO VI\nPROGRAMAS AVE\nArtículo 34. Penalizaciones. Texto.\n"
            "Capítulo 35. Procedimiento. Las solicitudes de Becas AVE serán atendidas por el área de operaciones."),
        )
    )
    last = units[-1].anchor
    assert last.article_from == 35
    assert last.chapter is not None and last.chapter.startswith("Capítulo VI")


def test_change_log_is_a_document_level_section() -> None:
    units = DocumentStructureParser().parse(
        ("CAPITULO VII\nOTRAS CONSIDERACIONES\nArtículo 38. Vigencia. Entra en vigor.\nControl de Cambios\nNo.\n9.0 Acta 06-2025",)
    )
    assert units[-1].anchor.chapter is None
    assert units[-1].anchor.section == "Control de Cambios"


def test_structural_chunks_respect_size_overlap_and_per_piece_pages() -> None:
    long_article = "Artículo 6. Directrices. " + " ".join(f"Oración número {i} del artículo." for i in range(60))
    units = DocumentStructureParser().parse((long_article[:900], long_article[900:]))
    pieces = StructuralChunkingService(max_chars=300, overlap=60).split(units)

    assert len(pieces) > 3
    assert all(len(piece.text) <= 300 for piece in pieces)
    assert all(piece.anchor.article_from == 6 for piece in pieces)
    assert pieces[0].anchor.page_start == 1 and pieces[-1].anchor.page_end == 2
    # Solapamiento: el comienzo de cada pieza repite el final de la anterior.
    assert pieces[1].text[:20] in pieces[0].text


def test_tiny_neighbouring_articles_are_grouped_within_a_chapter() -> None:
    units = DocumentStructureParser().parse(
        ("CAPITULO 2\nELECCIONES\nArtículo 7. Voto. Es secreto.\nArtículo 8. Padrón. Se verifica.",)
    )
    pieces = StructuralChunkingService(max_chars=600).split(units)
    assert len(pieces) == 1
    assert pieces[0].anchor.article_label == "Artículos 7 a 8"
