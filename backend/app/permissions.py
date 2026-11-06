from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Permission, User

from fastapi import HTTPException
from app.audit import log_event

VALID_GRANT_LEVELS = {"read", "edit"}

# Which access levels may perform which action.
# "owner" is not stored anywhere: it means document.owner_id == user.id.
ALLOWED = {
    "read": {"owner", "edit", "read"},
    "edit": {"owner", "edit"},
    "share": {"owner"},
    "delete": {"owner"},
}


def access_level(db: Session, user: User, document: Document) -> str | None:
    """Returns 'owner', 'edit', 'read', or None (no access)."""
    if document.owner_id == user.id:
        return "owner"
    grant = db.scalar(
        select(Permission).where(
            Permission.document_id == document.id,
            Permission.user_id == user.id,
        )
    )
    if grant and grant.level in VALID_GRANT_LEVELS:
        return grant.level
    return None


def can(db: Session, user: User, document: Document, action: str) -> bool:
    """The one place that decides access. Deny by default."""
    level = access_level(db, user, document)
    return level in ALLOWED.get(action, set())


def authorize(db: Session, user: User, document, action: str):
    """What routes call. Decides, logs the attempt either way, and answers 404 if denied."""
    if document is None:
        log_event(db, user.id, action, None, "denied")
        raise HTTPException(status_code=404, detail="Not found")
    allowed = can(db, user, document, action)
    log_event(db, user.id, action, document.id, "allowed" if allowed else "denied")
    if not allowed:
        raise HTTPException(status_code=404, detail="Not found")
    return document