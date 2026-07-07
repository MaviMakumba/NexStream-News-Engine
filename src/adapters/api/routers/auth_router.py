"""Kayıt / giriş / oturum endpoint'leri (/auth).

Oturum modeli: başarılı kayıt/giriş sonrası rastgele opak token üretilir,
`user_sessions` tablosuna TTL ile yazılır ve istemci sonraki isteklerde
`X-Session-Token` header'ı ile gönderir. JWT yerine DB-backed session
tercih edildi: anında iptal edilebilir (logout) ve ekstra sır gerektirmez.

Parola: bcrypt (passlib'siz, doğrudan) — bcrypt girdiyi 72 byte ile sınırlar.
"""

import bcrypt
import logging
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from src.adapters.api.auth_utils import has_admin_role, resolve_session_user
from src.adapters.api.limiter import limiter
from src.adapters.notifications.email_adapter import get_email_adapter
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, UserSession, UserTier, PasswordResetToken

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    language: str = "TR"


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# ── Yardımcılar ────────────────────────────────────────────────────────────────

def _make_token() -> str:
    """Kriptografik rastgele oturum token'ı (URL-safe, 43 karakter)."""
    return secrets.token_urlsafe(32)


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode()[:72], bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except Exception:
        # Bozuk/eski hash formatı → güvenli taraf: reddet
        return False


def _open_session(repo: UserRepository, user_id: int) -> str:
    """Yeni oturum açar, token'ı döner. Register ve login ortak kullanır."""
    token = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    repo.create_session(UserSession(user_id=user_id, token=token, expires_at=expires_at))
    return token


def _user_payload(user: User) -> dict:
    """API yanıtlarındaki kullanıcı gösterimi — parola hash'i asla sızmaz."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "tier": user.tier,
        "is_admin": has_admin_role(user),
    }


# ── Endpoint'ler ───────────────────────────────────────────────────────────────

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
    token = _open_session(repo, saved.id)

    logger.info("Yeni kullanıcı: %s (tier=free)", saved.email)
    return {"token": token, "user": _user_payload(saved)}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_email(req.email)
    # E-posta bulunamadı ile yanlış parola aynı mesajı döner (user enumeration önlemi)
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = _open_session(repo, user.id)
    logger.info("Giriş: %s", user.email)
    return {"token": token, "user": _user_payload(user)}


@router.post("/logout")
def logout(x_session_token: str = Header(None), db: Session = Depends(get_db)):
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    repo = UserRepository(db)
    if not repo.delete_session(x_session_token):
        raise HTTPException(status_code=401, detail="Invalid session token")
    return {"message": "Logged out"}


@router.get("/me")
def me(x_session_token: str = Header(None), db: Session = Depends(get_db)):
    """Aktif oturumun kullanıcısını döner — frontend sayfa açılışında çağırır."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    repo = UserRepository(db)
    user = resolve_session_user(repo, x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return {**_user_payload(user), "created_at": user.created_at}


_GENERIC_FORGOT_MESSAGE = "Eğer bu e-posta kayıtlıysa, şifre sıfırlama bağlantısı gönderildi."


@router.post("/forgot-password")
@limiter.limit("10/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Şifre sıfırlama e-postası tetikler.

    Kayıtlı olsun ya da olmasın aynı mesaj döner (user enumeration önlemi,
    login'deki desenle tutarlı). E-posta gönderimi başarısız olsa bile
    istemciye sızdırılmaz — sadece loglanır.
    """
    repo = UserRepository(db)
    user = repo.get_by_email(req.email)
    if user and user.is_active:
        token = _make_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_ttl_minutes)
        repo.create_reset_token(PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at))
        reset_url = f"{settings.frontend_url}/auth/reset-password?token={token}"
        ok = get_email_adapter().send_password_reset(user.email, reset_url, req.language)
        if not ok:
            logger.error("Şifre sıfırlama e-postası gönderilemedi: %s", user.email)
        else:
            logger.info("Şifre sıfırlama e-postası gönderildi: %s", user.email)
    return {"message": _GENERIC_FORGOT_MESSAGE}


@router.post("/reset-password")
@limiter.limit("20/minute")
def reset_password(request: Request, req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Token'ı doğrulayıp yeni şifreyi kaydeder; tüm oturumları düşürür."""
    repo = UserRepository(db)
    reset_token = repo.get_reset_token(req.token)
    if not reset_token or reset_token.used:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires = reset_token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    repo.update_password(reset_token.user_id, _hash_password(req.password))
    repo.mark_reset_token_used(req.token)
    repo.delete_sessions_for_user(reset_token.user_id)

    logger.info("Şifre sıfırlandı: user_id=%s", reset_token.user_id)
    return {"message": "Password updated successfully"}
