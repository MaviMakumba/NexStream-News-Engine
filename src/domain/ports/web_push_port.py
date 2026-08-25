"""Tarayıcı push bildirimi gönderme port'u — VAPID imzalı push mesajı yollama sözleşmesi.

Somut implementasyon: adapters/notifications/pywebpush_adapter.py (pywebpush).

İSİM NOTU: mevcut NotificationPort (domain/ports/notification_port.py) /ws/feed
canlı yayını için — alakasız bir kavram, isim çakışmasın diye bilinçli olarak
WebPushPort adı seçildi.
"""

from abc import ABC, abstractmethod
from src.domain.models.push_subscription import PushSubscription


class WebPushPort(ABC):
    @abstractmethod
    def send(self, subscription: PushSubscription, title: str, body: str, url: str) -> bool:
        """Gönderir; abonelik geçersizse (404/410) veya başka bir hatada False
        döner, hiçbir zaman exception fırlatmaz (fail-open)."""
