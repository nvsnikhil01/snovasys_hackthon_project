import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.audit import log_event
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Document, Permission, User
from app.provision_role import ProvisioningError, provision_role


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def add_user(session, email, role="user"):
    user = User(email=email, password_hash="unchanged-password-hash", role=role)
    session.add(user)
    session.flush()
    return user


def test_provision_updates_only_role_and_preserves_related_records(session_factory):
    with session_factory.begin() as db:
        target = add_user(db, "Admin@Example.com")
        recipient = add_user(db, "recipient@example.com")
        document = Document(
            owner_id=target.id,
            filename="private.txt",
            stored_path="private.bin",
            size=7,
            file_data=b"private",
            content=b"private",
        )
        db.add(document)
        db.flush()
        grant = Permission(document_id=document.id, user_id=recipient.id, level="read")
        db.add(grant)
        db.flush()
        target_id = target.id
        recipient_id = recipient.id
        document_id = document.id
        grant_id = grant.id

    with session_factory() as db:
        event = log_event(db, target_id, "upload", document_id, "allowed")
        original_event = (event.id, event.timestamp, event.user_id, event.action, event.hash)

    result = provision_role(
        " admin@example.com ", "admin", session_factory=session_factory, apply=True
    )
    assert result["changed"] is True
    with session_factory() as db:
        target = db.get(User, target_id)
        assert target.role == "admin"
        assert target.password_hash == "unchanged-password-hash"
        document = db.get(Document, document_id)
        assert document.owner_id == target_id
        assert document.file_data == b"private"
        assert document.content == b"private"
        assert db.get(Permission, grant_id).user_id == recipient_id
        assert db.scalar(select(func.count(AuditLog.id))) == 1
        event = db.get(AuditLog, original_event[0])
        assert (event.id, event.timestamp, event.user_id, event.action, event.hash) == original_event


def test_provision_dry_run_is_read_only_and_role_assignment_is_idempotent(session_factory):
    with session_factory.begin() as db:
        user = add_user(db, "admin@example.com")
        user_id = user.id

    dry_run = provision_role("admin@example.com", "admin", session_factory=session_factory)
    assert dry_run["changed"] is False
    assert dry_run["current_role"] == "user"
    with session_factory() as db:
        assert db.get(User, user_id).role == "user"

    first = provision_role("admin@example.com", "admin", session_factory=session_factory, apply=True)
    second = provision_role("admin@example.com", "admin", session_factory=session_factory, apply=True)
    assert first["changed"] is True
    assert second["changed"] is False
    with session_factory() as db:
        assert db.scalar(select(func.count(User.id))) == 1


def test_provision_refuses_unknown_accounts_and_unsupported_roles(session_factory):
    with pytest.raises(ProvisioningError, match="no existing account"):
        provision_role("missing@example.com", "admin", session_factory=session_factory, apply=True)
    with pytest.raises(ProvisioningError, match="one of: user, admin, auditor"):
        provision_role("missing@example.com", "root", session_factory=session_factory, apply=True)
    with session_factory() as db:
        assert db.scalar(select(func.count(User.id))) == 0


def test_provision_protects_last_admin(session_factory):
    with session_factory.begin() as db:
        admin = add_user(db, "only-admin@example.com", role="admin")
        admin_id = admin.id
    with pytest.raises(ProvisioningError, match="last administrator"):
        provision_role("only-admin@example.com", "user", session_factory=session_factory, apply=True)
    with session_factory() as db:
        assert db.get(User, admin_id).role == "admin"


def test_provision_allows_demoting_an_admin_when_another_admin_remains(session_factory):
    with session_factory.begin() as db:
        target = add_user(db, "admin-one@example.com", role="admin")
        add_user(db, "admin-two@example.com", role="admin")
        target_id = target.id
    result = provision_role("admin-one@example.com", "auditor", session_factory=session_factory, apply=True)
    assert result["changed"] is True
    with session_factory() as db:
        assert db.get(User, target_id).role == "auditor"
        assert db.scalar(select(func.count(User.id)).where(User.role == "admin")) == 1


def test_require_postgresql_refuses_sqlite(session_factory):
    with session_factory.begin() as db:
        add_user(db, "admin@example.com")
    with pytest.raises(ProvisioningError, match="not PostgreSQL"):
        provision_role(
            "admin@example.com",
            "admin",
            session_factory=session_factory,
            apply=True,
            require_postgresql=True,
        )
    with session_factory() as db:
        assert db.scalar(select(User.role).where(User.email == "admin@example.com")) == "user"


def test_role_is_reloaded_from_database_for_existing_jwt_and_registration_cannot_set_role(
    session_factory,
):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            assert client.get("/admin/audit").status_code == 401
            assert client.get("/admin/activity").status_code == 401

            target_response = client.post(
                "/auth/register",
                json={"email": "operator@example.com", "password": "password123", "role": "admin"},
            )
            backup_response = client.post(
                "/auth/register", json={"email": "backup@example.com", "password": "password123"}
            )
            normal_response = client.post(
                "/auth/register", json={"email": "normal@example.com", "password": "password123"}
            )
            assert target_response.json()["role"] == "user"
            assert backup_response.status_code == normal_response.status_code == 201

            def token_for(email):
                login_response = client.post(
                    "/auth/login", json={"email": email, "password": "password123"}
                )
                assert login_response.status_code == 200
                return {"Authorization": f"Bearer {login_response.json()['access_token']}"}

            target_headers = token_for("operator@example.com")
            backup_headers = token_for("backup@example.com")
            normal_headers = token_for("normal@example.com")
            assert client.get("/admin/audit", headers=target_headers).status_code == 403
            assert client.get("/admin/activity", headers=target_headers).status_code == 403
            assert client.get("/admin/audit", headers=normal_headers).status_code == 403
            assert client.get("/admin/activity", headers=normal_headers).status_code == 403

            provision_role(
                "backup@example.com", "admin", session_factory=session_factory, apply=True
            )
            provision_role(
                "operator@example.com", "admin", session_factory=session_factory, apply=True
            )
            assert client.get("/auth/me", headers=target_headers).json()["role"] == "admin"
            assert client.get("/admin/audit", headers=target_headers).status_code == 200
            assert client.get("/admin/activity", headers=target_headers).status_code == 200

            provision_role(
                "operator@example.com", "auditor", session_factory=session_factory, apply=True
            )
            assert client.get("/auth/me", headers=target_headers).json()["role"] == "auditor"
            assert client.get("/admin/audit", headers=target_headers).status_code == 200
            assert client.get("/admin/activity", headers=target_headers).status_code == 200
            assert client.get("/admin/documents", headers=target_headers).status_code == 403

    finally:
        app.dependency_overrides.clear()
