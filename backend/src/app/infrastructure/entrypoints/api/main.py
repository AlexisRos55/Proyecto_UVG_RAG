from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.infrastructure.adapters.auth.institutional_auth_adapter import InstitutionalAuthAdapter
from app.infrastructure.adapters.document_processing.pymupdf_extractor import (
    PyMuPDFExtractorAdapter,
)
from app.infrastructure.adapters.llm.anthropic_llm_adapter import AnthropicLLMAdapter
from app.infrastructure.adapters.llm.single_call_verification_adapter import (
    SingleCallVerificationAdapter,
)
from app.infrastructure.adapters.persistence.database import get_engine, get_session_factory
from app.infrastructure.adapters.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.vector_store.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingAdapter,
)
from app.infrastructure.bootstrap import seed_default_admin, seed_documents_from_directory
from app.infrastructure.config.settings import (
    get_anthropic_settings,
    get_app_settings,
    get_auth_settings,
    get_chroma_settings,
)
from app.infrastructure.entrypoints.api.middlewares.error_handlers import (
    register_exception_handlers,
)
from app.infrastructure.entrypoints.api.routers import admin_documents, auth, chat, health


def _configure_logging() -> None:
    settings = get_app_settings()
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level, backtrace=False, diagnose=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Composition root: builds every singleton adapter once per process (NFR-01, NFR-02)."""
    _configure_logging()

    chroma_settings = get_chroma_settings()
    anthropic_settings = get_anthropic_settings()
    auth_settings = get_auth_settings()

    app.state.embedding_port = SentenceTransformersEmbeddingAdapter()
    app.state.vector_store_port = ChromaVectorStoreAdapter(
        persist_directory=chroma_settings.chroma_persist_dir
    )
    app.state.text_extractor_port = PyMuPDFExtractorAdapter()
    llm_port = AnthropicLLMAdapter(anthropic_settings)
    app.state.verification_port = SingleCallVerificationAdapter(llm_port)
    app.state.auth_port = InstitutionalAuthAdapter(auth_settings)

    app_settings = get_app_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_default_admin(session, app.state.auth_port, auth_settings)
    async with session_factory() as session:
        await seed_documents_from_directory(
            session,
            app.state.text_extractor_port,
            app.state.embedding_port,
            app.state.vector_store_port,
            app_settings,
        )

    logger.info("Asistente Virtual RAG UVG Altiplano - backend listo (modelo={})", anthropic_settings.model)
    yield

    await get_engine().dispose()


def create_app() -> FastAPI:
    app_settings = get_app_settings()
    app = FastAPI(
        title="Asistente Virtual RAG - UVG Altiplano",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(admin_documents.router)

    return app


app = create_app()
