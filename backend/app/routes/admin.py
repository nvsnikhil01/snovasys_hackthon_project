from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import verify_chain
from app.database import get_db
from app.dependencies import require_role
from app.models import AuditLog, Document, User
from app.schemas import DocumentOut, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
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
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "user_id": r.user_id,
            "action": r.action,
            "document_id": r.document_id,
            "result": r.result,
        }
        for r in rows
    ]


@router.get("/audit/verify")
def audit_verify(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    return verify_chain(db)
