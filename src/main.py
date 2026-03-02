from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI

from src.infrastructure.config.database import engine, Base
from src.adapters.api.routers import news_router
from src.adapters.messaging.kafka_publisher import KafkaPublisherAdapter
from src.dependencies import set_message_publisher

# Tabloları oluştur
Base.metadata.create_all(bind=engine)

# Kafka Adaptörünü ayağa kaldırıyoruz (Sadece burada somut sınıf var)
kafka_adapter = KafkaPublisherAdapter(bootstrap_servers='kafka:29092')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI Yaşam Döngüsü: Uygulama açılırken ve kapanırken ne olacak?"""
    # 1. Başla
    await kafka_adapter.start()
    # 2. Dependency Container'a kaydet (Router kullanabilsin diye)
    set_message_publisher(kafka_adapter)
    print("✅ Message Publisher (Kafka) sisteme bağlandı.")
    
    yield # Uygulama çalışıyor...
    
    # 3. Kapanırken temizle
    await kafka_adapter.stop()
    print("🛑 Message Publisher bağlantısı kapatıldı.")

# FastAPI Uygulaması
app = FastAPI(
    title="NexStream News Engine API",
    description="Yapay Zeka Destekli Haber Motoru",
    version="1.0.0",
    lifespan=lifespan # Modern bağlama
)

app.include_router(news_router.router)

@app.get("/")
def root():
    return {"message": "NexStream API Çalışıyor! Haberler için /news adresine gidin."}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)