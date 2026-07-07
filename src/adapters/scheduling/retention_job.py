"""Günlük retention job'ı — her gün RETENTION_HOUR_UTC'de eski içerik temizliği yapar.

main.py lifespan'inde background task olarak çalışır (newsletter_job.py ile
aynı desen). İki katman:
  1. ChromaDB'den eski vektörleri kaldırır (chroma_retention_days > 0 ise) —
     geri dönüşü mümkündür (`POST /news/reindex`), Postgres etkilenmez.
  2. Postgres'ten KALICI siler (db_retention_days > 0 ise) — varsayılan
     kapalı, bilinçli olarak açılmalı.
Ayrıca son 7 günün haberlerini yeniden indexleyerek (upsert, ucuz) indexleme
boşluklarına karşı kendini onarır.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.adapters.repositories.news_repository import NewsRepository
from src.dependencies import get_search_repository

logger = logging.getLogger(__name__)

_SELF_HEAL_WINDOW_DAYS = 7


async def run_retention_job() -> None:
    """Background task: settings.retention_hour_utc'de her gün çalışır."""
    logger.info("Retention job başladı (her gün %02d:00 UTC'de)", settings.retention_hour_utc)

    while True:
        now = datetime.now(timezone.utc)
        target = now.replace(hour=settings.retention_hour_utc, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait = (target - now).total_seconds()
        logger.info("Retention: sonraki çalışma %s (%.0f sn sonra)", target.isoformat(), wait)
        await asyncio.sleep(wait)

        try:
            await _run_retention()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Retention job hatası: %s", e)


async def _run_retention() -> None:
    now = datetime.now(timezone.utc)
    search_repository = get_search_repository()

    if settings.chroma_retention_days > 0:
        cutoff_iso = (now - timedelta(days=settings.chroma_retention_days)).isoformat()
        deleted = search_repository.delete_before(cutoff_iso)
        logger.info("Retention: ChromaDB'den %d eski vektör kaldırıldı (cutoff=%s)", deleted, cutoff_iso)

    db = SessionLocal()
    try:
        news_repo = NewsRepository(db)

        if settings.db_retention_days > 0:
            db_cutoff = now - timedelta(days=settings.db_retention_days)
            removed = news_repo.delete_articles_before(db_cutoff)
            logger.info("Retention: Postgres'ten %d haber kalıcı silindi (cutoff=%s)", removed, db_cutoff.isoformat())

        # Self-healing: son 7 günün haberlerini tekrar indexler (ucuz, idempotent upsert).
        heal_cutoff = now - timedelta(days=_SELF_HEAL_WINDOW_DAYS)
        recent = news_repo.get_articles_created_after(heal_cutoff)
        reindexed = 0
        for article in recent:
            try:
                if search_repository.index_article(article):
                    reindexed += 1
            except Exception as e:
                logger.warning("Retention self-heal reindex hatası (id=%s): %s", article.id, e)
        logger.info("Retention: self-heal %d/%d haber yeniden indexlendi", reindexed, len(recent))
    finally:
        db.close()
