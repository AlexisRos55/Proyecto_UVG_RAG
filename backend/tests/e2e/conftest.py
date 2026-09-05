from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Environment must be set before app.infrastructure.config.settings is first imported/cached,
# since every get_*_settings() provider is memoized with functools.lru_cache.
os.environ.setdefault("ANTHROPIC_API_KEY", "e2e-test-key-unused-because-overridden")
os.environ.setdefault("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://rag_app:devpassword@localhost:5433/asistente_rag"
)
os.environ.setdefault("SESSION_SECRET", "e2e-test-secret-32-bytes-minimum-length!!")
os.environ.setdefault("ALLOWED_EMAIL_DOMAIN", "uvg.edu.gt")
os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="chroma_e2e_"))
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("DOCUMENTS_STORAGE_DIR", tempfile.mkdtemp(prefix="documents_e2e_"))
os.environ.setdefault("ADMIN_EMAILS", "admin.e2e@uvg.edu.gt")
# Absolute path (CWD-independent): exercises the real sprint 1 auto-seeding (ADR-0011)
# against the real demo corpus, instead of a throwaway fixture directory.
os.environ.setdefault(
    "SEED_DOCUMENTS_DIR", str(Path(__file__).resolve().parents[2] / "documents")
)
os.environ.setdefault("DEFAULT_ADMIN_EMAIL", "admin.e2e@uvg.edu.gt")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "adminE2ESeguro123")

ADMIN_EMAIL = "admin.e2e@uvg.edu.gt"
ADMIN_PASSWORD = "adminE2ESeguro123"

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.entrypoints.api.dependencies import get_verification_port
from app.infrastructure.entrypoints.api.main import app
from tests.fakes.fake_rag_ports import FakeVerificationStrategyPort


@pytest.fixture(scope="session", autouse=True)
def _reset_postgres_state() -> None:
    """Truncates tables once before the e2e session starts.

    CHROMA_PERSIST_DIR above is a fresh temp directory per pytest process, but the
    PostgreSQL dev container is long-lived across runs. Without this, a document already
    recorded in PostgreSQL from a previous run makes seed_documents_from_directory (ADR-0011)
    skip re-ingesting it, while the fresh ChromaDB has no vectors for it at all — a
    Postgres/Chroma split-brain that only exists in this test setup, not in docker-compose
    (where both volumes are always paired), but that would otherwise make e2e tests flaky.
    """
    database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE messages, conversations, documents, users CASCADE")


@pytest.fixture
def verification_double() -> FakeVerificationStrategyPort:
    return FakeVerificationStrategyPort()


@pytest.fixture
def client(verification_double: FakeVerificationStrategyPort):
    """A TestClient with the real app (real Postgres, real Chroma, real embeddings) except
    for the paid Anthropic call, which is overridden to keep e2e tests free and offline.
    """
    app.dependency_overrides[get_verification_port] = lambda: verification_double
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client: TestClient) -> str:
    """Logs into the admin account seeded automatically at startup (ADR-0011)."""
    login_response = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert login_response.status_code == 200, login_response.text
    return login_response.json()["session_token"]
