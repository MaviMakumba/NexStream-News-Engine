"""Kullanıcı kimlik doğrulama ve yetkilendirme dependency'leri.

Tüm router'ların paylaştığı FastAPI dependency zinciri:

    get_optional_user   → token/anahtar varsa kullanıcıyı çözer, yoksa None
    get_current_user    → kullanıcı zorunlu; yoksa 401
    require_admin       → admin yetkisi zorunlu (iki yol, aşağıya bak)
    check_tier_limit    → /api/v1 günlük kota kontrolü (429)

Kimlik çözme öncelik sırası (get_optional_user):
    1. X-Session-Token  — web oturumu (login/register sonrası)
    2. X-User-Key       — kullanıcıya özel API anahtarı (v1.11)

Admin yetkisi iki yoldan verilir (require_admin):
    1. X-API-Key        — paylaşımlı makine-makine anahtarı (settings.api_key)
    2. Admin kullanıcı  — users.is_admin=true VEYA e-posta ADMIN_EMAILS'te
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, TIER_DAILY_LIMITS


def resolve_session_user(repo: UserRepository, token: str) -> Optional[User]:
    """Session token'ını kullanıcıya çevirir; süresi dolmuşsa oturumu siler.

    auth_router (/auth/me) ve get_optional_user bu mantığı paylaşır —
    timezone-naive DB tarihleri UTC varsayılarak karşılaştırılır.
    """
    session = repo.get_session(token)
    if not session:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        repo.delete_session(token)
        return None
    return repo.get_by_id(session.user_id)


def has_admin_role(user: User) -> bool:
    """Etkin admin kontrolü: DB kolonu VEYA ADMIN_EMAILS bootstrap listesi.

    Env listesi sayesinde ilk admin, veritabanına dokunmadan atanabilir.
    """
    return user.is_admin or (user.email or "").lower() in settings.admin_email_set


def get_optional_user(
    x_session_token: Optional[str] = Header(None),
    x_user_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Kimlik bilgisi varsa kullanıcıyı döner; anonim isteklerde None.

    Anonim istekler hata almaz — public endpoint'ler kota uygulamadan çalışır.
    """
    repo = UserRepository(db)
    if x_session_token:
        user = resolve_session_user(repo, x_session_token)
        if user:
            return user
    if x_user_key:
        return repo.get_by_api_key(x_user_key)
    return None


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    """Oturum zorunlu olan endpoint'ler için: kullanıcı yoksa 401."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(
    x_api_key: Optional[str] = Header(None),
    user: Optional[User] = Depends(get_optional_user),
) -> None:
    """Admin endpoint koruması — geçerli X-API-Key VEYA admin kullanıcı oturumu.

    Paylaşımlı anahtar makine-makine entegrasyonları için korunur (v1.9);
    insan kullanıcılar v1.11'den itibaren rol tabanlı yetkiyle girer.
    """
    if x_api_key and x_api_key == settings.api_key:
        return
    if user and has_admin_role(user):
        return
    if user:
        # Oturum geçerli ama yetki yok → 403 (401 "kimliğini kanıtla" demek olurdu)
        raise HTTPException(status_code=403, detail="Admin privileges required")
    raise HTTPException(status_code=401, detail="Admin authentication required")


def check_tier_limit(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Kullanıcının günlük /api/v1 kotasını kontrol eder; aşımda 429.

    Anonim istekler kota dışıdır (None döner); Enterprise sınırsızdır.
    """
    if user is None:
        return None
    limit = TIER_DAILY_LIMITS.get(user.tier)
    if limit is None:
        return user
    repo = UserRepository(db)
    count = repo.get_daily_usage_count(user.id)
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily API limit reached ({limit} req/day). Upgrade your plan for higher limits.",
            headers={"X-Tier": user.tier, "X-Daily-Limit": str(limit)},
        )
    return user
