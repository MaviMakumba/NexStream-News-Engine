"""Paylaşımlı API anahtarı doğrulaması (X-API-Key).

Makine-makine erişimi içindir (script, CI, cron). İnsan kullanıcılar için
rol tabanlı yetki auth_utils.require_admin'dedir (v1.11).
"""

import secrets

from fastapi import Header, HTTPException
from src.infrastructure.config.settings import settings


def api_key_matches(candidate: str | None) -> bool:
    """Paylaşımlı anahtarı SABİT ZAMANDA karşılaştırır (auth_utils ile paylaşılır).

    Güvenlik denetimi: düz `==` karakter karakter erken çıkış yapabildiği için
    uzun ömürlü statik bir secret'ta teorik bir timing oracle bırakıyordu.
    `compare_digest` her durumda aynı süreyi harcar. Boş/None anahtar, yapılandırma
    boş bırakıldığında (settings.api_key == "") yanlışlıkla eşleşmesin diye
    ayrıca ve önce reddedilir.
    """
    if not candidate or not settings.api_key:
        return False
    return secrets.compare_digest(candidate, settings.api_key)


async def verify_api_key(x_api_key: str = Header(None)):
    if not api_key_matches(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
