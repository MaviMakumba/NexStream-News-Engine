import asyncio
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
TOPIC_NAME = "news_updates"
SOURCES = os.getenv('SCRAPE_SOURCES', 'BBC Technology').split(',')

producer: AIOKafkaProducer = None

async def send_scrape_command():
    for source in SOURCES:
        try:
            command = {"source": source.strip(), "action": "scrape"}
            await producer.send_and_wait(TOPIC_NAME, json.dumps(command).encode())
            print(f"✅ Emir gönderildi: {source}")
        except Exception as e:
            print(f"❌ Gönderilemedi ({source}): {e}")

async def main():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    while True:
        try:
            await producer.start()
            print("✅ Kafka Producer başladı.")
            break
        except Exception as e:
            print(f"⚠️ Kafka hazır değil, 5sn sonra tekrar: {e}")
            await asyncio.sleep(5)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_scrape_command, 'interval', minutes=30)
    scheduler.start()
    print("⏳ Scheduler başladı.")

    try:
        await asyncio.Event().wait()
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())