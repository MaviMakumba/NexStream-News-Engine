from fastapi import FastAPI, HTTPException
import json
import asyncio
from aiokafka import AIOKafkaProducer

# 1. Uygulama Ayarları
app = FastAPI(
    title="NexStream News Engine API (Event-Driven)",
    description="Kafka tabanlı, asenkron haber motoru servisi.",
    version="2.0.0"
)

# Global değişken: Kafka Producer nesnesi
producer = None

@app.on_event("startup")
async def startup_event():
    """Uygulama açılırken Kafka bağlantısını kurar."""
    global producer
    # Docker içinden Kafka'ya ulaşmak için 'kafka:29092' adresini kullanıyoruz.
    producer = AIOKafkaProducer(bootstrap_servers='kafka:29092')
    await producer.start()
    print("✅ Kafka Producer bağlantısı kuruldu.")

@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanırken bağlantıyı temizler."""
    global producer
    if producer:
        await producer.stop()
        print("🛑 Kafka Producer bağlantısı kapatıldı.")

@app.get("/")
def health_check():
    return {"status": "active", "mode": "Event-Driven Producer"}

@app.post("/news/update-bbc")
async def trigger_bbc_update_async():
    """
    Bu endpoint artık işi YAPMAZ.
    Sadece Kafka'ya 'Git işi yap' diye bir mesaj bırakır ve döner.
    """
    try:
        # Mesaj içeriği (Emir)
        event_data = {
            "source": "BBC Technology",
            "action": "scrape",
            "timestamp": "now" # Gerçek projede datetime.now() kullanılır
        }
        
        # Mesajı JSON formatına çevirip byte olarak hazırlıyoruz
        message_bytes = json.dumps(event_data).encode("utf-8")
        
        # Kafka'ya fırlat! (Konu başlığı: 'news_updates')
        await producer.send_and_wait("news_updates", message_bytes)
        
        return {
            "message": "İstek alındı ve kuyruğa atıldı.",
            "status": "QUEUED",
            "details": event_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kafka Hatası: {str(e)}")