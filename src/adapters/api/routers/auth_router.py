"""Kayıt / giriş / oturum endpoint'leri (/auth).

Oturum modeli: başarılı kayıt/giriş sonrası rastgele opak token üretilir,
`user_sessions` tablosuna TTL ile yazılır. İstemciye HttpOnly, `nxs_session`
adlı bir cookie olarak verilir (JS token değerini hiç göremez — XSS'e karşı
korumalı) ve tarayıcı sonraki isteklerde bunu otomatik gönderir. Next.js SSR
da aynı cookie'yi `next/headers` ile okuyup ilk render'ı doğru üretir (bkz.
frontend/app/layout.tsx) — bu sayede "önce misafir görünüp sonra giriş
yapılmış hale geçme" flaş'ı (FOUC) sunucu seviyesinde ortadan kalkar.
JWT yerine DB-backed session tercih edildi: anında iptal edilebilir (logout).

Parola: bcrypt (passlib'siz, doğrudan) — bcrypt girdiyi 72 byte ile sınırlar.
"""

import bcrypt
import logging
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Header, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session

from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from src.adapters.api.auth_utils import has_admin_role, has_moderator_role, effective_role, get_current_user, SESSION_COOKIE_NAME
from src.adapters.api.limiter import limiter
from src.adapters.notifications.email_adapter import get_email_adapter
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, UserSession, UserTier, PasswordResetToken, EmailVerificationToken

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    # bcrypt girdiyi zaten 72 byte'a kırpıyor; üst sınır olmaması sadece
    # gereksiz CPU/bant genişliği tüketimine açık kapı bırakıyordu (güvenlik denetimi).
    password: str = Field(..., max_length=128)
    # DB kolonu VARCHAR(255) — sınırsız kabul edip Postgres'te patlamak yerine 422 dön.
    name: str = Field("", max_length=255)
    language: str = "TR"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    language: str = "TR"


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., max_length=256)
    password: str = Field(..., max_length=128)


class ResendVerificationRequest(BaseModel):
    language: str = "TR"


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., max_length=256)


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


# Kayıtlı olmayan bir e-postayla login denendiğinde bcrypt'in ÇALIŞMAMASI
# (kullanıcı bulunamazsa erken dönüş) yanıt süresinden kayıtlı/kayıtsız e-posta
# ayrımı yapılabilmesine yol açan bir timing side-channel'dı (güvenlik denetimi).
# Bu sabit hash üzerinde HER durumda bcrypt çalıştırılarak süre eşitlenir.
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"nexstream-timing-safe-dummy", bcrypt.gensalt()).decode()


def _open_session(repo: UserRepository, user_id: int) -> str:
    """Yeni oturum açar, token'ı döner. Register ve login ortak kullanır."""
    token = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    repo.create_session(UserSession(user_id=user_id, token=token, expires_at=expires_at))
    return token


def _set_session_cookie(response: Response, token: str) -> None:
    """HttpOnly oturum cookie'sini yazar — register/login ortak kullanır.

    SameSite=Lax + aynı origin (Next.js rewrites/nginx proxy) varsayımıyla
    çalışır; farklı origin'den cross-site istekte tarayıcı bu cookie'yi
    göndermez (kasıtlı — CSRF yüzeyini büyütmemek için).
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


def _assert_deliverable_email(email: str) -> None:
    """Domain'in gerçekten mail kabul ettiğini DNS (MX/A kaydı) üzerinden doğrular.

    Sadece kayıtta çalışır — "muz@muz.com" gibi hiç var olmayan/mail almayan
    domain'leri yakalar. Var olan gerçek bir domain + uydurma kullanıcı adını
    (örn. rastgele123@gmail.com) YAKALAYAMAZ — bunun gerçek çözümü kayıt
    sonrası gönderilen e-posta doğrulama linkidir (v1.15, bkz.
    `_send_verification_email`). DNS sorgusunun kendisi ağ/timeout yüzünden
    başarısız olursa KAYDI ENGELLEMEYİZ — sadece definitif "bu domain mail
    almıyor" sonucunda 400 döneriz.
    """
    try:
        validate_email(email, check_deliverability=True)
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=f"E-posta adresi geçersiz görünüyor: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("E-posta deliverability kontrolü başarısız oldu (kayıt engellenmedi): %s", e)


def _user_payload(user: User) -> dict:
    """API yanıtlarındaki kullanıcı gösterimi — parola hash'i asla sızmaz.

    `role`: etkin yetki (user/moderator/admin, ADMIN_EMAILS bootstrap'i dahil) —
        frontend'in admin panel erişimini/rol yönetim kontrollerini göstermesi içindir.
    `is_admin`: geriye dönük uyumluluk için korunan türetilmiş alan (role == admin).
    `email_verified`: v1.15 — Free tier'da erişimi kısıtlamaz, sadece ücretli
        kademeye yükseltmede (billing checkout) şart koşulur.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "tier": user.tier,
        "role": effective_role(user),
        "is_admin": has_admin_role(user),
        "is_moderator": has_moderator_role(user),
        "email_verified": user.email_verified,
    }


def _send_verification_email(repo: UserRepository, user: User, language: str) -> None:
    """Yeni bir doğrulama token'ı üretip mail gönderir — register ve resend ortak kullanır.

    Best-effort: gönderim başarısız olsa da (ağ hatası, Resend down) çağıran
    akışı (register/resend) BOZMAZ — sadece loglanır. Kayıt/oturum açma email
    servisine bağımlı olmamalı (forgot-password'daki desenle tutarlı).
    """
    token = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.email_verification_ttl_minutes)
    repo.create_verification_token(EmailVerificationToken(user_id=user.id, token=token, expires_at=expires_at))
    verify_url = f"{settings.frontend_url}/auth/verify-email?token={token}"
    try:
        ok = get_email_adapter().send_verification(user.email, verify_url, language)
        if not ok:
            logger.error("Doğrulama e-postası gönderilemedi: %s", user.email)
    except Exception as e:
        logger.error("Doğrulama e-postası gönderilirken hata: %s (%s)", user.email, e)


# ── Endpoint'ler ───────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
def register(request: Request, req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    _assert_deliverable_email(req.email)

    user = User(
        email=req.email,
        password_hash=_hash_password(req.password),
        name=req.name,
        tier=UserTier.FREE,
    )
    saved = repo.create_user(user)
    token = _open_session(repo, saved.id)
    _set_session_cookie(response, token)
    _send_verification_email(repo, saved, req.language)

    logger.info("Yeni kullanıcı: %s (tier=free)", saved.email)
    return {"user": _user_payload(saved)}


@router.post("/login")
@limiter.limit("15/minute")
def login(request: Request, req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_email(req.email)
    # E-posta bulunamadı ile yanlış parola aynı mesajı döner (user enumeration önlemi).
    # bcrypt HER durumda çalıştırılır (dummy hash üzerinde) — yoksa "kullanıcı yok"
    # dalı erken dönüp yanıt süresinden kayıtlı e-postalar enumerate edilebilirdi.
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_ok = _verify_password(req.password, password_hash)
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = _open_session(repo, user.id)
    _set_session_cookie(response, token)
    logger.info("Giriş: %s", user.email)
    return {"user": _user_payload(user)}


@router.post("/logout")
def logout(
    response: Response,
    x_session_token: str = Header(None),
    session_cookie: str = Cookie(None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    token = x_session_token or session_cookie
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")
    repo = UserRepository(db)
    if not repo.delete_session(token):
        raise HTTPException(status_code=401, detail="Invalid session token")
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Aktif oturumun kullanıcısını döner — frontend hem client'ta hem SSR'da çağırır.

    Kimlik `get_current_user` → `get_optional_user` zincirinden gelir (header
    veya cookie); 401 zaten o katmanda fırlatılır.
    """
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

    # Token ÖNCE atomik olarak tüketilir, şifre SONRA değiştirilir — eşzamanlı iki
    # istekten yalnızca biri True alır (güvenlik denetimi: TOCTOU yarışı).
    if not repo.mark_reset_token_used(req.token):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    repo.update_password(reset_token.user_id, _hash_password(req.password))
    repo.delete_sessions_for_user(reset_token.user_id)

    logger.info("Şifre sıfırlandı: user_id=%s", reset_token.user_id)
    return {"message": "Password updated successfully"}


# ── E-posta doğrulama ────────────────────────────────────────────────────────

@router.post("/resend-verification")
@limiter.limit("5/minute")
def resend_verification(
    request: Request,
    req: ResendVerificationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Oturum açmış kullanıcı için yeni bir doğrulama e-postası tetikler.

    Zaten doğrulanmışsa no-op (idempotent) — hata değil, aynı başarı mesajı döner.
    """
    if user.email_verified:
        return {"message": "Email already verified"}
    repo = UserRepository(db)
    _send_verification_email(repo, user, req.language)
    logger.info("Doğrulama e-postası yeniden gönderildi: %s", user.email)
    return {"message": "Verification email sent"}


@router.post("/verify-email")
@limiter.limit("20/minute")
def verify_email(request: Request, req: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Token'ı doğrulayıp kullanıcıyı `email_verified=true` işaretler.

    Auth gerektirmez — mail linkine başka bir cihazda/tarayıcıda tıklansa da
    çalışır (reset-password ile aynı desen).
    """
    repo = UserRepository(db)
    verification_token = repo.get_verification_token(req.token)
    if not verification_token or verification_token.used:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    expires = verification_token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    # Token ÖNCE atomik tüketilir (bkz. reset_password'daki aynı TOCTOU gerekçesi).
    if not repo.mark_verification_token_used(req.token):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    repo.mark_email_verified(verification_token.user_id)

    logger.info("E-posta doğrulandı: user_id=%s", verification_token.user_id)
    return {"message": "Email verified successfully"}
