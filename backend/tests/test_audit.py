import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.audit import log_event, verify_chain
from app.database import Base
from app.models import AuditLog


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def add_three(db):
    log_event(db, 1, "read", 10, "allowed")
    log_event(db, 2, "read", 10, "denied")
    log_event(db, 1, "share", 10, "allowed")


def test_untouched_chain_verifies(db):
    add_three(db)
    assert verify_chain(db)["ok"] is True


def test_empty_log_verifies(db):
    assert verify_chain(db)["ok"] is True


def test_edited_row_is_detected(db):
    add_three(db)
    db.get(AuditLog, 2).result = "allowed"  # simulate tamper: flip denied to allowed
    db.commit()
    result = verify_chain(db)
    assert result["ok"] is False
    assert result["first_bad_id"] == 2
    assert result["events_checked"] == 2
    assert result["verified_at"] is not None


def test_deleted_row_is_detected(db):
    add_three(db)
    db.delete(db.get(AuditLog, 2))
    db.commit()
    assert verify_chain(db)["ok"] is False


def test_concurrent_writers_keep_the_chain_valid():
    engine = create_engine("sqlite:///./concurrent-audit-test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def write_events(worker):
        with factory() as session:
            for index in range(15):
                log_event(session, worker, "read", index, "allowed")

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(write_events, range(8)))
        with factory() as session:
            assert verify_chain(session)["ok"] is True
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
        import os
        if os.path.exists("./concurrent-audit-test.db"):
            os.remove("./concurrent-audit-test.db")
