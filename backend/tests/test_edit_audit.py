from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.audit import verify_chain
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr("app.routes.documents.UPLOAD_DIR", tmp_path)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def register_and_login(client, email):
    response = client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201
    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload_text_document(client, headers):
    response = client.post(
        "/documents",
        files={"file": ("sample.txt", b"original", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def edit_events_and_chain(client, doc_id):
    db_dependency = app.dependency_overrides[get_db]()
    db = next(db_dependency)
    try:
        events = db.execute(
            select(
                AuditLog.user_id,
                AuditLog.document_id,
                AuditLog.action,
                AuditLog.result,
                AuditLog.timestamp,
            )
            .where(AuditLog.document_id == doc_id, AuditLog.action == "edit")
            .order_by(AuditLog.id)
        ).all()
        return events, verify_chain(db)
    finally:
        db_dependency.close()


def test_successful_edit_creates_one_correct_audit_event(client):
    owner_headers = register_and_login(client, "edit-owner@example.com")
    owner_id = client.get("/auth/me", headers=owner_headers).json()["id"]
    doc_id = upload_text_document(client, owner_headers)
    edit_started_at = datetime.now(timezone.utc)

    response = client.put(
        f"/documents/{doc_id}",
        files={"file": ("updated.txt", b"updated", "text/plain")},
        headers=owner_headers,
    )

    assert response.status_code == 200
    events, _ = edit_events_and_chain(client, doc_id)
    assert len(events) == 1
    event = events[0]
    assert event.user_id == owner_id
    assert event.document_id == doc_id
    assert event.action == "edit"
    assert event.result == "allowed"
    assert event.timestamp is not None
    event_timestamp = event.timestamp
    if event_timestamp.tzinfo is None:
        event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
    assert edit_started_at <= event_timestamp <= datetime.now(timezone.utc)


def test_unauthorized_edit_creates_no_success_event(client):
    owner_headers = register_and_login(client, "edit-owner@example.com")
    stranger_headers = register_and_login(client, "edit-stranger@example.com")
    doc_id = upload_text_document(client, owner_headers)

    response = client.put(
        f"/documents/{doc_id}",
        files={"file": ("updated.txt", b"updated", "text/plain")},
        headers=stranger_headers,
    )

    assert response.status_code == 404
    events, _ = edit_events_and_chain(client, doc_id)
    assert not [event for event in events if event.result == "allowed"]
    assert any(event.result == "denied" for event in events)


def test_failed_edit_creates_no_success_event(client):
    owner_headers = register_and_login(client, "edit-owner@example.com")
    doc_id = upload_text_document(client, owner_headers)

    response = client.put(
        f"/documents/{doc_id}",
        files={"file": ("invalid.pdf", b"not a pdf", "application/pdf")},
        headers=owner_headers,
    )

    assert response.status_code == 400
    events, _ = edit_events_and_chain(client, doc_id)
    assert not [event for event in events if event.result == "allowed"]


def test_audit_chain_verifies_after_successful_edit(client):
    owner_headers = register_and_login(client, "edit-owner@example.com")
    doc_id = upload_text_document(client, owner_headers)

    response = client.put(
        f"/documents/{doc_id}",
        files={"file": ("updated.txt", b"updated", "text/plain")},
        headers=owner_headers,
    )

    assert response.status_code == 200
    _, chain_result = edit_events_and_chain(client, doc_id)
    assert chain_result["ok"] is True
