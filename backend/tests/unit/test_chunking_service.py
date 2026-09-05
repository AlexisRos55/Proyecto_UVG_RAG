from app.infrastructure.adapters.document_processing.chunking_service import FixedSizeChunkingService


def test_split_respects_chunk_size_and_overlap() -> None:
    service = FixedSizeChunkingService(chunk_size=20, overlap=5)
    text = "a" * 50

    chunks = service.split(text)

    assert all(len(chunk) <= 20 for chunk in chunks)
    assert len(chunks) > 1


def test_split_empty_text_returns_no_chunks() -> None:
    service = FixedSizeChunkingService()
    assert service.split("   ") == []


def test_split_short_text_returns_single_chunk() -> None:
    service = FixedSizeChunkingService(chunk_size=1000, overlap=100)
    text = "Reglamento estudiantil de UVG Altiplano."

    chunks = service.split(text)

    assert chunks == [text]


def test_consecutive_chunks_overlap() -> None:
    service = FixedSizeChunkingService(chunk_size=20, overlap=5)
    text = "0123456789" * 5  # 50 chars

    chunks = service.split(text)

    first_tail = chunks[0][-5:]
    second_head = chunks[1][:5]
    assert first_tail == second_head


def test_rejects_invalid_configuration() -> None:
    try:
        FixedSizeChunkingService(chunk_size=10, overlap=10)
        raise AssertionError("debía rechazar chunk_size <= overlap")
    except ValueError:
        pass
