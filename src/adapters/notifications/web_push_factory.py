"""Web push kompozisyon noktası — VAPID key'leri boşsa None döner (v2.5)."""

from typing import Optional

from src.domain.ports.web_push_port import WebPushPort
from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
from src.infrastructure.config.settings import settings


def build_web_push() -> Optional[WebPushPort]:
    if not settings.vapid_public_key or not settings.vapid_private_key:
        return None
    return PyWebPushAdapter()
