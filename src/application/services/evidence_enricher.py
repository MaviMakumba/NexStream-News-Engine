"""EvidenceEnricher — RAG kanıt paketindeki en iyi haberleri tam metinle zenginleştirir.

Retrieval/özel isim doğrulaması DEĞİŞMEZ: bu sınıf kanıt paketi oluştuktan SONRA çalışır ve
yalnızca her haberin LLM'e giden `content` alanını teaser yerine soruyla en alakalı pasajlarla
değiştirmek için bir sözlük döner. Her adım fail-open'dır: başarısız haber sözlükte yoktur,
çağıran eski `content[:500]` ile devam eder (spec 2026-10-07-rag-tam-metin-design.md).
"""

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Optional, Sequence

from src.domain.models.article import Article
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.embedding_port import EmbeddingPort
from src.domain.services.passage_selection import select_passages, split_paragraphs

logger = logging.getLogger(__name__)


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
    ):
        self._fetcher = fetcher
        self._embedder = embedder
        self._top_n = top_n
        self._budget = passage_token_budget
        self._total_timeout = total_timeout_seconds
        self._enabled = enabled

    def enrich(self, question: str, articles: Sequence[Article]) -> dict[int, str]:
        if not self._enabled:
            return {}
        targets = [a for a in articles[: self._top_n] if getattr(a, "url", None) and getattr(a, "id", None) is not None]
        if not targets:
            return {}
        pool = ThreadPoolExecutor(max_workers=len(targets))
        futures = {pool.submit(self._passages_for, question, a): a for a in targets}
        done, _ = wait(futures, timeout=self._total_timeout)
        # Bitmeyen thread'ler öldürülemez ama çekicinin kendi zaman aşımı onları sınırlar;
        # istek beklemeden döner.
        pool.shutdown(wait=False, cancel_futures=True)
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
