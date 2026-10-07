from unittest.mock import MagicMock, patch

from src.adapters.scrapers.article_text_factory import build_evidence_enricher
from src.adapters.scrapers.caching_article_text_fetcher import CachingArticleTextFetcher
from src.application.services.evidence_enricher import EvidenceEnricher


def test_disabled_setting_returns_none():
    with patch("src.adapters.scrapers.article_text_factory.settings") as s:
        s.rag_fetch_enabled = False
        assert build_evidence_enricher(MagicMock(), MagicMock()) is None


def test_enabled_builds_enricher_with_caching_fetcher_from_settings():
    cache, embedder = MagicMock(), MagicMock()
    enricher = build_evidence_enricher(cache, embedder)
    assert isinstance(enricher, EvidenceEnricher)
    assert isinstance(enricher._fetcher, CachingArticleTextFetcher)
    assert enricher._embedder is embedder
    assert enricher._top_n == 2 and enricher._budget == 450 and enricher._total_timeout == 6.0
