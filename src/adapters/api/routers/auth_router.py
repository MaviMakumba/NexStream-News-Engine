import bcrypt
import logging
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, UserSession, UserTier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _make_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode()[:72], bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except Exception:
        return False


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=req.email,
        password_hash=_hash_password(req.password),
        name=req.name,
        tier=UserTier.FREE,
    )
    saved = repo.create_user(user)

    token = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    session = UserSession(user_id=saved.id, token=token, expires_at=expires_at)
    repo.create_session(session)

    logger.info("Yeni kullanıcı: %s (tier=free)", saved.email)
    return {
        "token": token,
        "user": {"id": saved.id, "email": saved.email, "name": saved.name, "tier": saved.tier},
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_email(req.email)
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    session = UserSession(user_id=user.id, token=token, expires_at=expires_at)
    repo.create_session(session)

    logger.info("Giriş: %s", user.email)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "tier": user.tier},
    }


@router.post("/logout")
def logout(x_session_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    repo = UserRepository(db)
    ok = repo.delete_session(x_session_token)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return {"message": "Logged out"}


@router.get("/me")
def me(x_session_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    repo = UserRepository(db)
    session = repo.get_session(x_session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    now = datetime.now(timezone.utc)
    session_expires = session.expires_at
    if session_expires.tzinfo is None:
        session_expires = session_expires.replace(tzinfo=timezone.utc)
    if session_expires < now:
        repo.delete_session(x_session_token)
        raise HTTPException(status_code=401, detail="Session expired")
    user = repo.get_by_id(session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"id": user.id, "email": user.email, "name": user.name, "tier": user.tier, "created_at": user.created_at}
