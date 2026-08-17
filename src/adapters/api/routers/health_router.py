"""Sağlık kontrolü (/health) — DB + Kafka + ChromaDB + embedder durumunu verir.

Docker healthcheck'leri ve frontend durum göstergesi bu endpoint'i kullanır.
Bir bileşen düşükse status "degraded" döner ama HTTP 200 kalır (yanıt
verebiliyor olmak, kısmi hizmetin sinyalidir).
"""

import logging
import socket
from typing import Optional
import httpx
from fastapi import APIRouter, Request
from sqlalchemy import text
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
from src.adapters.api.limiter import limiter
from src.adapters.notifications.email_adapter import get_email_adapter, SmtpEmailAdapter, ResendEmailAdapter
import chromadb

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])

# Module-level singleton — avoids creating a new HttpClient on every health check.
# Reset to None on exception so the next request retries the connection.
_chroma_client: Optional[chromadb.HttpClient] = None


def _get_chroma_client() -> chromadb.HttpClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return _chroma_client


def _check_db() -> str:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return "ok"
    except Exception as e:
        logger.error("DB health check hatası: %s", e)
        return "error"


def _check_kafka() -> str:
    try:
        s = socket.create_connection((settings.kafka_host, settings.kafka_port), timeout=2)
        s.close()
        return "ok"
    except Exception as e:
        logger.error("Kafka health check hatası: %s", e)
        return "error"


def _check_embedder() -> str:
    """Embedder servisinin /health'ini yoklar.

    Kısa timeout: /health endpoint'i her istekte gerçek bağlantı açtığı için
    yavaş bir bağımlılık tüm health kontrolünü bekletmemeli.
    """
    try:
        response = httpx.get(f"{settings.embedder_url.rstrip('/')}/health", timeout=2.0)
        return "ok" if response.status_code == 200 else "down"
    except Exception as e:
        logger.warning("Embedder health kontrolü başarısız: %s", e)
        return "down"


def _check_email() -> str:
    """Hangi e-posta adapter'ının aktif olduğunu raporlar — sessiz Console
    düşüşünün ve kimliksiz SMTP'nin artık /health'te tek bakışta görünür
    olması için (v2.1, Finding 3: EMAIL_PROVIDER=smtp seçilip SMTP_USER/
    SMTP_PASSWORD boş bırakılırsa adapter yine SMTP döner ama her gönderim
    sessizce başarısız olur — bunu da Console kadar açık işaretle)."""
    adapter = get_email_adapter()
    if isinstance(adapter, SmtpEmailAdapter):
        return "smtp" if adapter.is_configured() else "smtp (kimlik eksik)"
    if isinstance(adapter, ResendEmailAdapter):
        return "resend"
    return "console (mail gönderilmiyor)"


def _check_chromadb() -> tuple[str, int]:
    global _chroma_client
    try:
        client = _get_chroma_client()
        collection = client.get_or_create_collection("news_articles")
        return "ok", collection.count()
    except Exception as e:
        _chroma_client = None  # reset so next call retries
        logger.error("ChromaDB health check hatası: %s", e)
        return "error", 0


@router.get("/health")
# Kimliksiz ve ucuz görünen bu endpoint her istekte Postgres + Kafka + ChromaDB'ye
# GERÇEK bağlantı açıyor — güvenlik denetimi bunu bir amplifikasyon vektörü olarak
# işaretledi (tek istek 3 backend'e yük bindiriyor). Docker healthcheck'i 10-30sn'de
# bir çağırdığı için 60/dk bol bir tavan, flood'u ise kesiyor.
@limiter.limit("60/minute")
def health_check(request: Request):
    db_status              = _check_db()
    kafka_status           = _check_kafka()
    chroma_status, indexed = _check_chromadb()

    embedder_status        = _check_embedder()
    email_status            = _check_email()

    all_ok = all(s == "ok" for s in [db_status, kafka_status, chroma_status, embedder_status])

    return {
        "status":           "ok" if all_ok else "degraded",
        "db":               db_status,
        "kafka":            kafka_status,
        "chromadb":         chroma_status,
        "embedder":         embedder_status,
        "email":            email_status,
        "indexed_articles": indexed,
    }
