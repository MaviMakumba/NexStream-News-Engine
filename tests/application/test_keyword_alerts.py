import pytest
from unittest.mock import MagicMock, patch
from src.application.services.news_service import NewsService
from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber


def _article(title="Beşiktaş galip geldi", summary="Beşiktaş, Fenerbahçe'yi 2-1 yendi."):
    a = Article(title=title, source="TRT", url="http://test.com/1", content="içerik " + title)
    a.summary = summary
    a.sentiment_label = "Positive"
    a.id = 1
    return a


def _instant_subscriber(keywords):
    return Subscriber(
        id=1, email="fan@test.com",
        keywords=keywords, frequency="instant", language="TR", is_active=True
    )


def _make_service(subscribers=None, email_ok=True):
    mock_repo = MagicMock()
    mock_analyzer = MagicMock()
    mock_sub_repo = MagicMock()
    mock_sub_repo.get_active_subscribers.return_value = subscribers or []
    mock_email = MagicMock()
    mock_email.send_alert.return_value = email_ok
    return (
        NewsService(
            repository=mock_repo,
            analyzer=mock_analyzer,
            subscriber_repository=mock_sub_repo,
            email_port=mock_email,
        ),
        mock_email,
        mock_sub_repo,
    )


def test_keyword_alert_sent_when_keyword_in_title():
    sub = _instant_subscriber(["beşiktaş"])
    service, mock_email, _ = _make_service([sub])
    service._send_keyword_alerts(_article("Beşiktaş şampiyon oldu"))
    mock_email.send_alert.assert_called_once()
    call_args = mock_email.send_alert.call_args
    assert call_args[0][0] == "fan@test.com"
    assert call_args[0][2] == "beşiktaş"


def test_keyword_alert_not_sent_for_daily_subscriber():
    sub = Subscriber(id=2, email="d@test.com", keywords=["beşiktaş"], frequency="daily", language="TR", is_active=True)
    service, mock_email, _ = _make_service([sub])
    service._send_keyword_alerts(_article("Beşiktaş şampiyon"))
    mock_email.send_alert.assert_not_called()


def test_keyword_alert_not_sent_when_no_match():
    sub = _instant_subscriber(["galatasaray"])
    service, mock_email, _ = _make_service([sub])
    service._send_keyword_alerts(_article("Fenerbahçe galibi"))
    mock_email.send_alert.assert_not_called()


def test_keyword_alert_only_one_per_article_per_subscriber():
    sub = _instant_subscriber(["beşiktaş", "galip"])  # two keywords both match
    service, mock_email, _ = _make_service([sub])
    service._send_keyword_alerts(_article("Beşiktaş galip geldi"))
    assert mock_email.send_alert.call_count == 1  # not called twice


def test_no_alert_when_subscriber_repository_is_none():
    service = NewsService(repository=MagicMock(), analyzer=MagicMock())
    article = _article()
    # Should not raise even without subscriber_repository
    service._send_keyword_alerts(article)


def test_alert_checked_in_update_news_flow():
    mock_repo = MagicMock()
    mock_repo.bulk_exists.return_value = set()
    mock_repo.save_article.return_value = True

    mock_analyzer = MagicMock()
    mock_analyzer.analyze_text.return_value = {
        "sentiment_score": 0.5, "sentiment_label": "Positive",
        "summary": "özet", "entities": {}, "topic": "Sports",
    }

    sub = _instant_subscriber(["beşiktaş"])
    mock_sub_repo = MagicMock()
    mock_sub_repo.get_active_subscribers.return_value = [sub]
    mock_email = MagicMock()
    mock_email.send_alert.return_value = True

    mock_scraper = MagicMock()
    article = _article()
    article.id = None

    import asyncio
    from unittest.mock import AsyncMock

    async def _fetch():
        return [article]

    mock_scraper.fetch_news = _fetch

    analyze_result = {
        "sentiment_score": 0.5, "sentiment_label": "Positive",
        "summary": "özet", "entities": {}, "topic": "Sports",
    }

    async def run():
        service = NewsService(
            repository=mock_repo,
            analyzer=mock_analyzer,
            subscriber_repository=mock_sub_repo,
            email_port=mock_email,
        )
        with patch("src.application.services.news_service.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=analyze_result)
            await service.update_news_from_source(mock_scraper)

    asyncio.run(run())
    mock_sub_repo.get_active_subscribers.assert_called()
