import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Document, Permission, User


@pytest.fixture
def client():
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


def create_account(client, email, role="user"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201

    if role != "user":
        db = next(app.dependency_overrides[get_db]())
        try:
            db.execute(update(User).where(User.email == email).values(role=role))
            db.commit()
        finally:
            db.close()

    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


ADMIN_ENDPOINTS = (
    "/admin/users",
    "/admin/audit",
    "/admin/audit/verify",
    "/admin/documents",
    "/admin/activity",
)


@pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
def test_admin_endpoints_require_authentication(client, endpoint):
    assert client.get(endpoint).status_code == 401


def test_normal_user_cannot_list_users_or_access_admin_routes(client):
    headers = create_account(client, "user@example.com")
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    create_account(client, "another-user@example.com")

    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.get("/auth/activity", headers=headers).status_code == 200
    assert {
        event["user_id"] for event in client.get("/auth/activity", headers=headers).json()
    } == {user_id}

    for endpoint in (
        "/admin/users",
        "/admin/audit",
        "/admin/audit/verify",
        "/admin/documents",
        "/admin/activity",
    ):
        assert client.get(endpoint, headers=headers).status_code == 403


def test_admin_can_access_all_admin_endpoints(client):
    headers = create_account(client, "admin@example.com", role="admin")

    for endpoint in ADMIN_ENDPOINTS:
        assert client.get(endpoint, headers=headers).status_code == 200


def test_auditor_can_access_audit_but_not_all_documents(client):
    headers = create_account(client, "auditor@example.com", role="auditor")

    assert client.get("/admin/users", headers=headers).status_code == 200
    assert client.get("/admin/audit", headers=headers).status_code == 200
    assert client.get("/admin/audit/verify", headers=headers).status_code == 200
    assert client.get("/admin/activity", headers=headers).status_code == 200
    assert client.get("/admin/documents", headers=headers).status_code == 403


def test_admin_and_auditor_can_read_directory_without_sensitive_fields(client):
    create_account(client, "listed@example.com")
    for role in ("admin", "auditor"):
        headers = create_account(client, f"{role}-reader@example.com", role=role)
        response = client.get("/admin/users", headers=headers)
        assert response.status_code == 200
        assert response.json()
        assert all(set(account) == {"id", "email", "role"} for account in response.json())


def test_only_admin_can_delete_accounts_and_deletion_transfers_documents(client):
    admin_headers = create_account(client, "delete-admin@example.com", role="admin")
    target_headers = create_account(client, "delete-target@example.com")
    reader_headers = create_account(client, "delete-reader@example.com")
    target_id = client.get("/auth/me", headers=target_headers).json()["id"]
    admin_id = client.get("/auth/me", headers=admin_headers).json()["id"]
    reader_id = client.get("/auth/me", headers=reader_headers).json()["id"]

    db = next(app.dependency_overrides[get_db]())
    try:
        target_document = Document(
            owner_id=target_id, filename="keep.pdf", stored_path="retained.bin", size=4,
            file_data=b"data", content=b"data",
        )
        admin_document = Document(
            owner_id=admin_id, filename="shared.txt", stored_path="shared.bin", size=4,
            file_data=b"data", content=b"data",
        )
        db.add_all([target_document, admin_document])
        db.flush()
        target_document_id = target_document.id
        admin_document_id = admin_document.id
        db.add_all([
            Permission(document_id=target_document_id, user_id=reader_id, level="read"),
            Permission(document_id=admin_document_id, user_id=target_id, level="edit"),
        ])
        db.commit()
    finally:
        db.close()

    assert client.delete(f"/admin/users/{target_id}", headers=target_headers).status_code == 403
    auditor_headers = create_account(client, "delete-auditor@example.com", role="auditor")
    assert client.delete(f"/admin/users/{target_id}", headers=auditor_headers).status_code == 403
    response = client.delete(f"/admin/users/{target_id}", headers=admin_headers)
    assert response.status_code == 204

    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.get(User, target_id) is None
        transferred = db.get(Document, target_document_id)
        assert transferred.owner_id == admin_id
        assert transferred.file_data == b"data"
        assert db.scalar(select(Permission).where(Permission.user_id == target_id)) is None
        assert db.scalar(select(Permission).where(
            Permission.document_id == target_document_id, Permission.user_id == reader_id
        )) is not None
        event = db.scalar(select(AuditLog).where(AuditLog.action == "delete_user"))
        assert event.user_id == admin_id
        assert event.details == (
            '{"deleted_user_email":"delete-target@example.com","deleted_user_id":' + str(target_id) + '}'
        )
    finally:
        db.close()

    audit = client.get("/admin/audit", headers=admin_headers)
    assert audit.status_code == 200
    deletion = next(item for item in audit.json()["items"] if item["action"] == "delete_user")
    assert deletion["details"] == {"deleted_user_id": target_id, "deleted_user_email": "delete-target@example.com"}
    assert client.get("/admin/audit/verify", headers=admin_headers).json()["ok"] is True


def test_admin_cannot_delete_self_or_missing_account(client):
    headers = create_account(client, "first-admin@example.com", role="admin")
    admin_id = client.get("/auth/me", headers=headers).json()["id"]
    second_headers = create_account(client, "second-admin@example.com", role="admin")
    second_id = client.get("/auth/me", headers=second_headers).json()["id"]
    assert client.delete(f"/admin/users/{second_id}", headers=headers).status_code == 204
    assert client.delete(f"/admin/users/{admin_id}", headers=headers).status_code == 400
    assert client.delete("/admin/users/99999", headers=headers).status_code == 404


def test_user_deletion_rolls_back_when_audit_transaction_fails(client, monkeypatch):
    headers = create_account(client, "rollback-admin@example.com", role="admin")
    target_headers = create_account(client, "rollback-target@example.com")
    target_id = client.get("/auth/me", headers=target_headers).json()["id"]
    db = next(app.dependency_overrides[get_db]())
    try:
        document = Document(
            owner_id=target_id, filename="rollback.txt", stored_path="rollback.bin", size=4,
            file_data=b"keep", content=b"keep",
        )
        db.add(document)
        db.commit()
        document_id = document.id
    finally:
        db.close()

    def fail_commit(_session):
        raise SQLAlchemyError("simulated database commit failure")

    with monkeypatch.context() as patcher:
        patcher.setattr(Session, "commit", fail_commit)
        response = client.delete(f"/admin/users/{target_id}", headers=headers)
    assert response.status_code == 500

    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.get(User, target_id) is not None
        assert db.get(Document, document_id).owner_id == target_id
        assert db.scalar(select(AuditLog).where(AuditLog.action == "delete_user")) is None
    finally:
        db.close()
