from sqlalchemy import select

from app import models  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

# Demo accounts only. Never reuse real passwords here.
DEMO_USERS = [
    ("admin@example.com", "admin-demo-123", "admin"),
    ("auditor@example.com", "auditor-demo-123", "auditor"),
    ("alice@example.com", "password123", "user"),
    ("bob@example.com", "password123", "user"),
]

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    for email, password, role in DEMO_USERS:
        if db.scalar(select(User).where(User.email == email)):
            print(f"skip (exists): {email}")
            continue
        db.add(User(email=email, password_hash=hash_password(password), role=role))
        print(f"created: {email} ({role})")
    db.commit()