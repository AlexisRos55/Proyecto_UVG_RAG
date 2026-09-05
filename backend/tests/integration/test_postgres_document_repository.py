import pytest

from app.domain.entities.document import Document, DocumentStatus
from app.infrastructure.adapters.persistence.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id

pytestmark = pytest.mark.integration


def _pending_document(filename: str) -> Document:
    return Document(
        id=new_id(),
        filename=filename,
        status=DocumentStatus.PENDING,
        uploaded_at=utc_now(),
        storage_path=f"/data/documents/{filename}",
    )


@pytest.mark.asyncio
async def test_add_and_get_by_id(db_session) -> None:
    repository = PostgresDocumentRepository(db_session)
    document = _pending_document("reglamento_estudiantil.pdf")

    await repository.add(document)
    found = await repository.get_by_id(document.id)

    assert found is not None
    assert found.status is DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_update_status_to_indexed_sets_indexed_at(db_session) -> None:
    repository = PostgresDocumentRepository(db_session)
    document = _pending_document("becas.pdf")
    await repository.add(document)

    await repository.update_status(document.id, DocumentStatus.INDEXED)

    updated = await repository.get_by_id(document.id)
    assert updated.status is DocumentStatus.INDEXED
    assert updated.indexed_at is not None


@pytest.mark.asyncio
async def test_update_status_to_error_stores_message(db_session) -> None:
    repository = PostgresDocumentRepository(db_session)
    document = _pending_document("corrupto.pdf")
    await repository.add(document)

    await repository.update_status(document.id, DocumentStatus.ERROR, error_message="PDF ilegible")

    updated = await repository.get_by_id(document.id)
    assert updated.status is DocumentStatus.ERROR
    assert updated.error_message == "PDF ilegible"


@pytest.mark.asyncio
async def test_list_all_and_delete(db_session) -> None:
    repository = PostgresDocumentRepository(db_session)
    document = _pending_document("seguros.pdf")
    await repository.add(document)

    all_documents = await repository.list_all()
    assert any(d.id == document.id for d in all_documents)

    await repository.delete(document.id)
    assert await repository.get_by_id(document.id) is None
