from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.dependencies import get_current_user

from app.database import get_db
from app.models import AuditLog, Document, User
from app.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Used when the email does not exist, so a wrong email and a wrong password
# take about the same time and give the same answer.
DUMMY_HASH = hash_password("not-a-real-password")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()

    # bcrypt only reads the first 72 bytes, so reject longer passwords
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long")

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # The role is always "user". The client can never choose it.
    user = User(email=email, password_hash=hash_password(data.password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    if len(data.password.encode("utf-8")) > 72:
        from app.audit import log_event
        log_event(db, None, "login", None, "denied")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    email = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Always run one password check, even for unknown emails
    password_ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)

    if user is None or not password_ok:
        from app.audit import log_event
        log_event(db, user.id if user else None, "login", None, "denied")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    from app.audit import log_event
    log_event(db, user.id, "login", None, "allowed")
    return TokenOut(access_token=create_access_token(user.id))
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/activity")
def activity(
    page: int | None = Query(None, ge=1),
    limit: int | None = Query(None, ge=1, le=100),
    action: str | None = Query(None, min_length=1, max_length=50, pattern="^[a-z][a-z0-9_]{0,49}$"),
    document_search: str | None = Query(None, min_length=1, max_length=255),
    outcome: str | None = Query(None, pattern="^(success|denied|failure)$"),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return only the authenticated user's activity, optionally paginated and filtered."""
    if start_at and start_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="start_at must include a timezone")
    if end_at and end_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="end_at must include a timezone")
    if start_at and end_at and start_at > end_at:
        raise HTTPException(status_code=422, detail="start_at must be before or equal to end_at")

    # This scope is fixed by the authenticated database user. No query parameter
    # can widen it, including user IDs or email searches.
    filters = [AuditLog.user_id == current_user.id]
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

    # Keep the original no-parameter list response available for existing API
    # consumers while providing the same paginated contract used by the UI.
    paginated = any((page is not None, limit is not None, action, document_search, outcome, start_at, end_at))
    if not paginated:
        rows = db.scalars(
            select(AuditLog).where(*filters).order_by(AuditLog.id.desc()).limit(500)
        ).all()
        return [{"id": row.id, "timestamp": row.timestamp, "user_id": row.user_id,
                 "action": row.action, "document_id": row.document_id, "result": row.result}
                for row in rows]

    page = page or 1
    limit = limit or 25
    joined = (
        select(AuditLog, User, Document)
        .outerjoin(User, User.id == AuditLog.user_id)
        .outerjoin(Document, Document.id == AuditLog.document_id)
        .where(*filters)
    )
    count_query = (
        select(func.count(AuditLog.id))
        .outerjoin(Document, Document.id == AuditLog.document_id)
        .where(*filters)
    )
    total = db.scalar(count_query) or 0
    rows = db.execute(
        joined.order_by(AuditLog.id.desc()).offset((page - 1) * limit).limit(limit)
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
