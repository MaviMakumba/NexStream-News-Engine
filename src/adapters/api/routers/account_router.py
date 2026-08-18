"""Hesap self-service endpoint'leri (/account) — v1.11.

Kullanıcının KENDİ verisine eriştiği endpoint'ler; admin yetkisi gerekmez,
sadece geçerli oturum (X-Session-Token) yeterlidir:

    GET    /account/usage    — günlük kota durumu + endpoint bazlı istatistik
    POST   /account/api-key  — kişisel API anahtarı üret/yenile
    DELETE /account/api-key  — anahtarı iptal et

API anahtarı `nxs_` öneklidir ve /api/v1 isteklerinde `X-User-Key` header'ı
ile session yerine kullanılabilir (kota kullanıcının tier'ından uygulanır).
"""

import logging
import secrets

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.adapters.api.auth_utils import get_current_user, user_effective_tier
from src.adapters.api.limiter import limiter
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, TIER_DAILY_LIMITS
from src.infrastructure.config.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["Account"])

# Anahtar öneki: loglarda/destek taleplerinde tür ayrımını kolaylaştırır.
_API_KEY_PREFIX = "nxs_"


@router.get("/usage")
def my_usage(
    days: int = Query(7, ge=1, le=90, description="İstatistik penceresi (gün)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının kendi kota ve kullanım özeti (hesap sayfası paneli)."""
    repo = UserRepository(db)
    limit = TIER_DAILY_LIMITS.get(user_effective_tier(current_user))    # None = sınırsız (owner dahil)
    used_today = repo.get_daily_usage_count(current_user.id)
    rows = repo.get_usage_stats(user_id=current_user.id, days=days)
    return {
        "tier": current_user.tier,
        "daily_limit": limit,
        "used_today": used_today,
        "remaining_today": None if limit is None else max(limit - used_today, 0),
        "days": days,
        "total_requests": sum(r["count"] for r in rows),
        "by_endpoint": rows,
        "has_api_key": bool(current_user.api_key),
    }


@router.post("/api-key", status_code=201)
@limiter.limit("10/minute")
def generate_api_key(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kişisel API anahtarı üretir; mevcut anahtar varsa üzerine yazar (rotate).

    Anahtar yalnızca bu yanıtta tam gösterilir varsayımı YOKTUR — basitlik
    için düz saklanır ve /account/api-key güvenli oturumla yeniden üretilebilir.
    """
    key = _API_KEY_PREFIX + secrets.token_urlsafe(24)
    UserRepository(db).set_api_key(current_user.id, key)
    logger.info("API anahtarı üretildi: user_id=%s", current_user.id)
    return {"api_key": key}


@router.delete("/api-key")
@limiter.limit("10/minute")
def revoke_api_key(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kişisel API anahtarını iptal eder — anahtar anında geçersizleşir."""
    UserRepository(db).set_api_key(current_user.id, None)
    logger.info("API anahtarı iptal edildi: user_id=%s", current_user.id)
    return {"message": "API key revoked"}


@router.get("/api-key")
def get_api_key(current_user: User = Depends(get_current_user)):
    """Mevcut anahtarı döner (hesap sayfasında 'kopyala' için)."""
    return {"api_key": current_user.api_key, "has_api_key": bool(current_user.api_key)}


# v2.1.1 (18 Ağu 2026): /subscriptions/{email} GET/PATCH X-API-Key (paylaşımlı
# admin anahtarı) gerektiriyor — normal bir kullanıcının TARAYICIDAN kendi
# abonelik durumunu okuyamaması anlamına geliyordu. Hesap sayfası kendi
# oturumuyla çalışsın diye burada, /account'un "kendi verin" desenini izleyen
# ayrı bir salt-okunur uç. Kaydetme/güncelleme için hâlâ mevcut PUBLIC
# `POST /subscriptions/` kullanılıyor (zaten upsert, admin anahtarı istemiyor,
# e-posta gövdede geliyor) — burada sadece ÖN-DOLDURMA için okuma eklendi.
@router.get("/newsletter")
def my_newsletter_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kendi bülten abonelik tercihlerin (varsa) — hesap sayfası formunu ön doldurur."""
    sub = SubscriberRepository(db).get_by_email(current_user.email)
    if not sub or not sub.is_active:
        return {"subscribed": False}
    return {
        "subscribed": True,
        "frequency": sub.frequency,
        "keywords": sub.keywords,
        "preferred_sources": sub.preferred_sources,
        "preferred_topics": sub.preferred_topics,
        "language": sub.language,
    }
