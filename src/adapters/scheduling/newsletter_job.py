"""Günlük newsletter job'ı — her gün NEWSLETTER_HOUR_UTC'de digest gönderir.

main.py lifespan'inde background task olarak çalışır; saat başı uyanır,
gönderim saati geldiyse aktif 'daily'/'instant' abonelere kişiselleştirilmiş
bir digest yollar: `domain/services/subscriber_matching.py` ile abonenin
tercih ettiği konu/kaynak/keyword'e uyan haberler öne çıkarılır. Hiç tercih
belirtmemiş (veya tercihine uyan haber bulunamayan) abone genel top-10'u alır
— boş mail atmak yerine her zaman bir digest gönderilir.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.notifications.email_adapter import get_email_adapter
from src.adapters.api.routers.admin_router import get_active_sponsor
from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber
from src.domain.services.subscriber_matching import has_preferences, article_matches_subscriber

logger = logging.getLogger(__name__)

# Kişiselleştirme için filtrelenecek aday havuzu — nihai digest'ten (10) büyük
# tutulur ki dar tercihli aboneler için de eşleşen haber bulma şansı olsun.
_CANDIDATE_POOL_SIZE = 60
_DIGEST_SIZE = 10


def _personalize(pool: List[Article], sub: Subscriber, limit: int = _DIGEST_SIZE) -> List[Article]:
    """Abonenin tercihine uyan haberleri döner; tercih yoksa veya hiç eşleşme
    yoksa genel (filtresiz) listeye düşer — abone her zaman bir şeyler alır."""
    if not has_preferences(sub):
        return pool[:limit]
    matched = [a for a in pool if article_matches_subscriber(a, sub)]
    return matched[:limit] if matched else pool[:limit]


async def run_newsletter_job() -> None:
    """Background task: sends daily digest at settings.newsletter_hour_utc every day."""
    email_adapter = get_email_adapter()
    logger.info("Newsletter job başladı (her gün %02d:00 UTC'de)", settings.newsletter_hour_utc)

    while True:
        now = datetime.now(timezone.utc)
        target = now.replace(hour=settings.newsletter_hour_utc, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait = (target - now).total_seconds()
        logger.info("Newsletter: sonraki gönderim %s (%.0f sn sonra)", target.isoformat(), wait)
        await asyncio.sleep(wait)

        try:
            await _send_digests(email_adapter)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Newsletter job hatası: %s", e)


async def _send_digests(email_adapter) -> None:
    db = SessionLocal()
    try:
        news_repo = NewsRepository(db)
        sub_repo = SubscriberRepository(db)

        candidate_pool = news_repo.get_latest_news(_CANDIDATE_POOL_SIZE)
        if not candidate_pool:
            logger.info("Newsletter: gönderilecek haber yok, atlanıyor.")
            return

        sponsor = None
        try:
            sponsor = get_active_sponsor(db)
        except Exception:
            pass

        subscribers = sub_repo.get_active_subscribers()
        sent = 0
        for sub in subscribers:
            if sub.frequency not in ("daily", "instant"):
                continue
            try:
                articles = _personalize(candidate_pool, sub)
                ok = email_adapter.send_digest(sub.email, articles, sub.language, sponsor=sponsor)
                if ok:
                    sent += 1
            except Exception as e:
                logger.warning("Digest gönderilemedi (%s): %s", sub.email, e)

        logger.info("Newsletter digest gönderildi: %d/%d abone | sponsor=%s", sent, len(subscribers), sponsor.name if sponsor else None)
    finally:
        db.close()
