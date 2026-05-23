import logging
import socket
from fastapi import APIRouter
from sqlalchemy import text
from src.infrastructure.config.database import SessionLocal
from src.infrastructure.config.settings import settings
import chromadb

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


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


def _check_chromadb() -> tuple[str, int]:
    try:
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        collection = client.get_or_create_collection("news_articles")
        return "ok", collection.count()
    except Exception as e:
        logger.error("ChromaDB health check hatası: %s", e)
        return "error", 0


@router.get("/health")
def health_check():
    db_status             = _check_db()
    kafka_status          = _check_kafka()
    chroma_status, indexed = _check_chromadb()

    all_ok = all(s == "ok" for s in [db_status, kafka_status, chroma_status])

    return {
        "status":           "ok" if all_ok else "degraded",
        "db":               db_status,
        "kafka":            kafka_status,
        "chromadb":         chroma_status,
        "indexed_articles": indexed,
    }
