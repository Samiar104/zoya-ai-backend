"""Authentication & authorisation for ZOYA AI Backend.

Two credential types (both NEVER expire, per project requirement):

1. Static API key (``X-API-Key`` header) — for devices and services.
   Generated once at first start, stored in ``.env`` (see
   ``app.core.config.ensure_api_key``). Rotate by changing ``.env``.

2. JWT access tokens — issued at login. Tokens carry NO ``exp`` claim,
   i.e. they do not expire. This is an explicit product requirement
   ("backend and API key must never expire"). Security trade-off: a leaked
   token stays valid until the user is deactivated or SECRET_KEY is
   rotated — both are supported (see README "Security & key lifecycle").

Passwords are hashed with bcrypt via passlib.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User

log = get_logger("zoya.security")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, username: str) -> str:
    """Create a JWT with NO expiry claim (never expires, by design)."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        # NOTE: deliberately no "exp" — tokens never expire (requirement).
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        # options: do not require exp (we never set one).
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM], options={"require_exp": False})
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user


def require_api_key(request: Request) -> str:
    """Validate the static X-API-Key header (never expires)."""
    from app.core.config import ensure_api_key

    expected = ensure_api_key()
    provided = request.headers.get("X-API-Key", "")
    if not provided or provided != expected:
        log.warning("Rejected request with missing/invalid API key from %s", request.client.host if request.client else "?")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-API-Key")
    return provided


def require_user_or_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Accept either a valid JWT (returns the user) or a valid API key.

    API-key callers get ``None`` as the user — endpoints that need a user
    should use ``get_current_user`` instead.
    """
    if credentials is not None:
        return get_current_user(credentials, db)
    require_api_key(request)
    return None
