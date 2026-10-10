"""Modo invitado de punta a punta (ADR-0019): app real, PostgreSQL real, ChromaDB real.

Solo la llamada de pago a Anthropic se sustituye (ver conftest.py).
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration

GUEST_PERSONAL_DATA = "Esa información únicamente está disponible para usuarios autenticados mediante una cuenta institucional"
ADMIN_ENDPOINTS = (
    ("get", "/admin/documents"),
    ("get", f"/admin/documents/{uuid.uuid4()}"),
    ("delete", f"/admin/documents/{uuid.uuid4()}"),
    ("post", f"/admin/documents/{uuid.uuid4()}/reindex"),
)


def _guest(client) -> dict:
    response = client.post("/auth/guest")
    assert response.status_code == 201, response.text
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_a_visitor_enters_without_email_or_password(client) -> None:
    session = _guest(client)
    assert session["role"] == "guest" and session["email"] is None and session["session_token"]


def test_institutional_login_still_works_next_to_guest_mode(client) -> None:
    _guest(client)
    email = f"e2e.{uuid.uuid4().hex[:12]}@uvg.edu.gt"
    client.post("/auth/register", json={"email": email, "password": "claveSegura123"})
    login = client.post("/auth/login", json={"email": email, "password": "claveSegura123"})
    assert login.status_code == 200 and login.json()["role"] == "student"


def test_a_guest_can_never_reach_the_administrative_panel(client) -> None:
    token = _guest(client)["session_token"]
    for method, path in ADMIN_ENDPOINTS:
        response = getattr(client, method)(path, headers=_auth(token))
        assert response.status_code == 401, (method, path, response.status_code)
    upload = client.post(
        "/admin/documents", headers=_auth(token), files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")}
    )
    assert upload.status_code == 401


def test_a_guest_converses_and_the_conversation_is_remembered(client) -> None:
    token = _guest(client)["session_token"]

    answer = client.post("/chat", json={"question": "Quiero estudiar en UVG, ¿cómo es la admisión?"}, headers=_auth(token))
    assert answer.status_code == 200
    assert not answer.json()["answer_text"].startswith(GUEST_PERSONAL_DATA)

    history = client.get("/chat/history", headers=_auth(token))
    assert history.status_code == 200 and history.json()


def test_a_guest_asking_for_personal_data_is_pointed_to_the_institutional_account(client) -> None:
    token = _guest(client)["session_token"]
    response = client.post("/chat", json={"question": "¿Cuál es mi promedio?"}, headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["answer_text"].startswith(GUEST_PERSONAL_DATA)


def test_a_student_asking_for_personal_data_keeps_the_original_answer(client) -> None:
    email = f"e2e.{uuid.uuid4().hex[:12]}@uvg.edu.gt"
    token = client.post("/auth/register", json={"email": email, "password": "claveSegura123"}).json()["session_token"]
    response = client.post("/chat", json={"question": "¿Cuál es mi promedio?"}, headers=_auth(token))
    assert response.status_code == 200
    assert not response.json()["answer_text"].startswith(GUEST_PERSONAL_DATA)
