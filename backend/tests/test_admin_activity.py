from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.audit import log_event
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Document, User


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


def login(client, email, role="user"):
    assert client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    ).status_code == 201
    if role != "user":
        db_dependency = app.dependency_overrides[get_db]()
        db = next(db_dependency)
        try:
            db.execute(update(User).where(User.email == email).values(role=role))
            db.commit()
        finally:
            db_dependency.close()
    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def db_session():
    return next(app.dependency_overrides[get_db]())


def add_activity_fixtures(db, client):
    user_id = client.get("/auth/me", headers=login(client, "activity@example.com")).json()["id"]
    other_id = client.get("/auth/me", headers=login(client, "other@example.com")).json()["id"]
    document = Document(
        owner_id=user_id,
        filename="Quarterly Report.pdf",
        stored_path="unused.bin",
        size=12,
    )
    second_document = Document(
        owner_id=other_id,
        filename="Notes.txt",
        stored_path="unused-2.bin",
        size=8,
    )
    db.add_all([document, second_document])
    db.flush()
    first = log_event(db, user_id, "upload", document.id, "allowed")
    second = log_event(db, user_id, "edit", document.id, "allowed")
    third = log_event(db, other_id, "download", second_document.id, "denied")
    system_event = log_event(db, None, "login", None, "denied")
    return user_id, other_id, document.id, [first.id, second.id, third.id, system_event.id]


def test_activity_requires_admin_or_auditor(client):
    assert client.get("/admin/activity").status_code == 401
    normal = login(client, "normal@example.com")
    assert client.get("/admin/activity", headers=normal).status_code == 403
    admin = login(client, "admin@example.com", role="admin")
    auditor = login(client, "auditor@example.com", role="auditor")
    assert client.get("/admin/activity", headers=admin).status_code == 200
    assert client.get("/admin/activity", headers=auditor).status_code == 200


def test_normal_user_activity_is_personal_and_cannot_be_widened_by_query_parameters(client):
    personal_headers = login(client, "personal@example.com")
    personal_user_id = client.get("/auth/me", headers=personal_headers).json()["id"]
    db = db_session()
    try:
        _, other_user_id, _, _ = add_activity_fixtures(db, client)
        own_event = log_event(db, personal_user_id, "edit", None, "allowed")
        own_event_id = own_event.id
    finally:
        db.close()

    response = client.get(
        "/auth/activity",
        params={"page": 1, "limit": 100, "user_search": "other@example.com", "user_id": other_user_id},
        headers=personal_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2  # registration/login and this test's own event
    assert {item["user_id"] for item in payload["items"]} == {personal_user_id}
    assert own_event_id in {item["id"] for item in payload["items"]}
    assert other_user_id not in {item["user_id"] for item in payload["items"]}
    other_document_search = client.get(
        "/auth/activity",
        params={"page": 1, "limit": 100, "document_search": "Notes"},
        headers=personal_headers,
    ).json()
    assert other_document_search["items"] == []
    assert other_document_search["total"] == 0
    assert client.get("/admin/activity", headers=personal_headers).status_code == 403


def test_personal_activity_filters_and_paginates_with_stable_order(client):
    headers = login(client, "personal@example.com")
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    db = db_session()
    try:
        document = Document(
            owner_id=user_id,
            filename="Personal Notes.txt",
            stored_path="unused.bin",
            size=4,
        )
        db.add(document)
        db.flush()
        first = log_event(db, user_id, "upload", document.id, "allowed")
        second = log_event(db, user_id, "edit", document.id, "allowed")
        first_id = first.id
        second_id = second.id
        log_event(db, user_id, "download", document.id, "denied")
        event_time = db.scalar(select(AuditLog.timestamp).where(AuditLog.id == second_id))
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
    finally:
        db.close()

    filtered = client.get(
        "/auth/activity",
        params={
            "page": 1,
            "limit": 10,
            "action": "edit",
            "document_search": "Personal Notes",
            "outcome": "success",
            "start_at": (event_time - timedelta(seconds=1)).isoformat(),
            "end_at": (event_time + timedelta(seconds=1)).isoformat(),
        },
        headers=headers,
    )
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["items"]] == [second_id]
    assert payload["items"][0]["document_name"] == "Personal Notes.txt"

    first_page = client.get("/auth/activity?page=1&limit=2", headers=headers).json()
    second_page = client.get("/auth/activity?page=2&limit=2", headers=headers).json()
    assert first_page["items"][0]["id"] > first_page["items"][1]["id"]
    assert first_page["items"][1]["id"] > second_page["items"][0]["id"]
    assert first_id in [item["id"] for item in first_page["items"] + second_page["items"]]


@pytest.mark.parametrize("role", ["admin", "auditor"])
def test_activity_records_are_existing_unique_rows_and_join_available_fields(client, role):
    headers = login(client, f"{role}@example.com", role=role)
    db = db_session()
    try:
        user_id, _, document_id, _ = add_activity_fixtures(db, client)
        expected_ids = db.scalars(select(AuditLog.id).order_by(AuditLog.id.desc())).all()
    finally:
        db.close()

    response = client.get("/admin/activity?limit=100", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    items = payload["items"]
    returned_ids = [item["id"] for item in items]
    assert returned_ids == expected_ids
    assert len(returned_ids) == len(set(returned_ids))
    upload = next(item for item in items if item["action"] == "upload")
    assert upload["user_id"] == user_id
    assert upload["actor_email"] == "activity@example.com"
    assert upload["document_id"] == document_id
    assert upload["document_name"] == "Quarterly Report.pdf"
    system = next(item for item in items if item["user_id"] is None)
    assert system["actor_email"] is None
    assert system["document_name"] is None


@pytest.mark.parametrize(
    "query_key,query_value,expected_action",
    [
        ("user_search", "activity@example.com", "upload"),
        ("action", "edit", "edit"),
        ("document_search", "Quarterly", "upload"),
        ("outcome", "denied", "download"),
    ],
)
def test_activity_filters_by_user_action_document_and_outcome(
    client, query_key, query_value, expected_action
):
    headers = login(client, "admin@example.com", role="admin")
    db = db_session()
    try:
        add_activity_fixtures(db, client)
    finally:
        db.close()

    response = client.get(
        "/admin/activity", params={query_key: query_value}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["items"]
    items = response.json()["items"]
    if query_key == "user_search":
        assert all(item["actor_email"] == query_value for item in items)
    elif query_key == "document_search":
        assert all(item["document_name"] == "Quarterly Report.pdf" for item in items)
        assert {item["action"] for item in items} == {"upload", "edit"}
    elif query_key == "outcome":
        assert {item["outcome"] for item in items} == {"denied"}
    else:
        assert {item["action"] for item in items} == {expected_action}


def test_activity_user_and_document_ids_and_time_range_filters(client):
    headers = login(client, "admin@example.com", role="admin")
    db = db_session()
    try:
        user_id, _, document_id, _ = add_activity_fixtures(db, client)
        event_time = db.scalar(
            select(AuditLog.timestamp).where(AuditLog.action == "upload")
        )
    finally:
        db.close()
    start = (event_time - timedelta(seconds=1)).replace(tzinfo=timezone.utc).isoformat()
    end = (event_time + timedelta(seconds=1)).replace(tzinfo=timezone.utc).isoformat()

    by_user = client.get(
        "/admin/activity", params={"user_search": str(user_id)}, headers=headers
    ).json()
    by_document = client.get(
        "/admin/activity", params={"document_search": str(document_id)}, headers=headers
    ).json()
    by_time = client.get(
        "/admin/activity", params={"start_at": start, "end_at": end}, headers=headers
    ).json()
    future_start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    past_end = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    after_start = client.get(
        "/admin/activity", params={"start_at": future_start}, headers=headers
    ).json()
    before_end = client.get(
        "/admin/activity", params={"end_at": past_end}, headers=headers
    ).json()
    assert all(item["user_id"] == user_id for item in by_user["items"])
    assert all(item["document_id"] == document_id for item in by_document["items"])
    assert any(item["action"] == "upload" for item in by_time["items"])
    assert after_start["items"] == []
    assert before_end["items"] == []


def test_activity_paginates_with_stable_descending_id_order(client):
    headers = login(client, "auditor@example.com", role="auditor")
    db = db_session()
    try:
        add_activity_fixtures(db, client)
        expected_ids = db.scalars(select(AuditLog.id).order_by(AuditLog.id.desc())).all()
    finally:
        db.close()

    first = client.get("/admin/activity?page=1&limit=2", headers=headers).json()
    second = client.get("/admin/activity?page=2&limit=2", headers=headers).json()
    third = client.get("/admin/activity?page=3&limit=2", headers=headers).json()
    fourth = client.get("/admin/activity?page=4&limit=2", headers=headers).json()
    assert [item["id"] for item in first["items"]] == expected_ids[:2]
    assert [item["id"] for item in second["items"]] == expected_ids[2:4]
    assert [item["id"] for item in third["items"]] == expected_ids[4:6]
    assert [item["id"] for item in fourth["items"]] == expected_ids[6:]
    assert first["total"] == len(expected_ids)
    assert first["pages"] == (len(expected_ids) + 1) // 2


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"limit": 101},
        {"action": "invalid action"},
        {"outcome": "unknown"},
        {"start_at": "2025-01-01T00:00:00Z", "end_at": "2024-01-01T00:00:00Z"},
        {"start_at": "2024-01-01T00:00:00"},
    ],
)
def test_activity_rejects_invalid_filters(client, params):
    headers = login(client, "admin@example.com", role="admin")
    assert client.get("/admin/activity", params=params, headers=headers).status_code == 422


def test_activity_empty_results_returns_empty_page_without_fabricated_rows(client):
    headers = login(client, "auditor@example.com", role="auditor")
    response = client.get(
        "/admin/activity?action=delete", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    assert response.json()["pages"] == 0


def test_activity_failure_outcome_filter_includes_nonstandard_failure_results(client):
    headers = login(client, "admin@example.com", role="admin")
    db = db_session()
    try:
        event_id = log_event(db, None, "upload", None, "failure").id
    finally:
        db.close()
    response = client.get("/admin/activity?outcome=failure", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [event_id]
    assert response.json()["items"][0]["outcome"] == "failure"
