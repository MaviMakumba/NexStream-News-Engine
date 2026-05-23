import os
import socket
from fastapi import APIRouter
from sqlalchemy import text
from src.infrastructure.config.database import SessionLocal
import chromadb

router = APIRouter(tags=["Health"])

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
KAFKA_HOST  = os.getenv("KAFKA_HOST", "kafka")
KAFKA_PORT  = int(os.getenv("KAFKA_PORT", "29092"))


def _check_db() -> str:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return "ok"
    except Exception:
        return "error"


def _check_kafka() -> str:
    try:
        s = socket.create_connection((KAFKA_HOST, KAFKA_PORT), timeout=2)
        s.close()
        return "ok"
    except Exception:
        return "error"


def _check_chromadb() -> tuple[str, int]:
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection("news_articles")
        return "ok", collection.count()
    except Exception:
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
