"""Embedding servisi — SentenceTransformer modelini TEK kopya yükleyen FastAPI app.

`app` ve `worker` container'ları modeli kendi süreçlerine yüklemek yerine bu
servise HTTP ile sorar (bkz. http_embedder.py). t3.small'da (1.9GB RAM) iki
ayrı kopya ~600MB israf ediyordu.

Çalıştırma: uvicorn src.adapters.search.embedder_service:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

MODEL_NAME = settings.embedder_model_name

_embedder: EmbeddingPort = None


def _get_embedder() -> EmbeddingPort:
    """Singleton — model süreç ömrü boyunca bir kez yüklenir.

    Import BİLİNÇLİ olarak fonksiyon içinde: modül seviyesinde olsaydı bu
    dosyayı import etmek (örneğin testte) sentence-transformers + torch'u da
    yükletirdi — tek başına ~10 saniye. Servisin kendisi zaten lifespan'de bu
    fonksiyonu çağırıyor, yani gerçek çalışmada hiçbir gecikme farkı yok.
    """
    global _embedder
    if _embedder is None:
        from src.adapters.search.sentence_transformer_embedder import (
            SentenceTransformerEmbedder,
        )
        logger.info("SentenceTransformer modeli yükleniyor: %s", MODEL_NAME)
        _embedder = SentenceTransformerEmbedder()
        logger.info("Model yüklendi.")
    return _embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Modeli açılışta yükle: ilk gerçek istek indirme/yükleme beklemesin ve
    # compose healthcheck'i model hazır olmadan "healthy" demesin.
    _get_embedder()
    yield


# docs kapalı: bu servis yalnızca iç ağdan erişilir, dışarı açılmaz.
app = FastAPI(title="NexStream Embedder", lifespan=lifespan, docs_url=None, redoc_url=None)


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class EmbedBatchRequest(BaseModel):
    # Üst sınır bilinçli: tek istekle sınırsız iş yüklenip servis (dolayısıyla
    # arama ve indeksleme) uzun süre bloklanamasın.
    texts: list[str] = Field(min_length=1, max_length=256)


@app.post("/embed")
def embed(req: EmbedRequest) -> dict:
    """Tek metni vektöre çevirir."""
    return {"vector": _get_embedder().embed_text(req.text)}


@app.post("/embed-batch")
def embed_batch(req: EmbedBatchRequest) -> dict:
    """Metin listesini toplu olarak vektöre çevirir."""
    return {"vectors": _get_embedder().embed_batch(req.texts)}


@app.get("/health")
def health() -> dict:
    """Model yüklüyse ok — compose healthcheck'i buna bakar."""
    _get_embedder()
    return {"status": "ok", "model": MODEL_NAME}
