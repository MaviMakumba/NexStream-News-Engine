"""Bülten iptal linki imzası (12 Eylül 2026 güvenlik turu).

`GET /subscriptions/unsubscribe?email=...` eskiden sadece adresi alıyordu —
adresi bilen herkes başkasını abonelikten çıkarabiliyordu (canlıda denendi ve
mail ile "zafiyet raporu" olarak ihbar edildi). Link artık adrese bağlı bir
HMAC-SHA256 imzası (`token`) taşır:

    * sunucu secret'ı olmadan üretilemez,
    * adres değişince geçersizleşir,
    * KASITLI olarak süresiz — aylar önceki bir digest'teki link de çalışmalı
      (RFC 2369 List-Unsubscribe deneyimi), bu yüzden DB'de token tablosu YOK,
      tamamen stateless.

Secret: `settings.unsubscribe_token_secret`, boşsa `settings.api_key` (prod
guard'ı zaten varsayılan/boş API_KEY ile açılmayı reddediyor). E-posta imza
öncesi lowercase normalize edilir — eski abone kayıtları karışık harfli olabilir.
"""

import hashlib
import hmac
from typing import Optional

from src.infrastructure.config.settings import settings


def _secret() -> bytes:
    return (settings.unsubscribe_token_secret or settings.api_key).encode()


def make_unsubscribe_token(email: str) -> str:
    return hmac.new(_secret(), email.strip().lower().encode(), hashlib.sha256).hexdigest()


def verify_unsubscribe_token(email: str, token: Optional[str]) -> bool:
    if not token:
        return False
    return hmac.compare_digest(make_unsubscribe_token(email), token)
