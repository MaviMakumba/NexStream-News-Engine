"""HttpArticleTextFetcher — `ArticleTextPort`'un HTTP + HTML çıkarıcı implementasyonu.

Senkron (answer_question senkron bir FastAPI handler'ı; paralellik EvidenceEnricher'ın thread
havuzunda). Yönlendirmeler ELLE izlenir ki her atlamada SSRF kontrolü yapılabilsin.
"""

import logging
import time
from typing import Optional
from urllib.parse import urlsplit

import httpx

from src.adapters.api.metrics import article_fetch_seconds, article_fetch_total
from src.adapters.scrapers.article_extractor import extract_article_text
from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
from src.adapters.scrapers.url_safety import UnsafeUrlError, assert_public_http_url
from src.domain.ports.article_text_port import ArticleTextPort

logger = logging.getLogger(__name__)

_REFUSAL_STATUSES = {401, 403, 429}


class _SourceRefused(Exception):
    """Kaynak isteği bilerek reddetti (paywall/WAF/rate limit)."""


class HttpArticleTextFetcher(ArticleTextPort):
    _MAX_REDIRECTS = 3

    def __init__(
        self,
        timeout_seconds: float,
        max_bytes: int,
        min_chars: int = 200,
        transport: Optional[httpx.BaseTransport] = None,
        guard=assert_public_http_url,
        clock=time.monotonic,
    ):
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._min_chars = min_chars
        self._transport = transport
        self._guard = guard
        self._clock = clock

    def fetch(self, url: str) -> Optional[str]:
        started = self._clock()
        result = "failed"
        text: Optional[str] = None
        try:
            extracted = extract_article_text(self._download(url))
            if len(extracted) < self._min_chars:
                result = "too_short"
            else:
                result, text = "fetched", extracted
        except (UnsafeUrlError, _SourceRefused) as e:
            result = "blocked"
            logger.warning("Makale metni engellendi (%s): %s", urlsplit(url).hostname, e)
        except Exception as e:
            logger.warning("Makale metni çekilemedi (%s): %s", urlsplit(url).hostname, e)
        finally:
            article_fetch_total.labels(result=result).inc()
            article_fetch_seconds.observe(self._clock() - started)
        return text

    def _download(self, url: str) -> bytes:
        deadline = self._clock() + self._timeout
        # identity: sıkıştırılmış gövde max_bytes'ı atlatır (gzip bombası: 64 KB girdi -> ~67 MB çıktı).
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Encoding": "identity",
        }
        current = url
        with httpx.Client(
            transport=self._transport, timeout=self._timeout, headers=headers, follow_redirects=False
        ) as client:
            for _ in range(self._MAX_REDIRECTS + 1):
                # httpx zaman aşımları işlem başınadır, toplam değil: her atlamaya KALAN süre verilir.
                remaining = deadline - self._clock()
                if remaining <= 0:
                    raise TimeoutError("toplam süre doldu")
                self._guard(current)
                with client.stream("GET", current, timeout=remaining) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("yönlendirme hedefi yok")
                        current = str(httpx.URL(current).join(location))
                        continue
                    if response.status_code in _REFUSAL_STATUSES:
                        raise _SourceRefused(f"HTTP {response.status_code}")
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "html" not in content_type:
                        raise ValueError(f"beklenmeyen içerik türü: {content_type!r}")
                    encoding = response.headers.get("content-encoding", "identity").strip().lower()
                    if encoding not in ("", "identity"):
                        raise ValueError(f"sıkıştırılmış gövde reddedildi: {encoding!r}")
                    return self._read_capped(response, deadline)
        raise ValueError("çok fazla yönlendirme")

    def _read_capped(self, response: httpx.Response, deadline: float) -> bytes:
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            total += len(chunk)
            if total >= self._max_bytes or self._clock() > deadline:
                break
        return b"".join(chunks)[: self._max_bytes]
