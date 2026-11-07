import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import ALGORITHM, SECRET_KEY

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if creds is None:
        raise unauthorized

    try:
        # Checks the signature and the expiry. Only HS256 is accepted.
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    # The user and the role are read from the database on every request
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
def require_role(*allowed_roles: str):
    """Returns a dependency that only lets users with one of these roles through."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user

    return checker
