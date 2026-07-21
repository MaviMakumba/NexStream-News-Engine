"""Kullanıcı repository port'u (hexagonal mimari sözleşmesi).

Application katmanı kullanıcı/oturum/kullanım-logu işlemlerine bu soyutlama
üzerinden erişir; somut PostgreSQL implementasyonu
`src/adapters/repositories/user_repository.py` içindedir.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.models.user import User, UserSession, PasswordResetToken, EmailVerificationToken


class UserRepositoryPort(ABC):
    # ── Kullanıcı CRUD ─────────────────────────────────────────────────────

    @abstractmethod
    def create_user(self, user: User) -> User: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def get_by_api_key(self, api_key: str) -> Optional[User]:
        """Kullanıcıya özel API anahtarından (X-User-Key) kullanıcıyı çözer."""
        ...

    @abstractmethod
    def list_users(self, limit: int, offset: int, tier: Optional[str] = None) -> List[User]:
        """Kayıt tarihine göre azalan sırada kullanıcı listesi (admin müşteri paneli)."""
        ...

    @abstractmethod
    def count_users(self, tier: Optional[str] = None) -> int: ...

    @abstractmethod
    def update_tier(self, user_id: int, tier: str, stripe_customer_id: Optional[str] = None) -> bool: ...

    @abstractmethod
    def update_role(self, user_id: int, role: str) -> bool: ...

    @abstractmethod
    def set_api_key(self, user_id: int, api_key: Optional[str]) -> bool:
        """API anahtarını günceller; None vermek anahtarı iptal eder."""
        ...

    @abstractmethod
    def update_password(self, user_id: int, password_hash: str) -> bool: ...

    # ── Oturum yönetimi ────────────────────────────────────────────────────

    @abstractmethod
    def create_session(self, session: UserSession) -> UserSession: ...

    @abstractmethod
    def get_session(self, token: str) -> Optional[UserSession]: ...

    @abstractmethod
    def delete_session(self, token: str) -> bool: ...

    @abstractmethod
    def delete_sessions_for_user(self, user_id: int) -> None:
        """Şifre değişiminde tüm cihazlardaki oturumları düşürür."""
        ...

    # ── Şifre sıfırlama ────────────────────────────────────────────────────

    @abstractmethod
    def create_reset_token(self, reset_token: PasswordResetToken) -> PasswordResetToken: ...

    @abstractmethod
    def get_reset_token(self, token: str) -> Optional[PasswordResetToken]: ...

    @abstractmethod
    def mark_reset_token_used(self, token: str) -> None: ...

    # ── E-posta doğrulama ──────────────────────────────────────────────────

    @abstractmethod
    def create_verification_token(self, verification_token: EmailVerificationToken) -> EmailVerificationToken: ...

    @abstractmethod
    def get_verification_token(self, token: str) -> Optional[EmailVerificationToken]: ...

    @abstractmethod
    def mark_verification_token_used(self, token: str) -> None: ...

    @abstractmethod
    def mark_email_verified(self, user_id: int) -> bool: ...

    # ── Kullanım takibi (kota + istatistik) ────────────────────────────────

    @abstractmethod
    def log_usage(self, user_id: Optional[int], endpoint: str, method: str, status_code: int, response_ms: float) -> None: ...

    @abstractmethod
    def get_usage_stats(self, user_id: Optional[int], days: int) -> List[dict]: ...

    @abstractmethod
    def get_daily_usage_count(self, user_id: int) -> int: ...
