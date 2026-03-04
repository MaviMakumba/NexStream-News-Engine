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