from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, UploadFile

from app.application.dto.document_dto import IngestDocumentRequest
from app.application.use_cases.get_indexing_status import GetIndexingStatusUseCase
from app.application.use_cases.ingest_document import IngestDocumentUseCase
from app.application.use_cases.manage_document import ManageDocumentUseCase
from app.application.use_cases.trigger_reindex import TriggerReindexUseCase
from app.domain.entities.user import User
from app.infrastructure.config.settings import AppSettings
from app.infrastructure.entrypoints.api.dependencies import (
    get_app_settings_dependency,
    get_indexing_status_use_case,
    get_ingest_document_use_case,
    get_manage_document_use_case,
    get_trigger_reindex_use_case,
    require_admin,
)
from app.infrastructure.entrypoints.api.schemas.document_schemas import (
    DocumentSummarySchema,
    IngestResultSchema,
)

router = APIRouter(prefix="/admin/documents", tags=["admin"])


def _safe_storage_path(settings: AppSettings, original_filename: str) -> Path:
    storage_dir = Path(settings.documents_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}_{Path(original_filename).name}"
    return storage_dir / safe_name


@router.post("", response_model=IngestResultSchema, status_code=201)
async def upload_document(
    file: UploadFile,
    _: Annotated[User, Depends(require_admin)],
    settings: Annotated[AppSettings, Depends(get_app_settings_dependency)],
    use_case: Annotated[IngestDocumentUseCase, Depends(get_ingest_document_use_case)],
) -> IngestResultSchema:
    """FR-15: sube un nuevo documento PDF y lo indexa de inmediato."""
    destination = _safe_storage_path(settings, file.filename or "documento.pdf")
    contents = await file.read()
    destination.write_bytes(contents)

    result = await use_case.execute(
        IngestDocumentRequest(filename=file.filename or destination.name, file_path=destination)
    )
    return IngestResultSchema.from_dto(result)


@router.get("", response_model=list[DocumentSummarySchema])
async def list_documents(
    _: Annotated[User, Depends(require_admin)],
    use_case: Annotated[GetIndexingStatusUseCase, Depends(get_indexing_status_use_case)],
) -> list[DocumentSummarySchema]:
    """FR-16, FR-19: lista los documentos administrados y su estado de indexación."""
    summaries = await use_case.list_all()
    return [DocumentSummarySchema.from_dto(s) for s in summaries]


@router.get("/{document_id}", response_model=DocumentSummarySchema)
async def get_document_status(
    document_id: UUID,
    _: Annotated[User, Depends(require_admin)],
    use_case: Annotated[GetIndexingStatusUseCase, Depends(get_indexing_status_use_case)],
) -> DocumentSummarySchema:
    """FR-19: estado de indexación de un documento específico."""
    summary = await use_case.get_one(document_id)
    return DocumentSummarySchema.from_dto(summary)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    _: Annotated[User, Depends(require_admin)],
    use_case: Annotated[ManageDocumentUseCase, Depends(get_manage_document_use_case)],
) -> None:
    """FR-17: elimina un documento y sus fragmentos indexados."""
    await use_case.delete(document_id)


@router.post("/{document_id}/reindex", response_model=IngestResultSchema)
async def reindex_document(
    document_id: UUID,
    _: Annotated[User, Depends(require_admin)],
    use_case: Annotated[TriggerReindexUseCase, Depends(get_trigger_reindex_use_case)],
) -> IngestResultSchema:
    """FR-18: dispara manualmente la reindexación de un documento ya administrado."""
    result = await use_case.execute(document_id)
    return IngestResultSchema.from_dto(result)
