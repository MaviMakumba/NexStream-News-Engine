"""Hesap self-service endpoint'leri (/account) — v1.11.

Kullanıcının KENDİ verisine eriştiği endpoint'ler; admin yetkisi gerekmez,
sadece geçerli oturum (X-Session-Token) yeterlidir:

    GET    /account/usage    — günlük kota durumu + endpoint bazlı istatistik
    POST   /account/api-key  — kişisel API anahtarı üret/yenile
    DELETE /account/api-key  — anahtarı iptal et
    GET    /account/saved    — kaydedilen (bookmark) haberler (v2.2)
    POST   /account/saved/{id}   — haberi kaydet (v2.2)
    DELETE /account/saved/{id}   — kaydı kaldır (v2.2)
    DELETE /account          — hesabı kalıcı olarak sil (v2.1.2)

API anahtarı `nxs_` öneklidir ve /api/v1 isteklerinde `X-User-Key` header'ı
ile session yerine kullanılabilir (kota kullanıcının tier'ından uygulanır).
"""

import logging
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.api.auth_utils import get_current_user, has_owner_role, user_effective_tier, verify_password, SESSION_COOKIE_NAME
from src.adapters.api.limiter import limiter
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.saved_article_repository import SavedArticleRepository
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, TIER_DAILY_LIMITS
from src.domain.schemas.news_schema import NewsResponse
from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings

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


# ── Kaydet / Sonra Oku (bookmarks, v2.2) ────────────────────────────────────
# Rakip taraması sonrası quick-win paketi (bkz. CLAUDE.md YOL HARİTASI, 19 Ağu
# 2026) — hemen hemen her rakip agregatörde olan tablo-stakes bir özellik.

@router.get("/saved", response_model=List[NewsResponse])
def list_saved_articles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kaydedilenler — en son kaydedilen önce (kayıt sırası korunur, DB dönüş
    sırası DEĞİL: `get_articles_by_ids` bir IN sorgusu, sırayı garanti etmez)."""
    ids = SavedArticleRepository(db).list_saved_article_ids(current_user.id)
    articles = {a.id: a for a in NewsRepository(db).get_articles_by_ids(ids)}
    return [articles[i] for i in ids if i in articles]


@router.post("/saved/{article_id}")
@limiter.limit("30/minute")
def save_article(
    request: Request,
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if NewsRepository(db).get_article_by_id(article_id) is None:
        raise HTTPException(status_code=404, detail="Haber bulunamadı.")
    SavedArticleRepository(db).save(current_user.id, article_id)
    return {"saved": True}


@router.delete("/saved/{article_id}")
@limiter.limit("30/minute")
def unsave_article(
    request: Request,
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Idempotent — zaten kayıtlı değilse de 200 döner (tekrar denemek zararsız)."""
    SavedArticleRepository(db).unsave(current_user.id, article_id)
    return {"saved": False}


# ── Hesap silme (v2.1.2) ─────────────────────────────────────────────────────

class DeleteAccountRequest(BaseModel):
    password: str = Field(..., max_length=128)


def _cancel_active_subscriptions(stripe_customer_id: str) -> None:
    """Hesap silinirken varsa aktif Stripe aboneliğini iptal eder.

    Best-effort: Stripe yapılandırılmamışsa no-op, API çağrısı başarısız
    olursa sadece loglanır — hesap silme akışını ASLA bloklamaz (projenin
    genel "exception yut, fallback dön" ilkesiyle tutarlı, bkz. CLAUDE.md).
    """
    if not settings.stripe_secret_key:
        return
    try:
        import stripe as _stripe
        _stripe.api_key = settings.stripe_secret_key
        subs = _stripe.Subscription.list(customer=stripe_customer_id, status="active")
        for sub in subs.auto_paging_iter():
            _stripe.Subscription.cancel(sub.id)
    except Exception as e:
        logger.error("Stripe abonelik iptali başarısız (hesap silme yine de devam ediyor): %s", e)


@router.delete("")
@limiter.limit("5/minute")
def delete_account(
    request: Request,
    req: DeleteAccountRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hesabı ve KENDİSİNE bağlı tüm veriyi kalıcı olarak siler — geri alınamaz.

    Sırasıyla: (1) owner rolü reddedilir (OWNER_EMAILS bootstrap'i DB satırı
    gitse de yetkiyi geri verir, kafa karışıklığı önlenir — rol değiştirmedeki
    self-block'la aynı gerekçe); (2) parola tekrar istenir (irreversible bir
    eylem için ek doğrulama — çalınmış/paylaşılmış oturuma karşı); (3) varsa
    Stripe aboneliği iptal edilir (best-effort); (4) bülten aboneliği
    (email eşleşmesi, user_id'ye bağlı değil) silinir; (5) `UserRepository.
    delete_user` ile kullanıcı + session/token/usage_log satırları silinir;
    (6) oturum cookie'si temizlenir.
    """
    if has_owner_role(current_user):
        raise HTTPException(status_code=403, detail="Owner hesapları bu şekilde silinemez.")
    if not verify_password(req.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Parola yanlış.")

    if current_user.stripe_customer_id:
        _cancel_active_subscriptions(current_user.stripe_customer_id)

    SubscriberRepository(db).delete_by_email(current_user.email)
    UserRepository(db).delete_user(current_user.id)

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    logger.info("Hesap silindi: user_id=%s", current_user.id)
    return {"message": "Account deleted"}
