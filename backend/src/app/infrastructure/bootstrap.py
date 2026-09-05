"""Startup-only seeding for the Sprint 1 demo: a predefined admin account and a bundled
document corpus, so `docker compose up` alone is enough to run the demo end to end.

This is purely additive orchestration on top of existing ports (UserRepositoryPort,
AuthPort, DocumentRepositoryPort) — it does not change ADR-0003/ADR-0004 or any port
contract, and both real use cases it wraps (RegisterStudentUseCase, IngestDocumentUseCase)
remain exactly as approved.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.auth_dto import RegisterStudentRequest
from app.application.dto.document_dto import IngestDocumentRequest
from app.application.use_cases.ingest_document import IngestDocumentUseCase
from app.application.use_cases.register_student import RegisterStudentUseCase
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.document_text_extractor_port import DocumentTextExtractorPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.infrastructure.adapters.persistence.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.adapters.persistence.postgres_user_repository import PostgresUserRepository
from app.infrastructure.config.settings import AppSettings, AuthSettings
from app.shared.exceptions.domain_errors import DuplicateUserError


async def seed_default_admin(
    session: AsyncSession, auth_port: AuthPort, auth_settings: AuthSettings
) -> None:
    user_repository = PostgresUserRepository(session)
    use_case = RegisterStudentUseCase(user_repository, auth_port, auth_settings)
    try:
        await use_case.execute(
            RegisterStudentRequest(
                email=auth_settings.default_admin_email,
                plain_password=auth_settings.default_admin_password,
            )
        )
        await session.commit()
        logger.info("Cuenta admin de demo creada: {}", auth_settings.default_admin_email)
    except DuplicateUserError:
        await session.rollback()
        logger.info("Cuenta admin de demo ya existía: {}", auth_settings.default_admin_email)


async def seed_documents_from_directory(
    session: AsyncSession,
    text_extractor: DocumentTextExtractorPort,
    embedding_port: EmbeddingPort,
    vector_store_port: VectorStorePort,
    app_settings: AppSettings,
) -> None:
    directory = Path(app_settings.seed_documents_dir)
    if not directory.is_dir():
        logger.warning("Directorio de documentos de arranque no encontrado: {}", directory)
        return

    document_repository: DocumentRepositoryPort = PostgresDocumentRepository(session)
    already_indexed = {d.filename for d in await document_repository.list_all()}

    pipeline = DocumentIndexingPipeline(
        text_extractor=text_extractor,
        embedding_port=embedding_port,
        vector_store_port=vector_store_port,
    )
    use_case = IngestDocumentUseCase(document_repository=document_repository, indexing_pipeline=pipeline)

    for pdf_path in sorted(directory.glob("*.pdf")):
        if pdf_path.name in already_indexed:
            continue
        result = await use_case.execute(
            IngestDocumentRequest(filename=pdf_path.name, file_path=pdf_path)
        )
        await session.commit()
        if result.status.value == "indexed":
            logger.info("Documento de arranque indexado: {} ({} fragmentos)", pdf_path.name, result.chunk_count)
        else:
            logger.error("Fallo al indexar documento de arranque {}: {}", pdf_path.name, result.error_message)
