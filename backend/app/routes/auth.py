from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.dependencies import get_current_user

from app.database import get_db
from app.models import AuditLog, User
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
def activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(AuditLog)
    if current_user.role not in {"admin", "auditor"}:
        query = query.where(AuditLog.user_id == current_user.id)
    rows = db.scalars(query.order_by(AuditLog.id.desc()).limit(500)).all()
    return [{"id": row.id, "timestamp": row.timestamp, "user_id": row.user_id,
             "action": row.action, "document_id": row.document_id, "result": row.result}
            for row in rows]
