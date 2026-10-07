"""Kanıt zenginleştirici kompozisyon noktası (`cache/factory.py` desenini izler)."""

from typing import Optional

from src.adapters.scrapers.article_text_fetcher import HttpArticleTextFetcher
from src.adapters.scrapers.caching_article_text_fetcher import CachingArticleTextFetcher
from src.application.services.evidence_enricher import EvidenceEnricher
from src.domain.ports.cache_port import CachePort
from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings


def build_evidence_enricher(cache: CachePort, embedder: EmbeddingPort) -> Optional[EvidenceEnricher]:
    if not settings.rag_fetch_enabled:
        return None
    fetcher = CachingArticleTextFetcher(
        HttpArticleTextFetcher(
            timeout_seconds=settings.rag_fetch_timeout_seconds,
            max_bytes=settings.rag_fetch_max_bytes,
        ),
        cache,
        ttl_seconds=settings.rag_fetch_cache_ttl_seconds,
        failure_ttl_seconds=settings.rag_fetch_failure_ttl_seconds,
    )
    return EvidenceEnricher(
        fetcher,
        embedder,
        top_n=settings.rag_fetch_top_n,
        passage_token_budget=settings.rag_passage_token_budget,
        total_timeout_seconds=settings.rag_fetch_total_timeout_seconds,
    )
