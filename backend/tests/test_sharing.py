import io
import pytest
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers all tables (users, documents, permissions, audit_log)
from app.database import Base, get_db
from app.main import app


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
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "Ã©" * 60})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
