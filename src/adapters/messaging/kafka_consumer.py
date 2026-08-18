"""Worker süreci — pipeline'ın tüketici ucu (ayrı container'da çalışır).

Akış: Kafka 'news_updates' mesajı → kaynağın scraper'ı → NewsService ile
analiz+kayıt+index → her çevrim sonunda eksik analizleri tamamla.
İlk açılışta tüm kaynaklar bir kez taranır (startup scrape); Kafka kopması
sonsuz döngüde yeniden bağlanılarak tolere edilir.
"""

import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.infrastructure.logging.logger import setup_logging
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.analysis.factory import build_analyzer
from src.adapters.scrapers.registry import SCRAPER_REGISTRY
from src.adapters.search.chroma_search_repository import ChromaSearchRepository
from src.adapters.notifications.email_adapter import get_email_adapter, EmailPort
from src.application.services.news_service import NewsService

logger = logging.getLogger(__name__)

_search_repo: Optional[ChromaSearchRepository] = None
_email_adapter: Optional[EmailPort] = None


def _get_search_repo() -> Optional[ChromaSearchRepository]:
    global _search_repo
    if _search_repo is None:
        try:
            _search_repo = ChromaSearchRepository()
        except Exception as e:
            logger.warning("ChromaDB bağlantısı kurulamadı, arama/dedup devre dışı: %s", e)
    return _search_repo


def _get_email_adapter() -> EmailPort:
    global _email_adapter
    if _email_adapter is None:
        _email_adapter = get_email_adapter()
    return _email_adapter


async def _process(scraper):
    db = SessionLocal()
    try:
        repo = NewsRepository(db)
        analyzer = build_analyzer()
        sub_repo = SubscriberRepository(db)
        service = NewsService(
            repository=repo,
            analyzer=analyzer,
            search_repository=_get_search_repo(),
            subscriber_repository=sub_repo,
            email_port=_get_email_adapter(),
        )
        await service.update_news_from_source(scraper)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, service.reanalyze_missed, 3)
    finally:
        db.close()


async def consume():
    setup_logging()
    startup_done = False  # Run startup scrape only once per process, not on every reconnect

    while True:  # outer loop: reconnect on Kafka failures
        consumer = AIOKafkaConsumer(
            'news_updates',
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="news_workers_group",
            auto_offset_reset="earliest",
        )
        while True:
            try:
                await consumer.start()
                logger.info("Kafka bağlantısı başarılı.")
                break
            except Exception as e:
                logger.warning("Kafka hazır değil, 5sn sonra tekrar: %s", e)
                await asyncio.sleep(5)

        if not startup_done:
            logger.info("Startup scrape başlatılıyor...")
            for scraper in SCRAPER_REGISTRY.values():
                try:
                    await _process(scraper)
                except Exception as e:
                    logger.error("Startup scrape hatası (%s): %s", getattr(scraper, 'source_name', '?'), e)
            logger.info("Startup scrape tamamlandı.")
            startup_done = True

        try:
            async for msg in consumer:
                data = json.loads(msg.value)
                source = data.get("source")
                scraper = SCRAPER_REGISTRY.get(source)
                if not scraper:
                    logger.warning("Bilinmeyen kaynak: %s", source)
                    continue
                logger.info("İşleniyor: %s", source)
                try:
                    await _process(scraper)
                except Exception as e:
                    logger.error("Mesaj işleme hatası (%s), sonraki mesaja geçiliyor: %s", source, e)
        except Exception as e:
            logger.error("Kafka consumer bağlantı hatası, 10sn sonra yeniden bağlanılıyor: %s", e)
            await asyncio.sleep(10)
        finally:
            try:
                await consumer.stop()
            except Exception:
                pass


if __name__ == "__main__":
    # v2.1.1 (18 Ağu 2026): worker'ın kendi HTTP sunucusu yoktu (kafka_consumer
    # ASGI değil, düz bir Python script) — `articles_processed_total` gibi asıl
    # pipeline sayaçları BURADA artıyor ama Prometheus SADECE app:8000/metrics'i
    # tarıyordu, worker'ın sayaçlarına HİÇ erişemiyordu. Bu, bugün eklenen
    # "1 saattir yeni haber işlenmedi" alert kuralının ilk kez tetiklenmesiyle
    # (yanlış pozitif — DatasourceNoData) bulundu: metrik prod'da HİÇ VERİ
    # ÜRETMEMİŞ, muhtemelen v1.6'dan beri. prometheus_client'ın kendi hafif
    # HTTP sunucusu (uvicorn/FastAPI gerekmez) 9100'de açılıyor; prometheus.yml
    # yeni bir scrape job'u ile tarıyor.
    from prometheus_client import start_http_server
    start_http_server(9100)
    asyncio.run(consume())
