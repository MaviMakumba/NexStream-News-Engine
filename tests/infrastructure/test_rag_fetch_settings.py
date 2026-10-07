from src.infrastructure.config.settings import Settings


def test_rag_fetch_defaults_match_spec():
    s = Settings()
    assert s.rag_fetch_enabled is True
    assert s.rag_fetch_top_n == 2
    assert s.rag_passage_token_budget == 450
    assert s.rag_fetch_timeout_seconds == 4.0
    assert s.rag_fetch_total_timeout_seconds == 6.0
    assert s.rag_fetch_cache_ttl_seconds == 3600
    assert s.rag_fetch_failure_ttl_seconds == 300
    assert s.rag_fetch_max_bytes == 1_500_000


def test_article_fetch_metrics_are_registered_with_fixed_labels():
    from src.adapters.api.metrics import article_fetch_total, article_fetch_seconds
    for result in ("hit", "fetched", "failed", "blocked", "too_short"):
        article_fetch_total.labels(result=result).inc(0)
    assert article_fetch_seconds is not None


def test_rss_scraper_and_fetcher_share_one_user_agent():
    from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
    from src.adapters.scrapers.rss_scrapers import BaseRssScraper
    assert BaseRssScraper._USER_AGENT == BROWSER_USER_AGENT
    assert BROWSER_USER_AGENT.startswith("Mozilla/5.0 (") and "Chrome/" in BROWSER_USER_AGENT
