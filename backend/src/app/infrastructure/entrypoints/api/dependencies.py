"""FastAPI dependency providers: the composition root for this entrypoint.

This is the only module allowed to wire concrete adapters into use cases
(docs/04-software-architecture.md, section 2.3). Routers depend only on these
functions, never on adapters directly.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.get_indexing_status import GetIndexingStatusUseCase
from app.application.use_cases.ingest_document import IngestDocumentUseCase
from app.application.use_cases.manage_document import ManageDocumentUseCase
from app.application.use_cases.register_student import RegisterStudentUseCase
from app.application.use_cases.trigger_reindex import TriggerReindexUseCase
from app.domain.entities.user import User
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.domain.ports.document_repository_port import DocumentRepositoryPort
from app.domain.ports.document_text_extractor_port import DocumentTextExtractorPort
from app.domain.ports.embedding_port import EmbeddingPort
from app.domain.ports.user_repository_port import UserRepositoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.verification_strategy_port import VerificationStrategyPort
from app.infrastructure.adapters.document_processing.document_indexing_pipeline import (
    DocumentIndexingPipeline,
)
from app.infrastructure.adapters.persistence.database import get_db_session
from app.infrastructure.adapters.persistence.postgres_conversation_repository import (
    PostgresConversationRepository,
)
from app.infrastructure.adapters.persistence.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.adapters.persistence.postgres_user_repository import PostgresUserRepository
from app.infrastructure.config.settings import (
    AppSettings,
    AuthSettings,
    get_app_settings,
    get_auth_settings,
)
from app.shared.exceptions.domain_errors import UnauthorizedError

# --- Singletons stored on app.state at startup (see app/infrastructure/entrypoints/api/main.py) ---


def get_embedding_port(request: Request) -> EmbeddingPort:
    return request.app.state.embedding_port


def get_vector_store_port(request: Request) -> VectorStorePort:
    return request.app.state.vector_store_port


def get_text_extractor_port(request: Request) -> DocumentTextExtractorPort:
    return request.app.state.text_extractor_port


def get_verification_port(request: Request) -> VerificationStrategyPort:
    return request.app.state.verification_port


def get_auth_port(request: Request) -> AuthPort:
    return request.app.state.auth_port


def get_auth_settings_dependency() -> AuthSettings:
    return get_auth_settings()


def get_app_settings_dependency() -> AppSettings:
    return get_app_settings()


# --- Per-request repositories (bound to a per-request DB session) ---


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepositoryPort:
    return PostgresUserRepository(session)


def get_conversation_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationRepositoryPort:
    return PostgresConversationRepository(session)


def get_document_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepositoryPort:
    return PostgresDocumentRepository(session)


# --- Use cases ---


def get_register_use_case(
    user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)],
    auth_port: Annotated[AuthPort, Depends(get_auth_port)],
    auth_settings: Annotated[AuthSettings, Depends(get_auth_settings_dependency)],
) -> RegisterStudentUseCase:
    return RegisterStudentUseCase(user_repository, auth_port, auth_settings)


def get_authenticate_use_case(
    user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)],
    auth_port: Annotated[AuthPort, Depends(get_auth_port)],
    auth_settings: Annotated[AuthSettings, Depends(get_auth_settings_dependency)],
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(user_repository, auth_port, auth_settings)


def get_answer_query_use_case(
    embedding_port: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    vector_store_port: Annotated[VectorStorePort, Depends(get_vector_store_port)],
    verification_port: Annotated[VerificationStrategyPort, Depends(get_verification_port)],
    conversation_repository: Annotated[
        ConversationRepositoryPort, Depends(get_conversation_repository)
    ],
    document_repository: Annotated[DocumentRepositoryPort, Depends(get_document_repository)],
) -> AnswerStudentQueryUseCase:
    return AnswerStudentQueryUseCase(
        embedding_port=embedding_port,
        vector_store_port=vector_store_port,
        verification_port=verification_port,
        conversation_repository=conversation_repository,
        document_repository=document_repository,
    )


def get_indexing_pipeline(
    text_extractor: Annotated[DocumentTextExtractorPort, Depends(get_text_extractor_port)],
    embedding_port: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    vector_store_port: Annotated[VectorStorePort, Depends(get_vector_store_port)],
) -> DocumentIndexingPipeline:
    return DocumentIndexingPipeline(
        text_extractor=text_extractor,
        embedding_port=embedding_port,
        vector_store_port=vector_store_port,
    )


def get_ingest_document_use_case(
    document_repository: Annotated[DocumentRepositoryPort, Depends(get_document_repository)],
    indexing_pipeline: Annotated[DocumentIndexingPipeline, Depends(get_indexing_pipeline)],
) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        document_repository=document_repository,
        indexing_pipeline=indexing_pipeline,
    )


def get_trigger_reindex_use_case(
    document_repository: Annotated[DocumentRepositoryPort, Depends(get_document_repository)],
    vector_store_port: Annotated[VectorStorePort, Depends(get_vector_store_port)],
    indexing_pipeline: Annotated[DocumentIndexingPipeline, Depends(get_indexing_pipeline)],
) -> TriggerReindexUseCase:
    return TriggerReindexUseCase(
        document_repository=document_repository,
        vector_store_port=vector_store_port,
        indexing_pipeline=indexing_pipeline,
    )


def get_manage_document_use_case(
    document_repository: Annotated[DocumentRepositoryPort, Depends(get_document_repository)],
    vector_store_port: Annotated[VectorStorePort, Depends(get_vector_store_port)],
) -> ManageDocumentUseCase:
    return ManageDocumentUseCase(
        document_repository=document_repository, vector_store_port=vector_store_port
    )


def get_indexing_status_use_case(
    document_repository: Annotated[DocumentRepositoryPort, Depends(get_document_repository)],
) -> GetIndexingStatusUseCase:
    return GetIndexingStatusUseCase(document_repository=document_repository)


# --- Authentication / authorization dependencies ---


async def get_current_user(
    auth_port: Annotated[AuthPort, Depends(get_auth_port)],
    user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Falta el encabezado Authorization con el token de sesión")

    token = authorization.split(" ", 1)[1].strip()
    user_id: UUID = auth_port.decode_session_token(token)

    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("El usuario de la sesión ya no existe")
    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise UnauthorizedError("Esta acción requiere el rol de administrador")
    return current_user
