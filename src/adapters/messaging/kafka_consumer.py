import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.infrastructure.logging.logger import setup_logging
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.analysis.groq_analyzer import GroqAnalyzer
from src.adapters.scrapers.registry import SCRAPER_REGISTRY
from src.adapters.search.chroma_search_repository import ChromaSearchRepository
from src.application.services.news_service import NewsService

logger = logging.getLogger(__name__)


def _process(scraper):
    db = SessionLocal()
    try:
        repo = NewsRepository(db)
        analyzer = GroqAnalyzer()
        search_repo = ChromaSearchRepository()
        service = NewsService(repository=repo, analyzer=analyzer, search_repository=search_repo)
        service.update_news_from_source(scraper)
    finally:
        db.close()


async def consume():
    setup_logging()
    consumer = AIOKafkaConsumer(
        'news_updates',
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="news_workers_group"
    )
    while True:
        try:
            await consumer.start()
            logger.info("Kafka bağlantısı başarılı.")
            break
        except Exception as e:
            logger.warning("Kafka hazır değil, 5sn sonra tekrar: %s", e)
            await asyncio.sleep(5)
    try:
        async for msg in consumer:
            data = json.loads(msg.value)
            source = data.get("source")
            scraper = SCRAPER_REGISTRY.get(source)
            if not scraper:
                logger.warning("Bilinmeyen kaynak: %s", source)
                continue
            logger.info("İşleniyor: %s", source)
            await asyncio.get_event_loop().run_in_executor(
                None, _process, scraper
            )
    except Exception as e:
        logger.error("Worker hatası: %s", e)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(consume())
