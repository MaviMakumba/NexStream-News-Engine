"""Kullanıcı repository port'u (hexagonal mimari sözleşmesi).

Application katmanı kullanıcı/oturum/kullanım-logu işlemlerine bu soyutlama
üzerinden erişir; somut PostgreSQL implementasyonu
`src/adapters/repositories/user_repository.py` içindedir.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.models.user import User, UserSession


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
    def update_tier(self, user_id: int, tier: str, stripe_customer_id: Optional[str] = None) -> bool: ...

    @abstractmethod
    def set_api_key(self, user_id: int, api_key: Optional[str]) -> bool:
        """API anahtarını günceller; None vermek anahtarı iptal eder."""
        ...

    # ── Oturum yönetimi ────────────────────────────────────────────────────

    @abstractmethod
    def create_session(self, session: UserSession) -> UserSession: ...

    @abstractmethod
    def get_session(self, token: str) -> Optional[UserSession]: ...

    @abstractmethod
    def delete_session(self, token: str) -> bool: ...

    # ── Kullanım takibi (kota + istatistik) ────────────────────────────────

    @abstractmethod
    def log_usage(self, user_id: Optional[int], endpoint: str, method: str, status_code: int, response_ms: float) -> None: ...

    @abstractmethod
    def get_usage_stats(self, user_id: Optional[int], days: int) -> List[dict]: ...

    @abstractmethod
    def get_daily_usage_count(self, user_id: int) -> int: ...
