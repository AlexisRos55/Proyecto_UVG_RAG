"""End-to-end tests against the real FastAPI app: real PostgreSQL, real ChromaDB, real
Sentence-Transformers embeddings. Only the paid Anthropic call is stubbed (see conftest.py)."""

from __future__ import annotations

import uuid

import pytest

from app.domain.value_objects.verified_answer import VerificationConfidence, VerifiedAnswer

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"e2e.{uuid.uuid4().hex[:12]}@uvg.edu.gt"


def test_health_check_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_then_login_flow(client) -> None:
    email = _unique_email()

    register_response = client.post(
        "/auth/register", json={"email": email, "password": "claveSegura123"}
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == email

    login_response = client.post(
        "/auth/login", json={"email": email, "password": "claveSegura123"}
    )
    assert login_response.status_code == 200
    assert login_response.json()["session_token"]


def test_register_rejects_non_institutional_email(client) -> None:
    response = client.post(
        "/auth/register", json={"email": "alguien@gmail.com", "password": "claveSegura123"}
    )
    assert response.status_code == 422


def test_login_with_wrong_password_returns_401(client) -> None:
    email = _unique_email()
    client.post("/auth/register", json={"email": email, "password": "claveSegura123"})

    response = client.post("/auth/login", json={"email": email, "password": "incorrecta"})

    assert response.status_code == 401


def test_chat_requires_authentication(client) -> None:
    response = client.post("/chat", json={"question": "¿Cómo me reincorporo?"})
    assert response.status_code == 401


def test_chat_abstains_when_verification_marks_answer_as_not_grounded(client, verification_double) -> None:
    """FR-08. Since sprint 1 (ADR-0011) the backend auto-seeds a real demo corpus at startup, so
    a "no chunks retrieved at all" scenario is no longer reliable to assert against with a real,
    shared, growing test corpus (an on-topic-sounding or even nonsense question can occasionally
    cross the similarity threshold by chance). Configuring the verification double directly tests
    the other, equally real abstention path deterministically: the LLM says it is not grounded.
    """
    verification_double.configured_answer = VerifiedAnswer(
        answer_text="Una respuesta que el modelo no pudo fundamentar en el contexto.",
        is_grounded=False,
        confidence=VerificationConfidence.LOW,
    )

    email = _unique_email()
    client.post("/auth/register", json={"email": email, "password": "claveSegura123"})
    login = client.post("/auth/login", json={"email": email, "password": "claveSegura123"})
    token = login.json()["session_token"]

    response = client.post(
        "/chat",
        json={"question": "¿Cuánto cubre la beca de excelencia académica?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_grounded"] is False
    assert body["sources"] == []


def test_chat_history_round_trips_after_asking_a_question(client) -> None:
    email = _unique_email()
    client.post("/auth/register", json={"email": email, "password": "claveSegura123"})
    login = client.post("/auth/login", json={"email": email, "password": "claveSegura123"})
    token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/chat", json={"question": "pregunta de prueba"}, headers=headers)
    history_response = client.get("/chat/history", headers=headers)

    assert history_response.status_code == 200
    conversations = history_response.json()
    assert len(conversations) == 1
    assert len(conversations[0]["messages"]) == 2
