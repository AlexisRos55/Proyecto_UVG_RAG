from app.infrastructure.adapters.document_processing.text_cleaner import RegexTextCleaner


def test_removes_standalone_page_number_lines() -> None:
    cleaner = RegexTextCleaner()
    raw = "Artículo 1. Disposiciones generales.\n12\nArtículo 2. Definiciones."

    cleaned = cleaner.clean(raw)

    assert "\n12\n" not in cleaned
    assert "Artículo 1." in cleaned
    assert "Artículo 2." in cleaned


def test_joins_hyphenated_line_breaks() -> None:
    cleaner = RegexTextCleaner()
    raw = "El estudiante deberá presen-\ntar su solicitud por escrito."

    cleaned = cleaner.clean(raw)

    assert "presentar" in cleaned


def test_collapses_multiple_blank_lines() -> None:
    cleaner = RegexTextCleaner()
    raw = "Primer párrafo.\n\n\n\n\nSegundo párrafo."

    cleaned = cleaner.clean(raw)

    assert "\n\n\n" not in cleaned


def test_collapses_multiple_spaces() -> None:
    cleaner = RegexTextCleaner()
    raw = "Reglamento     estudiantil       UVG."

    cleaned = cleaner.clean(raw)

    assert "  " not in cleaned
