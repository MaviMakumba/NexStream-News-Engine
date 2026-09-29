"""Worker süreci — pipeline'ın tüketici ucu (ayrı container'da çalışır).

Akış: Kafka 'news_updates' mesajı → kaynağın scraper'ı → NewsService ile
analiz+kayıt+index → her çevrim sonunda eksik analizleri tamamla.
İlk açılışta tüm kaynaklar bir kez taranır (startup scrape); Kafka kopması
sonsuz döngüde yeniden bağlanılarak tolere edilir.
"""

import asyncio
import json
import logging
import time
from typing import Optional
from aiokafka import AIOKafkaConsumer
from src.adapters.scrapers.source_policy import effective_daily_cap, parse_cap_overrides
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.infrastructure.logging.logger import setup_logging
from src.infrastructure.observability.sentry import init_sentry
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.subscriber_repository import SubscriberRepository
from src.adapters.repositories.push_subscription_repository import PushSubscriptionRepository
from src.adapters.notifications.web_push_factory import build_web_push
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


def _daily_cap_for(scraper) -> Optional[int]:
    """Kaynağın günlük tavanı: SOURCE_DAILY_CAPS override > scraper.daily_cap > None (sınırsız)."""
    overrides = parse_cap_overrides(settings.source_daily_caps)
    return effective_daily_cap(scraper.source_name, getattr(scraper, "daily_cap", None), overrides)


async def _process(scraper):
    db = SessionLocal()
    try:
        repo = NewsRepository(db)
        analyzer = build_analyzer()
        sub_repo = SubscriberRepository(db)
        push_repo = PushSubscriptionRepository(db)
        service = NewsService(
            repository=repo,
            analyzer=analyzer,
            search_repository=_get_search_repo(),
            subscriber_repository=sub_repo,
            email_port=_get_email_adapter(),
            push_repository=push_repo,
            web_push=build_web_push(),
        )
        # Kaynak başına haber sayısını sınırla — tek bir yoğun kaynak Groq rate
        # limit'e takılınca TÜM yeni haberlerini bitirmeden sıradaki kaynağa
        # geçilemiyordu, diğer 16 kaynak saatlerce aç kalıyordu (bkz. settings.py).
        cap = settings.worker_max_new_articles_per_run or None
        await service.update_news_from_source(scraper, max_new_articles=cap, daily_cap=_daily_cap_for(scraper))
        # 1 Eyl 2026: update_news_from_source ile reanalyze_missed arasında hiç
        # bekleme yoktu — Groq'un TPM kovasını (leaky bucket) anlık boşaltan
        # burst kaynaklarından biriydi (bkz. settings.py::groq_request_interval_seconds).
        await asyncio.sleep(settings.groq_request_interval_seconds)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, service.reanalyze_missed, 3)
        # Kaynaklar arası da hiç bekleme yoktu — 17 kaynak art arda boşluksuz
        # ateşleniyordu, aynı burst probleminin ikinci görünümü. Bu bekleme
        # _process()'in içinde olduğu için hem başlangıç taramasına hem
        # tekil Kafka mesajlarına otomatik uygulanır.
        await asyncio.sleep(settings.groq_request_interval_seconds)
    finally:
        db.close()


def _is_stale_command(timestamp_ms: Optional[int], now: Optional[float] = None) -> bool:
    """Scrape emri settings.worker_stale_command_seconds'tan eski mi?

    Timestamp'i olmayan (None / -1) mesajlar asla bayat sayılmaz — atlamak
    yerine işlemek daha güvenli.
    """
    max_age = settings.worker_stale_command_seconds
    if not max_age or timestamp_ms is None or timestamp_ms < 0:
        return False
    now = time.time() if now is None else now
    return now - timestamp_ms / 1000 > max_age


def _build_consumer() -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        'news_updates',
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="news_workers_group",
        auto_offset_reset="earliest",
        # Tek bir kaynak Groq rate-limit beklemeleriyle 10+ dk sürebiliyor;
        # varsayılan 5 dk'lık poll aralığı worker'ı her mesajda gruptan
        # attırıyordu (28 Eyl 2026, rpk: STATE Empty / MEMBERS 0).
        max_poll_interval_ms=60 * 60 * 1000,
    )


async def consume():
    setup_logging()
    init_sentry("worker")
    startup_done = False  # Run startup scrape only once per process, not on every reconnect

    while True:  # outer loop: reconnect on Kafka failures
        consumer = _build_consumer()
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
            skipped = 0
            async for msg in consumer:
                if _is_stale_command(msg.timestamp):
                    skipped += 1
                    if skipped % 500 == 0:
                        logger.info("Bayat scrape emri atlandı (toplam %d)", skipped)
                    continue
                if skipped:
                    logger.info("%d bayat scrape emri atlandı", skipped)
                    skipped = 0
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
