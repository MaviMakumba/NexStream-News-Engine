"""Web push abonelik repository port'u — tarayıcı push subscription'larının
kalıcı saklanması sözleşmesi.

Somut implementasyon: adapters/repositories/push_subscription_repository.py (PostgreSQL).
"""

from abc import ABC, abstractmethod
from typing import List
from src.domain.models.push_subscription import PushSubscription


class PushSubscriptionRepositoryPort(ABC):
    @abstractmethod
    def save(self, subscription: PushSubscription) -> PushSubscription:
        """endpoint UNIQUE — aynı endpoint tekrar gelirse üzerine yazar (upsert)."""

    @abstractmethod
    def get_by_email(self, email: str) -> List[PushSubscription]: ...

    @abstractmethod
    def delete_by_endpoint(self, endpoint: str) -> bool:
        """Silinen satır varsa True, yoksa False döner (idempotent çağrı için)."""

    @abstractmethod
    def delete_by_email(self, email: str) -> None:
        """Hesap silinirken kullanıcının TÜM cihaz aboneliklerini temizler."""
