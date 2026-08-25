"""Web push gönderim adapter'ı — pywebpush + VAPID imzalama (v2.5).

WebPushPort sözleşmesini gerçekler. pywebpush.webpush() hiçbir zaman dışarı
exception sızdırmaz — burada yakalanır, loglanır, False döner (projenin
"exception yut, logla, fallback dön" kuralı).
"""

import json
import logging

from pywebpush import webpush, WebPushException

from src.domain.models.push_subscription import PushSubscription
from src.domain.ports.web_push_port import WebPushPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# 1 saat — "anlık" bildirim niteliğinde, cihaz gün boyu çevrimdışıysa eski bir
# uyarıyı geç teslim etmenin anlamı yok (pywebpush varsayılanı ttl=0, yani
# cihaz o an çevrimdışıysa mesaj hiç saklanmaz — bu bizim için fazla agresif).
_PUSH_TTL_SECONDS = 3600


class PyWebPushAdapter(WebPushPort):
    def send(self, subscription: PushSubscription, title: str, body: str, url: str) -> bool:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
                ttl=_PUSH_TTL_SECONDS,
            )
            return True
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                return False
            logger.warning("Web push gönderilemedi (status=%s): %s", status, e)
            return False
