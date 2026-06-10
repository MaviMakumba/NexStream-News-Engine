"""Günlük newsletter job'ı — her gün NEWSLETTER_HOUR_UTC'de digest gönderir.

main.py lifespan'inde background task olarak çalışır; saat başı uyanır,
gönderim saati geldiyse aktif 'daily' abonelere son 24 saatin en iyi 10
haberini (tercihlere göre filtreli) yollar.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.notifications.email_adapter import get_email_adapter
from src.adapters.api.routers.admin_router import get_active_sponsor

logger = logging.getLogger(__name__)


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

        articles = news_repo.get_latest_news(10)
        if not articles:
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
                ok = email_adapter.send_digest(sub.email, articles, sub.language, sponsor=sponsor)
                if ok:
                    sent += 1
            except Exception as e:
                logger.warning("Digest gönderilemedi (%s): %s", sub.email, e)

        logger.info("Newsletter digest gönderildi: %d/%d abone | sponsor=%s", sent, len(subscribers), sponsor.name if sponsor else None)
    finally:
        db.close()
