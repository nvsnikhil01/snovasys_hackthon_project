import hashlib
import hmac
import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog

AUDIT_KEY = os.getenv("AUDIT_KEY")
if not AUDIT_KEY:
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("AUDIT_KEY must be set in production")
    # Fixed on purpose. A random key would break verification after every restart.
    AUDIT_KEY = "local-dev-audit-key"

GENESIS = "GENESIS"
_WRITE_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def _stamp(ts: datetime) -> str:
    # SQLite returns naive datetimes and Postgres returns aware ones.
    # Treat naive as UTC so the hash is the same either way.
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _compute_hash(prev_hash, ts, user_id, action, document_id, result) -> str:
    payload = json.dumps(
        [prev_hash, _stamp(ts), user_id, action, document_id, result],
        separators=(",", ":"),
    )
    return hmac.new(AUDIT_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _stage_event(db: Session, user_id, action: str, document_id, result: str) -> AuditLog:
    """Add a chained event to the current transaction without committing it."""
    last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev_hash = last.hash if last else GENESIS
    ts = datetime.now(timezone.utc)
    entry = AuditLog(
        timestamp=ts, user_id=user_id, action=action, document_id=document_id,
        result=result, prev_hash=prev_hash,
        hash=_compute_hash(prev_hash, ts, user_id, action, document_id, result),
    )
    db.add(entry)
    return entry


@contextmanager
def audit_transaction(
    db: Session, user_id, action: str, document_id, result: str
) -> Iterator[AuditLog]:
    """Commit a mutation and its audit event atomically in the supplied session."""
    with _WRITE_LOCK:
        try:
            entry = _stage_event(db, user_id, action, document_id, result)
            yield entry
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                logger.exception("Could not roll back failed audit transaction")
            raise


def log_event(db: Session, user_id, action: str, document_id, result: str) -> AuditLog:
    """Appends one row to the log. result is 'allowed' or 'denied'."""
    with audit_transaction(db, user_id, action, document_id, result) as entry:
        pass
    return entry


def verify_chain(db: Session) -> dict:
    prev = GENESIS
    checked = 0
    for entry in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        checked += 1
        expected = _compute_hash(
            prev, entry.timestamp, entry.user_id, entry.action, entry.document_id, entry.result
        )
        if entry.prev_hash != prev or not hmac.compare_digest(entry.hash, expected):
            return {"ok": False, "first_bad_id": entry.id, "events_checked": checked,
                    "verified_at": datetime.now(timezone.utc)}
        prev = entry.hash
    return {"ok": True, "first_bad_id": None, "events_checked": checked,
            "verified_at": datetime.now(timezone.utc)}
