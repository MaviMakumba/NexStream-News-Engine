"""Paylaşımlı API anahtarı doğrulaması (X-API-Key).

Makine-makine erişimi içindir (script, CI, cron). İnsan kullanıcılar için
rol tabanlı yetki auth_utils.require_admin'dedir (v1.11).
"""

from fastapi import Header, HTTPException
from src.infrastructure.config.settings import settings


async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
