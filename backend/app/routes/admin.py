from fastapi import APIRouter, Depends, Query
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


@router.get("/audit/verify")
def audit_verify(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    return verify_chain(db)
