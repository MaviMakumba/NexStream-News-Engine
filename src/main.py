from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from src.infrastructure.config.database import engine, Base
from src.infrastructure.config.settings import settings
from src.infrastructure.logging.logger import setup_logging
from src.adapters.api.limiter import limiter
from src.adapters.api.routers import news_router, health_router
from src.adapters.messaging.kafka_publisher import KafkaPublisherAdapter
from src.dependencies import set_message_publisher

setup_logging()

Base.metadata.create_all(bind=engine)

kafka_adapter = KafkaPublisherAdapter(bootstrap_servers=settings.kafka_bootstrap_servers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_adapter.start()
    set_message_publisher(kafka_adapter)
    import logging
    logging.getLogger(__name__).info("Message Publisher (Kafka) sisteme bağlandı.")
    yield
    await kafka_adapter.stop()
    logging.getLogger(__name__).info("Message Publisher bağlantısı kapatıldı.")


app = FastAPI(
    title="NexStream News Engine API",
    description="Yapay Zeka Destekli Haber Motoru",
    version="1.3.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router.router)
app.include_router(health_router.router)


@app.get("/")
def root():
    return {"message": "NexStream API Çalışıyor! Haberler için /news adresine gidin."}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
