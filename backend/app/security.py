import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# The secret comes from the environment. If it is missing (local development),
# a random one is made at startup, so no secret is ever written in the code.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("APP_ENV") == "production":
        # Deployed servers must have a fixed key, otherwise refuse to start
        raise RuntimeError("SECRET_KEY must be set in production")
    # Local development only: a random key, so old tokens die on restart
    SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
TOKEN_MINUTES = 60


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    # Only the user id and expiry go in the token. The role is NOT stored here.
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)