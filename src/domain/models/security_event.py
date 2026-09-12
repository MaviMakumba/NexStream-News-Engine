"""Güvenlik günlüğü (security audit trail) domain modeli — 13 Eylül 2026.

12 Eylül olayının dersi: DB'de `users.created_at`, nginx logunda IP vardı ama
ikisi kalıcı olarak bağlı değildi — "bu hesabı açan gerçekten şu IP miydi?"
sorusu saniye eşleştirerek cevaplandı. Bu model olayı, kaynağı (IP, user-agent),
hedefi (e-posta/kullanıcı) ve nginx'in `request_id`'sini TEK satırda tutar;
nginx access log ↔ app log ↔ bu tablo aynı `request_id` ile birbirine bağlanır.

Tek tablo, `category` ile bölümlenmiş (auth/access/abuse/admin): yeni bir olay
tipi eklemek = `EventType`'a bir sabit, şema değişmez. Kişisel veri içerir
(IP/e-posta/UA) → retention job 90 gün sonra siler. Parola, session token,
API anahtarı, cookie veya Authorization header'ı ASLA bu modele girmez.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class EventCategory:
    AUTH = "auth"        # kayıt/giriş/çıkış/şifre
    ACCESS = "access"    # yetki reddi, API anahtarı yaşam döngüsü
    ABUSE = "abuse"      # rate limit tetiklenmesi
    ADMIN = "admin"      # rol/tier/ban değişiklikleri (kim, kime)


class EventType:
    # auth
    REGISTER = "register"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_DONE = "password_reset_done"
    EMAIL_VERIFIED = "email_verified"
    # access
    ADMIN_ACCESS_DENIED = "admin_access_denied"
    API_KEY_GENERATED = "api_key_generated"
    API_KEY_REVOKED = "api_key_revoked"
    # abuse
    RATE_LIMITED = "rate_limited"
    # admin
    ROLE_CHANGED = "role_changed"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"
    TIER_CHANGED = "tier_changed"


USER_AGENT_MAX_LEN = 256
DETAIL_MAX_LEN = 500


@dataclass
class SecurityEvent:
    category: str
    event_type: str
    email: Optional[str] = None       # denenen adres — hesap yoksa bile (brute force hedefi)
    user_id: Optional[int] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    path: Optional[str] = None
    detail: Optional[str] = None      # kısa bağlam: "role user→moderator by admin@x"
    id: Optional[int] = None
    created_at: Optional[datetime] = None
