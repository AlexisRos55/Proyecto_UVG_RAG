"""EPIC-7 end-to-end tests: real Postgres, real ChromaDB, real embeddings, real file storage."""

from __future__ import annotations

import io
import uuid

import pymupdf
import pytest

pytestmark = pytest.mark.integration


def _sample_pdf_bytes() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Reglamento de becas: cubre hasta el 50% de la colegiatura.")
    buffer = io.BytesIO(document.tobytes())
    document.close()
    return buffer.getvalue()


def _student_token(client) -> str:
    email = f"estudiante.{uuid.uuid4().hex[:10]}@uvg.edu.gt"
    client.post("/auth/register", json={"email": email, "password": "claveSegura123"})
    login = client.post("/auth/login", json={"email": email, "password": "claveSegura123"})
    return login.json()["session_token"]


def test_student_cannot_access_admin_endpoints(client) -> None:
    token = _student_token(client)

    response = client.get("/admin/documents", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_admin_can_upload_list_and_get_status(client, admin_token: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    filename = f"becas_{uuid.uuid4().hex[:8]}.pdf"

    upload_response = client.post(
        "/admin/documents",
        headers=headers,
        files={"file": (filename, _sample_pdf_bytes(), "application/pdf")},
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["status"] == "indexed"
    assert body["chunk_count"] > 0
    document_id = body["document_id"]

    list_response = client.get("/admin/documents", headers=headers)
    assert list_response.status_code == 200
    assert any(d["document_id"] == document_id for d in list_response.json())

    status_response = client.get(f"/admin/documents/{document_id}", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "indexed"

    # Cleanup: other e2e tests share this ChromaDB/PostgreSQL for the whole session
    # (see conftest.py); leaving this indexed would pollute retrieval for later tests.
    client.delete(f"/admin/documents/{document_id}", headers=headers)


def test_admin_can_reindex_and_delete_document(client, admin_token: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    filename = f"seguros_{uuid.uuid4().hex[:8]}.pdf"
    upload_response = client.post(
        "/admin/documents",
        headers=headers,
        files={"file": (filename, _sample_pdf_bytes(), "application/pdf")},
    )
    document_id = upload_response.json()["document_id"]

    reindex_response = client.post(f"/admin/documents/{document_id}/reindex", headers=headers)
    assert reindex_response.status_code == 200
    assert reindex_response.json()["status"] == "indexed"

    delete_response = client.delete(f"/admin/documents/{document_id}", headers=headers)
    assert delete_response.status_code == 204

    status_response = client.get(f"/admin/documents/{document_id}", headers=headers)
    assert status_response.status_code == 404


def test_upload_rejects_unreadable_file_but_records_it(client, admin_token: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.post(
        "/admin/documents",
        headers=headers,
        files={"file": ("no_es_un_pdf.pdf", b"contenido invalido", "application/pdf")},
    )

    assert response.status_code == 201  # el use case registra el error, no lanza HTTP 500
    assert response.json()["status"] == "error"
