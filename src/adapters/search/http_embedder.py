"""HTTP tabanlı embedding adapter'ı — modeli ayrı bir serviste tutar.

`app` ve `worker` container'ları torch/sentence-transformers KURMAZ; embedding
işini `embedder` servisine devrederler. Böylece model RAM'de tek kopya durur
(t3.small'da iki kopya ~600MB israftı — bkz.
docs/superpowers/specs/2026-07-28-t3-small-ram-optimizasyonu-design.md).

Hata halinde `EmbeddingServiceError` fırlatır. Çağıranlar
(`ChromaSearchRepository`) bunu zaten yakalayıp güvenli varsayılana düşüyor:
arama boş liste (hybrid_search keyword'e düşer), indeksleme False, dedup
"kopya değil". Yani servis düşse de uygulama çalışmaya devam eder.
"""

import logging

import httpx

from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Embedder servisine ulaşılamadı ya da geçersiz yanıt döndü."""


class HttpEmbedderAdapter(EmbeddingPort):
    """Embedding'i uzak `embedder` servisine HTTP ile devreden EmbeddingPort."""

    def __init__(
        self,
        base_url: str = None,
        connect_timeout: float = None,
        read_timeout: float = None,
        batch_read_timeout: float = None,
        retries: int = None,
    ):
        # Hepsinde `or` DEĞİL `is None` kontrolü: retries=0 ("hiç yeniden deneme")
        # geçerli bir istek ve `or` ile falsy olduğu için sessizce ayarlardaki
        # değere düşerdi.
        def _default(value, fallback):
            return fallback if value is None else value

        self._base_url = _default(base_url, settings.embedder_url).rstrip("/")
        self._connect_timeout = _default(connect_timeout, settings.embedder_connect_timeout)
        self._read_timeout = _default(read_timeout, settings.embedder_read_timeout)
        self._batch_read_timeout = _default(
            batch_read_timeout, settings.embedder_batch_read_timeout
        )
        self._retries = _default(retries, settings.embedder_retries)

    def embed_text(self, text: str) -> list[float]:
        """Tek metni vektöre çevirir."""
        return self._post("/embed", {"text": text}, self._read_timeout)["vector"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Metin listesini toplu olarak vektöre çevirir."""
        return self._post("/embed-batch", {"texts": texts}, self._batch_read_timeout)["vectors"]

    def _post(self, path: str, payload: dict, read_timeout: float) -> dict:
        """Retry'lı POST. Tüm denemeler tükenirse EmbeddingServiceError fırlatır."""
        timeout = httpx.Timeout(read_timeout, connect=self._connect_timeout)
        last_error = None
        for attempt in range(self._retries + 1):
            try:
                response = httpx.post(f"{self._base_url}{path}", json=payload, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                last_error = e
                logger.warning(
                    "Embedder isteği başarısız (deneme %d/%d): %s",
                    attempt + 1, self._retries + 1, e,
                )
        raise EmbeddingServiceError(f"Embedder servisi yanıt vermedi: {last_error}")
