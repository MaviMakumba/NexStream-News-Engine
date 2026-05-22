from unittest.mock import MagicMock
from src.application.services.news_service import NewsService
from src.domain.models.article import Article

def make_article(url="https://bbc.com/test"):
    return Article(title="Test", source="BBC", url=url, content="Good news today")

def make_service():
    mock_repo = MagicMock()
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_text.return_value = {
        "sentiment_score": 0.8,
        "sentiment_label": "Positive",
        "summary": "Good news today"
    }
    return NewsService(repository=mock_repo, analyzer=mock_analyzer), mock_repo, mock_analyzer

def test_update_saves_analyzed_article():
    """Haber analiz edilip kaydediliyor mu?"""
    service, mock_repo, mock_analyzer = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news.return_value = [make_article()]
    mock_repo.save_article.return_value = True

    service.update_news_from_source(mock_scraper)

    mock_analyzer.analyze_text.assert_called_once_with("Good news today")
    mock_repo.save_article.assert_called_once()
    saved = mock_repo.save_article.call_args[0][0]
    assert saved.sentiment_label == "Positive"
    assert saved.sentiment_score == 0.8
    assert saved.summary == "Good news today"

def test_update_multiple_articles():
    """Birden fazla haber kaydediliyor mu?"""
    service, mock_repo, _ = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news.return_value = [
        make_article("https://bbc.com/1"),
        make_article("https://bbc.com/2"),
        make_article("https://bbc.com/3"),
    ]
    mock_repo.save_article.return_value = True

    service.update_news_from_source(mock_scraper)

    assert mock_repo.save_article.call_count == 3

def test_update_empty_source():
    """Scraper boş liste dönerse hata vermemeli"""
    service, mock_repo, mock_analyzer = make_service()
    mock_scraper = MagicMock()
    mock_scraper.fetch_news.return_value = []

    service.update_news_from_source(mock_scraper)

    mock_analyzer.analyze_text.assert_not_called()
    mock_repo.save_article.assert_not_called()

def test_list_news_passes_filters():
    """list_news filteleri repository'ye iletiyor mu?"""
    service, mock_repo, _ = make_service()
    mock_repo.get_latest_news.return_value = []

    service.list_news(limit=5, sentiment="Positive")

    mock_repo.get_latest_news.assert_called_once_with(5, "Positive")


# ── hybrid_search ─────────────────────────────────────────────────────────────

def make_service_with_search():
    service, mock_repo, mock_analyzer = make_service()
    mock_search = MagicMock()
    service.search_repository = mock_search
    return service, mock_repo, mock_search


def test_hybrid_search_returns_semantic_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Semantic Haber", "summary": "s", "source": "BBC", "url": "u", "score": 0.9}
    ]
    mock_repo.keyword_search.return_value = []

    results = service.hybrid_search("yapay zeka", n_results=5)

    assert len(results) == 1
    assert results[0]["score"] == 0.9
    mock_search.search.assert_called_once_with("yapay zeka", 5, None, None)


def test_hybrid_search_merges_keyword_only_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Semantic", "summary": "", "source": "BBC", "url": "u1", "score": 0.5}
    ]
    keyword_article = make_article("https://bbc.com/keyword")
    keyword_article.id = 2
    keyword_article.title = "Keyword haberi özeli"
    keyword_article.summary = "keyword özeti"
    mock_repo.keyword_search.return_value = [keyword_article]

    results = service.hybrid_search("keyword")

    result_ids = {r["id"] for r in results}
    assert len(results) == 2
    assert "1" in result_ids
    assert "2" in result_ids
    # "keyword" başlıkta geçiyor → skor 0.90 > semantic 0.50 → keyword result önde
    assert results[0]["id"] == "2"
    assert results[0]["score"] == 0.90


def test_hybrid_search_deduplicates_overlapping_results():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Ortak Haber", "summary": "", "source": "BBC", "url": "u", "score": 0.7}
    ]
    overlap_article = make_article()
    overlap_article.id = 1
    mock_repo.keyword_search.return_value = [overlap_article]

    results = service.hybrid_search("test")

    assert len(results) == 1


def test_hybrid_search_falls_back_to_keyword_when_no_search_repo():
    service, mock_repo, _ = make_service()
    service.search_repository = None
    keyword_article = make_article()
    keyword_article.id = 5
    keyword_article.title = "Fallback haberi burada"
    mock_repo.keyword_search.return_value = [keyword_article]

    results = service.hybrid_search("fallback")

    assert len(results) == 1
    assert results[0]["id"] == "5"
    assert results[0]["score"] == 0.90  # "fallback" başlıkta → 0.90


def test_hybrid_search_boosts_result_found_in_both():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Real Madrid haberi", "summary": "", "source": "BBC", "url": "u", "score": 0.6}
    ]
    boosted_article = make_article()
    boosted_article.id = 1
    mock_repo.keyword_search.return_value = [boosted_article]

    results = service.hybrid_search("real madrid")

    assert results[0]["id"] == "1"
    assert results[0]["score"] == round(0.6 + 0.15, 4)


def test_hybrid_search_keyword_only_ranks_above_low_semantic():
    """Başlık eşleşmesi (0.90) düşük semantik skorun önüne geçmeli."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "99", "title": "Alakasız haber", "summary": "", "source": "X", "url": "u", "score": 0.3}
    ]
    exact_article = make_article("https://bbc.com/real-madrid")
    exact_article.id = 7
    exact_article.title = "Real Madrid yıldızla yollarını ayırdı"
    mock_repo.keyword_search.return_value = [exact_article]

    results = service.hybrid_search("real madrid", n_results=2)

    assert results[0]["id"] == "7"   # başlık eşleşmesi (0.90) önde
    assert results[0]["score"] == 0.90
    assert results[1]["id"] == "99"  # düşük semantic (0.30) arkada


def test_hybrid_search_passes_filters_to_both():
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = []
    mock_repo.keyword_search.return_value = []

    service.hybrid_search("filtreli", n_results=3, source="TRT Haber", sentiment="Positive")

    mock_search.search.assert_called_once_with("filtreli", 3, "TRT Haber", "Positive")
    mock_repo.keyword_search.assert_called_once_with("filtreli", 3, "TRT Haber", "Positive")