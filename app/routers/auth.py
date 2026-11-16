"""Auth router — register, login, profile, API-key rotation.

JWTs issued here NEVER expire (no ``exp`` claim) — explicit project
requirement. See README "Security & key lifecycle" for revocation.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import ensure_api_key
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserOut, UserRegister
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger("zoya.auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    first_user = db.query(User).count() == 0
    user = User(
        username=data.username,
        email=data.email,
        display_name=data.display_name or data.username,
        hashed_password=hash_password(data.password),
        is_admin=first_user,  # first account becomes admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info("Registered user %s (admin=%s)", user.username, user.is_admin)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is deactivated")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, username=user.username)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)) -> User:
    return current


@router.get("/api-key-info")
def api_key_info(current: User = Depends(get_current_user)) -> dict:
    """Show the (never-expiring) static API key metadata.

    Only admins can view the key itself. The key is also stored in .env.
    """
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    key = ensure_api_key()
    return {"api_key": key, "expires": "never", "header": "X-API-Key"}


@router.post("/rotate-api-key", response_model=MessageResponse)
def rotate_api_key(current: User = Depends(get_current_user)) -> MessageResponse:
    """Generate a NEW static API key, replacing the old one in .env.

    Admin only. Devices using the old key must be updated.
    """
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    import secrets
    from pathlib import Path

    from app.core.config import BASE_DIR, get_settings

    new_key = "zoya_" + secrets.token_urlsafe(32)
    env_file = BASE_DIR / ".env"
    try:
        text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        if "ZOYA_API_KEY=" in text:
            lines = [f"ZOYA_API_KEY={new_key}" if line.startswith("ZOYA_API_KEY=") else line for line in text.splitlines()]
            env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            with env_file.open("a", encoding="utf-8") as fh:
                fh.write(f"\nZOYA_API_KEY={new_key}\n")
        get_settings.cache_clear()
        log.warning("API key rotated by admin %s", current.username)
        return MessageResponse(detail="API key rotated. New key saved to .env; restart the server to apply it.")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not write .env: {exc}") from exc
