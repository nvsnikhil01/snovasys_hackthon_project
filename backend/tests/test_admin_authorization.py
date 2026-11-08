import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app
from app.models import User


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


def test_normal_user_can_list_users_but_not_admin_routes(client):
    headers = create_account(client, "user@example.com")
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    create_account(client, "another-user@example.com")

    registered_users = client.get("/admin/users", headers=headers)
    assert registered_users.status_code == 200
    assert registered_users.json()
    assert all("password_hash" not in account for account in registered_users.json())
    assert client.get("/auth/activity", headers=headers).status_code == 200
    assert {
        event["user_id"] for event in client.get("/auth/activity", headers=headers).json()
    } == {user_id}

    for endpoint in (
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
