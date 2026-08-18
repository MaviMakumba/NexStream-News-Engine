"""Kullanıcı kimlik doğrulama ve yetkilendirme dependency'leri.

Tüm router'ların paylaştığı FastAPI dependency zinciri:

    get_optional_user   → token/anahtar varsa kullanıcıyı çözer, yoksa None
    get_current_user    → kullanıcı zorunlu; yoksa 401
    require_admin       → admin yetkisi zorunlu (iki yol, aşağıya bak)
    check_tier_limit    → /api/v1 günlük kota kontrolü (429)

Kimlik çözme öncelik sırası (get_optional_user):
    1. X-Session-Token  — SSR'ın kendi server-to-server fetch'i / API testleri
    2. nxs_session cookie — web oturumu (login/register HttpOnly cookie verir,
       tarayıcı otomatik gönderir; SSR'da next/headers ile okunur)
    3. X-User-Key       — kullanıcıya özel API anahtarı (v1.11)

Yetki hiyerarşisi (v1.13, user < moderator < admin — bkz. domain/models/user.py):
    require_moderator    → admin panelini GÖRME yetkisi (moderator veya admin)
    require_admin        — iki yoldan biri yeterlidir:
        1. X-API-Key        — paylaşımlı makine-makine anahtarı (settings.api_key)
        2. Admin kullanıcı  — users.role="admin" VEYA e-posta ADMIN_EMAILS'te
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from src.adapters.api.auth import api_key_matches
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, UserRole, UserTier, role_at_least, effective_tier, TIER_DAILY_LIMITS

# Oturum cookie'sinin adı — auth_router.py (set/delete) ile paylaşılır.
SESSION_COOKIE_NAME = "nxs_session"


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


def has_owner_role(user: User) -> bool:
    """Etkin owner kontrolü: DB'deki role="owner" VEYA OWNER_EMAILS bootstrap listesi.

    Owner rolü API'den asla atanamaz — tek kaynak bu env değişkeni ya da elle
    yazılan bir DB satırı. `tier` alanına dokunmaz, bkz. user_effective_tier.
    """
    return user.role == UserRole.OWNER or (user.email or "").lower() in settings.owner_email_set


def has_admin_role(user: User) -> bool:
    """Etkin admin kontrolü: role>=admin (owner dahil) VEYA ADMIN_EMAILS bootstrap.

    owner ⊃ admin ⊃ moderator — owner hiçbir admin endpoint'inden dışlanmaz.
    """
    return role_at_least(user.role, UserRole.ADMIN) or (user.email or "").lower() in settings.admin_email_set or has_owner_role(user)


def has_moderator_role(user: User) -> bool:
    """Admin panelini GÖRME yetkisi: moderator, admin, veya ADMIN_EMAILS bootstrap.

    Moderatör görüntüleme yapabilir (kullanım/kullanıcı/sponsor listeleri) ama
    rol değiştiremez, sponsor CRUD yapamaz — bu işlemler ayrıca require_admin ister.
    """
    return role_at_least(user.role, UserRole.MODERATOR) or has_admin_role(user)


def effective_role(user: User) -> str:
    """Frontend'e dönülen etkin rol — ADMIN_EMAILS/OWNER_EMAILS bootstrap'lerini yansıtır."""
    if has_owner_role(user):
        return UserRole.OWNER.value
    return UserRole.ADMIN.value if has_admin_role(user) else UserRole(user.role).value


def user_effective_tier(user: User) -> UserTier:
    """Owner tespitini (OWNER_EMAILS) çözüp saf domain fonksiyonuna devreden sarmalayıcı.

    Domain katmanı settings import edemediği için bu ayrım burada yaşar — tüm
    tier-gating çağrı noktaları `user.tier` yerine bunu okumalı.
    """
    return effective_tier(user.tier, has_owner_role(user))


def get_optional_user(
    x_session_token: Optional[str] = Header(None),
    session_cookie: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    x_user_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Kimlik bilgisi varsa kullanıcıyı döner; anonim isteklerde None.

    Anonim istekler hata almaz — public endpoint'ler kota uygulamadan çalışır.
    """
    repo = UserRepository(db)
    token = x_session_token or session_cookie
    if token:
        user = resolve_session_user(repo, token)
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
    if api_key_matches(x_api_key):
        return
    if user and has_admin_role(user):
        return
    if user:
        # Oturum geçerli ama yetki yok → 403 (401 "kimliğini kanıtla" demek olurdu)
        raise HTTPException(status_code=403, detail="Admin privileges required")
    raise HTTPException(status_code=401, detail="Admin authentication required")


def require_owner(
    x_api_key: Optional[str] = Header(None),
    user: Optional[User] = Depends(get_optional_user),
) -> None:
    """Owner-only endpoint koruması — geçerli X-API-Key VEYA owner kullanıcı oturumu."""
    if api_key_matches(x_api_key):
        return
    if user and has_owner_role(user):
        return
    if user:
        raise HTTPException(status_code=403, detail="Owner privileges required")
    raise HTTPException(status_code=401, detail="Admin authentication required")


def require_moderator(
    x_api_key: Optional[str] = Header(None),
    user: Optional[User] = Depends(get_optional_user),
) -> None:
    """Admin panelini GÖRME koruması — X-API-Key VEYA moderator/admin oturumu.

    require_admin'den farkı: moderator rolü de geçer. Rol değiştirme ve sponsor
    CRUD gibi yazma işlemleri ayrıca route düzeyinde require_admin ister.
    """
    if api_key_matches(x_api_key):
        return
    if user and has_moderator_role(user):
        return
    if user:
        raise HTTPException(status_code=403, detail="Moderator privileges required")
    raise HTTPException(status_code=401, detail="Admin authentication required")


def check_tier_limit(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Kullanıcının günlük /api/v1 kotasını kontrol eder; aşımda 429.

    Anonim istekler kota dışıdır (None döner); Enterprise ve owner sınırsızdır.
    """
    if user is None:
        return None
    tier = user_effective_tier(user)
    limit = TIER_DAILY_LIMITS.get(tier)
    if limit is None:
        return user
    repo = UserRepository(db)
    count = repo.get_daily_usage_count(user.id)
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily API limit reached ({limit} req/day). Upgrade your plan for higher limits.",
            headers={"X-Tier": tier, "X-Daily-Limit": str(limit)},
        )
    return user
