import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers all tables (users, documents, permissions, audit_log)
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # StaticPool ensures the in-memory database is shared across threads
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

    # Login Alice
    res = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert res.status_code == 200
    alice_token = res.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # Login Bob
    res = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert res.status_code == 200
    bob_token = res.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 2. Alice uploads a document
    file_content = b"Sample confidential text"
    res = client.post(
        "/documents",
        files={"file": ("sample.txt", io.BytesIO(file_content), "text/plain")},
        headers=alice_headers,
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 3. Bob attempts to access before being shared -> 404 (existence hidden via authorize())
    res = client.get(f"/documents/{doc_id}", headers=bob_headers)
    assert res.status_code == 404

    # 4. Alice shares doc with Bob with 'read' grant
    res = client.post(
        f"/documents/{doc_id}/share",
        json={"user_email": "bob@example.com", "level": "read"},
        headers=alice_headers,
    )
    assert res.status_code == 200
    assert res.json()["level"] == "read"

    # 5. Bob can now read the document
    res = client.get(f"/documents/{doc_id}", headers=bob_headers)
    assert res.status_code == 200

    # 6. Bob attempts to delete -> 404 (only owner can delete, unauthorized yields 404)
    res = client.delete(f"/documents/{doc_id}", headers=bob_headers)
    assert res.status_code == 404

    # 7. Alice revokes Bob's access
    bob_user_id = client.get("/auth/me", headers=bob_headers).json()["id"]
    res = client.delete(
        f"/documents/{doc_id}/share/{bob_user_id}", headers=alice_headers
    )
    assert res.status_code == 204

    # 8. Bob attempts to read again -> 404
    res = client.get(f"/documents/{doc_id}", headers=bob_headers)
    assert res.status_code == 404