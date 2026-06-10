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


@dataclass
class User:
    """Kayıtlı kullanıcı.

    is_admin: rol tabanlı admin yetkisi (v1.11). Paylaşımlı X-API-Key'in
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
    is_admin: bool = False
    api_key: Optional[str] = None
    stripe_customer_id: Optional[str] = None
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
