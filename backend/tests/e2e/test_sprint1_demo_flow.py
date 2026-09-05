"""Sprint 1 demo behaviors (ADR-0011): admin auto-seed and automatic corpus ingestion at
startup, exercised against the real backend/documents/ corpus and a real PostgreSQL/ChromaDB.
"""

from __future__ import annotations

import uuid

import pytest

from tests.e2e.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

pytestmark = pytest.mark.integration

KNOWN_DEMO_DOCUMENTS = {
    "reglamento_estudiantil.pdf",
    "becas_y_beneficios.pdf",
    "seguro_estudiantil.pdf",
}


def test_seeded_admin_account_can_log_in_without_registering(client) -> None:
    response = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_seeded_corpus_is_indexed_and_cited_as_a_source(client, admin_token: str) -> None:
    documents_response = client.get(
        "/admin/documents", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert documents_response.status_code == 200
    indexed_filenames = {d["filename"] for d in documents_response.json()}
    assert KNOWN_DEMO_DOCUMENTS.issubset(indexed_filenames)

    email = f"e2e.sprint1.{uuid.uuid4().hex[:10]}@uvg.edu.gt"
    client.post("/auth/register", json={"email": email, "password": "claveSegura123"})
    login = client.post("/auth/login", json={"email": email, "password": "claveSegura123"})
    token = login.json()["session_token"]

    chat_response = client.post(
        "/chat",
        json={"question": "¿Con cuántos días de anticipación debo solicitar mi reincorporación?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert chat_response.status_code == 200
    body = chat_response.json()
    assert body["is_grounded"] is True
    assert len(body["sources"]) >= 1
    assert body["sources"][0]["document_name"] in KNOWN_DEMO_DOCUMENTS
    assert body["sources"][0]["page_number"] is None
