"""Kullanıcı domain modelleri.

Hexagonal mimaride saf domain katmanı: hiçbir framework/DB bağımlılığı yoktur.
Kullanıcı hesapları (v1.9) ve rol/anahtar alanları (v1.11) burada tanımlanır;
ORM eşlemesi `src/adapters/repositories/orm_models.py` içindedir.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class UserTier(str, Enum):
    """Abonelik kademesi — API kotasını ve özellik setini belirler."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Kademe başına günlük /api/v1 istek limiti. None = sınırsız (Enterprise).
TIER_DAILY_LIMITS: dict = {
    UserTier.FREE: 100,
    UserTier.PRO: 2000,
    UserTier.ENTERPRISE: None,
}

# Kademe başına arama sonucu tavanı (pricing sayfasındaki vaat — v1.14 tier-gating).
TIER_SEARCH_RESULT_CAP: dict = {
    UserTier.FREE: 10,
    UserTier.PRO: 50,
    UserTier.ENTERPRISE: 200,
}

_TIER_RANK = {UserTier.FREE: 0, UserTier.PRO: 1, UserTier.ENTERPRISE: 2}


def tier_at_least(tier: "UserTier", minimum: "UserTier") -> bool:
    """`tier`, `minimum` seviyesinde veya üzerinde mi? (Pro+ özellik kontrolleri için)"""
    return _TIER_RANK[UserTier(tier)] >= _TIER_RANK[UserTier(minimum)]


def effective_tier(tier: "UserTier", is_owner: bool) -> "UserTier":
    """Owner için her zaman Enterprise döner, aksi halde `tier` aynen geçer.

    Saf domain fonksiyonu — owner tespiti (OWNER_EMAILS env) burada YAPILMAZ,
    çağıran katman (auth_utils.user_effective_tier) zaten çözüp bool geçirir.
    DB'deki `tier` kolonu asla `enterprise` olarak YAZILMAZ — bu sadece
    okuma-zamanı bir projeksiyon (admin panelindeki `is_paying` ayrımının
    kirlenmemesi için, bkz. CLAUDE.md v2.1 notu).
    """
    return UserTier.ENTERPRISE if is_owner else UserTier(tier)


class UserRole(str, Enum):
    """Yetki hiyerarşisi — user < moderator < admin < owner (v2.1'de owner eklendi).

    moderator: admin panelini GÖREBİLİR (kullanım/kullanıcı/sponsor listeleri)
        ama rol değiştiremez, sponsor CRUD yapamaz — destek/gözlem amaçlı.
    admin: rol değiştirebilir (kademeli — kendinden düşük roldekilere), sponsor CRUD.
    owner: sınırsız erişim (effective_tier ile Enterprise muamelesi), kimse
        rolünü değiştiremez. API'den ASLA atanamaz — tek kaynak OWNER_EMAILS
        env değişkeni (veya DB'ye elle yazılan role='owner').
    ADMIN_EMAILS bootstrap listesi DB'ye dokunmadan "admin" muamelesi görür
    (bkz. auth_utils.has_admin_role) — role kolonu bundan bağımsızdır.
    """

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


_ROLE_RANK = {UserRole.USER: 0, UserRole.MODERATOR: 1, UserRole.ADMIN: 2, UserRole.OWNER: 3}


def role_at_least(role: "UserRole", minimum: "UserRole") -> bool:
    """`role`, `minimum` seviyesinde veya üzerinde mi?"""
    return _ROLE_RANK[UserRole(role)] >= _ROLE_RANK[UserRole(minimum)]


@dataclass
class User:
    """Kayıtlı kullanıcı.

    role: yetki hiyerarşisi (v1.13, user/moderator/admin). Paylaşımlı X-API-Key'in
        yerine kullanıcı bazlı yetkilendirme sağlar; makine-makine erişimi
        için X-API-Key yolu korunur.
    api_key: kullanıcıya özel public API anahtarı (v1.11, opsiyonel).
        Session yerine `X-User-Key` header'ı ile /api/v1 erişimi sağlar.
    """

    email: str
    password_hash: str
    name: str = ""
    tier: UserTier = UserTier.FREE
    is_active: bool = True
    role: UserRole = UserRole.USER
    api_key: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    email_verified: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class UserSession:
    """Oturum kaydı — `X-Session-Token` header'ındaki opak token'ı temsil eder."""

    user_id: int
    token: str
    expires_at: datetime
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class PasswordResetToken:
    """Şifre sıfırlama token'ı — tek kullanımlık, kısa TTL'li opak değer.

    `used` işaretlendikten sonra (veya süresi dolduktan sonra) geçersizdir;
    session token'ların aksine kalıcı silinmez, denetim izi için tutulur.
    """

    user_id: int
    token: str
    expires_at: datetime
    used: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class EmailVerificationToken:
    """E-posta doğrulama token'ı — kayıtta gönderilen onay linkinin taşıyıcısı.

    PasswordResetToken ile aynı şekil (tek kullanımlık, TTL'li, opak): DNS/MX
    kontrolü (v1.14) gerçek bir domain + uydurma kullanıcı adını (örn.
    rastgele123@gmail.com) yakalayamaz — bunun tek gerçek çözümü budur.
    Doğrulanmamış kullanıcılar Free tier'da tam erişime sahiptir (yumuşak
    gating); yalnızca ücretli kademeye yükseltme (billing checkout) bunu şart
    koşar — bkz. billing_router.py::create_checkout.
    """

    user_id: int
    token: str
    expires_at: datetime
    used: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None
