"""FastAPI uygulama girişi — composition root.

Sorumlulukları:
    * Router'ları toplar (haber, auth, hesap, admin, billing, feed, ws, v1)
    * Lifespan içinde uzun ömürlü kaynakları açar/kapatır:
      Kafka publisher, SentenceTransformer ön-yükleme, WebSocket broadcast
      poller'ı ve günlük newsletter job'ı
    * CORS, rate-limit handler, Prometheus /metrics ve /api/v1 kullanım
      takibi middleware'ini bağlar

İş kuralı içermez — orkestrasyon NewsService'te, veri erişimi adapter'lardadır.
"""

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
from src.infrastructure.observability.sentry import init_sentry
from src.adapters.api.limiter import limiter
from src.adapters.api.routers import news_router, health_router
from src.adapters.api.routers.websocket_router import router as ws_router
from src.adapters.api.routers.feed_router import router as feed_router
from src.adapters.api.routers.v1.news_router_v1 import router as v1_router
from src.adapters.api.routers.subscription_router import router as subscription_router
from src.adapters.api.routers.auth_router import router as auth_router
from src.adapters.api.routers.account_router import router as account_router
from src.adapters.api.routers.admin_router import router as admin_router
from src.adapters.api.routers.billing_router import router as billing_router
from src.adapters.api.routers.market_router import router as market_router
from src.adapters.messaging.kafka_publisher import KafkaPublisherAdapter
from src.adapters.notifications.websocket_notifier import WebSocketNotifier
from src.adapters.notifications.email_adapter import get_email_adapter, ConsoleEmailAdapter, SmtpEmailAdapter
from src.adapters.scheduling.newsletter_job import run_newsletter_job
from src.adapters.scheduling.retention_job import run_retention_job
from src.dependencies import set_message_publisher, get_search_repository, set_notifier

setup_logging()
init_sentry("app")
log = logging.getLogger(__name__)

# Dev ortamında tabloları otomatik oluşturur; prod'da migrations/ script'leri esastır.
Base.metadata.create_all(bind=engine)

kafka_adapter = KafkaPublisherAdapter(bootstrap_servers=settings.kafka_bootstrap_servers)


def warn_if_email_disabled(environment: str, adapter) -> None:
    """Prod'da e-posta adapter'ı Console'a düşerse (veya SMTP kimliksiz kalırsa) sessiz kalmaz.

    Kök nedeni bulunan sorun: RESEND_API_KEY boş bırakılınca get_email_adapter()
    sessizce ConsoleEmailAdapter'a düşüyordu ve hiçbir yerde iz kalmıyordu —
    doğrulama, şifre sıfırlama, digest, keyword alert'lerin TAMAMI etkileniyordu.
    Aynı sessiz-işlevsizlik deseni EMAIL_PROVIDER=smtp açıkça seçilip
    SMTP_USER/SMTP_PASSWORD boş bırakıldığında da yaşanıyordu: get_email_adapter()
    yine bir SmtpEmailAdapter döner (bilinçli, get_email_adapter'a bak) ama her
    gönderim _deliver()'ın kendi except'inde sessizce başarısız olur (Finding 3).
    Uygulama durdurulmaz (mail altyapısı çökünce site de çökmemeli, mevcut
    fail-open felsefesiyle tutarlı) — sadece net bir hata logu bırakılır.
    """
    if environment != "production":
        return
    if isinstance(adapter, ConsoleEmailAdapter):
        log.error(
            "E-posta adapter'ı Console'a düştü — production'da HİÇBİR mail gönderilmiyor "
            "(SMTP_USER/SMTP_PASSWORD veya RESEND_API_KEY eksik/hatalı)."
        )
    elif isinstance(adapter, SmtpEmailAdapter) and not adapter.is_configured():
        log.error(
            "E-posta adapter'ı SMTP ama kimlik bilgileri eksik — production'da HİÇBİR mail "
            "gönderilmiyor (SMTP_USER/SMTP_PASSWORD boş)."
        )


warn_if_email_disabled(settings.environment, get_email_adapter())


async def _broadcast_new_articles(notifier: WebSocketNotifier) -> None:
    """DB'yi 15sn'de bir sorgular, yeni haberleri WebSocket istemcilerine gönderir.

    Bağlı istemci yoksa sorgu atlanır (boşuna DB yükü oluşturmaz).
    """
    from src.adapters.repositories.news_repository import NewsRepository

    # Başlangıç noktası: mevcut en yeni haber — eski kayıtlar tekrar yayınlanmaz.
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
    """Uygulama ömrü: kaynakları sırayla aç, kapanışta ters sırayla temizle."""
    await kafka_adapter.start()
    set_message_publisher(kafka_adapter)
    log.info("Message Publisher (Kafka) sisteme bağlandı.")

    # Arama deposu startup'ta ısıtılır: ChromaDB bağlantısı + koleksiyon handle'ı
    # ilk istekte kurulmasın. Model ARTIK BURADA YÜKLENMİYOR — ayrı `embedder`
    # servisinde tek kopya duruyor (v2.0 RAM optimizasyonu), bu çağrı sadece
    # HttpEmbedderAdapter kuruyor ve saniyeler değil milisaniyeler sürüyor.
    log.info("Arama deposu hazırlanıyor (ChromaDB bağlantısı)...")
    get_search_repository()
    log.info("Arama deposu hazır.")

    notifier = WebSocketNotifier(
        max_per_user=settings.ws_max_connections_per_user,
        max_total=settings.ws_max_total_connections,
    )
    set_notifier(notifier)
    broadcast_task = asyncio.create_task(_broadcast_new_articles(notifier))
    log.info("WebSocket broadcast poller başladı.")

    newsletter_task = asyncio.create_task(run_newsletter_job())
    log.info("Newsletter job başlatıldı.")

    retention_task = asyncio.create_task(run_retention_job())
    log.info("Retention job başlatıldı.")

    yield

    broadcast_task.cancel()
    newsletter_task.cancel()
    retention_task.cancel()
    for task in (broadcast_task, newsletter_task, retention_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
    await kafka_adapter.stop()
    log.info("Servisler kapatıldı.")


app = FastAPI(
    title="NexStream News Engine API",
    description="""
Türkiye ve dünya haberlerini toplayıp yapay zeka ile analiz eden (duygu +
varlık çıkarımı + konu sınıflandırma + özet), semantik + anahtar kelime
aramasıyla sunan bir haber motoru API'si.

**Başlarken:**
- Kimlik doğrulaması gerektirmeyen uçlar (`/news/search`, `/news/trending`, `/feed.xml`) doğrudan denenebilir.
- Sürümlü, kotalı public API için `/api/v1/*` uçlarını kullanın — `X-User-Key` header'ı ile (bkz. `/account/api-key`) ya da oturum çerezinizle kimlik doğrulanır.
- Tier'a göre kota ve özellik erişimi değişir — detay için `/billing/config` ve README'deki "API Tiers" tablosuna bakın.

**Kaynaklar:** [GitHub](https://github.com/MaviMakumba/NexStream-News-Engine) ·
[Canlı site](https://nexstreamnewsengine.duckdns.org) ·
[Postman koleksiyonu](https://github.com/MaviMakumba/NexStream-News-Engine/blob/main/docs/NexStream.postman_collection.json)
""",
    version="2.1.1",
    contact={
        "name": "MaviMakumba",
        "url": "https://github.com/MaviMakumba/NexStream-News-Engine",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/MaviMakumba/NexStream-News-Engine/blob/main/LICENSE",
    },
    openapi_tags=[
        {"name": "News", "description": "Haber listesi, arama (hibrit: semantik + anahtar kelime), gündem/trend, ilişkili haberler, kaynak yönetimi. Çoğu uç kimlik doğrulaması gerektirmez, rate-limit ile korunur."},
        {"name": "API v1", "description": "Sürümlü, kotalı public API — cursor tabanlı sayfalama, `X-RateLimit-*` header'ları, tier'a göre kota (bkz. README \"API Tiers\")."},
        {"name": "Auth", "description": "Kayıt, giriş/çıkış, e-posta doğrulama, şifre sıfırlama. Kimlik HttpOnly `nxs_session` çerezi ile taşınır."},
        {"name": "Account", "description": "Kendi kullanım istatistikleriniz + kişisel API key üretimi/iptali (`X-User-Key`)."},
        {"name": "Admin", "description": "Kullanıcı/kullanım/sponsor yönetimi — moderatör/admin/owner rolü gerektirir."},
        {"name": "Billing", "description": "Stripe tabanlı abonelik yönetimi (dev modda Stripe'sız simülasyon destekler)."},
        {"name": "Subscriptions", "description": "E-posta bülteni + anlık anahtar-kelime uyarıları için abonelik yönetimi."},
        {"name": "Feed", "description": "RSS/Atom 2.0 haber akışı (`/feed.xml`) — duygu ve konu etiketleriyle zenginleştirilmiş."},
        {"name": "WebSocket", "description": "`/ws/feed` ile canlı haber akışı (Pro+ tier gerektirir)."},
        {"name": "Health", "description": "Servis durumu — veritabanı, mesaj kuyruğu, vektör arama, embedder, e-posta adaptörü."},
    ],
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
app.include_router(account_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(market_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.middleware("http")
async def usage_tracking_middleware(request: Request, call_next):
    """/api/v1 isteklerini kota ve istatistik için asenkron loglar.

    Yanıtı bekletmemek için kayıt background task'ta yapılır; logging hatası
    isteği asla etkilemez.
    """
    start = time.time()
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response_ms = (time.time() - start) * 1000
        session_token = request.headers.get("x-session-token")
        user_key = request.headers.get("x-user-key")
        asyncio.create_task(
            _log_api_usage(session_token, user_key, str(request.url.path),
                           request.method, response.status_code, response_ms)
        )
    return response


async def _log_api_usage(session_token, user_key, path, method, status_code, response_ms):
    """Kullanım kaydını yazar; kimlik session token VEYA kullanıcı API anahtarından çözülür."""
    from src.adapters.repositories.user_repository import UserRepository
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user_id = None
        if session_token:
            session = repo.get_session(session_token)
            user_id = session.user_id if session else None
        if user_id is None and user_key:
            user = repo.get_by_api_key(user_key)
            user_id = user.id if user else None
        repo.log_usage(user_id, path, method, status_code, response_ms)
    except Exception as e:
        log.debug("Usage logging hatası: %s", e)
    finally:
        db.close()


@app.get("/")
def root():
    """Hızlı keşif için ana endpoint haritası."""
    return {
        "message": "NexStream API v1.11.0 Çalışıyor!",
        "docs": "/docs",
        "v1_api": "/api/v1/news",
        "auth": "/auth/register",
        "account": "/account/usage",
        "billing": "/billing/checkout",
        "admin": "/admin/usage",
        "related": "/news/{id}/related",
        "rss_feed": "/feed.xml",
        "websocket": "/ws/feed",
        "subscriptions": "/subscriptions",
    }


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
