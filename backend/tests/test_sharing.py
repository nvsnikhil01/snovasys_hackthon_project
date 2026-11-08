import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers all tables (users, documents, permissions, audit_log)
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Document, Permission


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr("app.routes.documents.UPLOAD_DIR", tmp_path)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _authenticated_user(client, email="owner@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    token = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _test_db_session():
    return next(app.dependency_overrides[get_db]())


def test_upload_persists_database_and_local_bytes_and_downloads(client, tmp_path):
    headers = _authenticated_user(client)
    payload = b"downloadable contents"
    uploaded = client.post(
        "/documents", files={"file": ("report.txt", payload, "text/plain")}, headers=headers
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]

    db = _test_db_session()
    try:
        document = db.get(Document, document_id)
        assert document.file_data == payload
        assert document.content == payload
        local_path = tmp_path / document.stored_path
        assert local_path.read_bytes() == payload
    finally:
        db.close()

    downloaded = client.get(f"/documents/{document_id}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == payload


def test_download_recovers_missing_local_file_from_database_bytes(client, tmp_path):
    headers = _authenticated_user(client)
    payload = b"recover from database"
    uploaded = client.post(
        "/documents", files={"file": ("recover.txt", payload, "text/plain")}, headers=headers
    )
    document_id = uploaded.json()["id"]
    db = _test_db_session()
    try:
        local_path = tmp_path / db.get(Document, document_id).stored_path
        local_path.unlink()
    finally:
        db.close()

    downloaded = client.get(f"/documents/{document_id}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == payload
    assert local_path.read_bytes() == payload


def test_download_recovers_legacy_content_column(client, tmp_path):
    headers = _authenticated_user(client)
    uploaded = client.post(
        "/documents", files={"file": ("legacy.txt", b"original", "text/plain")}, headers=headers
    )
    document_id = uploaded.json()["id"]
    db = _test_db_session()
    try:
        document = db.get(Document, document_id)
        local_path = tmp_path / document.stored_path
        local_path.unlink()
        document.file_data = None
        document.content = b"legacy content bytes"
        db.commit()
    finally:
        db.close()

    downloaded = client.get(f"/documents/{document_id}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == b"legacy content bytes"


def test_download_returns_not_found_when_local_and_database_copies_missing(client, tmp_path):
    headers = _authenticated_user(client)
    uploaded = client.post(
        "/documents", files={"file": ("gone.txt", b"gone", "text/plain")}, headers=headers
    )
    document_id = uploaded.json()["id"]
    db = _test_db_session()
    try:
        document = db.get(Document, document_id)
        (tmp_path / document.stored_path).unlink()
        document.file_data = None
        document.content = None
        db.commit()
    finally:
        db.close()

    missing = client.get(f"/documents/{document_id}/download", headers=headers)
    assert missing.status_code == 404


def test_delete_removes_database_record_permissions_and_local_file(client, tmp_path):
    headers = _authenticated_user(client)
    _authenticated_user(client, "recipient@example.com")
    uploaded = client.post(
        "/documents", files={"file": ("delete.txt", b"delete me", "text/plain")}, headers=headers
    )
    document_id = uploaded.json()["id"]
    client.post(
        f"/documents/{document_id}/share",
        json={"user_email": "recipient@example.com", "level": "read"},
        headers=headers,
    )
    db = _test_db_session()
    try:
        local_path = tmp_path / db.get(Document, document_id).stored_path
    finally:
        db.close()

    assert client.delete(f"/documents/{document_id}", headers=headers).status_code == 204
    assert not local_path.exists()
    db = _test_db_session()
    try:
        assert db.get(Document, document_id) is None
        assert db.scalar(select(Permission).where(Permission.document_id == document_id)) is None
    finally:
        db.close()


def test_failed_upload_commit_rolls_back_database_and_cleans_file(client, tmp_path, monkeypatch):
    headers = _authenticated_user(client)

    def fail_commit(_self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    failed = client.post(
        "/documents", files={"file": ("failure.txt", b"never persist", "text/plain")}, headers=headers
    )
    assert failed.status_code == 500
    assert list(tmp_path.iterdir()) == []
    db = _test_db_session()
    try:
        assert db.scalars(select(Document)).all() == []
        assert db.scalars(select(AuditLog).where(AuditLog.action == "upload")).all() == []
    finally:
        db.close()


def test_sharing_lifecycle(client):
    # 1. Register Alice and Bob
    res = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert res.status_code == 201

    res = client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert res.status_code == 201

    # Login Alice & Bob
    alice_token = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    ).json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    bob_token = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    ).json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 2. Alice uploads a document
    res = client.post(
        "/documents",
        files={"file": ("sample.txt", io.BytesIO(b"Sample confidential text"), "text/plain")},
        headers=alice_headers,
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 3. Bob attempts to access before being shared -> 404
    res = client.get(f"/documents/{doc_id}", headers=bob_headers)
    assert res.status_code == 404

    # 4. Alice shares doc with Bob with 'read' grant (testing case-insensitive email)
    res = client.post(
        f"/documents/{doc_id}/share",
        json={"user_email": "Bob@Example.com", "level": "read"},
        headers=alice_headers,
    )
    assert res.status_code == 200
    assert res.json()["level"] == "read"

    # 5. Bob can read, but cannot edit (PUT) or delete
    assert client.get(f"/documents/{doc_id}", headers=bob_headers).status_code == 200
    res_edit = client.put(
        f"/documents/{doc_id}",
        files={"file": ("updated.txt", io.BytesIO(b"Bob edit attempt"), "text/plain")},
        headers=bob_headers,
    )
    assert res_edit.status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=bob_headers).status_code == 404

    # 6. Alice upgrades Bob to 'edit' grant -> Bob can now update the document
    res = client.post(
        f"/documents/{doc_id}/share",
        json={"user_email": "bob@example.com", "level": "edit"},
        headers=alice_headers,
    )
    assert res.status_code == 200
    assert res.json()["level"] == "edit"

    res_edit_ok = client.put(
        f"/documents/{doc_id}",
        files={"file": ("updated.txt", io.BytesIO(b"Bob valid edit"), "text/plain")},
        headers=bob_headers,
    )
    assert res_edit_ok.status_code == 200
    assert res_edit_ok.json()["filename"] == "updated.txt"

    # 7. Alice revokes Bob's access
    bob_user_id = client.get("/auth/me", headers=bob_headers).json()["id"]
    res = client.delete(
        f"/documents/{doc_id}/share/{bob_user_id}", headers=alice_headers
    )
    assert res.status_code == 204

    # 8. Bob attempts to read again -> 404
    res = client.get(f"/documents/{doc_id}", headers=bob_headers)
    assert res.status_code == 404


def test_upload_rejects_spoofed_magic_bytes(client):
    client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    token = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload a file named .pdf that does not start with %PDF-
    res = client.post(
        "/documents",
        files={"file": ("fake.pdf", io.BytesIO(b"not a real pdf"), "application/pdf")},
        headers=headers,
    )
    assert res.status_code == 400


def test_login_with_overlong_multibyte_password_is_401_not_500(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "\u00e9" * 60})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


@pytest.mark.parametrize("method,route,status,kwargs", [
    ("get", "", 200, {}),
    ("get", "/download", 200, {}),
    ("put", "", 200, {"files": {"file": ("updated.txt", b"updated", "text/plain")}}),
    ("delete", "", 204, {}),
    ("post", "/share", 200, {"json": {"user_email": "bob@example.com", "level": "read"}}),
    ("get", "/shares", 200, {}),
    ("delete", "/share/{bob_id}", 204, {}),
])
def test_every_document_route_checks_permissions(client, method, route, status, kwargs):
    for email in ("owner@example.com", "bob@example.com", "stranger@example.com"):
        client.post("/auth/register", json={"email": email, "password": "password123"})
    def login(email):
        token = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    owner_headers, bob_headers, stranger_headers = map(login, ("owner@example.com", "bob@example.com", "stranger@example.com"))
    doc_id = client.post("/documents", files={"file": ("sample.txt", b"hello", "text/plain")}, headers=owner_headers).json()["id"]
    bob_id = client.get("/auth/me", headers=bob_headers).json()["id"]
    client.post(f"/documents/{doc_id}/share", json={"user_email": "bob@example.com", "level": "read"}, headers=owner_headers)
    path = f"/documents/{doc_id}" + route.format(bob_id=bob_id)
    stranger_response = getattr(client, method)(path, headers=stranger_headers, **kwargs)
    assert stranger_response.status_code == 404
    assert stranger_response.json() == {"detail": "Not found"}
    owner_response = getattr(client, method)(path, headers=owner_headers, **kwargs)
    assert owner_response.status_code == status


def test_shared_with_me_ignores_invalid_permission_levels(client):
    from app.database import get_db
    from app.models import Document, Permission
    client.post("/auth/register", json={"email": "owner@example.com", "password": "password123"})
    client.post("/auth/register", json={"email": "reader@example.com", "password": "password123"})
    tokens = {email: client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"] for email in ("owner@example.com", "reader@example.com")}
    headers = {email: {"Authorization": f"Bearer {token}"} for email, token in tokens.items()}
    owner_id = client.get("/auth/me", headers=headers["owner@example.com"]).json()["id"]
    reader_id = client.get("/auth/me", headers=headers["reader@example.com"]).json()["id"]
    db = next(app.dependency_overrides[get_db]())
    try:
        document = Document(owner_id=owner_id, filename="private.txt", stored_path="missing.bin", size=1)
        db.add(document)
        db.flush()
        db.add(Permission(document_id=document.id, user_id=reader_id, level="invalid"))
        db.commit()
    finally:
        db.close()
    response = client.get("/documents/shared-with-me", headers=headers["reader@example.com"])
    assert response.status_code == 200
    assert response.json() == []
