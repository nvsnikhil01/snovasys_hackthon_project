from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import verify_chain
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import AuditLog, Document, User
from app.schemas import DocumentOut, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalars(select(User).order_by(User.id)).all()


@router.get("/documents", response_model=list[DocumentOut])
def list_all_documents_metadata(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    """Admins can view document metadata only, never file contents unless granted."""
    return db.scalars(select(Document).order_by(Document.id)).all()


@router.get("/audit")
def audit_entries(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action: str | None = Query(None, min_length=1, max_length=50),
    result: str | None = Query(None, pattern="^(allowed|denied)$"),
    search: str | None = Query(None, max_length=255),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if result:
        filters.append(AuditLog.result == result)
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(User.email.ilike(term), Document.filename.ilike(term)))

    joined = select(AuditLog, User, Document).outerjoin(User, User.id == AuditLog.user_id).outerjoin(
        Document, Document.id == AuditLog.document_id
    )
    count_query = select(func.count(AuditLog.id)).outerjoin(
        User, User.id == AuditLog.user_id
    ).outerjoin(Document, Document.id == AuditLog.document_id)
    if filters:
        joined = joined.where(*filters)
        count_query = count_query.where(*filters)
    total = db.scalar(count_query) or 0
    rows = db.execute(
        joined.order_by(AuditLog.id.desc()).offset((page - 1) * limit).limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "user_id": event.user_id,
                "actor_name": actor.email if actor else "System",
                "actor_email": actor.email if actor else None,
                "action": event.action,
                "document_id": event.document_id,
                "document_name": document.filename if document else None,
                "result": event.result,
                "prev_hash": event.prev_hash,
                "hash": event.hash,
            }
            for event, actor, document in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "total_events": db.scalar(select(func.count(AuditLog.id))) or 0,
        "allowed_count": db.scalar(select(func.count(AuditLog.id)).where(AuditLog.result == "allowed")) or 0,
        "denied_count": db.scalar(select(func.count(AuditLog.id)).where(AuditLog.result == "denied")) or 0,
    }


@router.get("/activity")
def activity_history(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    user_search: str | None = Query(None, min_length=1, max_length=255),
    action: str | None = Query(None, min_length=1, max_length=50, pattern="^[a-z][a-z0-9_]{0,49}$"),
    document_search: str | None = Query(None, min_length=1, max_length=255),
    outcome: str | None = Query(None, pattern="^(success|denied|failure)$"),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    """Return a paginated, filterable view of existing audit-chain records."""
    if start_at and start_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="start_at must include a timezone")
    if end_at and end_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="end_at must include a timezone")
    if start_at and end_at and start_at > end_at:
        raise HTTPException(status_code=422, detail="start_at must be before or equal to end_at")

    filters = []
    if user_search and user_search.strip():
        term = user_search.strip()
        user_filter = [User.email.ilike(f"%{term}%")]
        if term.isdecimal():
            user_filter.append(AuditLog.user_id == int(term))
        filters.append(or_(*user_filter))
    if action:
        filters.append(AuditLog.action == action)
    if document_search and document_search.strip():
        term = document_search.strip()
        document_filter = [Document.filename.ilike(f"%{term}%")]
        if term.isdecimal():
            document_filter.append(AuditLog.document_id == int(term))
        filters.append(or_(*document_filter))
    if outcome == "success":
        filters.append(AuditLog.result == "allowed")
    elif outcome == "denied":
        filters.append(AuditLog.result == "denied")
    elif outcome == "failure":
        filters.append(AuditLog.result.notin_(("allowed", "denied")))
    if start_at:
        filters.append(AuditLog.timestamp >= start_at.astimezone(timezone.utc))
    if end_at:
        filters.append(AuditLog.timestamp <= end_at.astimezone(timezone.utc))

    joined = (
        select(AuditLog, User, Document)
        .outerjoin(User, User.id == AuditLog.user_id)
        .outerjoin(Document, Document.id == AuditLog.document_id)
    )
    count_query = (
        select(func.count(AuditLog.id))
        .outerjoin(User, User.id == AuditLog.user_id)
        .outerjoin(Document, Document.id == AuditLog.document_id)
    )
    if filters:
        joined = joined.where(*filters)
        count_query = count_query.where(*filters)

    total = db.scalar(count_query) or 0
    rows = db.execute(
        joined.order_by(AuditLog.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    outcome_labels = {"allowed": "success", "denied": "denied"}
    return {
        "items": [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "user_id": event.user_id,
                "actor_email": actor.email if actor else None,
                "action": event.action,
                "document_id": event.document_id,
                "document_name": document.filename if document else None,
                "outcome": outcome_labels.get(event.result, "failure"),
                "result": event.result,
                "prev_hash": event.prev_hash,
                "hash": event.hash,
            }
            for event, actor, document in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/audit/verify")
def audit_verify(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    return verify_chain(db)
