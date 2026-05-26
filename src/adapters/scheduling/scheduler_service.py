import asyncio
import json
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiokafka import AIOKafkaProducer
from src.infrastructure.config.settings import settings
from src.infrastructure.logging.logger import setup_logging

logger = logging.getLogger(__name__)

TOPIC_NAME = "news_updates"

producer: AIOKafkaProducer = None


async def send_scrape_command():
    sources = [s.strip() for s in settings.scrape_sources.split(",") if s.strip()]
    for source in sources:
        try:
            command = {"source": source, "action": "scrape"}
            await producer.send_and_wait(TOPIC_NAME, json.dumps(command).encode())
            logger.info("Scrape emri gönderildi: %s", source)
        except Exception as e:
            logger.error("Scrape emri gönderilemedi (%s): %s", source, e)


async def main():
    global producer
    setup_logging()
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)

    while True:
        try:
            await producer.start()
            logger.info("Kafka Producer başladı.")
            break
        except Exception as e:
            logger.warning("Kafka hazır değil, 5sn sonra tekrar: %s", e)
            await asyncio.sleep(5)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_scrape_command, 'interval', minutes=10, misfire_grace_time=120, coalesce=True)
    scheduler.start()
    logger.info("Scheduler başladı (10dk aralık).")
    await send_scrape_command()

    try:
        await asyncio.Event().wait()
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
