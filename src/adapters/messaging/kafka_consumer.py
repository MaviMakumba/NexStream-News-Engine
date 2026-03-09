import asyncio
import json
from aiokafka import AIOKafkaConsumer
from src.infrastructure.config.database import SessionLocal
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.analysis.groq_analyzer import GroqAnalyzer
from src.adapters.scrapers.rss_scrapers import (
    BBCTechnologyScraper, BBCSportScraper,
    TRTHaberScraper, BBCTurkishScraper,
    HurriyetScraper, HurriyetSporScraper,
)
from src.application.services.news_service import NewsService

SCRAPER_MAP = {
    "BBC Technology":  BBCTechnologyScraper(),
    "TRT Haber":       TRTHaberScraper(),
    "BBC Türkçe":      BBCTurkishScraper(),
    "Hürriyet":        HurriyetScraper(),
    "BBC Sport":       BBCSportScraper(),
    "Hürriyet Spor":   HurriyetSporScraper(),
}

def _process(scraper):
    """Background thread'de çalışır, kendi session'ını açar."""
    db = SessionLocal()
    try:
        repo = NewsRepository(db)
        analyzer = GroqAnalyzer()
        service = NewsService(repository=repo, analyzer=analyzer)
        service.update_news_from_source(scraper)
    finally:
        db.close()

async def consume():
    consumer = AIOKafkaConsumer(
        'news_updates',
        bootstrap_servers='kafka:29092',
        group_id="news_workers_group"
    )
    while True:
        try:
            await consumer.start()
            print("✅ Kafka bağlantısı başarılı!")
            break
        except Exception as e:
            print(f"⚠️ Kafka hazır değil, 5sn sonra tekrar: {e}")
            await asyncio.sleep(5)
    try:
        async for msg in consumer:
            data = json.loads(msg.value)
            source = data.get("source")
            scraper = SCRAPER_MAP.get(source)
            if not scraper:
                print(f"⚠️ Bilinmeyen kaynak: {source}")
                continue
            print(f"⚙️ İşleniyor: {source}")
            await asyncio.get_event_loop().run_in_executor(
                None, _process, scraper
            )
    except Exception as e:
        print(f"❌ Worker hatası: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())