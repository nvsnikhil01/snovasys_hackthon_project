import hashlib
import hmac
import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Callable, Iterator

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


def _compute_hash(prev_hash, ts, user_id, action, document_id, result, details=None) -> str:
    fields = [prev_hash, _stamp(ts), user_id, action, document_id, result]
    # Keep historical hashes valid while authenticating event details whenever
    # they are present on a new event.
    if details is not None:
        fields.append(details)
    payload = json.dumps(fields, separators=(",", ":"))
    return hmac.new(AUDIT_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _stage_event(db: Session, user_id, action: str, document_id, result: str, details=None) -> AuditLog:
    """Add a chained event to the current transaction without committing it."""
    last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev_hash = last.hash if last else GENESIS
    ts = datetime.now(timezone.utc)
    entry = AuditLog(
        timestamp=ts, user_id=user_id, action=action, document_id=document_id,
        result=result, prev_hash=prev_hash, details=details,
        hash=_compute_hash(prev_hash, ts, user_id, action, document_id, result, details),
    )
    db.add(entry)
    return entry


@contextmanager
def audit_transaction(
    db: Session,
    user_id,
    action: str,
    document_id,
    result: str,
    details: dict | Callable[[], dict] | None = None,
) -> Iterator[AuditLog]:
    """Commit a mutation and its audit event atomically in the supplied session."""
    with _WRITE_LOCK:
        try:
            resolved_details = details() if callable(details) else details
            serialized_details = (
                json.dumps(resolved_details, sort_keys=True, separators=(",", ":"))
                if resolved_details is not None else None
            )
            entry = _stage_event(db, user_id, action, document_id, result, serialized_details)
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
            prev, entry.timestamp, entry.user_id, entry.action, entry.document_id, entry.result,
            entry.details,
        )
        if entry.prev_hash != prev or not hmac.compare_digest(entry.hash, expected):
            return {"ok": False, "first_bad_id": entry.id, "events_checked": checked,
                    "verified_at": datetime.now(timezone.utc)}
        prev = entry.hash
    return {"ok": True, "first_bad_id": None, "events_checked": checked,
            "verified_at": datetime.now(timezone.utc)}
