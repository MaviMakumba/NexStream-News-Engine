import asyncio
import logging
import time
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from prometheus_fastapi_instrumentator import Instrumentator

from src.infrastructure.config.database import engine, Base, SessionLocal
from src.infrastructure.config.settings import settings
from src.infrastructure.logging.logger import setup_logging
from src.adapters.api.limiter import limiter
from src.adapters.api.routers import news_router, health_router
from src.adapters.api.routers.websocket_router import router as ws_router
from src.adapters.api.routers.feed_router import router as feed_router
from src.adapters.api.routers.v1.news_router_v1 import router as v1_router
from src.adapters.api.routers.subscription_router import router as subscription_router
from src.adapters.api.routers.auth_router import router as auth_router
from src.adapters.api.routers.admin_router import router as admin_router
from src.adapters.api.routers.billing_router import router as billing_router
from src.adapters.messaging.kafka_publisher import KafkaPublisherAdapter
from src.adapters.notifications.websocket_notifier import WebSocketNotifier
from src.adapters.scheduling.newsletter_job import run_newsletter_job
from src.dependencies import set_message_publisher, get_search_repository, set_notifier

setup_logging()
log = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

kafka_adapter = KafkaPublisherAdapter(bootstrap_servers=settings.kafka_bootstrap_servers)


async def _broadcast_new_articles(notifier: WebSocketNotifier) -> None:
    """DB'yi 15sn'de bir sorgular, yeni haberleri WebSocket istemcilerine gönderir."""
    from src.adapters.repositories.news_repository import NewsRepository

    last_id = 0
    db = SessionLocal()
    try:
        articles = NewsRepository(db).get_latest_news(1)
        last_id = articles[0].id if articles else 0
    except Exception:
        pass
    finally:
        db.close()

    while True:
        try:
            await asyncio.sleep(15)
            if notifier.connection_count == 0:
                continue
            db = SessionLocal()
            try:
                repo = NewsRepository(db)
                new_articles = repo.get_articles_after_id(last_id)
                for article in new_articles:
                    await notifier.broadcast_article(article)
                    last_id = article.id
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Broadcast poller hatası: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_adapter.start()
    set_message_publisher(kafka_adapter)
    log.info("Message Publisher (Kafka) sisteme bağlandı.")

    log.info("SentenceTransformer modeli yükleniyor...")
    get_search_repository()
    log.info("SentenceTransformer modeli hazır.")

    notifier = WebSocketNotifier()
    set_notifier(notifier)
    broadcast_task = asyncio.create_task(_broadcast_new_articles(notifier))
    log.info("WebSocket broadcast poller başladı.")

    newsletter_task = asyncio.create_task(run_newsletter_job())
    log.info("Newsletter job başlatıldı.")

    yield

    broadcast_task.cancel()
    newsletter_task.cancel()
    for task in (broadcast_task, newsletter_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
    await kafka_adapter.stop()
    log.info("Servisler kapatıldı.")


app = FastAPI(
    title="NexStream News Engine API",
    description="Yapay Zeka Destekli Haber Motoru",
    version="1.8.0",
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
app.include_router(ws_router)
app.include_router(feed_router)
app.include_router(v1_router)
app.include_router(subscription_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(billing_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.middleware("http")
async def usage_tracking_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response_ms = (time.time() - start) * 1000
        token = request.headers.get("x-session-token")
        asyncio.create_task(
            _log_api_usage(token, str(request.url.path), request.method, response.status_code, response_ms)
        )
    return response


async def _log_api_usage(token, path, method, status_code, response_ms):
    from src.adapters.repositories.user_repository import UserRepository
    db = SessionLocal()
    try:
        user_id = None
        if token:
            repo = UserRepository(db)
            session = repo.get_session(token)
            if session:
                user_id = session.user_id
        repo = UserRepository(db)
        repo.log_usage(user_id, path, method, status_code, response_ms)
    except Exception as e:
        log.debug("Usage logging hatası: %s", e)
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "NexStream API v1.9.0 Çalışıyor!",
        "docs": "/docs",
        "v1_api": "/api/v1/news",
        "auth": "/auth/register",
        "billing": "/billing/checkout",
        "admin": "/admin/usage",
        "related": "/news/{id}/related",
        "rss_feed": "/feed.xml",
        "websocket": "/ws/feed",
        "subscriptions": "/subscriptions",
    }


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
