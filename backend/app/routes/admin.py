from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import User
from app.schemas import UserOut

from app.audit import verify_chain
from app.models import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    return db.scalars(select(User).order_by(User.id)).all()
@router.get("/audit")
def audit_entries(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "auditor")),
):
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500))
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