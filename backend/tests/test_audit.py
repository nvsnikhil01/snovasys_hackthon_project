import pytest
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
    assert verify_chain(db) == {"ok": False, "first_bad_id": 2}


def test_deleted_row_is_detected(db):
    add_three(db)
    db.delete(db.get(AuditLog, 2))
    db.commit()
    assert verify_chain(db)["ok"] is False