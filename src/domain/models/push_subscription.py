"""Tarayıcı push abonelik domain modeli — Web Push protokolü subscription bilgisi (v2.5)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PushSubscription:
    email: str
    endpoint: str
    p256dh: str
    auth: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
