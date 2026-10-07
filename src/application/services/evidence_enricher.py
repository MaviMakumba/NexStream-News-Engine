"""EvidenceEnricher — RAG kanıt paketindeki en iyi haberleri tam metinle zenginleştirir.

Retrieval/özel isim doğrulaması DEĞİŞMEZ: bu sınıf kanıt paketi oluştuktan SONRA çalışır ve
yalnızca her haberin LLM'e giden `content` alanını teaser yerine soruyla en alakalı pasajlarla
değiştirmek için bir sözlük döner. Her adım fail-open'dır: başarısız haber sözlükte yoktur,
çağıran eski `content[:500]` ile devam eder (spec 2026-10-07-rag-tam-metin-design.md).
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Optional, Sequence

from src.domain.models.article import Article
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.embedding_port import EmbeddingPort
from src.domain.services.passage_selection import select_passages, split_paragraphs

logger = logging.getLogger(__name__)

_SHARED_MAX_WORKERS = 8
_shared_executor: Optional[ThreadPoolExecutor] = None
_shared_executor_lock = threading.Lock()


def _get_shared_executor() -> ThreadPoolExecutor:
    """Tüm sorular için TEK sınırlı havuz: takılan bir kaynak thread'i tutarken yeni sorular
    sınırsız thread açmaz, kuyruğa girer ve toplam süre dolunca iptal edilir (fail-open)."""
    global _shared_executor
    with _shared_executor_lock:
        if _shared_executor is None:
            _shared_executor = ThreadPoolExecutor(max_workers=_SHARED_MAX_WORKERS, thread_name_prefix="rag-fetch")
        return _shared_executor


class EvidenceEnricher:
    def __init__(
        self,
        fetcher: ArticleTextPort,
        embedder: EmbeddingPort,
        *,
        top_n: int,
        passage_token_budget: int,
        total_timeout_seconds: float,
        enabled: bool = True,
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        self._fetcher = fetcher
        self._embedder = embedder
        self._top_n = top_n
        self._budget = passage_token_budget
        self._total_timeout = total_timeout_seconds
        self._enabled = enabled
        self._executor = executor

    def enrich(self, question: str, articles: Sequence[Article]) -> dict[int, str]:
        if not self._enabled:
            return {}
        targets = [a for a in articles[: self._top_n] if getattr(a, "url", None) and getattr(a, "id", None) is not None]
        if not targets:
            return {}
        pool = self._executor or _get_shared_executor()
        futures = {pool.submit(self._passages_for, question, a): a for a in targets}
        done, pending = wait(futures, timeout=self._total_timeout)
        # Henüz BAŞLAMAMIŞ işler iptal edilir; çalışanlar öldürülemez ama havuz sınırlı olduğu için
        # birikemezler. İstek beklemeden döner.
        for future in pending:
            future.cancel()
        enriched: dict[int, str] = {}
        for future in done:
            try:
                passages = future.result()
            except Exception as e:
                logger.warning("Kanıt zenginleştirme başarısız (id=%s): %s", futures[future].id, e)
                continue
            if passages:
                enriched[futures[future].id] = passages
        return enriched

    def _passages_for(self, question: str, article: Article) -> Optional[str]:
        text = self._fetcher.fetch(article.url)
        if not text:
            return None
        paragraphs = split_paragraphs(text)
        if not paragraphs:
            return None
        vectors = self._embedder.embed_batch([question] + paragraphs)
        chosen = select_passages(paragraphs, vectors[0], vectors[1:], self._budget)
        return self._flatten(" ".join(chosen))

    @staticmethod
    def _flatten(text: str) -> str:
        """RAG prompt'u kanıtı `Content: "..."` biçiminde tırnaklı gömer; makale metni
        saldırgan kontrollü olabilir (HN keyfi sitelere link verir) → tırnak ve satır sonu
        bu biçimi bozup talimat enjekte edemesin."""
        return " ".join(text.replace('"', "'").split())
